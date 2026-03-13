# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


INVITATION_TEMPLATE_XMLID = 'open_sign.mail_template_signer_invitation'
REMINDER_TEMPLATE_XMLID = 'open_sign.mail_template_signer_reminder'
COMPLETION_SIGNER_TEMPLATE_XMLID = 'open_sign.mail_template_request_completed_signer'
COMPLETION_OWNER_TEMPLATE_XMLID = 'open_sign.mail_template_request_completed_owner'
DECLINE_OWNER_TEMPLATE_XMLID = 'open_sign.mail_template_request_declined_owner'
OTP_TEMPLATE_XMLID = 'open_sign.mail_template_signer_otp_code'
MAIL_LAYOUT_XMLID = 'mail.mail_notification_light'
FAILURE_REASON_MISSING_TEMPLATE = 'missing_template'
FAILURE_REASON_SIGNER_NOTIFICATION_URL_UNAVAILABLE = 'signer_notification_url_unavailable'
FAILURE_REASON_MAIL_QUEUE_ERROR = 'mail_queue_error'
FAILURE_REASON_NOTIFICATION_SERVICE_ERROR = 'notification_service_error'

_logger = logging.getLogger(__name__)


class NotificationQueueFailure(Exception):
    def __init__(
        self,
        *,
        notification_type,
        recipient_kind,
        recipient_email,
        template_xmlid,
        signer_id=False,
        reason,
        display_message,
    ):
        super().__init__(display_message)
        self.notification_type = notification_type
        self.recipient_kind = recipient_kind
        self.recipient_email = recipient_email or False
        self.template_xmlid = template_xmlid
        self.signer_id = signer_id or False
        self.reason = reason
        self.display_message = display_message


def _log_notification_exception(
    notification_type,
    trigger,
    exc,
    *,
    request_id=False,
    signer_id=False,
    template_xmlid=False,
):
    _logger.exception(
        "Notification failure type=%s trigger=%s request_id=%s signer_id=%s template=%s",
        notification_type,
        trigger,
        request_id or False,
        signer_id or False,
        template_xmlid or False,
        exc_info=exc,
    )


def _append_audit_event(sign_request, event_type, *, signer=False, metadata=None, event_at=None):
    return sign_request.env['open.sign.audit.log'].sudo().append_event(
        request_id=sign_request.id,
        signer_id=signer.id if signer else False,
        event_type=event_type,
        metadata=metadata or {},
        event_at=event_at or fields.Datetime.now(),
    )


def _append_notification_event(
    sign_request,
    *,
    event_type,
    notification_type,
    recipient_kind,
    recipient_email,
    trigger,
    template_xmlid,
    signer=False,
    mail_mail_id=False,
    reason=False,
):
    metadata = {
        'notification_type': notification_type,
        'recipient_kind': recipient_kind,
        'recipient_email': recipient_email or False,
        'trigger': trigger,
        'template_xmlid': template_xmlid,
    }
    if mail_mail_id:
        metadata['mail_mail_id'] = mail_mail_id
    if event_type == 'notification_skipped' and reason:
        metadata['skip_reason'] = reason
    elif event_type == 'notification_failed' and reason:
        metadata['failure_reason'] = reason
    return _append_audit_event(sign_request, event_type, signer=signer, metadata=metadata)


def _get_template(env, template_xmlid, *, notification_type, raise_on_failure):
    template = env.ref(template_xmlid, raise_if_not_found=False)
    if template:
        return template.sudo()
    display_message = _(
        "Notification template is missing for %(notification_type)s.",
        notification_type=notification_type,
    )
    if raise_on_failure:
        raise NotificationQueueFailure(
            notification_type=notification_type,
            recipient_kind='signer',
            recipient_email=False,
            template_xmlid=template_xmlid,
            signer_id=False,
            reason=FAILURE_REASON_MISSING_TEMPLATE,
            display_message=display_message,
        )
    return False


def _normalize_email(email_value):
    normalized = email_normalize((email_value or '').strip())
    return normalized or False


def _queue_template(
    template,
    record,
    *,
    email_to,
    email_values=None,
    context=None,
    raise_on_failure=False,
):
    if not template:
        return False
    return template.with_context(context or {}).send_mail(
        record.id,
        force_send=False,
        raise_exception=raise_on_failure,
        email_values=email_values or {'email_to': email_to},
        email_layout_xmlid=MAIL_LAYOUT_XMLID,
    )


