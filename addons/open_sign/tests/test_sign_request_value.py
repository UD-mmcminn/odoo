# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignRequestValue(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_value_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_value_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_value_auditor',
            groups='open_sign.group_open_sign_auditor',
        )

        cls.acl_template = cls._create_template_static(cls.env, 'ACL Value Template')
        cls.acl_role = cls.env['open.sign.role'].create({
            'template_id': cls.acl_template.id,
            'name': 'ACL Value Signer',
            'sequence': 10,
        })
        cls.acl_field = cls._create_field_static(
            cls.env,
            cls.acl_template,
            cls.acl_role,
            type='text',
            label='ACL Field',
        )
        cls.acl_request = cls.env['open.sign.request'].create({
            'name': 'ACL Value Request',
            'template_id': cls.acl_template.id,
            'owner_id': cls.open_sign_user.id,
        })
        cls.acl_signer = cls.env['open.sign.request.signer'].create({
            'request_id': cls.acl_request.id,
            'role_id': cls.acl_role.id,
            'email': 'acl.value.signer@example.com',
            'sequence': 10,
        })
        cls.acl_value = cls.env['open.sign.request.value'].create({
            'request_id': cls.acl_request.id,
            'template_field_id': cls.acl_field.id,
            'signer_id': cls.acl_signer.id,
            'value_text': 'ACL Initial Value',
        })

    @classmethod
    def _create_attachment_static(cls, env, name='template.pdf', res_model='open.sign.template', mimetype='application/pdf'):
        return env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(b'%PDF-1.4\n%%EOF\n'),
            'mimetype': mimetype,
            'res_model': res_model,
            'company_id': env.company.id,
        })

    @classmethod
    def _create_template_static(cls, env, name='Template'):
        template = env['open.sign.template'].create({
            'name': name,
            'source_attachment_id': cls._create_attachment_static(env, f'{name}.pdf').id,
        })
        template.action_publish()
        return template

    @classmethod
    def _create_field_static(cls, env, template, role, **overrides):
        values = {
            'template_id': template.id,
            'role_id': role.id,
            'type': 'text',
            'label': 'Field',
            'page': 1,
            'x': 0.1,
            'y': 0.1,
            'width': 0.3,
            'height': 0.05,
            'sequence': 10,
        }
        values.update(overrides)
        return env['open.sign.template.field'].create(values)

    def _create_template(self, name='Template'):
        return self._create_template_static(self.env, name)

    def _create_role(self, template, name='Signer', sequence=10):
        return self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': name,
            'sequence': sequence,
        })

    def _create_field(self, template, role, **overrides):
        return self._create_field_static(self.env, template, role, **overrides)

    def _create_request(self, template, name='Request', **overrides):
        values = {
            'name': name,
            'template_id': template.id,
        }
        values.update(overrides)
        return self.env['open.sign.request'].create(values)

    def _create_signer(self, request, role, email='signer@example.com', sequence=10):
        return self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': role.id,
            'email': email,
            'sequence': sequence,
        })

    def _create_value(self, request, template_field, signer, **overrides):
        values = {
            'request_id': request.id,
            'template_field_id': template_field.id,
            'signer_id': signer.id,
        }
        values.update(overrides)
        return self.env['open.sign.request.value'].create(values)

    def _mark_request_completed(self, request):
        template_version = request.template_id.action_publish_version()
        final_attachment = self._create_attachment_static(
            self.env,
            name=f'{request.name}_final.pdf',
            res_model='open.sign.request',
        )
        request.sudo().with_context(open_sign_skip_transition_check=True).write({
            'status': 'completed',
            'template_version_id': template_version.id,
            'source_pdf_sha256': template_version.source_pdf_sha256,
            'final_attachment_id': final_attachment.id,
            'final_pdf_sha256': 'f' * 64,
            'completed_at': fields.Datetime.now(),
        })

    def _set_request_terminal_status(self, request, status):
        if status == 'completed':
            self._mark_request_completed(request)
            return
        if status == 'cancelled':
            request.action_cancel()
            return
        if status == 'voided':
            self._mark_request_completed(request)
            request.action_void(reason='terminal value state test')
            return
        raise ValueError(f'Unsupported terminal status: {status}')

    def test_value_constraints_and_unique_slot(self):
        template_a = self._create_template('Value Constraints A')
        template_b = self._create_template('Value Constraints B')
        role_a_1 = self._create_role(template_a, name='A1', sequence=10)
        role_a_2 = self._create_role(template_a, name='A2', sequence=20)
        role_b = self._create_role(template_b, name='B1', sequence=10)
        field_a_1 = self._create_field(template_a, role_a_1, type='text', label='A1 Field')
        field_a_2 = self._create_field(template_a, role_a_2, type='text', label='A2 Field')
        field_b = self._create_field(template_b, role_b, type='text', label='B Field')
        request_a = self._create_request(template_a, name='Req A')
        request_b = self._create_request(template_a, name='Req B')
        signer_a = self._create_signer(request_a, role_a_1, email='a1@example.com', sequence=10)
        signer_b = self._create_signer(request_b, role_a_1, email='b1@example.com', sequence=10)

        self._create_value(request_a, field_a_1, signer_a, value_text='ok')
        with self.assertRaisesRegex(ValidationError, 'Each signer can store only one value per template field on a request.'):
            self._create_value(request_a, field_a_1, signer_a, value_text='duplicate')

        with self.assertRaisesRegex(ValidationError, 'Value field must belong to the same template as the request.'):
            self._create_value(request_a, field_b, signer_a, value_text='wrong template')

        with self.assertRaisesRegex(ValidationError, 'Value signer must belong to the same request.'):
            self._create_value(request_a, field_a_1, signer_b, value_text='wrong signer request')

        with self.assertRaisesRegex(ValidationError, 'Value signer role must match the template field role.'):
            self._create_value(request_a, field_a_2, signer_a, value_text='wrong role')

    def test_value_text_normalization(self):
        template = self._create_template('Value Text Normalization')
        role = self._create_role(template, name='Signer')
        request = self._create_request(template, name='Value Text Request')
        signer = self._create_signer(request, role, email='normalize@example.com')
        field_email = self._create_field(template, role, type='email', label='Email')
        field_initials = self._create_field(template, role, type='initials', label='Initials')
        field_multiline = self._create_field(template, role, type='multiline', label='Multiline')
        field_selection = self._create_field(
            template,
            role,
            type='selection',
            label='Selection',
            option_ids=[
                Command.create({'value': 'basic', 'label': 'Basic', 'sequence': 10, 'is_default': True}),
                Command.create({'value': 'pro', 'label': 'Pro', 'sequence': 20, 'is_default': False}),
            ],
        )

        value_email = self._create_value(request, field_email, signer, value_text='  ALICE@EXAMPLE.COM  ')
        self.assertEqual(value_email.value_text, 'alice@example.com')

        value_initials = self._create_value(request, field_initials, signer, value_text='  am ')
        self.assertEqual(value_initials.value_text, 'AM')

        value_multiline = self._create_value(request, field_multiline, signer, value_text='line1\r\nline2\rline3')
        self.assertEqual(value_multiline.value_text, 'line1\nline2\nline3')

        value_selection = self._create_value(request, field_selection, signer, value_text='  PRO  ')
        self.assertEqual(value_selection.value_text, 'pro')

    def test_value_json_normalization_and_type_constraints(self):
        template = self._create_template('Value JSON Normalization')
        role = self._create_role(template, name='Signer')
        request = self._create_request(template, name='Value JSON Request')
        signer = self._create_signer(request, role, email='json@example.com')
        field_checkbox = self._create_field(template, role, type='checkbox', label='Checkbox')
        field_date = self._create_field(template, role, type='date', label='Date')
        field_strike = self._create_field(template, role, type='strikethrough', label='Strike')

        value_checkbox = self._create_value(request, field_checkbox, signer, value_json=True)
        self.assertTrue(value_checkbox.value_json)

        value_date = self._create_value(request, field_date, signer, value_json='2026-02-28')
        self.assertEqual(value_date.value_json, {'iso_date': '2026-02-28'})
        value_date.write({'value_json': {'iso_date': '2026-03-01', 'timezone': '  UTC  '}})
        self.assertEqual(value_date.value_json, {'iso_date': '2026-03-01', 'timezone': 'UTC'})

        value_strike = self._create_value(request, field_strike, signer, value_json=True)
        self.assertEqual(value_strike.value_json, {'applied': True})

        with self.assertRaisesRegex(ValidationError, 'Checkbox values must be booleans.'):
            self._create_value(request, field_checkbox, signer, value_json='yes')
        with self.assertRaisesRegex(ValidationError, 'Date values must use ISO-8601 format'):
            self._create_value(request, field_date, signer, value_json='02/28/2026')
        with self.assertRaisesRegex(ValidationError, 'Strikethrough values must provide a boolean applied flag.'):
            self._create_value(request, field_strike, signer, value_json={'applied': 'yes'})

    def test_required_optional_and_rule_validation(self):
        template = self._create_template('Value Rule Validation')
        role = self._create_role(template, name='Signer')
        request = self._create_request(template, name='Value Rule Request')
        signer = self._create_signer(request, role, email='rules@example.com')

        field_required_text = self._create_field(
            template,
            role,
            type='text',
            label='Required Text',
            required=True,
            min_length=3,
            max_length=5,
            validation_regex='^[A-Z0-9]+$',
        )
        field_optional_text = self._create_field(template, role, type='text', label='Optional Text', required=False)
        field_initials = self._create_field(template, role, type='initials', label='Initials', required=True)
        field_phone = self._create_field(template, role, type='phone', label='Phone', required=True)
        field_checkbox = self._create_field(template, role, type='checkbox', label='Checkbox', required=True)
        field_checkbox_required_missing = self._create_field(
            template,
            role,
            type='checkbox',
            label='Checkbox Required Missing',
            required=True,
            sequence=11,
        )
        field_signature = self._create_field(template, role, type='signature', label='Signature', required=True)

        with self.assertRaisesRegex(ValidationError, 'Required field Required Text must have a value.'):
            self._create_value(request, field_required_text, signer, value_text='   ')

        with self.assertRaisesRegex(ValidationError, 'Value length must be greater than or equal to 3'):
            self._create_value(request, field_required_text, signer, value_text='AB')

        with self.assertRaisesRegex(ValidationError, 'Value does not match the field validation pattern.'):
            self._create_value(request, field_required_text, signer, value_text='ABC-')

        value_required_text = self._create_value(request, field_required_text, signer, value_text='  AB12 ')
        self.assertEqual(value_required_text.value_text, 'AB12')

        optional_value = self._create_value(request, field_optional_text, signer, value_text='  ')
        self.assertFalse(optional_value.value_text)

        with self.assertRaisesRegex(ValidationError, 'Single-line text values cannot contain newlines.'):
            optional_value.write({'value_text': 'line1\nline2'})

        with self.assertRaisesRegex(ValidationError, 'Initials values must be between 1 and 8 characters.'):
            self._create_value(request, field_initials, signer, value_text='ABCDEFGHI')

        initials_value = self._create_value(request, field_initials, signer, value_text=' am ')
        self.assertEqual(initials_value.value_text, 'AM')

        with self.assertRaisesRegex(ValidationError, 'Phone values must be digits with an optional leading \\+'):
            self._create_value(request, field_phone, signer, value_text='not-a-phone')

        phone_value = self._create_value(request, field_phone, signer, value_text=' (555) 123-4567 ')
        self.assertEqual(phone_value.value_text, '5551234567')

        checkbox_false = self._create_value(request, field_checkbox, signer, value_json=False)
        self.assertEqual(checkbox_false.value_json, False)

        with self.assertRaisesRegex(ValidationError, 'Required field Checkbox Required Missing must have a value.'):
            self._create_value(request, field_checkbox_required_missing, signer, value_json=None)

        with self.assertRaisesRegex(ValidationError, 'Signature and stamp values require a signed payload attachment.'):
            self._create_value(
                request,
                field_signature,
                signer,
                value_json={'method': 'draw', 'display_name': 'Alice Signer'},
            )

        payload_attachment = self._create_attachment_static(
            self.env,
            name='signature_payload.png',
            res_model='open.sign.request.value',
            mimetype='image/png',
        )
        signature_value = self._create_value(
            request,
            field_signature,
            signer,
            value_json={'method': 'draw', 'display_name': 'Alice Signer'},
            signed_payload_attachment_id=payload_attachment.id,
        )
        self.assertEqual(signature_value.value_json['method'], 'draw')
        self.assertFalse(signature_value.value_text)

    def test_is_valid_is_server_authoritative(self):
        template = self._create_template('Value Validation Guard')
        role = self._create_role(template, name='Signer')
        field_text = self._create_field(template, role, type='text', label='Guarded Field')
        request = self._create_request(template, name='Guarded Request', owner_id=self.open_sign_user.id)
        signer = self._create_signer(request, role, email='guard@example.com')
        value_model = self.env['open.sign.request.value'].with_user(self.open_sign_user)

        with self.assertRaisesRegex(ValidationError, 'Request value validation state cannot be set directly.'):
            value_model.create({
                'request_id': request.id,
                'template_field_id': field_text.id,
                'signer_id': signer.id,
                'value_text': 'user text',
                'is_valid': True,
            })

        created_value = value_model.create({
            'request_id': request.id,
            'template_field_id': field_text.id,
            'signer_id': signer.id,
            'value_text': 'user text',
        })
        with self.assertRaisesRegex(ValidationError, 'Request value validation state cannot be modified directly.'):
            created_value.write({'is_valid': True})

        created_value.sudo().write({'is_valid': True})
        self.assertTrue(created_value.is_valid)

    def test_default_context_cannot_bypass_value_guards_or_normalization(self):
        template = self._create_template('Value Default Context Guard')
        role = self._create_role(template, name='Signer')
        request = self._create_request(
            template,
            name='Value Default Context Request',
            owner_id=self.open_sign_user.id,
        )
        signer = self._create_signer(request, role, email='default.context@example.com')
        field_text = self._create_field(template, role, type='text', label='Text Field')
        field_email = self._create_field(template, role, type='email', label='Email Field')
        field_checkbox = self._create_field(template, role, type='checkbox', label='Checkbox Field')
        value_model = self.env['open.sign.request.value'].with_user(self.open_sign_user)

        with self.assertRaisesRegex(ValidationError, 'Request value validation state cannot be set directly.'):
            value_model.with_context(default_is_valid=True).create({
                'request_id': request.id,
                'template_field_id': field_text.id,
                'signer_id': signer.id,
            })

        email_value = value_model.with_context(default_value_text='  ALICE@EXAMPLE.COM  ').create({
            'request_id': request.id,
            'template_field_id': field_email.id,
            'signer_id': signer.id,
        })
        self.assertEqual(email_value.value_text, 'alice@example.com')

        with self.assertRaisesRegex(ValidationError, 'Checkbox values must be booleans.'):
            value_model.with_context(default_value_json='yes').create({
                'request_id': request.id,
                'template_field_id': field_checkbox.id,
                'signer_id': signer.id,
            })

    def test_auditor_value_access_is_read_only(self):
        value_model = self.env['open.sign.request.value'].with_user(self.open_sign_auditor)
        self.assertTrue(value_model.has_access('read'))
        self.assertFalse(value_model.has_access('create'))
        self.assertFalse(value_model.has_access('write'))
        self.assertFalse(value_model.has_access('unlink'))

        self.assertEqual(
            self.acl_value.with_user(self.open_sign_auditor).read(['value_text'])[0]['value_text'],
            'ACL Initial Value',
        )

        auditor_role = self._create_role(self.acl_template, name='ACL Auditor Value Role', sequence=50)
        auditor_field = self._create_field(self.acl_template, auditor_role, type='text', label='ACL Auditor Field')
        auditor_signer = self._create_signer(self.acl_request, auditor_role, email='acl.auditor.value@example.com', sequence=50)

        with self.assertRaises(AccessError):
            value_model.create({
                'request_id': self.acl_request.id,
                'template_field_id': auditor_field.id,
                'signer_id': auditor_signer.id,
                'value_text': 'auditor value',
            })
        with self.assertRaises(AccessError):
            self.acl_value.with_user(self.open_sign_auditor).write({'value_text': 'auditor update'})
        with self.assertRaises(AccessError):
            self.acl_value.with_user(self.open_sign_auditor).unlink()

    def test_user_can_create_write_but_not_unlink_value(self):
        value_model = self.env['open.sign.request.value'].with_user(self.open_sign_user)
        self.assertTrue(value_model.has_access('create'))
        self.assertTrue(value_model.has_access('write'))
        self.assertFalse(value_model.has_access('unlink'))

        role = self._create_role(self.acl_template, name='ACL User Value Role', sequence=30)
        field = self._create_field(self.acl_template, role, type='text', label='User Value Field')
        signer = self._create_signer(self.acl_request, role, email='user.value.signer@example.com', sequence=30)

        created_value = value_model.create({
            'request_id': self.acl_request.id,
            'template_field_id': field.id,
            'signer_id': signer.id,
            'value_text': '  User Value  ',
        })
        self.assertEqual(created_value.value_text, 'User Value')
        created_value.write({'value_text': '  User Value Updated  '})
        self.assertEqual(created_value.value_text, 'User Value Updated')

        with self.assertRaises(AccessError):
            created_value.unlink()

    def test_value_mutation_blocked_on_terminal_requests(self):
        for status in ('completed', 'cancelled', 'voided'):
            template = self._create_template(f'Terminal Value Mutation Template {status}')
            role = self._create_role(template, name=f'Terminal Value Role {status}', sequence=10)
            field_a = self._create_field(template, role, type='text', label=f'Terminal Value Field A {status}')
            field_b = self._create_field(template, role, type='text', label=f'Terminal Value Field B {status}', sequence=20)
            request = self._create_request(template, name=f'Terminal Value Mutation Request {status}')
            signer = self._create_signer(request, role, email=f'terminal.value.signer.{status}@example.com', sequence=10)
            value = self._create_value(request, field_a, signer, value_text='Terminal Initial')
            self._set_request_terminal_status(request, status)

            with self.assertRaisesRegex(ValidationError, 'Request values cannot be modified once the request is completed, cancelled, or voided.'):
                value.with_user(self.open_sign_user).write({'value_text': f'Terminal Update {status}'})

            with self.assertRaisesRegex(ValidationError, 'Request values cannot be modified once the request is completed, cancelled, or voided.'):
                self.env['open.sign.request.value'].with_user(self.open_sign_user).create({
                    'request_id': request.id,
                    'template_field_id': field_b.id,
                    'signer_id': signer.id,
                    'value_text': f'Terminal New Value {status}',
                })

            with self.assertRaisesRegex(ValidationError, 'Request values cannot be modified once the request is completed, cancelled, or voided.'):
                value.with_user(self.open_sign_manager).unlink()

    def test_multi_record_write_rolls_back_on_validation_error(self):
        template = self._create_template('Multi Write Atomicity Template')
        role = self._create_role(template, name='Atomicity Signer', sequence=10)
        request = self._create_request(template, name='Multi Write Atomicity Request')
        signer = self._create_signer(request, role, email='atomicity@example.com', sequence=10)
        field_date = self._create_field(template, role, type='date', label='Atomic Date Field')
        field_checkbox = self._create_field(template, role, type='checkbox', label='Atomic Checkbox Field', sequence=20)
        date_value = self._create_value(request, field_date, signer, value_json='2026-02-28')
        checkbox_value = self._create_value(request, field_checkbox, signer, value_json=False)

        values = self.env['open.sign.request.value'].browse([date_value.id, checkbox_value.id])
        with self.assertRaisesRegex(ValidationError, 'Checkbox values must be booleans.'):
            values.write({'value_json': '2026-03-01'})

        self.assertEqual(date_value.value_json, {'iso_date': '2026-02-28'})
        self.assertEqual(checkbox_value.value_json, False)

    def test_manager_can_unlink_value(self):
        role = self._create_role(self.acl_template, name='ACL Manager Value Role', sequence=40)
        field = self._create_field(self.acl_template, role, type='text', label='Manager Value Field')
        signer = self._create_signer(self.acl_request, role, email='manager.value.signer@example.com', sequence=40)
        created_value = self.env['open.sign.request.value'].with_user(self.open_sign_manager).create({
            'request_id': self.acl_request.id,
            'template_field_id': field.id,
            'signer_id': signer.id,
            'value_text': 'Manager Value',
        })
        value_id = created_value.id
        created_value.unlink()
        self.assertFalse(self.env['open.sign.request.value'].browse(value_id).exists())
