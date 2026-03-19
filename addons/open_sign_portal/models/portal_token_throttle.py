# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


TOKEN_THROTTLE_GC_BATCH_SIZE = 1000


class OpenSignPortalTokenThrottle(models.Model):
    _name = 'open.sign.portal.token.throttle'
    _description = 'Open Sign Portal Token Throttle'
    _order = 'last_attempt_at desc, id desc'
    _check_company_auto = True

    request_signer_id = fields.Many2one(
        'open.sign.request.signer',
        required=True,
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    client_ip = fields.Char(required=True, size=45, index=True)
    attempt_count = fields.Integer(required=True, default=0)
    first_attempt_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    last_attempt_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    blocked_until = fields.Datetime(index=True)
    company_id = fields.Many2one(
        'res.company',
        related='request_signer_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    _request_signer_client_ip_uniq = models.Constraint(
        'UNIQUE(request_signer_id, client_ip)',
        'Portal token throttle buckets must be unique per signer and client IP.',
    )
    _attempt_count_non_negative_check = models.Constraint(
        'CHECK(attempt_count >= 0)',
        'Portal token throttle attempt count must be zero or greater.',
    )

    @api.model
    def _cron_gc_portal_token_throttle(self):
        from odoo.addons.open_sign_portal.services import token_security_service

        while True:
            deleted_bucket_count = token_security_service.cleanup_stale_invalid_token_buckets(
                self.env,
                limit=TOKEN_THROTTLE_GC_BATCH_SIZE,
            )
            deleted_attempt_count = token_security_service.cleanup_stale_invalid_token_attempts(
                self.env,
                limit=TOKEN_THROTTLE_GC_BATCH_SIZE,
            )
            if (
                deleted_bucket_count < TOKEN_THROTTLE_GC_BATCH_SIZE
                and deleted_attempt_count < TOKEN_THROTTLE_GC_BATCH_SIZE
            ):
                break
        return True
