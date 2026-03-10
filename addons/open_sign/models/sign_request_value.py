# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..services import validation_service


TERMINAL_MUTATION_STATUSES = {'completed', 'cancelled', 'voided'}


class OpenSignRequestValue(models.Model):
    _name = 'open.sign.request.value'
    _description = 'Open Sign Request Value'
    _order = 'request_id, signer_id, template_field_id, id'
    _check_company_auto = True

    request_id = fields.Many2one(
        'open.sign.request',
        required=True,
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    template_field_id = fields.Many2one(
        'open.sign.template.field',
        required=True,
        ondelete='restrict',
        index=True,
    )
    signer_id = fields.Many2one(
        'open.sign.request.signer',
        required=True,
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    value_text = fields.Text()
    value_json = fields.Json()
    signed_payload_attachment_id = fields.Many2one(
        'ir.attachment',
        ondelete='set null',
        index=True,
        check_company=True,
    )
    is_valid = fields.Boolean(required=True, default=False, index=True)
    company_id = fields.Many2one(
        'res.company',
        related='request_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    _value_slot_uniq = models.Constraint(
        'UNIQUE(request_id, template_field_id, signer_id)',
        'Each signer can store only one value per template field on a request.',
    )

    @api.model
    def _get_effective_create_vals(self, vals, field_names):
        defaults = self.default_get(list(field_names))
        effective_vals = dict(defaults)
        effective_vals.update(vals)
        return defaults, effective_vals

    @api.model
    def _can_manage_validation_state(self):
        return self.env.su

    @api.model
    def _can_trust_prevalidated_portal_values(self):
        return self.env.su and self.env.context.get('open_sign_trusted_portal_value_payload')

    @api.model
    def _guard_is_valid_on_create(self, vals):
        if self._can_manage_validation_state():
            return
        if vals.get('is_valid'):
            raise ValidationError(_("Request value validation state cannot be set directly."))

    def _guard_is_valid_on_write(self, vals):
        if self._can_manage_validation_state():
            return
        if 'is_valid' in vals:
            raise ValidationError(_("Request value validation state cannot be modified directly."))

    @api.model
    def _guard_request_state_on_create(self, vals):
        if self.env.su:
            return
        request_id = vals.get('request_id')
        if not request_id:
            return
        request = self.env['open.sign.request'].browse(request_id).exists()
        if request and request.status in TERMINAL_MUTATION_STATUSES:
            raise ValidationError(_("Request values cannot be modified once the request is completed, cancelled, or voided."))

    def _guard_request_state_on_write(self, vals):
        if self.env.su:
            return
        target_request = None
        if 'request_id' in vals and vals.get('request_id'):
            target_request = self.env['open.sign.request'].browse(vals['request_id']).exists()
        if target_request and target_request.status in TERMINAL_MUTATION_STATUSES:
            raise ValidationError(_("Request values cannot be modified once the request is completed, cancelled, or voided."))
        if self.filtered(lambda value: value.request_id.status in TERMINAL_MUTATION_STATUSES):
            raise ValidationError(_("Request values cannot be modified once the request is completed, cancelled, or voided."))

    @api.model
    def _check_value_slot_available(self, request_id, template_field_id, signer_id, excluded_ids=None):
        domain = [
            ('request_id', '=', request_id),
            ('template_field_id', '=', template_field_id),
            ('signer_id', '=', signer_id),
        ]
        if excluded_ids:
            domain.append(('id', 'not in', list(excluded_ids)))
        if self.search_count(domain):
            raise ValidationError(_("Each signer can store only one value per template field on a request."))

    @api.model
    def _normalize_payload(self, vals, record=None):
        if self._can_trust_prevalidated_portal_values():
            return vals
        template_field = None
        template_field_id = vals.get('template_field_id')
        if template_field_id:
            template_field = self.env['open.sign.template.field'].browse(template_field_id)
        elif record:
            template_field = record.template_field_id
        if not template_field:
            return vals
        if record:
            value_text = vals.get('value_text', record.value_text)
            value_json = vals.get('value_json', record.value_json)
            signed_payload_attachment = vals.get('signed_payload_attachment_id', record.signed_payload_attachment_id.id)
        else:
            value_text = vals.get('value_text')
            value_json = vals.get('value_json')
            signed_payload_attachment = vals.get('signed_payload_attachment_id')
        normalized_text, normalized_json = validation_service.normalize_and_validate_field_value(
            template_field=template_field,
            value_text=value_text,
            value_json=value_json,
            signed_payload_attachment=signed_payload_attachment,
        )
        vals['value_text'] = normalized_text
        vals['value_json'] = normalized_json
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        pending_keys = set()
        create_fields = {
            'request_id',
            'template_field_id',
            'signer_id',
            'value_text',
            'value_json',
            'signed_payload_attachment_id',
            'is_valid',
        }
        for vals in vals_list:
            defaults, effective_vals = self._get_effective_create_vals(vals, create_fields)
            self._guard_request_state_on_create(effective_vals)
            self._guard_is_valid_on_create(effective_vals)

            normalized_vals = {
                'template_field_id': effective_vals.get('template_field_id'),
                'value_text': effective_vals.get('value_text'),
                'value_json': effective_vals.get('value_json'),
                'signed_payload_attachment_id': effective_vals.get('signed_payload_attachment_id'),
            }
            self._normalize_payload(normalized_vals)
            for payload_field in ('value_text', 'value_json'):
                if payload_field in vals or payload_field in defaults:
                    vals[payload_field] = normalized_vals.get(payload_field)

            request_id = effective_vals.get('request_id')
            template_field_id = effective_vals.get('template_field_id')
            signer_id = effective_vals.get('signer_id')
            if request_id and template_field_id and signer_id:
                key = (request_id, template_field_id, signer_id)
                if key in pending_keys:
                    raise ValidationError(_("Each signer can store only one value per template field on a request."))
                self._check_value_slot_available(request_id, template_field_id, signer_id)
                pending_keys.add(key)
        return super().create(vals_list)

    def _prepare_write_values(self, vals):
        vals = dict(vals)
        self._guard_request_state_on_write(vals)
        self._guard_is_valid_on_write(vals)

        changing_slot = bool({'request_id', 'template_field_id', 'signer_id'} & set(vals))
        pending_keys = set()
        record_values = {}
        for request_value in self:
            prepared_vals = dict(vals)
            self._normalize_payload(prepared_vals, record=request_value)
            if changing_slot:
                request_id = prepared_vals.get('request_id', request_value.request_id.id)
                template_field_id = prepared_vals.get('template_field_id', request_value.template_field_id.id)
                signer_id = prepared_vals.get('signer_id', request_value.signer_id.id)
                key = (request_id, template_field_id, signer_id)
                if key in pending_keys:
                    raise ValidationError(_("Each signer can store only one value per template field on a request."))
                pending_keys.add(key)
            record_values[request_value.id] = prepared_vals

        if changing_slot:
            for request_id, template_field_id, signer_id in pending_keys:
                self._check_value_slot_available(
                    request_id,
                    template_field_id,
                    signer_id,
                    excluded_ids=self.ids,
                )
        return record_values

    def write(self, vals):
        prepared_by_record = self._prepare_write_values(vals)
        with self.env.cr.savepoint():
            for request_value in self:
                super(OpenSignRequestValue, request_value).write(prepared_by_record[request_value.id])
        return True

    def unlink(self):
        if not self.env.su and self.filtered(lambda value: value.request_id.status in TERMINAL_MUTATION_STATUSES):
            raise ValidationError(_("Request values cannot be modified once the request is completed, cancelled, or voided."))
        return super().unlink()

    @api.constrains('template_field_id', 'request_id')
    def _check_field_matches_request_template(self):
        for request_value in self:
            if request_value.template_field_id.template_id != request_value.request_id.template_id:
                raise ValidationError(_("Value field must belong to the same template as the request."))

    @api.constrains('signer_id', 'request_id')
    def _check_signer_matches_request(self):
        for request_value in self:
            if request_value.signer_id.request_id != request_value.request_id:
                raise ValidationError(_("Value signer must belong to the same request."))

    @api.constrains('signer_id', 'template_field_id')
    def _check_signer_role_matches_field_role(self):
        for request_value in self:
            if request_value.signer_id.role_id != request_value.template_field_id.role_id:
                raise ValidationError(_("Value signer role must match the template field role."))
