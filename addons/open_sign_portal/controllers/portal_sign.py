# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import logging
import re
from types import SimpleNamespace
from uuid import UUID

from psycopg2.errors import LockNotAvailable

from odoo import _, fields, http
from odoo.addons.open_sign.services import notification_service, validation_service
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.open_sign_portal.services import idempotency_service, otp_service, token_security_service
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request
from odoo.tools import consteq


UUID_RE = re.compile(r'^[0-9a-fA-F-]{36}$')
TERMINAL_REQUEST_STATUSES = {'completed', 'cancelled', 'voided', 'declined', 'expired'}
TEXTUAL_FIELD_TYPES = {'initials', 'name', 'email', 'phone', 'company', 'text', 'multiline', 'radio', 'selection'}
SUPPORTED_PORTAL_FIELD_TYPES = TEXTUAL_FIELD_TYPES | {'checkbox', 'date', 'strikethrough'}
UNSUPPORTED_CAPTURE_TYPES = {'signature', 'stamp'}
SIGNER_MUTATION_REQUEST_STATUSES = {'sent', 'opened', 'in_progress', 'partially_signed'}
SIGNER_REVIEW_REQUEST_STATUSES = SIGNER_MUTATION_REQUEST_STATUSES | {'completed', 'declined', 'expired'}
PREVIEW_REQUEST_STATUSES = SIGNER_REVIEW_REQUEST_STATUSES | {'versioned'}
SIGNER_MUTABLE_STATES = {'pending', 'opened'}
READONLY_SIGNER_STATES = {'signed', 'declined', 'expired'}
READONLY_REQUEST_STATUSES = {'completed', 'declined', 'expired'}
STALE_REVISION_MARKER = 'STALE_REVISION'
SIGNING_ORDER_BLOCKED_MARKER = 'SIGNING_ORDER_BLOCKED'
CONSENT_REQUIRED_MARKER = 'CONSENT_REQUIRED'
CONTRACT_UNAVAILABLE_MARKER = 'CONTRACT_UNAVAILABLE'
IDEMPOTENCY_CONFLICT_MARKER = 'IDEMPOTENCY_CONFLICT'
EXPIRED_TOKEN_MARKER = 'EXPIRED_TOKEN'
OTP_REQUIRED_MARKER = 'OTP_REQUIRED'
OTP_INVALID_MARKER = 'OTP_INVALID'
OTP_EXPIRED_MARKER = 'OTP_EXPIRED'
OTP_ATTEMPTS_EXCEEDED_MARKER = 'OTP_ATTEMPTS_EXCEEDED'
OTP_REQUEST_COOLDOWN_MARKER = 'OTP_REQUEST_COOLDOWN'
DECLINE_REASON_MAX_LENGTH = 4000

_logger = logging.getLogger(__name__)


