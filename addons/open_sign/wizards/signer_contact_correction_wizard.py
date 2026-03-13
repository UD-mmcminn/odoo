# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.errors import LockNotAvailable

from odoo import _, api, fields, models
from odoo.addons.open_sign.services import notification_service
from odoo.exceptions import ValidationError


class OpenSignSignerContactCorrectionWizard(models.TransientModel):
    _name = 'open.sign.signer.contact_correction.wizard'
    _description = 'Open Sign Signer Contact Correction Wizard'

    signer_id = fields.Many2one('open.sign.request.signer', required=True, readonly=True)
    request_id = fields.Many2one(related='signer_id.request_id', readonly=True)
    current_email = fields.Char(readonly=True)
    target_email = fields.Char(required=True)
    reason = fields.Text(required=True)
    actionable_now = fields.Boolean(compute='_compute_actionable_now', readonly=True)
    request_status = fields.Selection(related='request_id.status', readonly=True)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        signer = self.env['open.sign.request.signer'].browse(defaults.get('signer_id')).exists()
        if signer:
            defaults.setdefault('current_email', signer.email)
            defaults.setdefault('target_email', signer.email)
        return defaults

    @api.depends('signer_id', 'request_id.status')
    def _compute_actionable_now(self):
        for wizard in self:
            signer = wizard.signer_id
            wizard.actionable_now = bool(
                signer
                and signer.request_id.status != 'versioned'
                and signer.request_id._is_signer_actionable(signer)
            )

    @staticmethod
    def _normalize_reason(reason):
        normalized = (reason or '').replace('\r\n', '\n').replace('\r', '\n').strip()
        if not normalized:
            raise ValidationError(_("Reason is required."))
        return normalized

    def _lock_request_for_update(self, sign_request):
        self.env.cr.execute(
            'SELECT id FROM open_sign_request WHERE id = %s FOR UPDATE NOWAIT',
            [sign_request.id],
        )

    def action_apply_contact_correction(self):
        self.ensure_one()
        signer = self.signer_id
        signer.with_user(self.env.user)._check_contact_correction_allowed()

        normalized_email = signer._sanitize_email(self.target_email)
        normalized_reason = self._normalize_reason(self.reason)

        sign_request = signer.request_id.sudo()
        try:
            with self.env.cr.savepoint():
                try:
                    self._lock_request_for_update(sign_request)
                except LockNotAvailable as exc:
                    raise ValidationError(_("The signing request is currently locked. Try again.")) from exc

                signer_sudo = signer.sudo()
                signer_sudo.with_user(self.env.user)._check_contact_correction_allowed()

                old_email = signer_sudo.email
                event_at = fields.Datetime.now()
                if normalized_email != old_email:
                    signer_sudo.write({'email': normalized_email})
                signer_sudo._rotate_portal_token()
                signer_sudo._invalidate_portal_security_state_on_manual_resend(
                    email_changed=normalized_email != old_email,
                )

                if sign_request.status == 'versioned':
                    delivery_disposition = 'deferred_until_send'
                elif sign_request._is_signer_actionable(signer_sudo):
                    delivery_disposition = 'queued_now'
                else:
                    delivery_disposition = 'deferred_future_wave'

                sign_request._append_audit_event(
                    'signer_contact_corrected',
                    signer=signer_sudo,
                    event_at=event_at,
                    metadata={
                        'old_email': old_email,
                        'new_email': normalized_email,
                        'reason': normalized_reason,
                        'request_status_before': sign_request.status,
                        'signer_state_before': signer_sudo.state,
                        'token_rotated': True,
                        'delivery_disposition': delivery_disposition,
                    },
                )

                if delivery_disposition == 'queued_now':
                    notification_service.queue_request_invitations(
                        sign_request,
                        signer_sudo,
                        trigger='manual_resend',
                        raise_on_failure=True,
                    )
                else:
                    notification_service._append_notification_event(
                        sign_request,
                        event_type='notification_skipped',
                        notification_type='invitation',
                        recipient_kind='signer',
                        recipient_email=normalized_email,
                        trigger='manual_resend',
                        template_xmlid=notification_service.INVITATION_TEMPLATE_XMLID,
                        signer=signer_sudo,
                        reason=delivery_disposition,
                    )

                sign_request.write({'last_event_at': event_at})
        except notification_service.NotificationQueueFailure as exc:
            notification_service.append_durable_notification_failure(
                sign_request.id,
                registry=self.env.registry,
                env=self.env,
                signer_id=signer.id,
                notification_type='invitation',
                recipient_kind='signer',
                recipient_email=normalized_email,
                trigger='manual_resend',
                template_xmlid=notification_service.INVITATION_TEMPLATE_XMLID,
                reason=exc.reason,
                event_at=fields.Datetime.now(),
            )
            raise ValidationError(exc.display_message) from exc

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invitation Updated'),
                'message': (
                    _('Invitation queued.')
                    if delivery_disposition == 'queued_now'
                    else _('Contact update recorded. Invitation will be sent when eligible.')
                ),
                'type': 'success',
                'sticky': False,
            },
        }
