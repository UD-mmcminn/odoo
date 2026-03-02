# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignRole(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_auditor',
            groups='open_sign.group_open_sign_auditor',
        )
        cls.acl_template = cls.env['open.sign.template'].create({
            'name': 'ACL Template',
            'source_attachment_id': cls.env['ir.attachment'].create({
                'name': 'acl_template.pdf',
                'datas': base64.b64encode(b'%PDF-1.4\n%%EOF\n'),
                'mimetype': 'application/pdf',
                'res_model': 'open.sign.template',
                'company_id': cls.env.company.id,
            }).id,
        })
        cls.acl_role = cls.env['open.sign.role'].create({
            'template_id': cls.acl_template.id,
            'name': 'ACL Reviewer',
            'sequence': 10,
        })

    def _create_attachment(self, name='template.pdf'):
        return self.env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(b'%PDF-1.4\n%%EOF\n'),
            'mimetype': 'application/pdf',
            'res_model': 'open.sign.template',
            'company_id': self.env.company.id,
        })

    def _create_template(self, name='Template'):
        return self.env['open.sign.template'].create({
            'name': name,
            'source_attachment_id': self._create_attachment(f'{name}.pdf').id,
        })

    def test_template_role_assignment_flow(self):
        template = self._create_template('Sales Contract')
        template.write({
            'role_ids': [
                Command.create({'name': 'Customer', 'sequence': 20}),
                Command.create({'name': 'Vendor', 'sequence': 10, 'required': True}),
            ],
        })

        self.assertEqual(len(template.role_ids), 2)
        self.assertTrue(all(role.template_id == template for role in template.role_ids))
        self.assertEqual(sorted(template.role_ids.mapped('sequence')), [10, 20])

    def test_role_name_must_be_unique_per_template(self):
        template = self._create_template('MSA')
        role_model = self.env['open.sign.role']
        role_model.create({
            'template_id': template.id,
            'name': 'Signer',
            'sequence': 10,
        })

        with self.assertRaisesRegex(ValidationError, 'Role names must be unique per template \\(case-insensitive\\).'):
            role_model.create({
                'template_id': template.id,
                'name': 'Signer',
                'sequence': 20,
            })

    def test_role_name_must_be_unique_per_template_case_insensitive(self):
        template = self._create_template('Case Check')
        role_model = self.env['open.sign.role']
        role_model.create({
            'template_id': template.id,
            'name': 'Signer',
            'sequence': 10,
        })

        with self.assertRaisesRegex(ValidationError, 'Role names must be unique per template \\(case-insensitive\\).'):
            role_model.create({
                'template_id': template.id,
                'name': 'sIgNeR',
                'sequence': 20,
            })

    def test_role_name_is_trimmed_on_create_and_write(self):
        template = self._create_template('Trim Check')
        role = self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': '  Signer  ',
            'sequence': 10,
        })
        self.assertEqual(role.name, 'Signer')
        self.assertEqual(role.name_normalized, 'signer')

        role.write({'name': '  Reviewer  '})
        self.assertEqual(role.name, 'Reviewer')
        self.assertEqual(role.name_normalized, 'reviewer')

    def test_role_name_normalized_cannot_be_injected(self):
        template = self._create_template('Normalization Guard')
        role = self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': 'Signer',
            'name_normalized': 'tampered',
            'sequence': 10,
        })

        self.assertEqual(role.name_normalized, 'signer')
        role.write({'name_normalized': 'attacker'})
        self.assertEqual(role.name_normalized, 'signer')

    def test_role_name_cannot_be_blank_after_normalization(self):
        template = self._create_template('Blank Name Guard')

        with self.assertRaisesRegex(ValidationError, 'Role name cannot be empty.'):
            self.env['open.sign.role'].create({
                'template_id': template.id,
                'name': '   ',
                'sequence': 10,
            })

    def test_role_sequence_must_be_non_negative(self):
        template = self._create_template('NDA')
        with self.assertRaisesRegex(ValidationError, 'Role sequence must be zero or greater.'):
            self.env['open.sign.role'].create({
                'template_id': template.id,
                'name': 'Approver',
                'sequence': -1,
            })

    def test_auditor_role_access_is_read_only(self):
        role_model = self.env['open.sign.role'].with_user(self.open_sign_auditor)
        self.assertTrue(role_model.has_access('read'))
        self.assertFalse(role_model.has_access('create'))
        self.assertFalse(role_model.has_access('write'))
        self.assertFalse(role_model.has_access('unlink'))
        self.assertEqual(self.acl_role.with_user(self.open_sign_auditor).read(['name'])[0]['name'], 'ACL Reviewer')

        with self.assertRaises(AccessError):
            role_model.create({
                'template_id': self.acl_template.id,
                'name': 'Auditor Create',
                'sequence': 20,
            })
        with self.assertRaises(AccessError):
            self.acl_role.with_user(self.open_sign_auditor).write({'name': 'Auditor Update'})
        with self.assertRaises(AccessError):
            self.acl_role.with_user(self.open_sign_auditor).unlink()

    def test_user_can_create_write_but_not_unlink_role(self):
        role_model = self.env['open.sign.role'].with_user(self.open_sign_user)
        self.assertTrue(role_model.has_access('create'))
        self.assertTrue(role_model.has_access('write'))
        self.assertFalse(role_model.has_access('unlink'))

        created_role = role_model.create({
            'template_id': self.acl_template.id,
            'name': 'User Create',
            'sequence': 30,
        })
        created_role.write({'name': 'User Updated'})
        self.assertEqual(created_role.name, 'User Updated')

        with self.assertRaises(AccessError):
            created_role.unlink()

    def test_manager_can_unlink_role(self):
        created_role = self.env['open.sign.role'].with_user(self.open_sign_manager).create({
            'template_id': self.acl_template.id,
            'name': 'Manager Delete',
            'sequence': 40,
        })
        role_id = created_role.id
        created_role.unlink()
        self.assertFalse(self.env['open.sign.role'].browse(role_id).exists())

    def test_role_create_wizard_creates_role_and_reloads(self):
        template = self._create_template('Wizard Role Template')
        wizard = self.env['open.sign.role.create.wizard'].with_user(self.open_sign_user).create({
            'template_id': template.id,
            'name': 'Wizard Signer',
            'required': False,
            'sequence': 25,
            'color': 3,
        })

        action = wizard.action_create_role()

        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'reload')
        created_role = self.env['open.sign.role'].search([
            ('template_id', '=', template.id),
            ('name', '=', 'Wizard Signer'),
        ], limit=1)
        self.assertTrue(created_role)
        self.assertFalse(created_role.required)
        self.assertEqual(created_role.sequence, 25)
