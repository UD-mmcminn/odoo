# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpenSignTemplate(models.Model):
    _name = 'open.sign.template'
    _description = 'Open Sign Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True, index=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ],
        default='draft',
        required=True,
        index=True,
        tracking=True,
    )
    source_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Source PDF',
        required=True,
        ondelete='restrict',
        check_company=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, index=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    owner_id = fields.Many2one(
        'res.users',
        required=True,
        index=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
    )
    role_ids = fields.One2many('open.sign.role', 'template_id', string='Signer Roles')
    field_ids = fields.One2many('open.sign.template.field', 'template_id', string='Template Fields')
    version_ids = fields.One2many('open.sign.template.version', 'template_id', string='Template Versions')
    request_ids = fields.One2many('open.sign.request', 'template_id', string='Sign Requests')

    @api.constrains('source_attachment_id')
    def _check_source_attachment_pdf(self):
        for template in self:
            if template.source_attachment_id.mimetype != 'application/pdf':
                raise ValidationError(_("The source attachment must be a PDF document."))

    def action_publish(self):
        self.write({'state': 'published'})

    def _build_role_snapshot(self):
        self.ensure_one()
        return [
            {
                'name': role.name,
                'name_normalized': role.name_normalized,
                'sequence': role.sequence,
                'required': role.required,
                'color': role.color,
            }
            for role in self.role_ids.sorted('sequence, id')
        ]

    def _build_field_snapshot(self):
        self.ensure_one()
        snapshot = []
        for template_field in self.field_ids.sorted('page, sequence, id'):
            snapshot.append({
                'type': template_field.type,
                'label': template_field.label,
                'required': template_field.required,
                'page': template_field.page,
                'x': template_field.x,
                'y': template_field.y,
                'width': template_field.width,
                'height': template_field.height,
                'sequence': template_field.sequence,
                'default_value': template_field.default_value,
                'validation_regex': template_field.validation_regex,
                'min_length': template_field.min_length,
                'max_length': template_field.max_length,
                'role_name': template_field.role_id.name,
                'options': [
                    {
                        'value': option.value,
                        'label': option.label,
                        'sequence': option.sequence,
                        'is_default': option.is_default,
                    }
                    for option in template_field.option_ids.sorted('sequence, id')
                ],
            })
        return snapshot

    def action_publish_version(self):
        versions = self.env['open.sign.template.version']
        for template in self:
            if template.state != 'published':
                raise ValidationError(_("Template must be published before versioning."))
            versions |= self.env['open.sign.template.version'].create_from_template(template)
        if len(versions) == 1:
            return versions[0]
        return versions

    def action_archive(self):
        self.write({'state': 'archived', 'active': False})

    def action_set_draft(self):
        self.write({'state': 'draft', 'active': True})