def append_durable_notification_failure(
    request_id,
    *,
    registry,
    env=False,
    signer_id=False,
    notification_type,
    recipient_kind,
    recipient_email,
    trigger,
    template_xmlid,
    reason,
    event_at=None,
):
    try:
        with registry.cursor() as cr:
            audit_env = api.Environment(cr, api.SUPERUSER_ID, {})
            audit_env['open.sign.audit.log'].sudo().append_event(
                request_id=request_id,
                signer_id=signer_id or False,
                event_type='notification_failed',
                metadata={
                    'notification_type': notification_type,
                    'recipient_kind': recipient_kind,
                    'recipient_email': recipient_email or False,
                    'trigger': trigger,
                    'template_xmlid': template_xmlid,
                    'failure_reason': reason,
                },
                event_at=event_at or fields.Datetime.now(),
            )
            return
    except ValidationError:
        if env:
            sign_request = env['open.sign.request'].browse(request_id).exists()
            if sign_request:
                sign_request._append_audit_event(
                    'notification_failed',
                    signer=env['open.sign.request.signer'].browse(signer_id).exists() if signer_id else False,
                    metadata={
                        'notification_type': notification_type,
                        'recipient_kind': recipient_kind,
                        'recipient_email': recipient_email or False,
                        'trigger': trigger,
                        'template_xmlid': template_xmlid,
                        'failure_reason': reason,
                    },
                    event_at=event_at or fields.Datetime.now(),
                )
                return
        _logger.exception(
            "Failed to persist durable notification failure audit for request %s",
            request_id,
        )
    except Exception:  # pragma: no cover - defensive logging around auxiliary audit cursor
        _logger.exception(
            "Failed to persist durable notification failure audit for request %s",
            request_id,
        )


def queue_request_invitations(sign_request, signers, *, trigger, raise_on_failure):
    sign_request.ensure_one()
    signers = signers.exists()
    template = _get_template(
        sign_request.env,
        INVITATION_TEMPLATE_XMLID,
        notification_type='invitation',
        raise_on_failure=raise_on_failure,
    )
    queued_mail_ids = []
    if not template:
        for signer in signers:
            _append_notification_event(
                sign_request,
                event_type='notification_failed',
                notification_type='invitation',
                recipient_kind='signer',
                recipient_email=_normalize_email(signer.email),
                trigger=trigger,
                template_xmlid=INVITATION_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_MISSING_TEMPLATE,
            )
        return queued_mail_ids
    for signer in signers:
        recipient_email = _normalize_email(signer.email)
        notification_url = signer._get_notification_sign_url()
        if not notification_url:
            if raise_on_failure:
                raise NotificationQueueFailure(
                    notification_type='invitation',
                    recipient_kind='signer',
                    recipient_email=recipient_email,
                    template_xmlid=INVITATION_TEMPLATE_XMLID,
                    signer_id=signer.id,
                    reason=FAILURE_REASON_SIGNER_NOTIFICATION_URL_UNAVAILABLE,
                    display_message=_("Signer notification URL is not available."),
                )
            _append_notification_event(
                sign_request,
                event_type='notification_skipped',
                notification_type='invitation',
                recipient_kind='signer',
                recipient_email=recipient_email,
                trigger=trigger,
                template_xmlid=INVITATION_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_SIGNER_NOTIFICATION_URL_UNAVAILABLE,
            )
            continue
        try:
            mail_mail_id = _queue_template(
                template,
                signer,
                email_to=recipient_email,
                email_values={'email_to': recipient_email},
                context={
                    'signer_portal_url': notification_url,
                    'otp_required': bool('otp_required' in signer._fields and signer.otp_required),
                },
                raise_on_failure=raise_on_failure,
            )
        except Exception as exc:  # pragma: no cover - exception type depends on mail internals
            _log_notification_exception(
                'invitation',
                trigger,
                exc,
                request_id=sign_request.id,
                signer_id=signer.id,
                template_xmlid=INVITATION_TEMPLATE_XMLID,
            )
            if raise_on_failure:
                raise NotificationQueueFailure(
                    notification_type='invitation',
                    recipient_kind='signer',
                    recipient_email=recipient_email,
                    template_xmlid=INVITATION_TEMPLATE_XMLID,
                    signer_id=signer.id,
                    reason=FAILURE_REASON_MAIL_QUEUE_ERROR,
                    display_message=_("Failed to queue the invitation email."),
                ) from exc
            _append_notification_event(
                sign_request,
                event_type='notification_failed',
                notification_type='invitation',
                recipient_kind='signer',
                recipient_email=recipient_email,
                trigger=trigger,
                template_xmlid=INVITATION_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_MAIL_QUEUE_ERROR,
            )
            continue
        _append_notification_event(
            sign_request,
            event_type='notification_queued',
            notification_type='invitation',
            recipient_kind='signer',
            recipient_email=recipient_email,
            trigger=trigger,
            template_xmlid=INVITATION_TEMPLATE_XMLID,
            signer=signer,
            mail_mail_id=mail_mail_id,
        )
        queued_mail_ids.append(mail_mail_id)
    return queued_mail_ids


