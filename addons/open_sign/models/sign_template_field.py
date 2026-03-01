# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


FIELD_TYPE_SELECTION = [
    ('signature', 'Signature'),
    ('initials', 'Initials'),
    ('name', 'Name'),
    ('email', 'Email'),
    ('phone', 'Phone'),
    ('company', 'Company'),
    ('text', 'Text'),
    ('multiline', 'Multiline Text'),
    ('checkbox', 'Checkbox'),
    ('radio', 'Radio'),
    ('selection', 'Selection'),
    ('date', 'Date'),
    ('strikethrough', 'Strikethrough'),
    ('stamp', 'Stamp'),
]
OPTION_FIELD_TYPES = {'radio', 'selection'}


class OpenSignTemplateField(models.Model):
    _name = 'open.sign.template.field'
    _description = 'Open Sign Template Field'
    _order = 'template_id, page, sequence, id'

    template_id = fields.Many2one(
        'open.sign.template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    role_id = fields.Many2one(
        'open.sign.role',
        required=True,
        ondelete='restrict',
        index=True,
    )
    type = fields.Selection(selection=FIELD_TYPE_SELECTION, required=True, index=True)
    label = fields.Char(required=True)
    required = fields.Boolean(default=False, required=True)
    page = fields.Integer(required=True, default=1, index=True)
    x = fields.Float(required=True, default=0.0)
    y = fields.Float(required=True, default=0.0)
    width = fields.Float(required=True, default=0.2)
    height = fields.Float(required=True, default=0.05)
    sequence = fields.Integer(required=True, default=10, index=True)
    default_value = fields.Text()
    validation_regex = fields.Char()
    min_length = fields.Integer()
    max_length = fields.Integer()
    option_ids = fields.One2many('open.sign.template.field.option', 'field_id', string='Options')
    request_value_ids = fields.One2many('open.sign.request.value', 'template_field_id', string='Request Values')

    _page_positive_check = models.Constraint(
        'CHECK(page >= 1)',
        'Field page must be 1 or greater.',
    )
    _geometry_bounds_check = models.Constraint(
        'CHECK(x >= 0 AND x <= 1 AND y >= 0 AND y <= 1 AND width > 0 AND width <= 1 AND height > 0 AND height <= 1)',
        'Field geometry must stay within normalized page bounds.',
    )
    _sequence_non_negative_check = models.Constraint(
        'CHECK(sequence >= 0)',
        'Field sequence must be zero or greater.',
    )
    _length_bounds_check = models.Constraint(
        'CHECK((min_length IS NULL OR min_length >= 0) AND (max_length IS NULL OR max_length >= 0) AND (min_length IS NULL OR max_length IS NULL OR max_length >= min_length))',
        'Field length bounds must be valid.',
    )
    _label_non_empty_check = models.Constraint(
        "CHECK(length(btrim(label)) > 0)",
        'Field label cannot be empty.',
    )

    @api.model
    def _normalize_label(self, label):
        return (label or '').strip()

    @api.model
    def _sanitize_label(self, label):
        normalized_label = self._normalize_label(label)
        if not normalized_label:
            raise ValidationError(_("Field label cannot be empty."))
        return normalized_label

    @api.model
    def _validate_label_invariant_value(self, label):
        normalized_label = self._normalize_label(label)
        if not normalized_label:
            raise ValidationError(_("Field label cannot be empty."))
        if label != normalized_label:
            raise ValidationError(_("Field label cannot contain leading or trailing whitespace."))

    @api.model
    def _validate_scalar_bounds(self, *, page, x, y, width, height, sequence, min_length, max_length):
        if page is not None and page < 1:
            raise ValidationError(_("Field page must be 1 or greater."))
        if x is not None and (x < 0 or x > 1):
            raise ValidationError(_("Field x coordinate must be between 0 and 1."))
        if y is not None and (y < 0 or y > 1):
            raise ValidationError(_("Field y coordinate must be between 0 and 1."))
        if width is not None and (width <= 0 or width > 1):
            raise ValidationError(_("Field width must be greater than 0 and at most 1."))
        if height is not None and (height <= 0 or height > 1):
            raise ValidationError(_("Field height must be greater than 0 and at most 1."))
        if sequence is not None and sequence < 0:
            raise ValidationError(_("Field sequence must be zero or greater."))
        if min_length is not None and min_length < 0:
            raise ValidationError(_("Minimum length must be zero or greater."))
        if max_length is not None and max_length < 0:
            raise ValidationError(_("Maximum length must be zero or greater."))
        if min_length is not None and max_length is not None and max_length < min_length:
            raise ValidationError(_("Maximum length must be greater than or equal to minimum length."))

    @api.model_create_multi
    def create(self, vals_list):
        default_vals = self.default_get(['label', 'page', 'x', 'y', 'width', 'height', 'sequence', 'min_length', 'max_length'])
        for vals in vals_list:
            if 'label' in vals:
                vals['label'] = self._sanitize_label(vals['label'])
            elif 'label' in default_vals:
                self._validate_label_invariant_value(default_vals.get('label'))
                vals['label'] = default_vals.get('label')
            self._validate_scalar_bounds(
                page=vals.get('page', default_vals.get('page')),
                x=vals.get('x', default_vals.get('x')),
                y=vals.get('y', default_vals.get('y')),
                width=vals.get('width', default_vals.get('width')),
                height=vals.get('height', default_vals.get('height')),
                sequence=vals.get('sequence', default_vals.get('sequence')),
                min_length=vals.get('min_length', default_vals.get('min_length')),
                max_length=vals.get('max_length', default_vals.get('max_length')),
            )
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if 'label' in vals:
            vals['label'] = self._sanitize_label(vals['label'])
        if {'page', 'x', 'y', 'width', 'height', 'sequence', 'min_length', 'max_length'}.intersection(vals):
            for field in self:
                self._validate_scalar_bounds(
                    page=vals.get('page', field.page),
                    x=vals.get('x', field.x),
                    y=vals.get('y', field.y),
                    width=vals.get('width', field.width),
                    height=vals.get('height', field.height),
                    sequence=vals.get('sequence', field.sequence),
                    min_length=vals.get('min_length', field.min_length),
                    max_length=vals.get('max_length', field.max_length),
                )
        return super().write(vals)

    @api.constrains('label')
    def _check_label_invariant(self):
        for field in self:
            normalized_label = self._normalize_label(field.label)
            if not normalized_label:
                raise ValidationError(_("Field label cannot be empty."))
            if field.label != normalized_label:
                raise ValidationError(_("Field label cannot contain leading or trailing whitespace."))

    @api.constrains('role_id', 'template_id')
    def _check_role_template_match(self):
        for field in self:
            if field.role_id.template_id != field.template_id:
                raise ValidationError(_("Field role must belong to the same template."))

    @api.constrains('page')
    def _check_page_number(self):
        for field in self:
            if field.page < 1:
                raise ValidationError(_("Field page must be 1 or greater."))

    @api.constrains('x', 'y', 'width', 'height')
    def _check_geometry_bounds(self):
        for field in self:
            if field.x < 0 or field.x > 1:
                raise ValidationError(_("Field x coordinate must be between 0 and 1."))
            if field.y < 0 or field.y > 1:
                raise ValidationError(_("Field y coordinate must be between 0 and 1."))
            if field.width <= 0 or field.width > 1:
                raise ValidationError(_("Field width must be greater than 0 and at most 1."))
            if field.height <= 0 or field.height > 1:
                raise ValidationError(_("Field height must be greater than 0 and at most 1."))

    @api.constrains('sequence')
    def _check_sequence_non_negative(self):
        for field in self:
            if field.sequence < 0:
                raise ValidationError(_("Field sequence must be zero or greater."))

    @api.constrains('validation_regex')
    def _check_validation_regex(self):
        for field in self.filtered('validation_regex'):
            try:
                re.compile(field.validation_regex)
            except re.error as exc:
                raise ValidationError(_("Validation regex is invalid: %(error)s", error=str(exc))) from exc

    @api.constrains('min_length', 'max_length')
    def _check_length_bounds(self):
        for field in self:
            if field.min_length is not None and field.min_length < 0:
                raise ValidationError(_("Minimum length must be zero or greater."))
            if field.max_length is not None and field.max_length < 0:
                raise ValidationError(_("Maximum length must be zero or greater."))
            if (
                field.min_length is not None
                and field.max_length is not None
                and field.max_length < field.min_length
            ):
                raise ValidationError(_("Maximum length must be greater than or equal to minimum length."))

    @api.constrains('type', 'option_ids')
    def _check_options_by_type(self):
        for field in self:
            option_count = len(field.option_ids)
            if field.type in OPTION_FIELD_TYPES and option_count == 0:
                raise ValidationError(_("Radio and selection fields require at least one option."))
            if field.type not in OPTION_FIELD_TYPES and option_count:
                raise ValidationError(_("Only radio and selection fields can define options."))
