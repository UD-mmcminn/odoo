# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


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

    def test_template_unlink_archives_instead_of_hard_delete(self):
        pdf_attachment = self._create_attachment(
            'template_for_unlink.pdf',
            'application/pdf',
            b'%PDF-1.4\n%%EOF\n',
        )
        template = self.env['open.sign.template'].create({
            'name': 'Template Retained',
            'source_attachment_id': pdf_attachment.id,
        })
        request = self.env['open.sign.request'].create({
            'name': 'Linked Request',
            'template_id': template.id,
        })

        template.unlink()

        template_reloaded = self.env['open.sign.template'].with_context(active_test=False).browse(template.id)
        self.assertTrue(template_reloaded.exists())
        self.assertFalse(template_reloaded.active)
        self.assertEqual(template_reloaded.state, 'archived')
        self.assertTrue(template_reloaded.deleted_at)
        self.assertEqual(request.template_id.id, template.id)

    def test_template_hard_delete_escape_hatch_is_superuser_only(self):
        pdf_attachment = self._create_attachment(
            'template_hard_delete.pdf',
            'application/pdf',
            b'%PDF-1.4\n%%EOF\n',
        )
        template = self.env['open.sign.template'].create({
            'name': 'Template Hard Delete',
            'source_attachment_id': pdf_attachment.id,
        })

        template.with_context(open_sign_allow_template_hard_delete=True).unlink()

        template_reloaded = self.env['open.sign.template'].with_context(active_test=False).browse(template.id)
        self.assertFalse(template_reloaded.exists())

    def test_template_hard_delete_escape_hatch_ignored_for_regular_users(self):
        manager_user = new_test_user(
            self.env,
            login='open_sign_template_manager_unlink',
            groups='open_sign.group_open_sign_manager',
        )
        pdf_attachment = self._create_attachment(
            'template_soft_delete_non_su.pdf',
            'application/pdf',
            b'%PDF-1.4\n%%EOF\n',
        )
        template = self.env['open.sign.template'].create({
            'name': 'Template Soft Delete Non SU',
            'source_attachment_id': pdf_attachment.id,
        })

        template.with_user(manager_user).with_context(open_sign_allow_template_hard_delete=True).unlink()

        template_reloaded = self.env['open.sign.template'].with_context(active_test=False).browse(template.id)
        self.assertTrue(template_reloaded.exists())
        self.assertFalse(template_reloaded.active)
        self.assertEqual(template_reloaded.state, 'archived')