class OpenSignPortalController(CustomerPortal):

    def _resolve_access_token(self, access_token, payload=None):
        payload = payload or {}
        return access_token or payload.get('access_token') or request.httprequest.args.get('access_token')

    def _get_signer_sudo(self, signer_id):
        signer_sudo = request.env['open.sign.request.signer'].sudo().browse(signer_id).exists()
        if not signer_sudo or not signer_sudo.request_id.active:
            raise MissingError(_("This signing request is no longer available."))
        return signer_sudo

    def _require_internal_user(self):
        user = request.env.user
        if user._is_public() or user.share:
            raise AccessError(_("This page is only available to internal users."))
        return user

    def _token_matches_signer(self, signer_sudo, access_token):
        return bool(access_token and signer_sudo.access_token and consteq(signer_sudo.access_token, access_token))

    @staticmethod
    def _build_auth_context(
        signer_sudo,
        *,
        auth_mode,
        effective_access_token=False,
        token_state=False,
        token_audit_identity=False,
    ):
        return SimpleNamespace(
            signer=signer_sudo,
            auth_mode=auth_mode,
            effective_access_token=effective_access_token or False,
            token_state=token_state or False,
            token_audit_identity=token_audit_identity or False,
        )

    def _get_client_ip(self):
        return token_security_service.normalize_client_ip(request.env, self._extract_request_ip())

    @staticmethod
    def _is_partner_linked_signer(signer_sudo):
        return bool(signer_sudo.partner_id)

    def _record_invalid_token_attempt(self, signer_sudo, client_ip, *, force_isolated=False):
        if not client_ip:
            return False
        try:
            return token_security_service.record_invalid_token_attempt(
                signer_sudo,
                client_ip,
                force_isolated=force_isolated,
            )
        except Exception:  # pragma: no cover - defensive logging around abuse-control state
            _logger.exception("Failed to record invalid portal token attempt for signer %s", signer_sudo.id)
            return False

    def _clear_invalid_token_attempts(self, signer_sudo, client_ip, *, force_isolated=False):
        if not client_ip:
            return 0
        try:
            return token_security_service.clear_invalid_token_attempts(
                signer_sudo,
                client_ip,
                force_isolated=force_isolated,
            )
        except Exception:  # pragma: no cover - defensive logging around abuse-control state
            _logger.exception("Failed to clear invalid portal token attempts for signer %s", signer_sudo.id)
            return 0

    def _capture_token_audit_identity(self, signer_sudo, access_token, *, token_state):
        if token_state not in {'valid', 'expired', 'revoked'}:
            return False
        if not self._token_matches_signer(signer_sudo, access_token):
            return False
        return signer_sudo._get_current_email_token_audit_identity()

    def _append_token_opened_from_auth_context(self, auth_context, *, entrypoint):
        if auth_context.auth_mode != 'token' or not auth_context.token_audit_identity:
            return False
        return auth_context.signer._append_token_opened_if_needed(
            entrypoint=entrypoint,
            token_identity=auth_context.token_audit_identity,
            event_at=fields.Datetime.now(),
            ip=self._extract_request_ip(),
            user_agent=self._extract_user_agent(),
            force_isolated=(entrypoint == 'document'),
        )

    def _append_token_rejected_from_snapshot(
        self,
        signer_sudo,
        *,
        entrypoint,
        token_state,
        rejection_code,
        token_audit_identity,
    ):
        if not token_audit_identity:
            return False
        return signer_sudo._append_token_rejected_if_needed(
            entrypoint=entrypoint,
            token_state=token_state,
            rejection_code=rejection_code,
            token_identity=token_audit_identity,
            event_at=fields.Datetime.now(),
            ip=self._extract_request_ip(),
            user_agent=self._extract_user_agent(),
        )

    def _check_signer_external_token_access(
        self,
        signer_sudo,
        access_token,
        *,
        token_state=False,
        token_audit_identity=False,
    ):
        token_state = token_state or signer_sudo._classify_current_email_token_access(access_token)
        client_ip = self._get_client_ip()
        if token_state == 'valid':
            if client_ip:
                self._clear_invalid_token_attempts(
                    signer_sudo,
                    client_ip,
                    force_isolated=bool(request.env.cr.readonly),
                )
            return self._build_auth_context(
                signer_sudo,
                auth_mode='token',
                effective_access_token=access_token,
                token_state=token_state,
                token_audit_identity=token_audit_identity,
            )
        if token_state == 'expired':
            raise AccessError(
                f"{EXPIRED_TOKEN_MARKER}::" + _("This signing link has expired. Request a new link.")
            )
        if not self._token_matches_signer(signer_sudo, access_token):
            raise AccessError(_("Signer session is not allowed for this user."))
        raise AccessError(_("Signer session is not allowed for this user."))

    def _check_signer_internal_partner_fallback_access(self, signer_sudo, *, token_state=False):
        user = self._require_internal_user()
        if not self._is_partner_linked_signer(signer_sudo) or signer_sudo.partner_id != user.partner_id:
            raise AccessError(_("Signer session is not allowed for this user."))
        signer = request.env['open.sign.request.signer'].browse(signer_sudo.id)
        signer.with_user(user).check_access('read')
        return self._build_auth_context(
            signer_sudo,
            auth_mode='internal_fallback',
            effective_access_token=False,
            token_state=token_state,
            token_audit_identity=False,
        )

    @staticmethod
    def _is_request_readonly(sign_request):
        return sign_request.status in READONLY_REQUEST_STATUSES

    def _get_request_readonly_message(self, sign_request):
        if sign_request.status == 'completed':
            return _("This signing request has already been completed and is now read-only.")
        if sign_request.status == 'declined':
            return _("This signing request has already been declined and is now read-only.")
        if sign_request.status == 'expired':
            return _("This signing request has expired and is now read-only.")
        return False

    def _assert_request_read_access_allowed(self, sign_request):
        if sign_request.status not in SIGNER_REVIEW_REQUEST_STATUSES:
            raise ValidationError(_("This signing request is not available for signing."))

    def _assert_request_action_access_allowed(self, sign_request):
        if sign_request.status in SIGNER_MUTATION_REQUEST_STATUSES:
            return
        readonly_message = self._get_request_readonly_message(sign_request)
        if readonly_message:
            raise ValidationError(readonly_message)
        if sign_request.status == 'versioned':
            raise ValidationError(_("This signing request is not available for signing."))
        raise ValidationError(_("This signing request can no longer be modified."))

    def _assert_preview_access_allowed(self, sign_request):
        if sign_request.status not in PREVIEW_REQUEST_STATUSES:
            raise ValidationError(_("This signing request preview is not available in its current state."))

    def _check_signer_preview_access(self, signer_id):
        self._require_internal_user()
        signer_sudo = self._document_check_access('open.sign.request.signer', signer_id)
        if not signer_sudo or not signer_sudo.request_id.active:
            raise MissingError(_("This signing request is no longer available."))
        self._assert_preview_access_allowed(signer_sudo.request_id)
        return self._build_auth_context(signer_sudo, auth_mode='preview', effective_access_token=False)

    def _check_signer_identity_access(self, signer_id, access_token=None, *, entrypoint=False):
        signer_sudo = self._get_signer_sudo(signer_id)
        token_state = signer_sudo._classify_current_email_token_access(access_token)
        token_audit_identity = self._capture_token_audit_identity(
            signer_sudo,
            access_token,
            token_state=token_state,
        )
        try:
            return self._check_signer_external_token_access(
                signer_sudo,
                access_token,
                token_state=token_state,
                token_audit_identity=token_audit_identity,
            )
        except AccessError as exc:
            try:
                return self._check_signer_internal_partner_fallback_access(
                    signer_sudo,
                    token_state=token_state,
                )
            except AccessError:
                if entrypoint and token_state in {'expired', 'revoked'}:
                    rejection_code = 'expired_token' if token_state == 'expired' else 'invalid_token'
                    try:
                        self._append_token_rejected_from_snapshot(
                            signer_sudo,
                            entrypoint=entrypoint,
                            token_state=token_state,
                            rejection_code=rejection_code,
                            token_audit_identity=token_audit_identity,
                        )
                    except Exception:  # pragma: no cover - preserve denial contract if audit append fails
                        _logger.exception(
                            "Failed to append token rejection audit for signer %s on %s",
                            signer_sudo.id,
                            entrypoint,
                        )
                if token_state in {'invalid', 'revoked'}:
                    client_ip = self._get_client_ip()
                    if client_ip:
                        self._record_invalid_token_attempt(
                            signer_sudo,
                            client_ip,
                            force_isolated=bool(request.env.cr.readonly),
                        )
                raise exc

    def _check_signer_read_access(self, signer_id, access_token=None, *, entrypoint=False):
        auth_context = self._check_signer_identity_access(
            signer_id,
            access_token=access_token,
            entrypoint=entrypoint,
        )
        self._assert_request_read_access_allowed(auth_context.signer.request_id)
        return auth_context

    def _check_signer_action_access(self, signer_id, access_token=None, *, entrypoint=False):
        auth_context = self._check_signer_identity_access(
            signer_id,
            access_token=access_token,
            entrypoint=entrypoint,
        )
        self._assert_request_action_access_allowed(auth_context.signer.request_id)
        return auth_context

    @staticmethod
    def _is_signer_readonly(signer):
        return signer.state in READONLY_SIGNER_STATES

    def _assert_signer_mutation_allowed(self, signer):
        if signer.state in SIGNER_MUTABLE_STATES:
            return
        if signer.state == 'signed':
            raise ValidationError(_("This signing session is read-only because it has already been submitted."))
        if signer.state == 'declined':
            raise ValidationError(_("This signing session is read-only because it has already been declined."))
        if signer.state == 'expired':
            raise ValidationError(_("This signing session is read-only because it has expired."))
        raise ValidationError(_("This signing session is read-only."))

    def _is_signer_waiting_for_turn(self, signer):
        sign_request = signer.request_id
        return (
            sign_request.status in SIGNER_MUTATION_REQUEST_STATUSES
            and signer.state in SIGNER_MUTABLE_STATES
            and sign_request.ordered_signing
            and sign_request._is_signer_waiting(signer)
        )

    @staticmethod
    def _get_waiting_message(_signer):
        return _("This request uses sequential signing. Another signer must complete before your turn begins. Refresh this page later.")

    def _assert_signer_order_allows_mutation(self, signer):
        if self._is_signer_waiting_for_turn(signer):
            raise AccessError(f"{SIGNING_ORDER_BLOCKED_MARKER}::" + self._get_waiting_message(signer))

    def _assert_locked_signer_mutation_allowed(self, signer):
        self._assert_request_action_access_allowed(signer.request_id)
        self._assert_signer_mutation_allowed(signer)
        self._assert_signer_order_allows_mutation(signer)

    def _assert_locked_signer_decline_allowed(self, signer):
        self._assert_request_action_access_allowed(signer.request_id)
        self._assert_signer_mutation_allowed(signer)

    @staticmethod
    def _is_otp_required_for_signer(signer):
        return bool(getattr(signer, 'otp_required', False))

    def _get_otp_submit_block_reason(self, signer):
        if not self._is_otp_required_for_signer(signer) or signer.otp_verified_at:
            return False
        return _("Email verification is required before submit.")

    def _assert_locked_signer_otp_allowed(self, signer, *, action):
        del action
        self._assert_request_action_access_allowed(signer.request_id)
        self._assert_signer_mutation_allowed(signer)
        if not self._is_otp_required_for_signer(signer):
            raise ValidationError(f"{OTP_REQUIRED_MARKER}::" + _("OTP verification is not enabled for this signer."))
        if signer.otp_verified_at:
            raise ValidationError(
                f"{OTP_REQUIRED_MARKER}::" + _("Email verification is already complete for this signer.")
            )
        self._assert_signer_order_allows_mutation(signer)

    def _check_signer_document_access(self, signer_id, access_token=None, *, allow_preview=False):
        if access_token:
            return self._check_signer_read_access(
                signer_id,
                access_token=access_token,
                entrypoint='document',
            )
        try:
            return self._check_signer_read_access(
                signer_id,
                access_token=access_token,
                entrypoint='document',
            )
        except (AccessError, ValidationError):
            if not allow_preview:
                raise
            return self._check_signer_preview_access(signer_id)

    @staticmethod
    def _get_signer_document_attachment(signer_sudo):
        return signer_sudo.request_id.template_version_id.source_attachment_id or signer_sudo.request_id.template_id.source_attachment_id

    @staticmethod
    def _build_error_response(error_code, message):
        return {
            'ok': False,
            'error_code': error_code,
            'message': message,
        }

    @staticmethod
    def _build_jsonrpc_success_state(*, state, request_revision):
        return {
            'ok': True,
            'state': state,
            'request_revision': request_revision,
        }

    def _build_jsonrpc_redirect_url(self, *, signer_id, access_token=False, query_flag=False):
        redirect_url = f'/my/sign/{signer_id}'
        query_params = []
        if access_token:
            query_params.append(f'access_token={access_token}')
        if query_flag:
            query_params.append(query_flag)
        if query_params:
            redirect_url = f"{redirect_url}?{'&'.join(query_params)}"
        return redirect_url

    def _build_jsonrpc_success_redirect(self, *, signer_id, access_token=False, request_revision, query_flag):
        return {
            'ok': True,
            'force_refresh': True,
            'redirect_url': self._build_jsonrpc_redirect_url(
                signer_id=signer_id,
                access_token=access_token,
                query_flag=query_flag,
            ),
            'request_revision': request_revision,
        }

    def _build_jsonrpc_success_otp_verified(self, *, signer_id, access_token=False, request_revision):
        response = self._build_jsonrpc_success_redirect(
            signer_id=signer_id,
            access_token=access_token,
            request_revision=request_revision,
            query_flag='otp_verified=1',
        )
        response['otp_verified'] = True
        return response

    def _invalid_token_response(self):
        return self._build_error_response(
            'invalid_token',
            _("Invalid or expired signing link."),
        )

    def _expired_token_response(self, message=False):
        return self._build_error_response(
            'expired_token',
            message or _("This signing link has expired. Request a new link."),
        )

    @staticmethod
    def _extract_marked_message(message, marker):
        prefix = f'{marker}::'
        if message.startswith(prefix):
            return message.split('::', 1)[1]
        return False

    def _jsonrpc_error_from_access(self, exc, *, allow_order_block=False, allow_consent=False, allow_expired_token=False):
        message = str(exc)
        if allow_order_block and message.startswith(f'{SIGNING_ORDER_BLOCKED_MARKER}::'):
            return self._build_error_response('signing_order_blocked', message.split('::', 1)[1])
        if allow_consent and message.startswith(f'{CONSENT_REQUIRED_MARKER}::'):
            return self._build_error_response('consent_required', message.split('::', 1)[1])
        if allow_expired_token and message.startswith(f'{EXPIRED_TOKEN_MARKER}::'):
            return self._expired_token_response(message.split('::', 1)[1])
        return self._invalid_token_response()

    def _jsonrpc_error_from_validation(self, exc, *, allow_contract_message=False, allow_idempotency_conflict=False):
        message = str(exc)
        if self._extract_marked_message(message, STALE_REVISION_MARKER):
            return self._build_error_response('stale_revision', message.split('::', 1)[1])
        if allow_idempotency_conflict:
            conflict_message = self._extract_marked_message(message, IDEMPOTENCY_CONFLICT_MARKER)
            if conflict_message:
                return self._build_error_response('idempotency_conflict', conflict_message)
        if allow_contract_message:
            contract_message = self._extract_marked_message(message, CONTRACT_UNAVAILABLE_MARKER)
            if contract_message:
                return self._build_error_response('validation_error', contract_message)
        if '::' in message:
            return self._build_error_response('validation_error', message.split('::', 1)[1])
        return self._build_error_response('validation_error', message)

    def _jsonrpc_request_locked_response(self):
        return self._build_error_response(
            'request_locked',
            _("The signing request is currently locked. Try again."),
        )

    @staticmethod
    def _normalize_line_endings(value):
        return (value or '').replace('\r\n', '\n').replace('\r', '\n')

    def _normalize_consent_text(self, value):
        lines = self._normalize_line_endings(value).split('\n')
        return '\n'.join(line.rstrip() for line in lines)

    def _get_consent_text(self):
        return _("I agree to sign electronically and confirm my intent to sign this document.")

    def _get_consent_hash(self):
        normalized_text = self._normalize_consent_text(self._get_consent_text())
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()

    def _raise_contract_unavailable(self):
        raise ValidationError(
            f"{CONTRACT_UNAVAILABLE_MARKER}::"
            + _("This signing request definition is no longer available. Contact the sender.")
        )

    @staticmethod
    def _extract_request_ip():
        forwarded = request.httprequest.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.httprequest.remote_addr or False

    @staticmethod
    def _extract_user_agent():
        return request.httprequest.headers.get('User-Agent') or False

    def _ensure_uuid(self, value, *, field_name):
        token = str(value or '').strip()
        if not UUID_RE.fullmatch(token):
            raise ValidationError(_("%(field)s must be a UUID.", field=field_name))
        try:
            UUID(token)
        except ValueError as exc:
            raise ValidationError(_("%(field)s must be a UUID.", field=field_name)) from exc
        return token

    def _ensure_request_revision(self, payload):
        revision = payload.get('request_revision')
        try:
            normalized_revision = int(revision)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("request_revision must be an integer.")) from exc
        if normalized_revision < 0:
            raise ValidationError(_("request_revision must be zero or greater."))
        return normalized_revision

    def _ensure_values_payload(self, payload):
        if 'values' not in payload:
            raise ValidationError(_("values payload is required."))
        values = payload.get('values')
        if not isinstance(values, list):
            raise ValidationError(_("values payload must be a list."))
        parsed = {}
        for item in values:
            if not isinstance(item, dict):
                raise ValidationError(_("Each values item must be an object."))
            field_id = item.get('field_id')
            try:
                normalized_field_id = int(field_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("Each values item requires an integer field_id.")) from exc
            if normalized_field_id in parsed:
                raise ValidationError(_("Duplicate field entries are not allowed in values payload."))
            parsed[normalized_field_id] = item
        return parsed

    def _validate_mutation_payload(self, payload):
        idempotency_key = self._ensure_uuid(payload.get('idempotency_key'), field_name='idempotency_key')
        request_revision = self._ensure_request_revision(payload)
        parsed_values = self._ensure_values_payload(payload)
        return request_revision, parsed_values, idempotency_key

    def _normalize_decline_reason(self, reason):
        normalized_reason = self._normalize_line_endings(reason or '').strip()
        if not normalized_reason:
            raise ValidationError(_("Decline reason is required."))
        if len(normalized_reason) > DECLINE_REASON_MAX_LENGTH:
            raise ValidationError(_("Decline reason cannot exceed 4000 characters."))
        return normalized_reason

    def _validate_decline_payload(self, payload):
        idempotency_key = self._ensure_uuid(payload.get('idempotency_key'), field_name='idempotency_key')
        request_revision = self._ensure_request_revision(payload)
        normalized_reason = self._normalize_decline_reason(payload.get('reason'))
        return request_revision, normalized_reason, idempotency_key

    def _validate_otp_request_payload(self, payload):
        return self._ensure_request_revision(payload)

    def _validate_otp_verify_payload(self, payload):
        request_revision = self._ensure_request_revision(payload)
        normalized_code = str(payload.get('code') or '').strip()
        if len(normalized_code) != otp_service.OTP_CODE_LENGTH or not normalized_code.isdigit():
            raise ValidationError(f"{OTP_INVALID_MARKER}::" + _("The verification code is invalid."))
        return request_revision, normalized_code

    def _lock_request_for_update(self, sign_request):
        # Keep lock-miss handling isolated so JSON-RPC callers can return
        # request_locked without leaving the outer HTTP transaction aborted.
        with request.env.cr.savepoint():
            request.env.cr.execute(
                "SELECT id FROM open_sign_request WHERE id = %s FOR UPDATE NOWAIT",
                [sign_request.id],
            )

    def _assert_request_revision(self, sign_request, request_revision):
        if sign_request.lock_version != request_revision:
            raise ValidationError(
                f"{STALE_REVISION_MARKER}::" + _("This signing session is out of date. Refresh and try again.")
            )

    @staticmethod
    def _is_value_present(field_type, value_text, value_json):
        if field_type == 'checkbox' and isinstance(value_json, bool):
            return True
        if field_type == 'strikethrough' and isinstance(value_json, dict):
            return isinstance(value_json.get('applied'), bool)
        if field_type == 'date' and isinstance(value_json, dict):
            return bool((value_json.get('iso_date') or '').strip())
        if field_type in UNSUPPORTED_CAPTURE_TYPES and isinstance(value_json, dict):
            return bool(value_json)
        if isinstance(value_text, str):
            return bool(value_text.strip())
        if value_text not in (False, None):
            return True
        if isinstance(value_json, dict):
            return bool(value_json)
        if value_json not in (False, None):
            return True
        return False

    def _extract_value_payload(self, field_descriptor, payload_item):
        if 'value_text' in payload_item or 'value_json' in payload_item:
            return payload_item.get('value_text'), payload_item.get('value_json')

        raw_value = payload_item.get('value', False)
        if field_descriptor.type in TEXTUAL_FIELD_TYPES:
            return raw_value, False
        return False, raw_value

    def _build_snapshot_field_descriptor(self, contract_field):
        return SimpleNamespace(
            type=contract_field['type'],
            label=contract_field['label'],
            required=bool(contract_field.get('required')),
            validation_regex=contract_field.get('validation_regex') or False,
            min_length=contract_field.get('min_length'),
            max_length=contract_field.get('max_length'),
            option_ids=[
                SimpleNamespace(
                    value=option.get('value'),
                    label=option.get('label') or option.get('value'),
                    sequence=int(option.get('sequence') or 0),
                    is_default=bool(option.get('is_default')),
                )
                for option in contract_field.get('options', [])
            ],
        )

    def _resolve_snapshot_role(self, sign_request, snapshot_role):
        role_model = request.env['open.sign.role']
        template = sign_request.template_id
        snapshot_payload = dict(snapshot_role)
        role_id = snapshot_payload.get('role_id')
        if role_id:
            try:
                normalized_role_id = int(role_id)
            except (TypeError, ValueError):
                self._raise_contract_unavailable()
            role = template.role_ids.filtered(lambda candidate: candidate.id == normalized_role_id)
        else:
            role = role_model._find_snapshot_matches(template, snapshot_payload)
        if len(role) != 1:
            self._raise_contract_unavailable()
        resolved_payload = dict(snapshot_payload)
        resolved_payload['role_id'] = role.id
        resolved_payload['name'] = resolved_payload.get('name') or role.name
        resolved_payload['name_normalized'] = (
            resolved_payload.get('name_normalized') or role.name_normalized
        )
        resolved_payload['sequence'] = resolved_payload.get('sequence', role.sequence)
        resolved_payload['required'] = resolved_payload.get('required', role.required)
        resolved_payload['color'] = resolved_payload.get('color', role.color)
        return resolved_payload

    def _resolve_snapshot_field_role_id(self, sign_request, snapshot_field, resolved_roles_by_name):
        template = sign_request.template_id
        role_model = request.env['open.sign.role']
        role_id = snapshot_field.get('role_id')
        if role_id:
            try:
                normalized_role_id = int(role_id)
            except (TypeError, ValueError):
                self._raise_contract_unavailable()
            role = template.role_ids.filtered(lambda candidate: candidate.id == normalized_role_id)
            if len(role) != 1:
                self._raise_contract_unavailable()
            return role.id

        role_name_key = role_model._normalize_role_name_key(
            snapshot_field.get('role_name_normalized') or snapshot_field.get('role_name')
        )
        if role_name_key in resolved_roles_by_name:
            return resolved_roles_by_name[role_name_key]['role_id']

        role = template.role_ids.filtered(lambda candidate: candidate.name_normalized == role_name_key)
        if len(role) != 1:
            self._raise_contract_unavailable()
        return role.id

    def _resolve_snapshot_field(self, sign_request, snapshot_field, resolved_roles_by_name):
        field_model = request.env['open.sign.template.field']
        template = sign_request.template_id
        snapshot_payload = dict(snapshot_field)
        field_id = snapshot_payload.get('template_field_id')
        if field_id:
            try:
                normalized_field_id = int(field_id)
            except (TypeError, ValueError):
                self._raise_contract_unavailable()
            live_field = template.field_ids.filtered(lambda field: field.id == normalized_field_id)
        else:
            live_field = field_model._find_snapshot_matches(template, snapshot_payload)
        if len(live_field) != 1:
            self._raise_contract_unavailable()

        resolved_role_id = self._resolve_snapshot_field_role_id(sign_request, snapshot_payload, resolved_roles_by_name)
        if live_field.role_id.id != resolved_role_id:
            self._raise_contract_unavailable()

        resolved_payload = dict(snapshot_payload)
        resolved_payload['template_field_id'] = live_field.id
        resolved_payload['id'] = live_field.id
        resolved_payload['role_id'] = resolved_role_id
        resolved_payload['role_name'] = resolved_payload.get('role_name') or live_field.role_id.name
        resolved_payload['role_name_normalized'] = (
            resolved_payload.get('role_name_normalized') or live_field.role_id.name_normalized
        )
        resolved_payload['options'] = [
            field_model._build_snapshot_option_payload(option)
            for option in resolved_payload.get('options', [])
        ]
        resolved_payload['supported_on_portal'] = resolved_payload['type'] in SUPPORTED_PORTAL_FIELD_TYPES
        resolved_payload['descriptor'] = self._build_snapshot_field_descriptor(resolved_payload)
        return resolved_payload

    def _get_request_field_contract(self, sign_request):
        template_version = sign_request.template_version_id
        if not template_version:
            self._raise_contract_unavailable()

        role_model = request.env['open.sign.role']
        resolved_roles_by_name = {}
        for snapshot_role in template_version.role_snapshot_json or []:
            resolved_role = self._resolve_snapshot_role(sign_request, snapshot_role)
            role_name_key = role_model._normalize_role_name_key(
                resolved_role.get('name_normalized') or resolved_role.get('name')
            )
            resolved_roles_by_name[role_name_key] = resolved_role

        resolved_fields = [
            self._resolve_snapshot_field(sign_request, snapshot_field, resolved_roles_by_name)
            for snapshot_field in (template_version.field_snapshot_json or [])
        ]
        return sorted(
            resolved_fields,
            key=lambda field: (field['page'], field['sequence'], field['template_field_id']),
        )

    def _get_signer_contract_fields(self, signer):
        return [
            field
            for field in self._get_request_field_contract(signer.request_id)
            if field['role_id'] == signer.role_id.id
        ]

    def _normalize_field_value(self, field_descriptor, payload_item, *, enforce_required):
        value_text, value_json = self._extract_value_payload(field_descriptor, payload_item)
        if field_descriptor.type in UNSUPPORTED_CAPTURE_TYPES and self._is_value_present(
            field_descriptor.type, value_text, value_json
        ):
            raise ValidationError(_("Signature and stamp field capture is not available yet on the portal."))

        normalized_text, normalized_json = validation_service.normalize_and_validate_field_value(
            template_field=field_descriptor,
            value_text=value_text,
            value_json=value_json,
            signed_payload_attachment=False,
            enforce_required=enforce_required,
        )
        has_value = self._is_value_present(field_descriptor.type, normalized_text, normalized_json)
        return normalized_text, normalized_json, has_value

    def _ensure_supported_required_fields(self, signer, signer_fields):
        unsupported_required = [
            field['label']
            for field in signer_fields
            if field['required'] and field['type'] in UNSUPPORTED_CAPTURE_TYPES
        ]
        if unsupported_required:
            raise ValidationError(_(
                "Required signature/stamp fields are not supported in the portal yet: %(labels)s",
                labels=', '.join(unsupported_required),
            ))

        signer_field_ids = {field['template_field_id'] for field in signer_fields}
        signer_values = signer.request_id.value_ids.filtered(
            lambda value: value.signer_id == signer and value.template_field_id.id in signer_field_ids
        )
        values_by_field_id = {value.template_field_id.id: value for value in signer_values}
        for field in [field for field in signer_fields if field['required'] and field['supported_on_portal']]:
            value = values_by_field_id.get(field['template_field_id'])
            if not value:
                raise ValidationError(_("Required field %(label)s is missing.", label=field['label']))
            if not self._is_value_present(field['type'], value.value_text, value.value_json):
                raise ValidationError(_("Required field %(label)s is missing.", label=field['label']))

    def _upsert_signer_values(self, signer, parsed_values, *, enforce_required):
        signer_fields = self._get_signer_contract_fields(signer)
        fields_by_id = {field['template_field_id']: field for field in signer_fields}
        existing_values = signer.request_id.value_ids.filtered(
            lambda value: value.signer_id == signer and value.template_field_id.id in fields_by_id
        )
        values_by_field = {value.template_field_id.id: value for value in existing_values}

        value_model = request.env['open.sign.request.value'].sudo().with_context(
            open_sign_trusted_portal_value_payload=True
        )
        changed = False
        touched_field_ids = []
        for field_id, payload_item in parsed_values.items():
            field = fields_by_id.get(field_id)
            if not field:
                raise ValidationError(_("Field %(field_id)s does not belong to this signer session.", field_id=field_id))
            if not field['supported_on_portal']:
                raise ValidationError(_("Field %(field_id)s is not supported on the portal.", field_id=field_id))
            normalized_text, normalized_json, has_value = self._normalize_field_value(
                field['descriptor'],
                payload_item,
                enforce_required=enforce_required,
            )
            touched_field_ids.append(field_id)
            current_value = values_by_field.get(field_id)
            if not has_value:
                if current_value:
                    current_value.sudo().unlink()
                    changed = True
                continue

            value_vals = {
                'request_id': signer.request_id.id,
                'template_field_id': field_id,
                'signer_id': signer.id,
                'value_text': normalized_text,
                'value_json': normalized_json,
                'signed_payload_attachment_id': False,
                'is_valid': True,
            }
            if current_value:
                if (
                    current_value.value_text != normalized_text
                    or current_value.value_json != normalized_json
                    or not current_value.is_valid
                ):
                    current_value.sudo().with_context(
                        open_sign_trusted_portal_value_payload=True
                    ).write({
                        'value_text': normalized_text,
                        'value_json': normalized_json,
                        'signed_payload_attachment_id': False,
                        'is_valid': True,
                    })
                    changed = True
            else:
                value_model.create(value_vals)
                changed = True
        return changed, touched_field_ids, signer_fields

    def _append_audit_event(self, signer, event_type, *, event_at, metadata=None, consent_text_hash=False):
        return request.env['open.sign.audit.log'].sudo().append_event(
            request_id=signer.request_id.id,
            signer_id=signer.id,
            event_type=event_type,
            metadata=metadata or {},
            ip=self._extract_request_ip(),
            user_agent=self._extract_user_agent(),
            consent_text_hash=consent_text_hash,
            event_at=event_at,
        )

    @staticmethod
    def _get_newly_actionable_pending_signers(sign_request, actionable_before_ids):
        actionable_after = sign_request._get_actionable_signers().filtered(lambda signer: signer.state == 'pending')
        return actionable_after.filtered(lambda signer: signer.id not in actionable_before_ids)

    def _queue_best_effort_next_wave_invitations(self, sign_request, signers):
        if not signers:
            return
        with request.env.cr.savepoint():
            try:
                notification_service.queue_request_invitations(
                    sign_request,
                    signers,
                    trigger='wave_unblocked',
                    raise_on_failure=False,
                )
            except Exception as exc:  # pragma: no cover - defensive best-effort guard
                _logger.exception(
                    "Wave-unblocked invitation notification service failure for request %s",
                    sign_request.id,
                    exc_info=exc,
                )
                sign_request._append_audit_event(
                    'notification_failed',
                    metadata={
                        'notification_type': 'invitation',
                        'recipient_kind': 'signer',
                        'trigger': 'wave_unblocked',
                        'template_xmlid': notification_service.INVITATION_TEMPLATE_XMLID,
                        'failure_reason': notification_service.FAILURE_REASON_NOTIFICATION_SERVICE_ERROR,
                    },
                )

    def _queue_best_effort_decline_notification(self, sign_request, signer):
        with request.env.cr.savepoint():
            try:
                notification_service.queue_request_decline_notification(
                    sign_request,
                    signer,
                    raise_on_failure=False,
                )
            except Exception as exc:  # pragma: no cover - defensive best-effort guard
                _logger.exception(
                    "Decline notification service failure for request %s signer %s",
                    sign_request.id,
                    signer.id,
                    exc_info=exc,
                )
                sign_request._append_audit_event(
                    'notification_failed',
                    signer=signer,
                    metadata={
                        'notification_type': 'decline',
                        'recipient_kind': 'owner',
                        'trigger': 'request_declined',
                        'template_xmlid': notification_service.DECLINE_OWNER_TEMPLATE_XMLID,
                        'failure_reason': notification_service.FAILURE_REASON_NOTIFICATION_SERVICE_ERROR,
                    },
                )

    @staticmethod
    def _invalidate_active_otp_challenges(signer):
        if 'otp_required' not in signer._fields:
            return
        otp_service.invalidate_active_challenges(signer.sudo())

    def _ensure_session_opened(self, signer, *, event_at):
        transitioned = False
        first_open = signer.state == 'pending'
        signer.sudo().write({
            'last_opened_at': event_at,
            'ip_last': self._extract_request_ip(),
            'state': 'opened' if first_open else signer.state,
        })
        if first_open:
            transitioned = True
            self._append_audit_event(
                signer,
                'signer_opened',
                event_at=event_at,
                metadata={'request_status': signer.request_id.status},
            )
        if signer.request_id.status == 'sent':
            signer.request_id.sudo()._transition_to('opened', {'last_event_at': event_at})
            transitioned = True
        return transitioned

    def _move_request_to_in_progress(self, sign_request, *, event_at):
        if sign_request.status == 'sent':
            sign_request._transition_to('opened', {'last_event_at': event_at})
        if sign_request.status == 'opened':
            sign_request._transition_to('in_progress', {'last_event_at': event_at})

    def _move_request_to_partially_signed(self, sign_request, *, event_at):
        self._move_request_to_in_progress(sign_request, event_at=event_at)
        if sign_request.status == 'in_progress':
            sign_request._transition_to('partially_signed', {'last_event_at': event_at})

    def _assert_submit_allowed(self, signer):
        self._assert_locked_signer_mutation_allowed(signer)

    def _check_consent_payload(self, payload):
        consent = payload.get('consent')
        if not isinstance(consent, dict) or consent.get('accepted') is not True:
            raise AccessError(f"{CONSENT_REQUIRED_MARKER}::" + _("Signer consent is required before submit."))
        provided_hash = (consent.get('text_hash') or '').strip()
        if not provided_hash:
            raise ValidationError(_("Signer consent text hash is required."))
        expected_hash = self._get_consent_hash()
        if not consteq(provided_hash, expected_hash):
            raise ValidationError(_("Signer consent text hash does not match the server disclosure."))
        signer_timezone = (consent.get('timezone') or '').strip() or False
        return expected_hash, signer_timezone

    def _extract_submit_hash_inputs(self, payload):
        consent = payload.get('consent')
        if not isinstance(consent, dict):
            return False, False, False
        return (
            bool(consent.get('accepted')),
            (consent.get('text_hash') or '').strip(),
            (consent.get('timezone') or '').strip() or False,
        )

    @staticmethod
    def _canonicalize_idempotency_value(normalized_text, normalized_json, has_value):
        if not has_value:
            return False
        if normalized_json not in (False, None):
            return normalized_json
        return normalized_text

    def _get_normalized_submit_values_for_idempotency(self, signer, parsed_values):
        signer_fields = self._get_signer_contract_fields(signer)
        fields_by_id = {field['template_field_id']: field for field in signer_fields}
        normalized_values = []
        for field_id, payload_item in parsed_values.items():
            field = fields_by_id.get(field_id)
            if not field:
                raise ValidationError(_("Field %(field_id)s does not belong to this signer session.", field_id=field_id))
            if not field['supported_on_portal']:
                raise ValidationError(_("Field %(field_id)s is not supported on the portal.", field_id=field_id))
            normalized_text, normalized_json, has_value = self._normalize_field_value(
                field['descriptor'],
                payload_item,
                enforce_required=False,
            )
            normalized_values.append({
                'field_id': field_id,
                'value': self._canonicalize_idempotency_value(normalized_text, normalized_json, has_value),
            })
        return normalized_values

    def _append_idempotency_conflict_event(self, signer, *, endpoint, idempotency_key, existing_state):
        event_at = fields.Datetime.now()
        self._append_audit_event(
            signer,
            'idempotency_conflict',
            event_at=event_at,
            metadata={
                'endpoint': endpoint,
                'idempotency_key': idempotency_key,
                'existing_state': existing_state,
                'request_status_before': signer.request_id.status,
                'signer_state_before': signer.state,
            },
        )
        return event_at

    def _resolve_portal_idempotency(self, signer, *, endpoint, idempotency_key, request_hash):
        resolution, record = idempotency_service.claim_or_resolve(
            signer,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if resolution == 'replay':
            return resolution, record, dict(record.response_json or {})
        if resolution == 'locked':
            return resolution, record, self._jsonrpc_request_locked_response()
        if resolution == 'conflict':
            if not record.conflict_logged_at:
                event_at = self._append_idempotency_conflict_event(
                    signer,
                    endpoint=endpoint,
                    idempotency_key=idempotency_key,
                    existing_state=record.state,
                )
                idempotency_service.mark_conflict_logged(record, when=event_at)
            raise ValidationError(
                f"{IDEMPOTENCY_CONFLICT_MARKER}::"
                + _("This action conflicts with an earlier request. Refresh and try again.")
            )
        return resolution, record, False

    def _build_portal_field_value(self, contract_field, request_value):
        if not request_value:
            return False if contract_field['type'] in {'checkbox', 'strikethrough'} else ''
        if contract_field['type'] in TEXTUAL_FIELD_TYPES:
            return request_value.value_text or ''
        if contract_field['type'] == 'checkbox':
            return bool(isinstance(request_value.value_json, bool) and request_value.value_json)
        if contract_field['type'] == 'date':
            if isinstance(request_value.value_json, dict):
                return (request_value.value_json or {}).get('iso_date') or ''
            return ''
        if contract_field['type'] == 'strikethrough':
            if isinstance(request_value.value_json, dict):
                return bool(request_value.value_json.get('applied'))
            return False
        return ''

    def _build_portal_fields(self, signer):
        signer_fields = self._get_signer_contract_fields(signer)
        signer_values = signer.request_id.value_ids.filtered(
            lambda value: value.signer_id == signer and value.template_field_id.id in {
                field['template_field_id'] for field in signer_fields
            }
        )
        values_by_field_id = {value.template_field_id.id: value for value in signer_values}

        portal_fields = []
        unsupported_required_fields = []
        for field in signer_fields:
            field_value = values_by_field_id.get(field['template_field_id'])
            if field['required'] and field['type'] in UNSUPPORTED_CAPTURE_TYPES:
                unsupported_required_fields.append(field['label'])
            portal_fields.append({
                'id': field['template_field_id'],
                'label': field['label'],
                'type': field['type'],
                'required': field['required'],
                'supported_on_portal': field['supported_on_portal'],
                'value': self._build_portal_field_value(field, field_value),
                'options': field['options'],
            })
        return portal_fields, unsupported_required_fields

    def _build_portal_page_values(self, auth_context, *, preview_mode=False, portal_error_message=False, **kwargs):
        signer_sudo = auth_context.signer
        access_token = False if preview_mode else auth_context.effective_access_token
        sign_request = signer_sudo.request_id
        attachment = sign_request.template_version_id.source_attachment_id or sign_request.template_id.source_attachment_id
        document_url = False
        waiting_mode = (
            not preview_mode
            and not portal_error_message
            and self._is_signer_waiting_for_turn(signer_sudo)
        )
        readonly_mode = (
            preview_mode
            or bool(portal_error_message)
            or self._is_request_readonly(sign_request)
            or self._is_signer_readonly(signer_sudo)
            or waiting_mode
        )
        readonly_message = False
        waiting_message = False
        refresh_url = False
        if not preview_mode:
            readonly_message = self._get_request_readonly_message(sign_request)
            if waiting_mode:
                waiting_message = self._get_waiting_message(signer_sudo)
            elif not readonly_message and signer_sudo.state == 'signed':
                readonly_message = _("Your submission has already been recorded. This session is read-only.")
            elif not readonly_message and signer_sudo.state == 'declined':
                readonly_message = _("This signing session has already been declined and is now read-only.")
            elif not readonly_message and signer_sudo.state == 'expired':
                readonly_message = _("This signing session has expired and is now read-only.")
            refresh_url = f'/my/sign/{signer_sudo.id}'
            if access_token:
                refresh_url = f'{refresh_url}?access_token={access_token}'
        if attachment:
            document_url = f'/my/sign/{signer_sudo.id}/document'
            if access_token:
                document_url = f'{document_url}?access_token={access_token}'
            elif preview_mode:
                document_url = f'{document_url}?preview=1'

        portal_fields = []
        submit_blocked_reason = False
        otp_required = self._is_otp_required_for_signer(signer_sudo)
        otp_verified = bool(otp_required and signer_sudo.otp_verified_at)
        otp_active_challenge = otp_service.get_active_challenge(signer_sudo) if otp_required else False
        otp_panel_available = (
            otp_required
            and not preview_mode
            and not portal_error_message
            and not waiting_mode
            and not readonly_mode
        )
        otp_submit_block_reason = self._get_otp_submit_block_reason(signer_sudo) if otp_panel_available else False
        decline_available = (
            not preview_mode
            and not portal_error_message
            and sign_request.status in SIGNER_MUTATION_REQUEST_STATUSES
            and signer_sudo.state in SIGNER_MUTABLE_STATES
        )
        decline_route = f'/my/sign/{signer_sudo.id}/decline' if decline_available else False
        declined_reason_display = signer_sudo.declined_reason if signer_sudo.state == 'declined' else False
        if not portal_error_message:
            portal_fields, unsupported_required_fields = self._build_portal_fields(signer_sudo)
            if unsupported_required_fields:
                submit_blocked_reason = _(
                    "Submitting is blocked until portal signature/stamp capture is implemented for: %(labels)s",
                    labels=', '.join(unsupported_required_fields),
                )

        values = self._get_page_view_values(
            signer_sudo,
            access_token,
            {
                'page_name': 'open_sign_document_preview' if preview_mode else 'open_sign_document',
                'signer': signer_sudo,
                'sign_request': sign_request,
                'portal_fields': portal_fields,
                'portal_error_message': portal_error_message,
                'preview_mode': preview_mode,
                'waiting_mode': waiting_mode,
                'waiting_message': waiting_message,
                'readonly_mode': readonly_mode,
                'readonly_message': readonly_message,
                'consent_text': self._get_consent_text(),
                'consent_hash': self._get_consent_hash(),
                'document_url': document_url,
                'refresh_url': refresh_url,
                'request_revision': sign_request.lock_version,
                'submit_blocked_reason': submit_blocked_reason,
                'access_token': access_token,
                'save_route': False if readonly_mode else f'/my/sign/{signer_sudo.id}/save',
                'submit_route': False if readonly_mode else f'/my/sign/{signer_sudo.id}/submit',
                'decline_available': decline_available,
                'decline_route': decline_route,
                'declined_reason_display': declined_reason_display,
                'otp_required': otp_required,
                'otp_verified': otp_verified,
                'otp_request_url': f'/my/sign/{signer_sudo.id}/otp/request' if otp_panel_available and not otp_verified else False,
                'otp_verify_url': f'/my/sign/{signer_sudo.id}/otp/verify' if otp_panel_available and not otp_verified else False,
                'otp_email_hint': otp_service.mask_email_address(signer_sudo.email) if otp_panel_available else False,
                'otp_has_active_challenge': bool(otp_active_challenge),
                'otp_expires_at': otp_active_challenge.expires_at if otp_active_challenge else False,
                'otp_submit_block_reason': otp_submit_block_reason,
            },
            'my_open_sign_history',
            True,
            **kwargs,
        )
        return values

    @http.route(['/my/sign'], type='http', auth='user', website=True, readonly=True)
    def portal_my_sign(self, **kwargs):
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'open_sign_documents',
        })
        return request.render('open_sign_portal.portal_my_sign', values)

    @http.route(['/my/sign/<int:signer_id>/preview'], type='http', auth='user', website=True, readonly=True)
    def portal_sign_preview_page(self, signer_id, **kwargs):
        auth_context = None
        try:
            auth_context = self._check_signer_preview_access(signer_id)
            values = self._build_portal_page_values(auth_context, preview_mode=True, **kwargs)
        except (AccessError, MissingError):
            return request.redirect('/my')
        except ValidationError as exc:
            contract_message = self._extract_marked_message(str(exc), CONTRACT_UNAVAILABLE_MARKER)
            if auth_context and contract_message:
                values = self._build_portal_page_values(
                    auth_context,
                    preview_mode=True,
                    portal_error_message=contract_message,
                    **kwargs,
                )
                return request.render('open_sign_portal.portal_sign_page', values)
            return request.redirect('/my')
        return request.render('open_sign_portal.portal_sign_page', values)

    @http.route(['/my/sign/<int:signer_id>'], type='http', auth='public', website=True)
    def portal_sign_page(self, signer_id, access_token=None, **kwargs):
        access_token = self._resolve_access_token(access_token)
        auth_context = None
        try:
            auth_context = self._check_signer_read_access(
                signer_id,
                access_token=access_token,
                entrypoint='page',
            )
            signer_sudo = auth_context.signer
            if auth_context.auth_mode == 'token':
                try:
                    self._append_token_opened_from_auth_context(auth_context, entrypoint='page')
                except Exception:  # pragma: no cover - preserve page contract if audit append fails
                    _logger.exception(
                        "Failed to append token opened audit for signer %s on page",
                        signer_sudo.id,
                    )
            values = self._build_portal_page_values(auth_context, **kwargs)
            if (
                signer_sudo.state in SIGNER_MUTABLE_STATES
                and signer_sudo.request_id.status in SIGNER_MUTATION_REQUEST_STATUSES
                and signer_sudo.request_id._is_signer_actionable(signer_sudo)
            ):
                event_at = fields.Datetime.now()
                session_transitioned = self._ensure_session_opened(signer_sudo, event_at=event_at)
                if session_transitioned:
                    signer_sudo.request_id.sudo().write({
                        'lock_version': signer_sudo.request_id.lock_version + 1,
                        'last_event_at': event_at,
                    })
                    values['request_revision'] = signer_sudo.request_id.lock_version
        except (AccessError, MissingError):
            return request.redirect('/my')
        except ValidationError as exc:
            contract_message = self._extract_marked_message(str(exc), CONTRACT_UNAVAILABLE_MARKER)
            if auth_context and contract_message:
                values = self._build_portal_page_values(
                    auth_context,
                    portal_error_message=contract_message,
                    **kwargs,
                )
                return request.render('open_sign_portal.portal_sign_page', values)
            return request.redirect('/my')
        return request.render('open_sign_portal.portal_sign_page', values)

    @http.route(['/my/sign/<int:signer_id>/document'], type='http', auth='public', website=True, readonly=True)
    def portal_sign_document(self, signer_id, access_token=None, **kwargs):
        del kwargs
        access_token = self._resolve_access_token(access_token)
        allow_preview = request.httprequest.args.get('preview') == '1'
        try:
            auth_context = self._check_signer_document_access(
                signer_id,
                access_token=access_token,
                allow_preview=allow_preview,
            )
        except (AccessError, MissingError, ValidationError):
            return request.redirect('/my')
        signer_sudo = auth_context.signer
        attachment = self._get_signer_document_attachment(signer_sudo)
        if not attachment:
            return request.redirect('/my')
        if auth_context.auth_mode == 'token':
            try:
                self._append_token_opened_from_auth_context(auth_context, entrypoint='document')
            except Exception:  # pragma: no cover - preserve document contract if audit append fails
                _logger.exception(
                    "Failed to append token opened audit for signer %s on document",
                    signer_sudo.id,
                )
        return request.env['ir.binary']._get_stream_from(attachment).get_response(as_attachment=False)

    @http.route(['/my/sign/<int:signer_id>/save'], type='jsonrpc', auth='public')
    def portal_sign_save(self, signer_id, access_token=None, **payload):
        access_token = self._resolve_access_token(access_token, payload=payload)
        try:
            auth_context = self._check_signer_identity_access(
                signer_id,
                access_token=access_token,
                entrypoint='save',
            )
            signer_sudo = auth_context.signer
            request_revision, parsed_values, _idempotency_key = self._validate_mutation_payload(payload)
            sign_request = signer_sudo.request_id.sudo()
            with request.env.cr.savepoint():
                self._lock_request_for_update(sign_request)
                self._assert_request_revision(sign_request, request_revision)
                self._assert_locked_signer_mutation_allowed(signer_sudo)
                event_at = fields.Datetime.now()
                session_changed = self._ensure_session_opened(signer_sudo, event_at=event_at)
                values_changed, touched_field_ids, _signer_fields = self._upsert_signer_values(
                    signer_sudo,
                    parsed_values,
                    enforce_required=False,
                )
                if values_changed:
                    self._move_request_to_in_progress(sign_request, event_at=event_at)
                    self._append_audit_event(
                        signer_sudo,
                        'value_saved',
                        event_at=event_at,
                        metadata={
                            'field_ids': touched_field_ids,
                            'field_count': len(touched_field_ids),
                        },
                    )
                if session_changed or values_changed:
                    sign_request.sudo().write({
                        'lock_version': sign_request.lock_version + 1,
                        'last_event_at': event_at,
                    })
            return self._build_jsonrpc_success_state(
                state=sign_request.status,
                request_revision=sign_request.lock_version,
            )
        except MissingError:
            return self._invalid_token_response()
        except AccessError as exc:
            return self._jsonrpc_error_from_access(exc, allow_order_block=True, allow_expired_token=True)
        except LockNotAvailable:
            return self._jsonrpc_request_locked_response()
        except ValidationError as exc:
            return self._jsonrpc_error_from_validation(exc, allow_contract_message=True)

    @http.route(['/my/sign/<int:signer_id>/submit'], type='jsonrpc', auth='public')
    def portal_sign_submit(self, signer_id, access_token=None, **payload):
        access_token = self._resolve_access_token(access_token, payload=payload)
        try:
            auth_context = self._check_signer_identity_access(
                signer_id,
                access_token=access_token,
                entrypoint='submit',
            )
            signer_sudo = auth_context.signer
            request_revision, parsed_values, idempotency_key = self._validate_mutation_payload(payload)
            sign_request = signer_sudo.request_id.sudo()
            newly_actionable_signers = request.env['open.sign.request.signer']
            response = False
            consent_accepted, provided_consent_hash, requested_signer_timezone = self._extract_submit_hash_inputs(payload)
            self._lock_request_for_update(sign_request)
            request_hash = idempotency_service.build_submit_request_hash(
                self._get_normalized_submit_values_for_idempotency(signer_sudo, parsed_values),
                consent_accepted=consent_accepted,
                consent_hash=provided_consent_hash,
                signer_timezone=requested_signer_timezone,
            )
            resolution, idempotency_record, immediate_response = self._resolve_portal_idempotency(
                signer_sudo,
                endpoint='submit',
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if resolution in {'replay', 'locked'}:
                return immediate_response
            try:
                with request.env.cr.savepoint():
                    self._assert_request_revision(sign_request, request_revision)
                    self._assert_submit_allowed(signer_sudo)
                    if self._is_otp_required_for_signer(signer_sudo) and not signer_sudo.otp_verified_at:
                        raise ValidationError(_("Email verification is required before submit."))
                    consent_hash, signer_timezone = self._check_consent_payload(payload)
                    actionable_before_ids = set(sign_request._get_actionable_signers().ids)

                    event_at = fields.Datetime.now()
                    session_changed = self._ensure_session_opened(signer_sudo, event_at=event_at)
                    _values_changed, touched_field_ids, signer_fields = self._upsert_signer_values(
                        signer_sudo,
                        parsed_values,
                        enforce_required=False,
                    )
                    self._ensure_supported_required_fields(signer_sudo, signer_fields)

                    signer_sudo.sudo().write({
                        'state': 'signed',
                        'signed_at': event_at,
                        'consent_accepted_at': event_at,
                        'consent_text_hash': consent_hash,
                        'signer_timezone': signer_timezone,
                        'ip_last': self._extract_request_ip(),
                    })
                    self._invalidate_active_otp_challenges(signer_sudo)

                    if sign_request.status in TERMINAL_REQUEST_STATUSES:
                        raise ValidationError(_("This signing request can no longer be modified."))
                    self._move_request_to_partially_signed(sign_request, event_at=event_at)
                    sign_request.sudo().write({
                        'lock_version': sign_request.lock_version + 1,
                        'last_event_at': event_at,
                    })
                    self._append_audit_event(
                        signer_sudo,
                        'signer_submitted',
                        event_at=event_at,
                        metadata={
                            'field_ids': touched_field_ids,
                            'field_count': len(touched_field_ids),
                            'session_opened': bool(session_changed),
                            'idempotency_key': idempotency_key,
                        },
                        consent_text_hash=consent_hash,
                    )
                    newly_actionable_signers = self._get_newly_actionable_pending_signers(
                        sign_request,
                        actionable_before_ids,
                    )
                    response = self._build_jsonrpc_success_redirect(
                        signer_id=signer_sudo.id,
                        access_token=auth_context.effective_access_token,
                        request_revision=sign_request.lock_version,
                        query_flag='submitted=1',
                    )
            except Exception:
                idempotency_service.mark_failed(idempotency_record)
                raise
            idempotency_service.mark_completed(idempotency_record, response)

            self._queue_best_effort_next_wave_invitations(sign_request, newly_actionable_signers)
            return response
        except MissingError:
            return self._invalid_token_response()
        except AccessError as exc:
            return self._jsonrpc_error_from_access(
                exc,
                allow_order_block=True,
                allow_consent=True,
                allow_expired_token=True,
            )
        except LockNotAvailable:
            return self._jsonrpc_request_locked_response()
        except ValidationError as exc:
            return self._jsonrpc_error_from_validation(
                exc,
                allow_contract_message=True,
                allow_idempotency_conflict=True,
            )

    @http.route(['/my/sign/<int:signer_id>/decline'], type='jsonrpc', auth='public')
    def portal_sign_decline(self, signer_id, access_token=None, **payload):
        access_token = self._resolve_access_token(access_token, payload=payload)
        try:
            auth_context = self._check_signer_identity_access(
                signer_id,
                access_token=access_token,
                entrypoint='decline',
            )
            signer_sudo = auth_context.signer
            request_revision, normalized_reason, idempotency_key = self._validate_decline_payload(payload)
            sign_request = signer_sudo.request_id.sudo()
            response = False
            self._lock_request_for_update(sign_request)
            request_hash = idempotency_service.build_decline_request_hash(normalized_reason)
            resolution, idempotency_record, immediate_response = self._resolve_portal_idempotency(
                signer_sudo,
                endpoint='decline',
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if resolution in {'replay', 'locked'}:
                return immediate_response
            try:
                with request.env.cr.savepoint():
                    self._assert_request_revision(sign_request, request_revision)
                    self._assert_locked_signer_decline_allowed(signer_sudo)

                    event_at = fields.Datetime.now()
                    request_status_before = sign_request.status
                    signer_state_before = signer_sudo.state
                    signer_sudo.sudo().write({
                        'state': 'declined',
                        'declined_reason': normalized_reason,
                        'ip_last': self._extract_request_ip(),
                    })
                    self._invalidate_active_otp_challenges(signer_sudo)
                    sign_request._transition_to('declined', {'last_event_at': event_at})
                    sign_request.sudo().write({
                        'lock_version': sign_request.lock_version + 1,
                        'last_event_at': event_at,
                    })
                    self._append_audit_event(
                        signer_sudo,
                        'signer_declined',
                        event_at=event_at,
                        metadata={
                            'reason': normalized_reason,
                            'request_status_before': request_status_before,
                            'signer_state_before': signer_state_before,
                            'idempotency_key': idempotency_key,
                        },
                    )
                    response = self._build_jsonrpc_success_redirect(
                        signer_id=signer_sudo.id,
                        access_token=auth_context.effective_access_token,
                        request_revision=sign_request.lock_version,
                        query_flag='declined=1',
                    )
            except Exception:
                idempotency_service.mark_failed(idempotency_record)
                raise
            idempotency_service.mark_completed(idempotency_record, response)

            self._queue_best_effort_decline_notification(sign_request, signer_sudo)
            return response
        except MissingError:
            return self._invalid_token_response()
        except AccessError as exc:
            return self._jsonrpc_error_from_access(exc, allow_expired_token=True)
        except LockNotAvailable:
            return self._jsonrpc_request_locked_response()
        except ValidationError as exc:
            return self._jsonrpc_error_from_validation(
                exc,
                allow_contract_message=True,
                allow_idempotency_conflict=True,
            )

    @http.route(['/my/sign/<int:signer_id>/otp/request'], type='jsonrpc', auth='public')
    def portal_sign_otp_request(self, signer_id, access_token=None, **payload):
        access_token = self._resolve_access_token(access_token, payload=payload)
        signer_sudo = False
        try:
            auth_context = self._check_signer_identity_access(
                signer_id,
                access_token=access_token,
                entrypoint='otp_request',
            )
            signer_sudo = auth_context.signer
            request_revision = self._validate_otp_request_payload(payload)
            sign_request = signer_sudo.request_id.sudo()
            with request.env.cr.savepoint():
                self._lock_request_for_update(sign_request)
                self._assert_request_revision(sign_request, request_revision)
                self._assert_locked_signer_otp_allowed(signer_sudo, action='request')

                event_at = fields.Datetime.now()
                request_status_before = sign_request.status
                signer_state_before = signer_sudo.state
                challenge = otp_service.request_otp_challenge(signer_sudo, trigger='otp_request')
                sign_request.sudo().write({
                    'lock_version': sign_request.lock_version + 1,
                    'last_event_at': event_at,
                })
                self._append_audit_event(
                    signer_sudo,
                    'otp_requested',
                    event_at=event_at,
                    metadata={
                        'expires_at': fields.Datetime.to_string(challenge.expires_at),
                        'delivery_channel': 'email',
                        'request_status_before': request_status_before,
                        'signer_state_before': signer_state_before,
                    },
                )

            return self._build_jsonrpc_success_redirect(
                signer_id=signer_sudo.id,
                access_token=auth_context.effective_access_token,
                request_revision=sign_request.lock_version,
                query_flag='otp_requested=1',
            )
        except notification_service.NotificationQueueFailure as exc:
            notification_service.append_durable_notification_failure(
                signer_sudo.request_id.id,
                registry=request.env.registry,
                env=request.env,
                signer_id=signer_sudo.id,
                notification_type='otp',
                recipient_kind='signer',
                recipient_email=signer_sudo.email,
                trigger='otp_request',
                template_xmlid=notification_service.OTP_TEMPLATE_XMLID,
                reason=exc.reason,
                event_at=fields.Datetime.now(),
            )
            return self._build_error_response('validation_error', exc.display_message)
        except MissingError:
            return self._invalid_token_response()
        except AccessError as exc:
            return self._jsonrpc_error_from_access(exc, allow_order_block=True, allow_expired_token=True)
        except LockNotAvailable:
            return self._jsonrpc_request_locked_response()
        except ValidationError as exc:
            return self._jsonrpc_error_from_validation(exc)

    @http.route(['/my/sign/<int:signer_id>/otp/verify'], type='jsonrpc', auth='public')
    def portal_sign_otp_verify(self, signer_id, access_token=None, **payload):
        access_token = self._resolve_access_token(access_token, payload=payload)
        try:
            auth_context = self._check_signer_identity_access(
                signer_id,
                access_token=access_token,
                entrypoint='otp_verify',
            )
            signer_sudo = auth_context.signer
            request_revision, normalized_code = self._validate_otp_verify_payload(payload)
            sign_request = signer_sudo.request_id.sudo()
            with request.env.cr.savepoint():
                self._lock_request_for_update(sign_request)
                self._assert_request_revision(sign_request, request_revision)
                self._assert_locked_signer_otp_allowed(signer_sudo, action='verify')

                request_status_before = sign_request.status
                signer_state_before = signer_sudo.state
                try:
                    challenge, attempt_count_before, verified_at = otp_service.verify_otp_challenge(
                        signer_sudo,
                        normalized_code,
                        trigger='otp_verify',
                    )
                except ValidationError as exc:
                    # Invalid attempts must persist challenge attempt counters.
                    return self._jsonrpc_error_from_validation(exc)
                signer_sudo.sudo().write({
                    'otp_verified_at': verified_at,
                    'ip_last': self._extract_request_ip(),
                })
                sign_request.sudo().write({
                    'lock_version': sign_request.lock_version + 1,
                    'last_event_at': verified_at,
                })
                self._append_audit_event(
                    signer_sudo,
                    'otp_verified',
                    event_at=verified_at,
                    metadata={
                        'delivery_channel': 'email',
                        'request_status_before': request_status_before,
                        'signer_state_before': signer_state_before,
                        'attempt_count_before': attempt_count_before,
                    },
                )
            return self._build_jsonrpc_success_otp_verified(
                signer_id=signer_sudo.id,
                access_token=auth_context.effective_access_token,
                request_revision=sign_request.lock_version,
            )
        except MissingError:
            return self._invalid_token_response()
        except AccessError as exc:
            return self._jsonrpc_error_from_access(exc, allow_order_block=True, allow_expired_token=True)
        except LockNotAvailable:
            return self._jsonrpc_request_locked_response()
        except ValidationError as exc:
            return self._jsonrpc_error_from_validation(exc)
