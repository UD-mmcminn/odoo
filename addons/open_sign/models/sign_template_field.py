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
REQUEST_FIELD_DELETE_BLOCKING_STATUSES = {'versioned', 'sent', 'opened', 'in_progress', 'partially_signed'}


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

    @api.model
    def _sanitize_sequence(self, sequence):
        try:
            normalized_sequence = int(sequence)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Field sequence must be zero or greater.")) from exc
        if normalized_sequence < 0:
            raise ValidationError(_("Field sequence must be zero or greater."))
        return normalized_sequence

    @api.model
    def _normalize_snapshot_sequence(self, sequence):
        return self._sanitize_sequence(sequence or 0)

    @api.model
    def _normalize_snapshot_page(self, page):
        try:
            normalized_page = int(page)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Field page must be 1 or greater.")) from exc
        if normalized_page < 1:
            raise ValidationError(_("Field page must be 1 or greater."))
        return normalized_page

    @api.model
    def _normalize_snapshot_float(self, value, label):
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("%(label)s must be a valid number.", label=label)) from exc

    @api.model
    def _normalize_snapshot_length_bound(self, value):
        if value in (None, False, ''):
            return False
        try:
            normalized_value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("Field length bounds must be valid.")) from exc
        if normalized_value < 0:
            raise ValidationError(_("Field length bounds must be valid."))
        return normalized_value

    @api.model
    def _build_snapshot_option_payload(self, option):
        if hasattr(option, 'value'):
            return {
                'value': option.value,
                'label': option.label,
                'sequence': option.sequence,
                'is_default': option.is_default,
            }
        return {
            'value': (option.get('value') or '').strip(),
            'label': (option.get('label') or option.get('value') or '').strip(),
            'sequence': int(option.get('sequence') or 0),
            'is_default': bool(option.get('is_default')),
        }

    @api.model
    def _build_snapshot_option_fingerprint(self, option):
        payload = self._build_snapshot_option_payload(option)
        return (
            payload['value'],
            payload['label'],
            int(payload['sequence']),
            bool(payload['is_default']),
        )

    def _build_snapshot_payload(self):
        self.ensure_one()
        return {
            'template_field_id': self.id,
            'role_id': self.role_id.id,
            'role_name': self.role_id.name,
            'role_name_normalized': self.role_id.name_normalized,
            'type': self.type,
            'label': self.label,
            'required': self.required,
            'page': self.page,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'sequence': self.sequence,
            'default_value': self.default_value,
            'validation_regex': self.validation_regex,
            'min_length': self.min_length,
            'max_length': self.max_length,
            'options': [
                self._build_snapshot_option_payload(option)
                for option in self.option_ids.sorted(lambda option: (option.sequence, option.id))
            ],
        }

    @api.model
    def _build_snapshot_fingerprint(self, snapshot_field):
        role_model = self.env['open.sign.role']
        min_length = self._normalize_snapshot_length_bound(snapshot_field.get('min_length'))
        max_length = self._normalize_snapshot_length_bound(snapshot_field.get('max_length'))
        if min_length not in (False, None) and max_length not in (False, None) and max_length < min_length:
            raise ValidationError(_("Field length bounds must be valid."))
        return (
            snapshot_field.get('type') or False,
            self._sanitize_label(snapshot_field.get('label')),
            bool(snapshot_field.get('required')),
            self._normalize_snapshot_page(snapshot_field.get('page')),
            self._normalize_snapshot_float(snapshot_field.get('x'), _('Field x coordinate')),
            self._normalize_snapshot_float(snapshot_field.get('y'), _('Field y coordinate')),
            self._normalize_snapshot_float(snapshot_field.get('width'), _('Field width')),
            self._normalize_snapshot_float(snapshot_field.get('height'), _('Field height')),
            self._normalize_snapshot_sequence(snapshot_field.get('sequence')),
            snapshot_field.get('default_value') or False,
            snapshot_field.get('validation_regex') or False,
            min_length,
            max_length,
            role_model._normalize_role_name_key(
                snapshot_field.get('role_name_normalized') or snapshot_field.get('role_name')
            ),
            tuple(
                self._build_snapshot_option_fingerprint(option)
                for option in snapshot_field.get('options', [])
            ),
        )

    @api.model
    def _find_snapshot_matches(self, template, snapshot_field):
        template.ensure_one()
        expected_fingerprint = self._build_snapshot_fingerprint(snapshot_field)
        return template.field_ids.filtered(
            lambda field: self._build_snapshot_fingerprint(field._build_snapshot_payload()) == expected_fingerprint
        )

    def _get_blocking_versioned_requests(self):
        return self.env['open.sign.request'].sudo().search([
            ('template_id', 'in', self.mapped('template_id').ids),
            ('template_version_id', '!=', False),
            ('status', 'in', list(REQUEST_FIELD_DELETE_BLOCKING_STATUSES)),
        ])

    def _is_referenced_by_request_snapshot(self, sign_request, template_field):
        snapshot_fields = sign_request.template_version_id.field_snapshot_json or []
        for snapshot_field in snapshot_fields:
            if snapshot_field.get('template_field_id'):
                if int(snapshot_field['template_field_id']) == template_field.id:
                    return True
                continue
            matches = self._find_snapshot_matches(sign_request.template_id, snapshot_field)
            if len(matches) == 1 and matches[0] == template_field:
                return True
        return False

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
        if 'role_id' in vals:
            blocking_requests = self._get_blocking_versioned_requests()
            for template_field in self:
                for sign_request in blocking_requests.filtered(lambda request: request.template_id == template_field.template_id):
                    if self._is_referenced_by_request_snapshot(sign_request, template_field):
                        raise ValidationError(_(
                            "Cannot change the role for field %(label)s because it is referenced by active sign requests. Archive the template or publish a new version instead.",
                            label=template_field.label,
                        ))
        return super().write(vals)

    def unlink(self):
        blocking_requests = self._get_blocking_versioned_requests()
        for template_field in self:
            for sign_request in blocking_requests.filtered(lambda request: request.template_id == template_field.template_id):
                if self._is_referenced_by_request_snapshot(sign_request, template_field):
                    raise ValidationError(_(
                        "Cannot delete field %(label)s because it is referenced by active sign requests. Archive the template or publish a new version instead.",
                        label=template_field.label,
                    ))
        return super().unlink()

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
