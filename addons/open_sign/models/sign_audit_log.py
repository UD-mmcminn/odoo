# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


SHA256_HEX_RE = re.compile(r'^[0-9a-f]{64}$')
TERMINAL_REQUEST_STATUSES = {'completed', 'voided'}
AUDIT_EVENT_TYPE_SELECTION = [
    ('request_created', 'Request Created'),
    ('template_version_published', 'Template Version Published'),
    ('request_versioned', 'Request Versioned'),
    ('request_sent', 'Request Sent'),
    ('signer_opened', 'Signer Opened'),
    ('value_saved', 'Value Saved'),
    ('signer_submitted', 'Signer Submitted'),
    ('signer_declined', 'Signer Declined'),
    ('request_completed', 'Request Completed'),
    ('request_expired', 'Request Expired'),
    ('request_voided', 'Request Voided'),
    ('otp_requested', 'OTP Requested'),
    ('otp_verified', 'OTP Verified'),
    ('artifact_generated', 'Artifact Generated'),
    ('artifact_downloaded', 'Artifact Downloaded'),
]


class OpenSignAuditLog(models.Model):
    _name = 'open.sign.audit.log'
    _description = 'Open Sign Audit Log'
    _order = 'request_id, event_sequence, id'
    _check_company_auto = True

    request_id = fields.Many2one(
        'open.sign.request',
        required=True,
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    signer_id = fields.Many2one(
        'open.sign.request.signer',
        ondelete='set null',
        index=True,
        check_company=True,
    )
    event_type = fields.Selection(selection=AUDIT_EVENT_TYPE_SELECTION, required=True, index=True)
    event_sequence = fields.Integer(required=True, index=True)
    event_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    ip = fields.Char(size=45)
    user_agent = fields.Char()
    metadata_json = fields.Json()
    hash_chain = fields.Char(required=True, index=True)
    previous_hash = fields.Char()
    consent_text_hash = fields.Char()
    company_id = fields.Many2one(
        'res.company',
        related='request_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    _request_hash_chain_uniq = models.Constraint(
        'UNIQUE(request_id, hash_chain)',
        'Audit hash-chain values must be unique per request.',
    )
    _request_event_sequence_uniq = models.Constraint(
        'UNIQUE(request_id, event_sequence)',
        'Audit event sequence must be unique per request.',
    )
    _event_sequence_positive_check = models.Constraint(
        'CHECK(event_sequence > 0)',
        'Audit event sequence must be greater than zero.',
    )

    @api.model
    def _can_repair_mutate_audit_log(self):
        return self.env.su and self.env.context.get('open_sign_allow_audit_log_repair')

    @api.model
    def _check_hash_chain_available(self, request_id, hash_chain, excluded_ids=None):
        domain = [
            ('request_id', '=', request_id),
            ('hash_chain', '=', hash_chain),
        ]
        if excluded_ids:
            domain.append(('id', 'not in', list(excluded_ids)))
        if self.search_count(domain):
            raise ValidationError(_("Audit hash-chain values must be unique per request."))

    @api.model
    def _check_event_sequence_available(self, request_id, event_sequence, excluded_ids=None):
        domain = [
            ('request_id', '=', request_id),
            ('event_sequence', '=', event_sequence),
        ]
        if excluded_ids:
            domain.append(('id', 'not in', list(excluded_ids)))
        if self.search_count(domain):
            raise ValidationError(_("Audit event sequence must be unique per request."))

    @api.model
    def _sanitize_event_sequence(self, event_sequence):
        try:
            normalized_sequence = int(event_sequence)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Audit event sequence must be greater than zero.")) from exc
        if normalized_sequence <= 0:
            raise ValidationError(_("Audit event sequence must be greater than zero."))
        return normalized_sequence

    @api.model_create_multi
    def create(self, vals_list):
        default_vals = self.default_get(['request_id', 'hash_chain', 'event_sequence'])
        pending_hash_keys = set()
        pending_sequence_keys = set()
        for vals in vals_list:
            request_id = vals.get('request_id', default_vals.get('request_id'))
            hash_chain = vals.get('hash_chain', default_vals.get('hash_chain'))
            event_sequence = vals.get('event_sequence', default_vals.get('event_sequence'))
            if event_sequence is not None:
                event_sequence = self._sanitize_event_sequence(event_sequence)
                vals['event_sequence'] = event_sequence
            if request_id and hash_chain:
                hash_key = (request_id, hash_chain)
                if hash_key in pending_hash_keys:
                    raise ValidationError(_("Audit hash-chain values must be unique per request."))
                self._check_hash_chain_available(request_id, hash_chain)
                pending_hash_keys.add(hash_key)
            if request_id and event_sequence is not None:
                sequence_key = (request_id, event_sequence)
                if sequence_key in pending_sequence_keys:
                    raise ValidationError(_("Audit event sequence must be unique per request."))
                self._check_event_sequence_available(request_id, event_sequence)
                pending_sequence_keys.add(sequence_key)
        return super().create(vals_list)

    @api.constrains('event_sequence')
    def _check_event_sequence(self):
        for audit_log in self:
            if audit_log.event_sequence <= 0:
                raise ValidationError(_("Audit event sequence must be greater than zero."))

    @api.constrains('signer_id', 'request_id')
    def _check_signer_belongs_to_request(self):
        for audit_log in self.filtered('signer_id'):
            if audit_log.signer_id.request_id != audit_log.request_id:
                raise ValidationError(_("Audit signer must belong to the same request."))

    @api.constrains('hash_chain', 'previous_hash', 'consent_text_hash')
    def _check_hash_formats(self):
        for audit_log in self:
            if not SHA256_HEX_RE.fullmatch(audit_log.hash_chain or ''):
                raise ValidationError(_("Audit hash chain must be a 64-character lowercase hexadecimal string."))
            if audit_log.previous_hash and not SHA256_HEX_RE.fullmatch(audit_log.previous_hash):
                raise ValidationError(_("Audit previous hash must be a 64-character lowercase hexadecimal string."))
            if audit_log.consent_text_hash and not SHA256_HEX_RE.fullmatch(audit_log.consent_text_hash):
                raise ValidationError(_("Audit consent text hash must be a 64-character lowercase hexadecimal string."))

    def write(self, vals):
        self.check_access('write')
        if self._can_repair_mutate_audit_log():
            return super().write(vals)
        if self.filtered(lambda log: log.request_id.status in TERMINAL_REQUEST_STATUSES):
            raise ValidationError(_("Audit log records are immutable once the request is completed or voided."))
        raise ValidationError(_("Audit log records are append-only and cannot be modified directly."))

    def unlink(self):
        self.check_access('unlink')
        if self._can_repair_mutate_audit_log():
            return super().unlink()
        if self.filtered(lambda log: log.request_id.status in TERMINAL_REQUEST_STATUSES):
            raise ValidationError(_("Audit log records are immutable once the request is completed or voided."))
        raise ValidationError(_("Audit log records are append-only and cannot be deleted directly."))
