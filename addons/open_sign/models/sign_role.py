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

    @api.depends('name')
    def _compute_name_normalized(self):
        for role in self:
            role.name_normalized = self._normalize_role_name_key(role.name)

    @api.model_create_multi
    def create(self, vals_list):
        pending_keys = set()
        for vals in vals_list:
            vals.pop('name_normalized', None)
            if 'name' in vals:
                vals['name'] = self._sanitize_role_name(vals['name'])
            template_id = vals.get('template_id')
            if template_id and vals.get('name'):
                key = (template_id, self._normalize_role_name_key(vals['name']))
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
