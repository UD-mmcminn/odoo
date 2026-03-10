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
        index=True,
        check_company=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, index=True)
    deleted_at = fields.Datetime(index=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        ondelete='restrict',
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

    def action_open_new_role_wizard(self):
        self.ensure_one()
        self.check_access('write')
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Signer Role'),
            'res_model': 'open.sign.role.create.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('open_sign.view_open_sign_role_create_wizard_form').id,
            'target': 'new',
            'context': {
                'default_template_id': self.id,
            },
        }

    def action_open_pdf_editor(self):
        self.ensure_one()
        self.check_access('read')
        return {
            'type': 'ir.actions.client',
            'name': _('Template PDF Editor'),
            'tag': 'open_sign_web.template_canvas_action',
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            },
        }

    def _build_role_snapshot(self):
        self.ensure_one()
        return [role._build_snapshot_payload() for role in self.role_ids.sorted('sequence, id')]

    def _build_field_snapshot(self):
        self.ensure_one()
        return [template_field._build_snapshot_payload() for template_field in self.field_ids.sorted('page, sequence, id')]

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
        self.write({
            'state': 'archived',
            'active': False,
            'deleted_at': fields.Datetime.now(),
        })

    def action_set_draft(self):
        self.write({
            'state': 'draft',
            'active': True,
            'deleted_at': False,
        })

    @api.model
    def _can_hard_delete_template(self):
        return self.env.su and self.env.context.get('open_sign_allow_template_hard_delete')

    def unlink(self):
        self.check_access('unlink')
        if self._can_hard_delete_template():
            return super().unlink()
        self.write({
            'state': 'archived',
            'active': False,
            'deleted_at': fields.Datetime.now(),
        })
        return True
