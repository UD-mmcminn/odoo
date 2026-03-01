# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


SHA256_HEX_RE = re.compile(r'^[0-9a-f]{64}$')


class OpenSignTemplateVersion(models.Model):
    _name = 'open.sign.template.version'
    _description = 'Open Sign Template Version'
    _order = 'template_id, version_number desc, id desc'
    _check_company_auto = True

    template_id = fields.Many2one(
        'open.sign.template',
        required=True,
        ondelete='cascade',
        index=True,
        check_company=True,
    )
    version_number = fields.Integer(required=True, index=True)
    source_attachment_id = fields.Many2one(
        'ir.attachment',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    source_pdf_sha256 = fields.Char(required=True, index=True)
    field_snapshot_json = fields.Json(default=list)
    role_snapshot_json = fields.Json(default=list)
    published_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    published_by = fields.Many2one(
        'res.users',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
        index=True,
    )
    state = fields.Selection(
        selection=[
            ('published', 'Published'),
        ],
        required=True,
        default='published',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='template_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    _template_version_uniq = models.Constraint(
        'UNIQUE(template_id, version_number)',
        'Template version number must be unique per template.',
    )
    _version_number_positive_check = models.Constraint(
        'CHECK(version_number > 0)',
        'Template version number must be greater than zero.',
    )

    def _can_mutate_version_record(self):
        return self.env.su and self.env.context.get('open_sign_allow_template_version_mutation')

    @api.model
    def _compute_attachment_sha256(self, attachment):
        attachment.ensure_one()
        if not attachment.datas:
            raise ValidationError(_("Template source attachment must have binary content."))
        binary_payload = base64.b64decode(attachment.datas)
        return hashlib.sha256(binary_payload).hexdigest()

    @api.model
    def create_from_template(self, template):
        template.ensure_one()
        if template.source_attachment_id.mimetype != 'application/pdf':
            raise ValidationError(_("Template source attachment must be a PDF document."))
        latest_version = self.search([('template_id', '=', template.id)], order='version_number desc', limit=1)
        next_version_number = (latest_version.version_number or 0) + 1
        source_digest = self._compute_attachment_sha256(template.source_attachment_id)
        return self.sudo().create({
            'template_id': template.id,
            'version_number': next_version_number,
            'source_attachment_id': template.source_attachment_id.id,
            'source_pdf_sha256': source_digest,
            'field_snapshot_json': template._build_field_snapshot(),
            'role_snapshot_json': template._build_role_snapshot(),
            'published_by': self.env.user.id,
            'state': 'published',
        })

    def write(self, vals):
        if not self._can_mutate_version_record():
            raise ValidationError(_("Template versions are immutable once published."))
        return super().write(vals)

    def unlink(self):
        if not self._can_mutate_version_record():
            raise ValidationError(_("Template versions are immutable once published."))
        return super().unlink()

    @api.constrains('source_pdf_sha256')
    def _check_source_digest_format(self):
        for version in self:
            if not SHA256_HEX_RE.fullmatch(version.source_pdf_sha256 or ''):
                raise ValidationError(_("Source PDF SHA-256 must be a 64-character lowercase hexadecimal string."))
