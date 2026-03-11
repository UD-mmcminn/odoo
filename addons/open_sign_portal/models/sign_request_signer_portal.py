# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


TOKEN_CONTROL_FIELDS = {'access_token'}


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

    def _get_portal_sign_path(self):
        self.ensure_one()
        return f"/my/sign/{self.id}"

    def _compute_access_url(self):
        for signer in self:
            signer.access_url = signer._get_portal_sign_path() if signer.id else False

    def _compute_portal_sign_url(self):
        for signer in self:
            signer.portal_sign_url = signer.get_portal_url() if signer.id else False

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
