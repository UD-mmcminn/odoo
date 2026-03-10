# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignTemplateField(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_field_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_field_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_field_auditor',
            groups='open_sign.group_open_sign_auditor',
        )

        acl_attachment = cls.env['ir.attachment'].create({
            'name': 'acl_field_template.pdf',
            'datas': base64.b64encode(b'%PDF-1.4\n%%EOF\n'),
            'mimetype': 'application/pdf',
            'res_model': 'open.sign.template',
            'company_id': cls.env.company.id,
        })
        cls.acl_template = cls.env['open.sign.template'].create({
            'name': 'ACL Field Template',
            'source_attachment_id': acl_attachment.id,
        })
        cls.acl_role = cls.env['open.sign.role'].create({
            'template_id': cls.acl_template.id,
            'name': 'ACL Signer',
            'sequence': 10,
        })
        cls.acl_text_field = cls.env['open.sign.template.field'].create({
            'template_id': cls.acl_template.id,
            'role_id': cls.acl_role.id,
            'type': 'text',
            'label': 'ACL Text',
            'page': 1,
            'x': 0.1,
            'y': 0.1,
            'width': 0.4,
            'height': 0.05,
            'sequence': 10,
        })
        cls.acl_selection_field = cls.env['open.sign.template.field'].create({
            'template_id': cls.acl_template.id,
            'role_id': cls.acl_role.id,
            'type': 'selection',
            'label': 'ACL Choice',
            'page': 1,
            'x': 0.2,
            'y': 0.2,
            'width': 0.4,
            'height': 0.05,
            'sequence': 20,
            'option_ids': [
                Command.create({'value': 'choice_a', 'label': 'Choice A', 'sequence': 10, 'is_default': True}),
            ],
        })
        cls.acl_option = cls.acl_selection_field.option_ids[:1]

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

    def _create_role(self, template, name='Signer'):
        return self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': name,
            'sequence': 10,
        })

    def _create_field(self, template, role, **overrides):
        values = {
            'template_id': template.id,
            'role_id': role.id,
            'type': 'text',
            'label': 'Field',
            'page': 1,
            'x': 0.1,
            'y': 0.1,
            'width': 0.4,
            'height': 0.05,
            'sequence': 10,
        }
        values.update(overrides)
        return self.env['open.sign.template.field'].create(values)

    def test_template_field_assignment_flow_with_options(self):
        template = self._create_template('Field Assignment')
        signer = self._create_role(template, 'Signer')
        template.write({
            'field_ids': [
                Command.create({
                    'role_id': signer.id,
                    'type': 'text',
                    'label': 'Full Name',
                    'page': 1,
                    'x': 0.1,
                    'y': 0.1,
                    'width': 0.4,
                    'height': 0.05,
                    'sequence': 10,
                }),
                Command.create({
                    'role_id': signer.id,
                    'type': 'selection',
                    'label': 'Plan',
                    'page': 2,
                    'x': 0.2,
                    'y': 0.2,
                    'width': 0.4,
                    'height': 0.05,
                    'sequence': 20,
                    'option_ids': [
                        Command.create({'value': 'basic', 'label': 'Basic', 'sequence': 10, 'is_default': True}),
                        Command.create({'value': 'pro', 'label': 'Pro', 'sequence': 20, 'is_default': False}),
                    ],
                }),
            ],
        })

        self.assertEqual(len(template.field_ids), 2)
        selection_field = template.field_ids.filtered(lambda field: field.type == 'selection')
        self.assertEqual(len(selection_field), 1)
        self.assertEqual(selection_field.option_ids.mapped('value'), ['basic', 'pro'])
        self.assertEqual(selection_field.option_ids.filtered('is_default').mapped('value'), ['basic'])

    def test_field_role_must_match_template(self):
        template_a = self._create_template('Template A')
        template_b = self._create_template('Template B')
        role_a = self._create_role(template_a, 'Signer A')

        with self.assertRaisesRegex(ValidationError, 'Field role must belong to the same template.'):
            self._create_field(template_b, role_a, label='Cross Template')

    def test_field_type_option_constraints(self):
        template = self._create_template('Options Check')
        role = self._create_role(template, 'Signer')

        with self.assertRaisesRegex(ValidationError, 'Radio and selection fields require at least one option.'):
            self._create_field(template, role, type='radio', label='Need Options')

        with self.assertRaisesRegex(ValidationError, 'Only radio and selection fields can define options.'):
            self._create_field(
                template,
                role,
                type='text',
                label='No Options Allowed',
                option_ids=[Command.create({'value': 'v1', 'label': 'Option 1'})],
            )

    def test_field_geometry_and_validation_constraints(self):
        template = self._create_template('Field Bounds')
        role = self._create_role(template, 'Signer')

        with self.assertRaisesRegex(ValidationError, 'Field page must be 1 or greater.'):
            self._create_field(template, role, page=0)

        with self.assertRaisesRegex(ValidationError, 'Field x coordinate must be between 0 and 1.'):
            self._create_field(template, role, x=-0.1)

        with self.assertRaisesRegex(ValidationError, 'Field width must be greater than 0 and at most 1.'):
            self._create_field(template, role, width=0)

        with self.assertRaisesRegex(ValidationError, 'Validation regex is invalid:'):
            self._create_field(template, role, validation_regex='(')

        with self.assertRaisesRegex(ValidationError, 'Minimum length must be zero or greater.'):
            self._create_field(template, role, min_length=-1)

        with self.assertRaisesRegex(ValidationError, 'Maximum length must be greater than or equal to minimum length.'):
            self._create_field(template, role, min_length=5, max_length=4)

    def test_option_constraints(self):
        template = self._create_template('Option Constraints')
        role = self._create_role(template, 'Signer')
        field = self._create_field(
            template,
            role,
            type='selection',
            label='Choice',
            option_ids=[Command.create({'value': 'choice_a', 'label': 'Choice A', 'is_default': True})],
        )

        option_model = self.env['open.sign.template.field.option']
        with self.assertRaisesRegex(ValidationError, 'Option values must be unique per field.'):
            option_model.create({
                'field_id': field.id,
                'value': 'choice_a',
                'label': 'Duplicate',
            })

        with self.assertRaisesRegex(ValidationError, 'Only one default option is allowed per field.'):
            option_model.create({
                'field_id': field.id,
                'value': 'choice_b',
                'label': 'Choice B',
                'is_default': True,
            })

    def test_field_and_option_value_normalization(self):
        template = self._create_template('Normalization')
        role = self._create_role(template, 'Signer')
        field = self._create_field(template, role, label='  Display Name  ')
        self.assertEqual(field.label, 'Display Name')

        option_field = self._create_field(
            template,
            role,
            type='selection',
            label='Plan',
            option_ids=[Command.create({'value': '  basic  ', 'label': '  Basic  ', 'is_default': True})],
        )
        option = option_field.option_ids[:1]
        self.assertEqual(option.value, 'basic')
        self.assertEqual(option.label, 'Basic')

        with self.assertRaisesRegex(ValidationError, 'Field label cannot be empty.'):
            self._create_field(template, role, label='   ')

        with self.assertRaisesRegex(ValidationError, 'Option value cannot be empty.'):
            option_field.option_ids.create({
                'field_id': option_field.id,
                'value': '   ',
                'label': 'New Label',
            })

    def test_field_label_invariant_blocks_default_context_bypass(self):
        template = self._create_template('Field Label Invariant')
        role = self._create_role(template, 'Signer')
        field_model = self.env['open.sign.template.field']

        with self.assertRaisesRegex(ValidationError, 'Field label cannot be empty.'):
            field_model.with_context(default_label='   ').create({
                'template_id': template.id,
                'role_id': role.id,
                'type': 'text',
                'page': 1,
                'x': 0.1,
                'y': 0.1,
                'width': 0.4,
                'height': 0.05,
            })

        with self.assertRaisesRegex(ValidationError, 'Field label cannot contain leading or trailing whitespace.'):
            field_model.with_context(default_label='  Default Label  ').create({
                'template_id': template.id,
                'role_id': role.id,
                'type': 'text',
                'page': 1,
                'x': 0.1,
                'y': 0.1,
                'width': 0.4,
                'height': 0.05,
            })

    def test_option_text_invariant_blocks_default_context_bypass(self):
        template = self._create_template('Option Text Invariant')
        role = self._create_role(template, 'Signer')
        field = self._create_field(
            template,
            role,
            type='selection',
            label='Choice',
            option_ids=[Command.create({'value': 'choice_a', 'label': 'Choice A', 'is_default': True})],
        )
        option_model = self.env['open.sign.template.field.option']

        with self.assertRaisesRegex(ValidationError, 'Option value cannot be empty.'):
            option_model.with_context(default_value='   ').create({
                'field_id': field.id,
                'label': 'Choice B',
            })

        with self.assertRaisesRegex(ValidationError, 'Option label cannot contain leading or trailing whitespace.'):
            option_model.with_context(default_label='  Choice B  ').create({
                'field_id': field.id,
                'value': 'choice_b',
            })

    def test_auditor_field_and_option_access_is_read_only(self):
        field_model = self.env['open.sign.template.field'].with_user(self.open_sign_auditor)
        option_model = self.env['open.sign.template.field.option'].with_user(self.open_sign_auditor)

        self.assertTrue(field_model.has_access('read'))
        self.assertFalse(field_model.has_access('create'))
        self.assertFalse(field_model.has_access('write'))
        self.assertFalse(field_model.has_access('unlink'))

        self.assertTrue(option_model.has_access('read'))
        self.assertFalse(option_model.has_access('create'))
        self.assertFalse(option_model.has_access('write'))
        self.assertFalse(option_model.has_access('unlink'))

        self.assertEqual(
            self.acl_text_field.with_user(self.open_sign_auditor).read(['label'])[0]['label'],
            'ACL Text',
        )
        self.assertEqual(
            self.acl_option.with_user(self.open_sign_auditor).read(['value'])[0]['value'],
            'choice_a',
        )

        with self.assertRaises(AccessError):
            field_model.create({
                'template_id': self.acl_template.id,
                'role_id': self.acl_role.id,
                'type': 'text',
                'label': 'Auditor Field',
                'page': 1,
                'x': 0.1,
                'y': 0.1,
                'width': 0.4,
                'height': 0.05,
            })
        with self.assertRaises(AccessError):
            option_model.create({
                'field_id': self.acl_selection_field.id,
                'value': 'choice_b',
                'label': 'Choice B',
            })

    def test_user_can_create_write_but_not_unlink_field_and_option(self):
        field_model = self.env['open.sign.template.field'].with_user(self.open_sign_user)
        option_model = self.env['open.sign.template.field.option'].with_user(self.open_sign_user)

        self.assertTrue(field_model.has_access('create'))
        self.assertTrue(field_model.has_access('write'))
        self.assertFalse(field_model.has_access('unlink'))

        self.assertTrue(option_model.has_access('create'))
        self.assertTrue(option_model.has_access('write'))
        self.assertFalse(option_model.has_access('unlink'))

        created_field = field_model.create({
            'template_id': self.acl_template.id,
            'role_id': self.acl_role.id,
            'type': 'text',
            'label': 'User Field',
            'page': 1,
            'x': 0.3,
            'y': 0.3,
            'width': 0.4,
            'height': 0.05,
        })
        created_field.write({'label': 'User Updated Field'})
        self.assertEqual(created_field.label, 'User Updated Field')

        created_option = option_model.create({
            'field_id': self.acl_selection_field.id,
            'value': 'choice_c',
            'label': 'Choice C',
        })
        created_option.write({'label': 'Choice C Updated'})
        self.assertEqual(created_option.label, 'Choice C Updated')

        with self.assertRaises(AccessError):
            created_field.unlink()
        with self.assertRaises(AccessError):
            created_option.unlink()

    def test_manager_can_unlink_field_and_option(self):
        manager_field = self.env['open.sign.template.field'].with_user(self.open_sign_manager).create({
            'template_id': self.acl_template.id,
            'role_id': self.acl_role.id,
            'type': 'text',
            'label': 'Manager Field',
            'page': 1,
            'x': 0.4,
            'y': 0.4,
            'width': 0.4,
            'height': 0.05,
        })
        manager_option = self.env['open.sign.template.field.option'].with_user(self.open_sign_manager).create({
            'field_id': self.acl_selection_field.id,
            'value': 'choice_d',
            'label': 'Choice D',
        })

        field_id = manager_field.id
        option_id = manager_option.id
        manager_field.unlink()
        manager_option.unlink()

        self.assertFalse(self.env['open.sign.template.field'].browse(field_id).exists())
        self.assertFalse(self.env['open.sign.template.field.option'].browse(option_id).exists())

    def test_field_role_change_and_unlink_blocked_for_active_versioned_requests(self):
        template = self._create_template('Versioned Field Guard')
        role_a = self._create_role(template, 'Signer A')
        role_b = self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': 'Signer B',
            'sequence': 20,
        })
        field = self._create_field(template, role_a, label='Guarded Field')
        request = self.env['open.sign.request'].create({
            'name': 'Guarded Request',
            'template_id': template.id,
        })
        self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': role_a.id,
            'email': 'guarded@example.com',
            'sequence': 10,
        })
        template.action_publish()
        request.action_version()
        request.action_send()

        with self.assertRaisesRegex(ValidationError, 'Cannot change the role for field Guarded Field because it is referenced by active sign requests.'):
            field.write({'role_id': role_b.id})

        with self.assertRaisesRegex(ValidationError, 'Cannot delete field Guarded Field because it is referenced by active sign requests.'):
            field.unlink()
