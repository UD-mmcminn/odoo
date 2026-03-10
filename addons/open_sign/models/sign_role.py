# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpenSignRole(models.Model):
    _name = 'open.sign.role'
    _description = 'Open Sign Signer Role'
    _order = 'template_id, sequence, id'

    template_id = fields.Many2one(
        'open.sign.template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(required=True)
    name_normalized = fields.Char(
        required=True,
        index=True,
        readonly=True,
        copy=False,
        compute='_compute_name_normalized',
        store=True,
        precompute=True,
    )
    sequence = fields.Integer(required=True, default=10, index=True)
    required = fields.Boolean(default=True, required=True)
    color = fields.Integer(default=0)

    _name_normalized_template_uniq = models.Constraint(
        'UNIQUE(template_id, name_normalized)',
        'Role names must be unique per template (case-insensitive).',
    )
    _sequence_non_negative_check = models.Constraint(
        'CHECK(sequence >= 0)',
        'Role sequence must be zero or greater.',
    )
    _name_non_empty_check = models.Constraint(
        "CHECK(length(btrim(name)) > 0)",
        'Role name cannot be empty.',
    )

    @api.model
    def _check_name_available(self, template_id, normalized_name, excluded_ids=None):
        domain = [
            ('template_id', '=', template_id),
            ('name_normalized', '=', normalized_name),
        ]
        if excluded_ids:
            domain.append(('id', 'not in', list(excluded_ids)))
        if self.search_count(domain):
            raise ValidationError(_("Role names must be unique per template (case-insensitive)."))

    @api.model
    def _normalize_role_name(self, name):
        return (name or '').strip()

    @api.model
    def _normalize_role_name_key(self, name):
        return self._normalize_role_name(name).casefold()

    @api.model
    def _sanitize_role_name(self, name):
        normalized_name = self._normalize_role_name(name)
        if not normalized_name:
            raise ValidationError(_("Role name cannot be empty."))
        return normalized_name

    @api.model
    def _sanitize_sequence(self, sequence):
        try:
            normalized_sequence = int(sequence)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Role sequence must be zero or greater.")) from exc
        if normalized_sequence < 0:
            raise ValidationError(_("Role sequence must be zero or greater."))
        return normalized_sequence

    def _build_snapshot_payload(self):
        self.ensure_one()
        return {
            'role_id': self.id,
            'name': self.name,
            'name_normalized': self.name_normalized,
            'sequence': self.sequence,
            'required': self.required,
            'color': self.color,
        }

    @api.model
    def _build_snapshot_fingerprint(self, snapshot_role):
        return (
            self._normalize_role_name_key(snapshot_role.get('name_normalized') or snapshot_role.get('name')),
            self._sanitize_sequence(snapshot_role.get('sequence', 0)),
            bool(snapshot_role.get('required', True)),
            int(snapshot_role.get('color') or 0),
        )

    @api.model
    def _find_snapshot_matches(self, template, snapshot_role):
        template.ensure_one()
        expected_fingerprint = self._build_snapshot_fingerprint(snapshot_role)
        return template.role_ids.filtered(
            lambda role: self._build_snapshot_fingerprint(role._build_snapshot_payload()) == expected_fingerprint
        )

    @api.depends('name')
    def _compute_name_normalized(self):
        for role in self:
            role.name_normalized = self._normalize_role_name_key(role.name)

    @api.model_create_multi
    def create(self, vals_list):
        default_vals = self.default_get(['template_id', 'name', 'sequence'])
        pending_keys = set()
        for vals in vals_list:
            vals.pop('name_normalized', None)
            if 'name' in vals or 'name' in default_vals:
                vals['name'] = self._sanitize_role_name(vals.get('name', default_vals.get('name')))
            if 'sequence' in vals or 'sequence' in default_vals:
                vals['sequence'] = self._sanitize_sequence(vals.get('sequence', default_vals.get('sequence')))
            template_id = vals.get('template_id', default_vals.get('template_id'))
            role_name = vals.get('name')
            if template_id and role_name:
                key = (template_id, self._normalize_role_name_key(role_name))
                if key in pending_keys:
                    raise ValidationError(_("Role names must be unique per template (case-insensitive)."))
                self._check_name_available(template_id, key[1])
                pending_keys.add(key)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        vals.pop('name_normalized', None)
        if 'name' in vals:
            vals['name'] = self._sanitize_role_name(vals['name'])
        if 'sequence' in vals:
            vals['sequence'] = self._sanitize_sequence(vals['sequence'])
        if 'template_id' in vals or 'name' in vals:
            candidate_keys = set()
            for role in self:
                template_id = vals.get('template_id', role.template_id.id)
                normalized_name = self._normalize_role_name_key(vals.get('name', role.name))
                key = (template_id, normalized_name)
                if key in candidate_keys:
                    raise ValidationError(_("Role names must be unique per template (case-insensitive)."))
                candidate_keys.add(key)
            for template_id, normalized_name in candidate_keys:
                self._check_name_available(template_id, normalized_name, excluded_ids=self.ids)
        return super().write(vals)

    @api.constrains('name', 'name_normalized')
    def _check_name_normalized_invariant(self):
        for role in self:
            if role.name_normalized != self._normalize_role_name_key(role.name):
                raise ValidationError(_("Role name normalization is inconsistent."))

    @api.constrains('sequence')
    def _check_sequence_non_negative(self):
        for role in self:
            if role.sequence < 0:
                raise ValidationError(_("Role sequence must be zero or greater."))
