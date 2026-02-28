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

    @api.constrains('source_attachment_id')
    def _check_source_attachment_pdf(self):
        for template in self:
            if template.source_attachment_id.mimetype != 'application/pdf':
                raise ValidationError(_("The source attachment must be a PDF document."))

    def action_publish(self):
        self.write({'state': 'published'})

    def action_archive(self):
        self.write({'state': 'archived', 'active': False})

    def action_set_draft(self):
        self.write({'state': 'draft', 'active': True})
