# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ipaddress
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError


SIGNER_STATE_SELECTION = [
    ('pending', 'Pending'),
    ('opened', 'Opened'),
    ('signed', 'Signed'),
    ('declined', 'Declined'),
    ('expired', 'Expired'),
]
SHA256_HEX_RE = re.compile(r'^[0-9a-f]{64}$')
LIFECYCLE_FIELDS = {
    'state',
    'signed_at',
    'declined_reason',
    'last_opened_at',
    'ip_last',
    'consent_accepted_at',
    'consent_text_hash',
    'signer_timezone',
}
TERMINAL_MUTATION_STATUSES = {'completed', 'cancelled', 'voided'}


class OpenSignRequestSigner(models.Model):
    _name = 'open.sign.request.signer'
    _description = 'Open Sign Request Signer'
    _order = 'request_id, sequence, id'
    _check_company_auto = True

    request_id = fields.Many2one(
        'open.sign.request',
        required=True,
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        ondelete='set null',
        index=True,
    )
    email = fields.Char(required=True, index=True)
    role_id = fields.Many2one(
        'open.sign.role',
        required=True,
        ondelete='restrict',
        index=True,
    )
    sequence = fields.Integer(required=True, default=10, index=True)
    state = fields.Selection(selection=SIGNER_STATE_SELECTION, required=True, default='pending', index=True)
    signed_at = fields.Datetime(index=True)
    declined_reason = fields.Text()
    last_opened_at = fields.Datetime(index=True)
    ip_last = fields.Char(size=45)
    consent_accepted_at = fields.Datetime(index=True)
    consent_text_hash = fields.Char()
    signer_timezone = fields.Char()
    value_ids = fields.One2many('open.sign.request.value', 'signer_id', string='Captured Values')
    company_id = fields.Many2one(
        'res.company',
        related='request_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    _request_role_uniq = models.Constraint(
        'UNIQUE(request_id, role_id)',
        'Each role can be assigned only once per request.',
    )
    _sequence_non_negative_check = models.Constraint(
        'CHECK(sequence >= 0)',
        'Signer sequence must be zero or greater.',
    )
    _signed_state_requires_timestamp_check = models.Constraint(
        "CHECK(state != 'signed' OR signed_at IS NOT NULL)",
        'Signed signer state requires signed_at timestamp.',
    )

    @api.model
    def _get_effective_create_vals(self, vals, field_names):
        defaults = self.default_get(list(field_names))
        effective_vals = dict(defaults)
        effective_vals.update(vals)
        return defaults, effective_vals

    @api.model
    def _can_manage_lifecycle_fields(self):
        # Signer lifecycle/evidence fields must only be updated by privileged server flows.
        return self.env.su

    @api.model
    def _guard_lifecycle_values_on_create(self, vals):
        if self._can_manage_lifecycle_fields():
            return
        lifecycle_values = LIFECYCLE_FIELDS.intersection(vals)
        if not lifecycle_values:
            return
        if lifecycle_values == {'state'} and vals.get('state') in {False, 'pending'}:
            return
        raise ValidationError(_("Signer lifecycle fields cannot be set directly."))

    def _guard_lifecycle_values_on_write(self, vals):
        if self._can_manage_lifecycle_fields():
            return
        if LIFECYCLE_FIELDS.intersection(vals):
            raise ValidationError(_("Signer lifecycle fields cannot be modified directly."))

    @api.model
    def _guard_request_state_on_create(self, vals):
        if self.env.su:
            return
        request_id = vals.get('request_id')
        if not request_id:
            return
        request = self.env['open.sign.request'].browse(request_id).exists()
        if request and request.status in TERMINAL_MUTATION_STATUSES:
            raise ValidationError(_("Signer records cannot be modified once the request is completed, cancelled, or voided."))

    def _guard_request_state_on_write(self, vals):
        if self.env.su:
            return
        target_request = None
        if 'request_id' in vals and vals.get('request_id'):
            target_request = self.env['open.sign.request'].browse(vals['request_id']).exists()
        if target_request and target_request.status in TERMINAL_MUTATION_STATUSES:
            raise ValidationError(_("Signer records cannot be modified once the request is completed, cancelled, or voided."))
        if self.filtered(lambda signer: signer.request_id.status in TERMINAL_MUTATION_STATUSES):
            raise ValidationError(_("Signer records cannot be modified once the request is completed, cancelled, or voided."))

    @api.model
    def _sanitize_email(self, email):
        normalized_email = tools.email_normalize((email or '').strip())
        if not normalized_email:
            raise ValidationError(_("Signer email must be a valid email address."))
        return normalized_email

    @api.model
    def _sanitize_ip_last(self, ip_last):
        normalized_ip = (ip_last or '').strip()
        if not normalized_ip:
            return False
        try:
            return ipaddress.ip_address(normalized_ip).compressed
        except ValueError as exc:
            raise ValidationError(_("Signer IP must be a valid IPv4 or IPv6 address.")) from exc

    @api.model
    def _sanitize_consent_text_hash(self, consent_text_hash):
        normalized_hash = (consent_text_hash or '').strip()
        if not normalized_hash:
            return False
        if not SHA256_HEX_RE.fullmatch(normalized_hash):
            raise ValidationError(_("Signer consent text hash must be a 64-character lowercase hexadecimal string."))
        return normalized_hash

    @api.model
    def _sanitize_signer_timezone(self, signer_timezone):
        normalized_timezone = (signer_timezone or '').strip()
        if not normalized_timezone:
            return False
        try:
            ZoneInfo(normalized_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValidationError(_("Signer timezone must be a valid IANA timezone identifier.")) from exc
        return normalized_timezone

    @api.model
    def _sanitize_sequence(self, sequence):
        try:
            normalized_sequence = int(sequence)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Signer sequence must be zero or greater.")) from exc
        if normalized_sequence < 0:
            raise ValidationError(_("Signer sequence must be zero or greater."))
        return normalized_sequence

    @api.model
    def _check_signed_state_timestamp_pair(self, state, signed_at):
        if state == 'signed' and not signed_at:
            raise ValidationError(_("Signed signer state requires signed_at timestamp."))

    @api.model
    def _check_role_available(self, request_id, role_id, excluded_ids=None):
        domain = [
            ('request_id', '=', request_id),
            ('role_id', '=', role_id),
        ]
        if excluded_ids:
            domain.append(('id', 'not in', list(excluded_ids)))
        if self.search_count(domain):
            raise ValidationError(_("Each role can be assigned only once per request."))

    @api.model_create_multi
    def create(self, vals_list):
        pending_keys = set()
        create_fields = {'request_id', 'role_id', 'email', 'sequence'} | set(LIFECYCLE_FIELDS)
        for vals in vals_list:
            defaults, effective_vals = self._get_effective_create_vals(vals, create_fields)
            self._guard_request_state_on_create(effective_vals)
            self._guard_lifecycle_values_on_create(effective_vals)
            if 'email' in vals or 'email' in defaults:
                vals['email'] = self._sanitize_email(effective_vals.get('email'))
            if 'sequence' in vals or 'sequence' in defaults:
                vals['sequence'] = self._sanitize_sequence(effective_vals.get('sequence'))
            if 'ip_last' in vals or 'ip_last' in defaults:
                vals['ip_last'] = self._sanitize_ip_last(effective_vals.get('ip_last'))
            if 'consent_text_hash' in vals or 'consent_text_hash' in defaults:
                vals['consent_text_hash'] = self._sanitize_consent_text_hash(effective_vals.get('consent_text_hash'))
            if 'signer_timezone' in vals or 'signer_timezone' in defaults:
                vals['signer_timezone'] = self._sanitize_signer_timezone(effective_vals.get('signer_timezone'))
            if {'state', 'signed_at'}.intersection(vals) or {'state', 'signed_at'}.intersection(defaults):
                self._check_signed_state_timestamp_pair(effective_vals.get('state'), effective_vals.get('signed_at'))
            request_id = effective_vals.get('request_id')
            role_id = effective_vals.get('role_id')
            if request_id and role_id:
                key = (request_id, role_id)
                if key in pending_keys:
                    raise ValidationError(_("Each role can be assigned only once per request."))
                self._check_role_available(request_id, role_id)
                pending_keys.add(key)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        self._guard_request_state_on_write(vals)
        self._guard_lifecycle_values_on_write(vals)
        if 'email' in vals:
            vals['email'] = self._sanitize_email(vals['email'])
        if 'sequence' in vals:
            vals['sequence'] = self._sanitize_sequence(vals['sequence'])
        if 'ip_last' in vals:
            vals['ip_last'] = self._sanitize_ip_last(vals['ip_last'])
        if 'consent_text_hash' in vals:
            vals['consent_text_hash'] = self._sanitize_consent_text_hash(vals['consent_text_hash'])
        if 'signer_timezone' in vals:
            vals['signer_timezone'] = self._sanitize_signer_timezone(vals['signer_timezone'])
        if 'state' in vals or 'signed_at' in vals:
            for signer in self:
                self._check_signed_state_timestamp_pair(
                    vals.get('state', signer.state),
                    vals.get('signed_at', signer.signed_at),
                )
        if 'request_id' in vals or 'role_id' in vals:
            candidate_keys = set()
            for signer in self:
                request_id = vals.get('request_id', signer.request_id.id)
                role_id = vals.get('role_id', signer.role_id.id)
                key = (request_id, role_id)
                if key in candidate_keys:
                    raise ValidationError(_("Each role can be assigned only once per request."))
                candidate_keys.add(key)
            for request_id, role_id in candidate_keys:
                self._check_role_available(request_id, role_id, excluded_ids=self.ids)
        return super().write(vals)

    def unlink(self):
        if not self.env.su and self.filtered(lambda signer: signer.request_id.status in TERMINAL_MUTATION_STATUSES):
            raise ValidationError(_("Signer records cannot be modified once the request is completed, cancelled, or voided."))
        return super().unlink()

    @api.constrains('email')
    def _check_email_format(self):
        for signer in self:
            if signer.email != self._sanitize_email(signer.email):
                raise ValidationError(_("Signer email normalization is inconsistent."))

    @api.constrains('ip_last')
    def _check_ip_last_format(self):
        for signer in self:
            if (signer.ip_last or False) != self._sanitize_ip_last(signer.ip_last):
                raise ValidationError(_("Signer IP normalization is inconsistent."))

    @api.constrains('consent_text_hash')
    def _check_consent_text_hash_format(self):
        for signer in self:
            if (signer.consent_text_hash or False) != self._sanitize_consent_text_hash(signer.consent_text_hash):
                raise ValidationError(_("Signer consent text hash normalization is inconsistent."))

    @api.constrains('signer_timezone')
    def _check_signer_timezone_format(self):
        for signer in self:
            if (signer.signer_timezone or False) != self._sanitize_signer_timezone(signer.signer_timezone):
                raise ValidationError(_("Signer timezone normalization is inconsistent."))

    @api.constrains('role_id', 'request_id')
    def _check_role_matches_request_template(self):
        for signer in self:
            if signer.role_id.template_id != signer.request_id.template_id:
                raise ValidationError(_("Signer role must belong to the same template as the request."))

    @api.constrains('state', 'signed_at')
    def _check_signed_state_requires_timestamp(self):
        for signer in self:
            if signer.state == 'signed' and not signer.signed_at:
                raise ValidationError(_("Signed signer state requires signed_at timestamp."))

    @api.constrains('sequence')
    def _check_sequence_non_negative(self):
        for signer in self:
            if signer.sequence < 0:
                raise ValidationError(_("Signer sequence must be zero or greater."))
