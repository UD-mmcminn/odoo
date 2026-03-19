# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import uuid

from psycopg2.errors import LockNotAvailable

from odoo import _, api, fields, models
from odoo.addons.open_sign.models.sign_request_signer import PENDING_CORRECTION_REQUEST_STATUSES
from odoo.exceptions import AccessError, ValidationError
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
        try:
            with self.env.cr.savepoint():
                try:
                    signer._lock_request_for_update_nowait()
                except LockNotAvailable as exc:
                    raise ValidationError(_("The signing request is currently locked. Try again.")) from exc
                signer.sudo()._revoke_email_portal_token(now=fields.Datetime.now())
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
