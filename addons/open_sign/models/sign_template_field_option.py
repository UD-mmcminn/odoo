# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


OPTION_FIELD_TYPES = {'radio', 'selection'}


class OpenSignTemplateFieldOption(models.Model):
    _name = 'open.sign.template.field.option'
    _description = 'Open Sign Template Field Option'
    _order = 'field_id, sequence, id'

    field_id = fields.Many2one(
        'open.sign.template.field',
        required=True,
        ondelete='cascade',
        index=True,
    )
    value = fields.Char(required=True)
    label = fields.Char(required=True)
    sequence = fields.Integer(required=True, default=10, index=True)
    is_default = fields.Boolean(required=True, default=False)

    _field_value_uniq = models.Constraint(
        'UNIQUE(field_id, value)',
        'Option values must be unique per field.',
    )
    _sequence_non_negative_check = models.Constraint(
        'CHECK(sequence >= 0)',
        'Option sequence must be zero or greater.',
    )
    _value_non_empty_check = models.Constraint(
        "CHECK(length(btrim(value)) > 0)",
        'Option value cannot be empty.',
    )
    _label_non_empty_check = models.Constraint(
        "CHECK(length(btrim(label)) > 0)",
        'Option label cannot be empty.',
    )

    @api.model
    def _check_value_available(self, field_id, value, excluded_ids=None):
        domain = [
            ('field_id', '=', field_id),
            ('value', '=', value),
        ]
        if excluded_ids:
            domain.append(('id', 'not in', list(excluded_ids)))
        if self.search_count(domain):
            raise ValidationError(_("Option values must be unique per field."))

    @api.model
    def _sanitize_text(self, text, message):
        normalized_text = (text or '').strip()
        if not normalized_text:
            raise ValidationError(message)
        return normalized_text

    @api.model
    def _validate_text_invariant_value(self, text, empty_message, spacing_message):
        normalized_text = (text or '').strip()
        if not normalized_text:
            raise ValidationError(empty_message)
        if text != normalized_text:
            raise ValidationError(spacing_message)

    @api.model
    def _sanitize_sequence(self, sequence):
        try:
            normalized_sequence = int(sequence)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Option sequence must be zero or greater.")) from exc
        if normalized_sequence < 0:
            raise ValidationError(_("Option sequence must be zero or greater."))
        return normalized_sequence

    @api.model_create_multi
    def create(self, vals_list):
        default_vals = self.default_get(['field_id', 'value', 'label', 'sequence'])
        pending_keys = set()
        for vals in vals_list:
            if 'value' in vals:
                vals['value'] = self._sanitize_text(vals['value'], _("Option value cannot be empty."))
            elif 'value' in default_vals:
                self._validate_text_invariant_value(
                    default_vals.get('value'),
                    _("Option value cannot be empty."),
                    _("Option value cannot contain leading or trailing whitespace."),
                )
                vals['value'] = default_vals.get('value')
            if 'label' in vals:
                vals['label'] = self._sanitize_text(vals['label'], _("Option label cannot be empty."))
            elif 'label' in default_vals:
                self._validate_text_invariant_value(
                    default_vals.get('label'),
                    _("Option label cannot be empty."),
                    _("Option label cannot contain leading or trailing whitespace."),
                )
                vals['label'] = default_vals.get('label')
            if 'sequence' in vals or 'sequence' in default_vals:
                vals['sequence'] = self._sanitize_sequence(vals.get('sequence', default_vals.get('sequence')))
            field_id = vals.get('field_id', default_vals.get('field_id'))
            option_value = vals.get('value')
            if field_id and option_value:
                key = (field_id, option_value)
                if key in pending_keys:
                    raise ValidationError(_("Option values must be unique per field."))
                self._check_value_available(field_id, option_value)
                pending_keys.add(key)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if 'value' in vals:
            vals['value'] = self._sanitize_text(vals['value'], _("Option value cannot be empty."))
        if 'label' in vals:
            vals['label'] = self._sanitize_text(vals['label'], _("Option label cannot be empty."))
        if 'sequence' in vals:
            vals['sequence'] = self._sanitize_sequence(vals['sequence'])
        if 'field_id' in vals or 'value' in vals:
            candidate_keys = set()
            for option in self:
                field_id = vals.get('field_id', option.field_id.id)
                value = vals.get('value', option.value)
                key = (field_id, value)
                if key in candidate_keys:
                    raise ValidationError(_("Option values must be unique per field."))
                candidate_keys.add(key)
            for field_id, value in candidate_keys:
                self._check_value_available(field_id, value, excluded_ids=self.ids)
        return super().write(vals)

    @api.constrains('value', 'label')
    def _check_text_invariants(self):
        for option in self:
            normalized_value = (option.value or '').strip()
            normalized_label = (option.label or '').strip()
            if not normalized_value:
                raise ValidationError(_("Option value cannot be empty."))
            if not normalized_label:
                raise ValidationError(_("Option label cannot be empty."))
            if option.value != normalized_value:
                raise ValidationError(_("Option value cannot contain leading or trailing whitespace."))
            if option.label != normalized_label:
                raise ValidationError(_("Option label cannot contain leading or trailing whitespace."))

    @api.constrains('field_id')
    def _check_field_type_supports_options(self):
        for option in self:
            if option.field_id.type not in OPTION_FIELD_TYPES:
                raise ValidationError(_("Only radio and selection fields can define options."))

    @api.constrains('is_default', 'field_id')
    def _check_single_default_option(self):
        for option in self.filtered('is_default'):
            default_count = self.search_count([
                ('field_id', '=', option.field_id.id),
                ('is_default', '=', True),
            ])
            if default_count > 1:
                raise ValidationError(_("Only one default option is allowed per field."))

    @api.constrains('sequence')
    def _check_sequence_non_negative(self):
        for option in self:
            if option.sequence < 0:
                raise ValidationError(_("Option sequence must be zero or greater."))
