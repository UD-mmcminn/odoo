# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpenSignOtpChallenge(models.Model):
    _name = 'open.sign.otp.challenge'
    _description = 'Open Sign OTP Challenge'
    _order = 'requested_at desc, id desc'
    _check_company_auto = True

    request_signer_id = fields.Many2one(
        'open.sign.request.signer',
        required=True,
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    request_id = fields.Many2one(
        'open.sign.request',
        related='request_signer_id.request_id',
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='request_signer_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )
    requested_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    expires_at = fields.Datetime(required=True, index=True)
    attempt_count = fields.Integer(required=True, default=0)
    verified_at = fields.Datetime(index=True)
    code_salt = fields.Char(required=True, groups='base.group_system')
    code_hash = fields.Char(required=True, groups='base.group_system')

    _attempt_count_non_negative_check = models.Constraint(
        'CHECK(attempt_count >= 0)',
        'OTP attempt count must be zero or greater.',
    )

    @api.constrains('request_signer_id', 'verified_at', 'expires_at')
    def _check_single_active_challenge(self):
        now = fields.Datetime.now()
        for challenge in self.filtered(lambda challenge: not challenge.verified_at and challenge.expires_at and challenge.expires_at > now):
            duplicate_count = self.search_count([
                ('id', '!=', challenge.id),
                ('request_signer_id', '=', challenge.request_signer_id.id),
                ('verified_at', '=', False),
                ('expires_at', '>', now),
            ])
            if duplicate_count:
                raise ValidationError(_('Only one active OTP challenge is allowed per signer.'))
