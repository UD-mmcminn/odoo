# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


REQUEST_HASH_RE = re.compile(r'^[0-9a-f]{64}$')
IDEMPOTENCY_ENDPOINT_SELECTION = [
    ('submit', 'Submit'),
    ('decline', 'Decline'),
]
IDEMPOTENCY_STATE_SELECTION = [
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
]
IDEMPOTENCY_RETENTION_DAYS = 30
IDEMPOTENCY_GC_BATCH_SIZE = 1000


class OpenSignPortalIdempotency(models.Model):
    _name = 'open.sign.portal.idempotency'
    _description = 'Open Sign Portal Idempotency'
    _order = 'created_at desc, id desc'
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
    endpoint = fields.Selection(selection=IDEMPOTENCY_ENDPOINT_SELECTION, required=True, index=True)
    idempotency_key = fields.Char(required=True, index=True)
    request_hash = fields.Char(required=True, index=True)
    response_json = fields.Json(groups='base.group_system')
    conflict_logged_at = fields.Datetime(index=True, groups='base.group_system')
    state = fields.Selection(selection=IDEMPOTENCY_STATE_SELECTION, required=True, default='in_progress', index=True)
    created_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    expires_at = fields.Datetime(required=True, index=True)

    _request_signer_endpoint_key_uniq = models.Constraint(
        'UNIQUE(request_signer_id, endpoint, idempotency_key)',
        'Portal idempotency keys must be unique per signer and endpoint.',
    )

    @api.constrains('idempotency_key')
    def _check_idempotency_key(self):
        for record in self:
            if not (record.idempotency_key or '').strip():
                raise ValidationError(_('Portal idempotency key is required.'))

    @api.constrains('request_hash')
    def _check_request_hash_format(self):
        for record in self:
            if not REQUEST_HASH_RE.fullmatch(record.request_hash or ''):
                raise ValidationError(_('Portal request hash must be a 64-character lowercase hexadecimal string.'))

    @api.model
    def _default_expiration(self):
        return fields.Datetime.now() + timedelta(days=IDEMPOTENCY_RETENTION_DAYS)

    @api.model
    def _cron_gc_portal_idempotency(self):
        from odoo.addons.open_sign_portal.services import idempotency_service

        while True:
            deleted_count = idempotency_service.cleanup_expired_records(self.env, limit=IDEMPOTENCY_GC_BATCH_SIZE)
            if deleted_count < IDEMPOTENCY_GC_BATCH_SIZE:
                break
        return True
