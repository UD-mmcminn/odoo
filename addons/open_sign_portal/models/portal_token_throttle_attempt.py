# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import create_index


class OpenSignPortalTokenThrottleAttempt(models.Model):
    _name = 'open.sign.portal.token.throttle.attempt'
    _description = 'Open Sign Portal Token Throttle Attempt'
    _order = 'attempted_at desc, id desc'
    _check_company_auto = True

    request_signer_id = fields.Many2one(
        'open.sign.request.signer',
        required=True,
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    client_ip = fields.Char(required=True, size=45, index=True)
    attempted_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    company_id = fields.Many2one(
        'res.company',
        related='request_signer_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    @api.model
    def init(self):
        create_index(
            self.env.cr,
            f"{self._table}_signer_ip_attempted_at_idx",
            self._table,
            ['request_signer_id', 'client_ip', 'attempted_at'],
        )