def queue_request_reminders(sign_request, signers, *, trigger, raise_on_failure=False):
    sign_request.ensure_one()
    signers = signers.exists()
    template = _get_template(
        sign_request.env,
        REMINDER_TEMPLATE_XMLID,
        notification_type='reminder',
        raise_on_failure=raise_on_failure,
    )
    queued_mail_ids = []
    if not template:
        for signer in signers:
            _append_notification_event(
                sign_request,
                event_type='notification_failed',
                notification_type='reminder',
                recipient_kind='signer',
                recipient_email=_normalize_email(signer.email),
                trigger=trigger,
                template_xmlid=REMINDER_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_MISSING_TEMPLATE,
            )
        return queued_mail_ids
    for signer in signers:
        recipient_email = _normalize_email(signer.email)
        notification_url = signer._get_notification_sign_url()
        if not notification_url:
            _append_notification_event(
                sign_request,
                event_type='notification_skipped',
                notification_type='reminder',
                recipient_kind='signer',
                recipient_email=recipient_email,
                trigger=trigger,
                template_xmlid=REMINDER_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_SIGNER_NOTIFICATION_URL_UNAVAILABLE,
            )
            continue
        try:
            mail_mail_id = _queue_template(
                template,
                signer,
                email_to=recipient_email,
                email_values={'email_to': recipient_email},
                context={
                    'signer_portal_url': notification_url,
                    'otp_required': bool('otp_required' in signer._fields and signer.otp_required),
                },
                raise_on_failure=raise_on_failure,
            )
        except Exception as exc:  # pragma: no cover - exception type depends on mail internals
            _log_notification_exception(
                'reminder',
                trigger,
                exc,
                request_id=sign_request.id,
                signer_id=signer.id,
                template_xmlid=REMINDER_TEMPLATE_XMLID,
            )
            _append_notification_event(
                sign_request,
                event_type='notification_failed',
                notification_type='reminder',
                recipient_kind='signer',
                recipient_email=recipient_email,
                trigger=trigger,
                template_xmlid=REMINDER_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_MAIL_QUEUE_ERROR,
            )
            if raise_on_failure:
                raise
            continue
        _append_notification_event(
            sign_request,
            event_type='notification_queued',
            notification_type='reminder',
            recipient_kind='signer',
            recipient_email=recipient_email,
            trigger=trigger,
            template_xmlid=REMINDER_TEMPLATE_XMLID,
            signer=signer,
            mail_mail_id=mail_mail_id,
        )
        queued_mail_ids.append(mail_mail_id)
    return queued_mail_ids


