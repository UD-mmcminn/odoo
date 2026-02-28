# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignTemplate(TransactionCase):

    def _create_attachment(self, name, mimetype, payload):
        return self.env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(payload),
            'mimetype': mimetype,
            'res_model': 'open.sign.template',
            'company_id': self.env.company.id,
        })

    def test_template_requires_pdf_attachment(self):
        text_attachment = self._create_attachment(
            'not_pdf.txt',
            'text/plain',
            b'hello world',
        )

        with self.assertRaises(ValidationError):
            self.env['open.sign.template'].create({
                'name': 'Invalid Template',
                'source_attachment_id': text_attachment.id,
            })

    def test_template_state_actions(self):
        pdf_attachment = self._create_attachment(
            'template.pdf',
            'application/pdf',
            b'%PDF-1.4\n%%EOF\n',
        )
        template = self.env['open.sign.template'].create({
            'name': 'Master Agreement',
            'source_attachment_id': pdf_attachment.id,
        })

        self.assertEqual(template.state, 'draft')
        self.assertTrue(template.active)

        template.action_publish()
        self.assertEqual(template.state, 'published')

        template.action_archive()
        self.assertEqual(template.state, 'archived')
        self.assertFalse(template.active)

        template.action_set_draft()
        self.assertEqual(template.state, 'draft')
        self.assertTrue(template.active)

    def test_auditor_group_has_menu_access(self):
        root_menu = self.env.ref('open_sign.menu_open_sign_root')
        auditor_group = self.env.ref('open_sign.group_open_sign_auditor')
        self.assertIn(auditor_group, root_menu.group_ids)
