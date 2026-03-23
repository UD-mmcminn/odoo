# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import hashlib
import uuid

from psycopg2.errors import LockNotAvailable
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED

import odoo.sql_db
from odoo import SUPERUSER_ID, _, api, fields, models, modules
from odoo.addons.open_sign.models.sign_request_signer import PENDING_CORRECTION_REQUEST_STATUSES
from odoo.exceptions import AccessError, ValidationError
from odoo.orm.environments import Transaction
from odoo.tools import consteq

from odoo.addons.open_sign_portal.services import otp_service


EMAIL_TOKEN_TTL_HOURS = 72
EMAIL_TOKEN_ROTATION_TRIGGERS = {'initial_send', 'wave_unblocked', 'manual_resend'}
TOKEN_CONTROL_FIELDS = {
    'access_token',
    'email_token_issued_at',
    'email_token_expires_at',
    'email_token_revoked_at',
}


class OpenSignRequestSigner(models.Model):
    _name = 'open.sign.request.signer'
    _inherit = ['open.sign.request.signer', 'portal.mixin']

    access_token = fields.Char(groups='base.group_system')
    portal_sign_url = fields.Char(
        string='Portal Link',
        compute='_compute_portal_sign_url',
        compute_sudo=True,
        readonly=True,
        groups='open_sign.group_open_sign_user,open_sign.group_open_sign_manager',
    )
    otp_required = fields.Boolean(
        string='Require Email OTP',
        default=False,
        index=True,
        groups='open_sign.group_open_sign_user,open_sign.group_open_sign_manager',
    )
    otp_verified_at = fields.Datetime(
        string='OTP Verified At',
        index=True,
        readonly=True,
        groups='open_sign.group_open_sign_user,open_sign.group_open_sign_manager',
    )
    email_token_issued_at = fields.Datetime(
        string='Email Token Issued At',
        readonly=True,
        index=True,
        groups='open_sign.group_open_sign_manager',
    )
    email_token_expires_at = fields.Datetime(
        string='Email Token Expires At',
        readonly=True,
        index=True,
        groups='open_sign.group_open_sign_manager',
    )
    email_token_revoked_at = fields.Datetime(
        string='Email Token Revoked At',
        readonly=True,
        index=True,
        groups='open_sign.group_open_sign_manager',
    )

    def _get_portal_sign_path(self):
        self.ensure_one()
        return f"/my/sign/{self.id}"

    def _compute_access_url(self):
        for signer in self:
            signer.access_url = signer._get_portal_sign_path() if signer.id else False

    def _compute_portal_sign_url(self):
        for signer in self:
            signer.portal_sign_url = signer._get_backend_portal_sign_url()

    def _get_notification_sign_url(self):
        self.ensure_one()
        return self.get_portal_url() if self.id else False

    def _supports_portal_resend_rotation(self):
        self.ensure_one()
        return True

    def _rotate_portal_token(self):
        self.ensure_one()
        new_token = str(uuid.uuid4())
        self.sudo().write({'access_token': new_token})
        return new_token

    def _compute_email_token_expires_at(self, issued_at):
        self.ensure_one()
        issued_at = fields.Datetime.to_datetime(issued_at or fields.Datetime.now())
        expires_at = issued_at + timedelta(hours=EMAIL_TOKEN_TTL_HOURS)
        request_expires_at = fields.Datetime.to_datetime(self.request_id.expires_at) if self.request_id.expires_at else False
        if request_expires_at and request_expires_at < expires_at:
            return request_expires_at
        return expires_at

    def _has_revoked_email_token(self):
        self.ensure_one()
        return bool(self.email_token_revoked_at)

    def _is_email_token_metadata_expired(self, *, now=None):
        self.ensure_one()
        now = fields.Datetime.to_datetime(now or fields.Datetime.now())
        if not self.email_token_issued_at or not self.email_token_expires_at:
            return True
        expires_at = fields.Datetime.to_datetime(self.email_token_expires_at)
        return expires_at <= now

    def _classify_current_email_token_access(self, access_token, *, now=None):
        self.ensure_one()
        signer = self.sudo()
        if not access_token or not signer.access_token or not consteq(signer.access_token, access_token):
            return 'invalid'
        if signer._has_revoked_email_token():
            return 'revoked'
        if not signer.email_token_issued_at or not signer.email_token_expires_at:
            return 'invalid'
        if signer._is_email_token_metadata_expired(now=now):
            return 'expired'
        return 'valid'

    def _is_current_email_token_active(self, *, now=None):
        self.ensure_one()
        return self._classify_current_email_token_access(self.access_token, now=now) == 'valid'

    @api.model
    def _format_email_token_audit_datetime(self, value):
        datetime_value = fields.Datetime.to_datetime(value) if value else False
        return datetime_value.strftime('%Y-%m-%d %H:%M:%S.%f') if datetime_value else False

    def _get_current_email_token_audit_identity(self):
        self.ensure_one()
        signer = self.sudo()
        if not signer.email_token_issued_at:
            return False
        latest_issue_event = self.env['open.sign.audit.log'].sudo().search([
            ('request_id', '=', signer.request_id.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'token_issued'),
        ], order='event_sequence desc, id desc', limit=1)
        return {
            'token_audit_sequence': latest_issue_event.event_sequence or False,
            'token_issued_at_utc': signer._format_email_token_audit_datetime(signer.email_token_issued_at),
            'token_expires_at_utc': signer._format_email_token_audit_datetime(signer.email_token_expires_at),
            'token_revoked_at_utc': signer._format_email_token_audit_datetime(signer.email_token_revoked_at),
        }

    @staticmethod
    def _token_audit_lock_hash(lock_key_text):
        digest = hashlib.blake2s(lock_key_text.encode('utf-8'), digest_size=4).digest()
        return int.from_bytes(digest, 'big', signed=True)

    def _lock_email_token_audit_event_key(self, event_type, *, token_identity, rejection_code=False):
        self.ensure_one()
        identity_key = (
            token_identity.get('token_audit_sequence')
            or token_identity.get('token_issued_at_utc')
            or 'no-token-identity'
        )
        lock_key_text = f"{self.id}:{event_type}:{identity_key}:{rejection_code or ''}"
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            [int(self.id) & 0x7FFFFFFF, self._token_audit_lock_hash(lock_key_text)],
        )

    def _run_email_token_audit_operation(self, callback, *, force_isolated=False):
        self.ensure_one()
        if force_isolated:
            if self.env.cr.readonly:
                if modules.module.current_test:
                    return False
                cr = odoo.sql_db.db_connect(self.env.registry.db_name).cursor()
                cr.connection.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
                cr.transaction = Transaction(self.env.registry)
                try:
                    audit_env = api.Environment(cr, SUPERUSER_ID, dict(self.env.context))
                    try:
                        result = callback(audit_env)
                        cr.commit()
                        return result
                    except ValidationError as exc:
                        cr.rollback()
                        if str(exc) != _("Audit request does not exist."):
                            raise
                        return False
                    except Exception:
                        cr.rollback()
                        raise
                    finally:
                        audit_env.clear()
                finally:
                    cr.close()
            with self.env.registry.cursor() as cr:
                audit_env = api.Environment(cr, SUPERUSER_ID, dict(self.env.context))
                try:
                    result = callback(audit_env)
                    cr.commit()
                    return result
                except ValidationError as exc:
                    cr.rollback()
                    if str(exc) != _("Audit request does not exist."):
                        raise
                    return callback(self.env)
                except Exception:
                    cr.rollback()
                    raise
                finally:
                    audit_env.clear()
        return callback(self.env)

    def _append_email_token_audit_event(
        self,
        event_type,
        *,
        event_at,
        metadata=None,
        ip=False,
        user_agent=False,
        force_isolated=False,
    ):
        self.ensure_one()
        append_kwargs = {
            'request_id': self.request_id.id,
            'signer_id': self.id,
            'event_type': event_type,
            'metadata': metadata or {},
            'event_at': event_at,
            'ip': ip or False,
            'user_agent': user_agent or False,
        }
        return self._run_email_token_audit_operation(
            lambda audit_env: audit_env['open.sign.audit.log'].sudo().append_event(**append_kwargs),
            force_isolated=force_isolated,
        )

    def _has_email_token_audit_event(
        self,
        event_type,
        *,
        token_identity,
        rejection_code=False,
        request_id=False,
        signer_id=False,
    ):
        self.ensure_one()
        request_id = request_id or self.request_id.id
        signer_id = signer_id or self.id
        token_audit_sequence = token_identity.get('token_audit_sequence')
        token_issued_at_utc = token_identity.get('token_issued_at_utc')
        token_expires_at_utc = token_identity.get('token_expires_at_utc')
        if not token_issued_at_utc:
            return False
        audit_logs = self.env['open.sign.audit.log'].sudo().search([
            ('request_id', '=', request_id),
            ('signer_id', '=', signer_id),
            ('event_type', '=', event_type),
        ])
        for audit_log in audit_logs:
            metadata = audit_log.metadata_json or {}
            if token_audit_sequence and metadata.get('token_audit_sequence') != token_audit_sequence:
                continue
            if metadata.get('token_issued_at_utc') != token_issued_at_utc:
                continue
            if token_expires_at_utc and metadata.get('token_expires_at_utc') != token_expires_at_utc:
                continue
            if rejection_code and metadata.get('rejection_code') != rejection_code:
                continue
            return True
        return False

    def _append_email_token_audit_event_once(
        self,
        event_type,
        *,
        token_identity,
        event_at,
        metadata=None,
        rejection_code=False,
        ip=False,
        user_agent=False,
        force_isolated=False,
    ):
        self.ensure_one()
        if not token_identity:
            return False
        append_kwargs = {
            'request_id': self.request_id.id,
            'signer_id': self.id,
            'event_type': event_type,
            'metadata': metadata or {},
            'event_at': event_at,
            'ip': ip or False,
            'user_agent': user_agent or False,
        }

        def _append_once(audit_env):
            audit_signer = audit_env['open.sign.request.signer'].browse(self.id)
            audit_signer._lock_email_token_audit_event_key(
                event_type,
                token_identity=token_identity,
                rejection_code=rejection_code,
            )
            if audit_signer._has_email_token_audit_event(
                event_type,
                token_identity=token_identity,
                rejection_code=rejection_code,
                request_id=append_kwargs['request_id'],
                signer_id=append_kwargs['signer_id'],
            ):
                return False
            return audit_env['open.sign.audit.log'].sudo().append_event(**append_kwargs)

        return self._run_email_token_audit_operation(
            _append_once,
            force_isolated=force_isolated,
        )

    def _append_token_opened_if_needed(
        self,
        *,
        entrypoint,
        token_identity,
        event_at,
        ip=False,
        user_agent=False,
        force_isolated=False,
    ):
        self.ensure_one()
        if not token_identity:
            return False
        return self._append_email_token_audit_event_once(
            'token_opened',
            token_identity=token_identity,
            event_at=event_at,
            ip=ip,
            user_agent=user_agent,
            force_isolated=force_isolated,
            metadata={
                'entrypoint': entrypoint,
                'token_audit_sequence': token_identity.get('token_audit_sequence'),
                'token_issued_at_utc': token_identity.get('token_issued_at_utc'),
                'token_expires_at_utc': token_identity.get('token_expires_at_utc'),
                'request_status_before': self.request_id.status,
                'signer_state_before': self.state,
            },
        )

    def _append_token_rejected_if_needed(
        self,
        *,
        entrypoint,
        token_state,
        rejection_code,
        token_identity,
        event_at,
        ip=False,
        user_agent=False,
        force_isolated=True,
    ):
        self.ensure_one()
        if not token_identity:
            return False
        return self._append_email_token_audit_event_once(
            'token_rejected',
            token_identity=token_identity,
            event_at=event_at,
            ip=ip,
            user_agent=user_agent,
            rejection_code=rejection_code,
            force_isolated=force_isolated,
            metadata={
                'entrypoint': entrypoint,
                'rejection_code': rejection_code,
                'token_state': token_state,
                'token_audit_sequence': token_identity.get('token_audit_sequence'),
                'token_issued_at_utc': token_identity.get('token_issued_at_utc'),
                'token_expires_at_utc': token_identity.get('token_expires_at_utc'),
                'request_status_before': self.request_id.status,
                'signer_state_before': self.state,
            },
        )

    def _append_token_revoked_if_needed(
        self,
        *,
        reason,
        event_at,
        issued_at_utc,
        expires_at_utc,
        request_status_before,
        signer_state_before,
    ):
        self.ensure_one()
        if not issued_at_utc:
            return False
        return self._append_email_token_audit_event(
            'token_revoked',
            event_at=event_at,
            metadata={
                'reason': reason,
                'token_audit_sequence': self._get_current_email_token_audit_identity()['token_audit_sequence'],
                'token_issued_at_utc': issued_at_utc,
                'token_expires_at_utc': expires_at_utc,
                'token_revoked_at_utc': self._format_email_token_audit_datetime(event_at),
                'request_status_before': request_status_before,
                'signer_state_before': signer_state_before,
            },
        )

    def _get_current_distributed_portal_url(self, *, now=None):
        self.ensure_one()
        signer = self.sudo()
        if not signer.id or not signer.access_token or signer._has_revoked_email_token():
            return False
        if not signer.email_token_issued_at or not signer.email_token_expires_at:
            return False
        if signer._is_email_token_metadata_expired(now=now):
            return False
        return f"{signer._get_portal_sign_path()}?access_token={signer.access_token}"

    def _issue_email_portal_token(self, *, trigger, now=None, force_rotate=False):
        self.ensure_one()
        signer = self.sudo()
        now = fields.Datetime.to_datetime(now or fields.Datetime.now())
        request_status_before = signer.request_id.status
        signer_state_before = signer.state
        should_rotate = (
            force_rotate
            or trigger in EMAIL_TOKEN_ROTATION_TRIGGERS
            or not signer.access_token
            or signer._has_revoked_email_token()
            or signer._is_email_token_metadata_expired(now=now)
        )
        if should_rotate:
            signer.write({
                'access_token': str(uuid.uuid4()),
                'email_token_issued_at': now,
                'email_token_expires_at': signer._compute_email_token_expires_at(now),
                'email_token_revoked_at': False,
            })
            identity = signer._get_current_email_token_audit_identity()
            signer._append_email_token_audit_event(
                'token_issued',
                event_at=now,
                metadata={
                    'trigger': trigger,
                    'token_issued_at_utc': identity['token_issued_at_utc'],
                    'token_expires_at_utc': identity['token_expires_at_utc'],
                    'request_status_before': request_status_before,
                    'signer_state_before': signer_state_before,
                },
            )
        return signer.get_portal_url() if signer.id else False

    def _revoke_email_portal_token(self, *, now=None):
        self.ensure_one()
        signer = self.sudo()
        signer.write({
            'access_token': str(uuid.uuid4()),
            'email_token_revoked_at': fields.Datetime.to_datetime(now or fields.Datetime.now()),
        })
        signer._invalidate_portal_security_state_on_manual_resend(email_changed=False)

    def _get_backend_portal_sign_url(self):
        self.ensure_one()
        return self._get_current_distributed_portal_url()

    def _get_notification_sign_url_for_delivery(self, *, notification_type, trigger):
        self.ensure_one()
        del notification_type
        if not self.id:
            return False
        if (
            trigger == 'manual_resend'
            and self.env.context.get('open_sign_manual_resend_reuse_current_token')
        ):
            current_url = self._get_current_distributed_portal_url()
            if current_url:
                return current_url
        if trigger in EMAIL_TOKEN_ROTATION_TRIGGERS:
            return self._issue_email_portal_token(trigger=trigger, force_rotate=True)
        if trigger == 'cron_reminder':
            signer = self.sudo()
            if (
                signer.access_token
                and not signer._has_revoked_email_token()
                and not signer._is_email_token_metadata_expired()
            ):
                return signer.get_portal_url()
            return signer._issue_email_portal_token(trigger=trigger)
        return self._get_notification_sign_url()

    def _invalidate_portal_security_state_on_manual_resend(self, *, email_changed=False):
        self.ensure_one()
        otp_service.invalidate_active_challenges(self.sudo(), verified_too=True)
        if email_changed and self.otp_verified_at:
            self.sudo().write({'otp_verified_at': False})

    def _check_portal_token_revoke_allowed(self):
        self.ensure_one()
        if not self.env.user.has_group("open_sign.group_open_sign_manager"):
            raise AccessError(_("Only Open Sign Managers can revoke signer links."))
        if not self._supports_portal_resend_rotation():
            raise ValidationError(_("Install Open Sign Portal to revoke signer invitation links."))
        if self.request_id.status not in PENDING_CORRECTION_REQUEST_STATUSES:
            raise ValidationError(_("Signer links can only be revoked while the request is versioned or actively awaiting signatures."))
        if self.state != 'pending':
            raise ValidationError(_("Only pending signer links can be revoked."))

    def _lock_request_for_update_nowait(self):
        self.ensure_one()
        self.env.cr.execute(
            'SELECT id FROM open_sign_request WHERE id = %s FOR UPDATE NOWAIT',
            [self.request_id.id],
        )

    def action_revoke_signer_portal_token(self):
        self.ensure_one()
        signer = self.with_user(self.env.user)
        signer._check_portal_token_revoke_allowed()
        audit_identity = signer.sudo()._get_current_email_token_audit_identity()
        request_status_before = signer.request_id.status
        signer_state_before = signer.state
        already_revoked = bool(signer.email_token_revoked_at)
        try:
            with self.env.cr.savepoint():
                try:
                    signer._lock_request_for_update_nowait()
                except LockNotAvailable as exc:
                    raise ValidationError(_("The signing request is currently locked. Try again.")) from exc
                event_at = fields.Datetime.now()
                signer.sudo()._revoke_email_portal_token(now=event_at)
                if audit_identity and not already_revoked:
                    signer.sudo()._append_token_revoked_if_needed(
                        reason='manager_revoke',
                        event_at=event_at,
                        issued_at_utc=audit_identity['token_issued_at_utc'],
                        expires_at_utc=audit_identity['token_expires_at_utc'],
                        request_status_before=request_status_before,
                        signer_state_before=signer_state_before,
                    )
        except (AccessError, ValidationError):
            raise
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Signer Link Revoked'),
                'message': _('The current signer link is now invalid. A new invitation will require resend.'),
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def _can_manage_portal_token_fields(self):
        return self.env.su

    @api.model
    def _guard_portal_token_mutation(self, vals):
        if self._can_manage_portal_token_fields():
            return
        if TOKEN_CONTROL_FIELDS.intersection(vals):
            raise AccessError(_("Signer portal token fields cannot be modified directly."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._guard_portal_token_mutation(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._guard_portal_token_mutation(vals)
        return super().write(vals)