def queue_request_completion_notifications(sign_request, *, raise_on_failure=False):
    sign_request.ensure_one()
    attachment_commands = [(4, sign_request.final_attachment_id.id)] if sign_request.final_attachment_id else []
    backend_url = sign_request._get_backend_form_url()
    queued_mail_ids = []

    owner_email = _normalize_email(sign_request.owner_id.partner_id.email or sign_request.owner_id.email)
    if owner_email:
        owner_template = _get_template(
            sign_request.env,
            COMPLETION_OWNER_TEMPLATE_XMLID,
            notification_type='completion',
            raise_on_failure=raise_on_failure,
        )
        if not owner_template:
            _append_notification_event(
                sign_request,
                event_type='notification_failed',
                notification_type='completion',
                recipient_kind='owner',
                recipient_email=owner_email,
                trigger='request_completed',
                template_xmlid=COMPLETION_OWNER_TEMPLATE_XMLID,
                reason=FAILURE_REASON_MISSING_TEMPLATE,
            )
        else:
            try:
                mail_mail_id = _queue_template(
                    owner_template,
                    sign_request,
                    email_to=owner_email,
                    email_values={
                        'email_to': owner_email,
                        'attachment_ids': attachment_commands,
                    },
                    context={'request_backend_url': backend_url},
                    raise_on_failure=raise_on_failure,
                )
            except Exception as exc:  # pragma: no cover - exception type depends on mail internals
                _log_notification_exception(
                    'completion',
                    'request_completed',
                    exc,
                    request_id=sign_request.id,
                    template_xmlid=COMPLETION_OWNER_TEMPLATE_XMLID,
                )
                _append_notification_event(
                    sign_request,
                    event_type='notification_failed',
                    notification_type='completion',
                    recipient_kind='owner',
                    recipient_email=owner_email,
                    trigger='request_completed',
                    template_xmlid=COMPLETION_OWNER_TEMPLATE_XMLID,
                    reason=FAILURE_REASON_MAIL_QUEUE_ERROR,
                )
            else:
                _append_notification_event(
                    sign_request,
                    event_type='notification_queued',
                    notification_type='completion',
                    recipient_kind='owner',
                    recipient_email=owner_email,
                    trigger='request_completed',
                    template_xmlid=COMPLETION_OWNER_TEMPLATE_XMLID,
                    mail_mail_id=mail_mail_id,
                )
                queued_mail_ids.append(mail_mail_id)
    else:
        _append_notification_event(
            sign_request,
            event_type='notification_skipped',
            notification_type='completion',
            recipient_kind='owner',
            recipient_email=False,
            trigger='request_completed',
            template_xmlid=COMPLETION_OWNER_TEMPLATE_XMLID,
            reason='owner_missing_email',
        )

    signer_template = _get_template(
        sign_request.env,
        COMPLETION_SIGNER_TEMPLATE_XMLID,
        notification_type='completion',
        raise_on_failure=raise_on_failure,
    )
    for signer in sign_request.signer_ids:
        recipient_email = _normalize_email(signer.email)
        notification_url = signer._get_notification_sign_url()
        if not signer_template:
            _append_notification_event(
                sign_request,
                event_type='notification_failed',
                notification_type='completion',
                recipient_kind='signer',
                recipient_email=recipient_email,
                trigger='request_completed',
                template_xmlid=COMPLETION_SIGNER_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_MISSING_TEMPLATE,
            )
            continue
        if not notification_url:
            _append_notification_event(
                sign_request,
                event_type='notification_skipped',
                notification_type='completion',
                recipient_kind='signer',
                recipient_email=recipient_email,
                trigger='request_completed',
                template_xmlid=COMPLETION_SIGNER_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_SIGNER_NOTIFICATION_URL_UNAVAILABLE,
            )
            continue
        try:
            mail_mail_id = _queue_template(
                signer_template,
                signer,
                email_to=recipient_email,
                email_values={
                    'email_to': recipient_email,
                    'attachment_ids': attachment_commands,
                },
                context={'signer_portal_url': notification_url},
                raise_on_failure=raise_on_failure,
            )
        except Exception as exc:  # pragma: no cover - exception type depends on mail internals
            _log_notification_exception(
                'completion',
                'request_completed',
                exc,
                request_id=sign_request.id,
                signer_id=signer.id,
                template_xmlid=COMPLETION_SIGNER_TEMPLATE_XMLID,
            )
            _append_notification_event(
                sign_request,
                event_type='notification_failed',
                notification_type='completion',
                recipient_kind='signer',
                recipient_email=recipient_email,
                trigger='request_completed',
                template_xmlid=COMPLETION_SIGNER_TEMPLATE_XMLID,
                signer=signer,
                reason=FAILURE_REASON_MAIL_QUEUE_ERROR,
            )
            continue
        _append_notification_event(
            sign_request,
            event_type='notification_queued',
            notification_type='completion',
            recipient_kind='signer',
            recipient_email=recipient_email,
            trigger='request_completed',
            template_xmlid=COMPLETION_SIGNER_TEMPLATE_XMLID,
            signer=signer,
            mail_mail_id=mail_mail_id,
        )
        queued_mail_ids.append(mail_mail_id)
    return queued_mail_ids


