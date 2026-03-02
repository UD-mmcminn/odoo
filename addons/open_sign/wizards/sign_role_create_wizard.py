# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class OpenSignRoleCreateWizard(models.TransientModel):
    _name = 'open.sign.role.create.wizard'
    _description = 'Open Sign Role Create Wizard'

    template_id = fields.Many2one(
        'open.sign.template',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    name = fields.Char(required=True)
    required = fields.Boolean(default=True, required=True)
    sequence = fields.Integer(default=10, required=True)
    color = fields.Integer(default=0)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        template_id = values.get('template_id') or self.env.context.get('default_template_id')
        if template_id and ('sequence' in fields_list or not fields_list):
            last_role = self.env['open.sign.role'].search(
                [('template_id', '=', template_id)],
                order='sequence desc, id desc',
                limit=1,
            )
            values['sequence'] = (last_role.sequence if last_role else 0) + 10
        return values

    def action_create_role(self):
        self.ensure_one()
        template = self.template_id
        template.check_access('write')
        self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': self.name,
            'required': self.required,
            'sequence': self.sequence,
            'color': self.color,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'name': _('Role Created'),
        }