def queue_request_decline_notification(sign_request, decliner, *, raise_on_failure=False):
    sign_request.ensure_one()
    backend_url = sign_request._get_backend_form_url()
    owner_email = _normalize_email(sign_request.owner_id.partner_id.email or sign_request.owner_id.email)
    if not owner_email:
        _append_notification_event(
            sign_request,
            event_type='notification_skipped',
            notification_type='decline',
            recipient_kind='owner',
            recipient_email=False,
            trigger='request_declined',
            template_xmlid=DECLINE_OWNER_TEMPLATE_XMLID,
            reason='owner_missing_email',
        )
        return False
    template = _get_template(
        sign_request.env,
        DECLINE_OWNER_TEMPLATE_XMLID,
        notification_type='decline',
        raise_on_failure=raise_on_failure,
    )
    if not template:
        _append_notification_event(
            sign_request,
            event_type='notification_failed',
            notification_type='decline',
            recipient_kind='owner',
            recipient_email=owner_email,
            trigger='request_declined',
            template_xmlid=DECLINE_OWNER_TEMPLATE_XMLID,
            signer=decliner,
            reason=FAILURE_REASON_MISSING_TEMPLATE,
        )
        return False
    try:
        mail_mail_id = _queue_template(
            template,
            sign_request,
            email_to=owner_email,
            email_values={'email_to': owner_email},
            context={
                'request_backend_url': backend_url,
                'decliner_email': decliner.email,
                'decliner_role': decliner.role_id.name,
                'decline_reason': decliner.declined_reason or False,
            },
            raise_on_failure=raise_on_failure,
        )
    except Exception as exc:  # pragma: no cover - exception type depends on mail internals
        _log_notification_exception(
            'decline',
            'request_declined',
            exc,
            request_id=sign_request.id,
            signer_id=decliner.id,
            template_xmlid=DECLINE_OWNER_TEMPLATE_XMLID,
        )
        _append_notification_event(
            sign_request,
            event_type='notification_failed',
            notification_type='decline',
            recipient_kind='owner',
            recipient_email=owner_email,
            trigger='request_declined',
            template_xmlid=DECLINE_OWNER_TEMPLATE_XMLID,
            signer=decliner,
            reason=FAILURE_REASON_MAIL_QUEUE_ERROR,
        )
        if raise_on_failure:
            raise
        return False
    _append_notification_event(
        sign_request,
        event_type='notification_queued',
        notification_type='decline',
        recipient_kind='owner',
        recipient_email=owner_email,
        trigger='request_declined',
        template_xmlid=DECLINE_OWNER_TEMPLATE_XMLID,
        signer=decliner,
        mail_mail_id=mail_mail_id,
    )
    return mail_mail_id


def queue_request_otp_notification(sign_request, signer, *, otp_code, expires_at, trigger, raise_on_failure=True):
    sign_request.ensure_one()
    signer.ensure_one()
    recipient_email = _normalize_email(signer.email)
    template = _get_template(
        sign_request.env,
        OTP_TEMPLATE_XMLID,
        notification_type='otp',
        raise_on_failure=raise_on_failure,
    )
    if not template:
        _append_notification_event(
            sign_request,
            event_type='notification_failed',
            notification_type='otp',
            recipient_kind='signer',
            recipient_email=recipient_email,
            trigger=trigger,
            template_xmlid=OTP_TEMPLATE_XMLID,
            signer=signer,
            reason=FAILURE_REASON_MISSING_TEMPLATE,
        )
        return False
    try:
        mail_mail_id = _queue_template(
            template,
            signer,
            email_to=recipient_email,
            email_values={'email_to': recipient_email},
            context={
                'otp_code': otp_code,
                'otp_expires_at': fields.Datetime.to_string(expires_at),
                'otp_ttl_minutes': 10,
            },
            raise_on_failure=raise_on_failure,
        )
    except Exception as exc:  # pragma: no cover - exception type depends on mail internals
        _log_notification_exception(
            'otp',
            trigger,
            exc,
            request_id=sign_request.id,
            signer_id=signer.id,
            template_xmlid=OTP_TEMPLATE_XMLID,
        )
        if raise_on_failure:
            raise NotificationQueueFailure(
                notification_type='otp',
                recipient_kind='signer',
                recipient_email=recipient_email,
                template_xmlid=OTP_TEMPLATE_XMLID,
                signer_id=signer.id,
                reason=FAILURE_REASON_MAIL_QUEUE_ERROR,
                display_message=_("Failed to queue the verification email."),
            ) from exc
        _append_notification_event(
            sign_request,
            event_type='notification_failed',
            notification_type='otp',
            recipient_kind='signer',
            recipient_email=recipient_email,
            trigger=trigger,
            template_xmlid=OTP_TEMPLATE_XMLID,
            signer=signer,
            reason=FAILURE_REASON_MAIL_QUEUE_ERROR,
        )
        return False
    _append_notification_event(
        sign_request,
        event_type='notification_queued',
        notification_type='otp',
        recipient_kind='signer',
        recipient_email=recipient_email,
        trigger=trigger,
        template_xmlid=OTP_TEMPLATE_XMLID,
        signer=signer,
        mail_mail_id=mail_mail_id,
    )
    return mail_mail_id
