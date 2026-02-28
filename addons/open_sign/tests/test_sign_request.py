# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_request_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_request_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_request_auditor',
            groups='open_sign.group_open_sign_auditor',
        )
        cls.acl_template = cls._create_template_static(cls.env, 'ACL Request Template')
        cls.acl_version = cls.acl_template.action_publish_version()
        cls.acl_request = cls.env['open.sign.request'].create({
            'name': 'ACL Request',
            'template_id': cls.acl_template.id,
        })

    @classmethod
    def _create_attachment_static(cls, env, name='template.pdf', res_model='open.sign.template'):
        return env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(b'%PDF-1.4\n%%EOF\n'),
            'mimetype': 'application/pdf',
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

    def _create_attachment(self, name='template.pdf', res_model='open.sign.template'):
        return self._create_attachment_static(self.env, name, res_model)

    def _create_template(self, name='Template'):
        return self._create_template_static(self.env, name)

    def _create_request(self, template=None, **overrides):
        template = template or self._create_template('Request Template')
        values = {
            'name': f'{template.name} Request',
            'template_id': template.id,
        }
        values.update(overrides)
        return self.env['open.sign.request'].create(values)

    def test_request_action_version_send_complete_void_flow(self):
        template = self._create_template('Request Flow')
        request = self._create_request(template)
        self.assertEqual(request.status, 'draft')

        request.action_version()
        self.assertEqual(request.status, 'versioned')
        self.assertTrue(request.template_version_id)
        self.assertEqual(request.source_pdf_sha256, request.template_version_id.source_pdf_sha256)

        request.action_send()
        self.assertEqual(request.status, 'sent')
        self.assertTrue(request.sent_at)

        final_attachment = self._create_attachment(name='request_final.pdf', res_model='open.sign.request')
        request.write({
            'final_attachment_id': final_attachment.id,
            'final_pdf_sha256': 'a' * 64,
        })
        request.write({'status': 'in_progress'})
        request.action_complete()
        self.assertEqual(request.status, 'completed')
        self.assertTrue(request.completed_at)

        request.action_void(reason='Manual void')
        self.assertEqual(request.status, 'voided')

    def test_invalid_transitions_are_rejected(self):
        request = self._create_request(self._create_template('Transition Rules'))

        with self.assertRaisesRegex(ValidationError, 'Invalid status transition'):
            request.action_send()

        request.action_version()
        with self.assertRaisesRegex(ValidationError, 'Invalid status transition'):
            request.write({'status': 'draft'})

        request.action_send()
        with self.assertRaisesRegex(ValidationError, 'Invalid status transition'):
            request.action_void()

        request.action_cancel()
        with self.assertRaisesRegex(ValidationError, 'Invalid status transition'):
            request.action_send()

    def test_transition_bypass_context_requires_superuser(self):
        request = self._create_request(self._create_template('Transition Bypass'))
        user_request = request.with_user(self.open_sign_user)

        with self.assertRaisesRegex(ValidationError, 'Invalid status transition'):
            user_request.with_context(open_sign_skip_transition_check=True).write({'status': 'sent'})

        version = request.template_id.action_publish_version()
        request.sudo().with_context(open_sign_skip_transition_check=True).write({
            'status': 'sent',
            'template_version_id': version.id,
            'source_pdf_sha256': version.source_pdf_sha256,
        })
        self.assertEqual(request.status, 'sent')

    def test_request_binding_is_frozen_after_versioning(self):
        template_a = self._create_template('Binding Template A')
        template_b = self._create_template('Binding Template B')
        request = self._create_request(template_a, name='Binding Freeze Request')

        request.action_version()
        request.action_send()
        original_version = request.template_version_id
        original_digest = request.source_pdf_sha256
        alternate_version = template_a.action_publish_version()

        with self.assertRaisesRegex(ValidationError, 'Template binding cannot be changed once a request is versioned.'):
            request.write({'template_id': template_b.id})
        with self.assertRaisesRegex(ValidationError, 'Template version binding cannot be changed once a request is versioned.'):
            request.write({'template_version_id': alternate_version.id})
        with self.assertRaisesRegex(ValidationError, 'Source PDF digest cannot be changed once a request is versioned.'):
            request.write({'source_pdf_sha256': 'b' * 64})

        self.assertEqual(request.template_id, template_a)
        self.assertEqual(request.template_version_id, original_version)
        self.assertEqual(request.source_pdf_sha256, original_digest)

    def test_request_constraints_and_digest_rules(self):
        template_a = self._create_template('Template A')
        template_b = self._create_template('Template B')
        version_a = template_a.action_publish_version()
        version_b = template_b.action_publish_version()

        request_template_mismatch = self._create_request(template_a, name='Constraint Template Mismatch')
        with self.assertRaisesRegex(ValidationError, 'Template version must belong to the selected template.'):
            request_template_mismatch.sudo().with_context(open_sign_skip_transition_check=True).write({
                'status': 'versioned',
                'template_version_id': version_b.id,
                'source_pdf_sha256': version_b.source_pdf_sha256,
            })

        request_source_mismatch = self._create_request(template_a, name='Constraint Source Mismatch')
        with self.assertRaisesRegex(ValidationError, 'Source digest must match the selected template version digest.'):
            request_source_mismatch.sudo().with_context(open_sign_skip_transition_check=True).write({
                'status': 'versioned',
                'template_version_id': version_a.id,
                'source_pdf_sha256': 'b' * 64,
            })

        request_digest_format = self._create_request(template_a, name='Constraint Digest Format')
        with self.assertRaisesRegex(ValidationError, 'Source PDF SHA-256 must be a 64-character lowercase hexadecimal string.'):
            request_digest_format.write({'source_pdf_sha256': 'INVALID'})

        request_digest_format.write({'source_pdf_sha256': version_a.source_pdf_sha256})
        with self.assertRaisesRegex(ValidationError, 'Final PDF SHA-256 must be a 64-character lowercase hexadecimal string.'):
            request_digest_format.write({'final_pdf_sha256': 'INVALID'})
        request_digest_format.write({'final_pdf_sha256': False})

        now = fields.Datetime.now()
        request_expiration = self._create_request(template_a, name='Constraint Expiration')
        with self.assertRaisesRegex(ValidationError, 'Expiration datetime must be greater than or equal to sent datetime.'):
            request_expiration.sudo().with_context(open_sign_skip_transition_check=True).write({
                'status': 'sent',
                'template_version_id': version_a.id,
                'source_pdf_sha256': version_a.source_pdf_sha256,
                'sent_at': now,
                'expires_at': now - timedelta(hours=1),
            })

        request_completed = self._create_request(template_a, name='Constraint Completed')
        with self.assertRaisesRegex(ValidationError, 'Completed requests require a final attachment.'):
            request_completed.sudo().with_context(open_sign_skip_transition_check=True).write({
                'status': 'completed',
                'template_version_id': version_a.id,
                'source_pdf_sha256': version_a.source_pdf_sha256,
                'completed_at': now,
                'final_pdf_sha256': 'a' * 64,
            })

    def test_template_publish_version_builds_snapshots(self):
        template = self._create_template('Snapshot Template')
        role = self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': 'Signer',
            'sequence': 10,
        })
        self.env['open.sign.template.field'].create({
            'template_id': template.id,
            'role_id': role.id,
            'type': 'selection',
            'label': 'Plan',
            'page': 1,
            'x': 0.1,
            'y': 0.2,
            'width': 0.3,
            'height': 0.05,
            'sequence': 10,
            'option_ids': [
                Command.create({'value': 'basic', 'label': 'Basic', 'sequence': 10, 'is_default': True}),
                Command.create({'value': 'pro', 'label': 'Pro', 'sequence': 20, 'is_default': False}),
            ],
        })

        version_1 = template.action_publish_version()
        self.assertEqual(version_1.version_number, 1)
        self.assertEqual(len(version_1.role_snapshot_json), 1)
        self.assertEqual(version_1.role_snapshot_json[0]['name'], 'Signer')
        self.assertEqual(len(version_1.field_snapshot_json), 1)
        self.assertEqual(version_1.field_snapshot_json[0]['type'], 'selection')
        self.assertEqual(len(version_1.field_snapshot_json[0]['options']), 2)

        version_2 = template.action_publish_version()
        self.assertEqual(version_2.version_number, 2)

    def test_template_version_records_are_immutable(self):
        version = self._create_template('Immutable Version Template').action_publish_version()

        with self.assertRaisesRegex(ValidationError, 'Template versions are immutable once published.'):
            version.write({'source_pdf_sha256': 'a' * 64})
        with self.assertRaisesRegex(ValidationError, 'Template versions are immutable once published.'):
            version.unlink()

        version.sudo().with_context(open_sign_allow_template_version_mutation=True).write({
            'source_pdf_sha256': 'a' * 64,
        })
        self.assertEqual(version.source_pdf_sha256, 'a' * 64)

    def test_template_version_acl_is_read_only(self):
        version_model_user = self.env['open.sign.template.version'].with_user(self.open_sign_user)
        version_model_manager = self.env['open.sign.template.version'].with_user(self.open_sign_manager)
        version_model_auditor = self.env['open.sign.template.version'].with_user(self.open_sign_auditor)

        self.assertTrue(version_model_user.has_access('read'))
        self.assertFalse(version_model_user.has_access('create'))
        self.assertFalse(version_model_user.has_access('write'))
        self.assertFalse(version_model_user.has_access('unlink'))

        self.assertTrue(version_model_manager.has_access('read'))
        self.assertFalse(version_model_manager.has_access('create'))
        self.assertFalse(version_model_manager.has_access('write'))
        self.assertFalse(version_model_manager.has_access('unlink'))

        self.assertTrue(version_model_auditor.has_access('read'))
        self.assertFalse(version_model_auditor.has_access('create'))
        self.assertFalse(version_model_auditor.has_access('write'))
        self.assertFalse(version_model_auditor.has_access('unlink'))

        self.assertEqual(self.acl_version.with_user(self.open_sign_user).read(['version_number'])[0]['version_number'], 1)
        with self.assertRaises(AccessError):
            version_model_manager.create({
                'template_id': self.acl_template.id,
                'version_number': 999,
                'source_attachment_id': self.acl_template.source_attachment_id.id,
                'source_pdf_sha256': 'a' * 64,
                'published_by': self.open_sign_manager.id,
            })
        with self.assertRaisesRegex(ValidationError, 'Template versions are immutable once published.'):
            self.acl_version.with_user(self.open_sign_manager).write({'source_pdf_sha256': 'b' * 64})
        with self.assertRaisesRegex(ValidationError, 'Template versions are immutable once published.'):
            self.acl_version.with_user(self.open_sign_manager).unlink()

    def test_auditor_request_access_is_read_only(self):
        request_model = self.env['open.sign.request'].with_user(self.open_sign_auditor)
        self.assertTrue(request_model.has_access('read'))
        self.assertFalse(request_model.has_access('create'))
        self.assertFalse(request_model.has_access('write'))
        self.assertFalse(request_model.has_access('unlink'))
        self.assertEqual(self.acl_request.with_user(self.open_sign_auditor).read(['name'])[0]['name'], 'ACL Request')

        with self.assertRaises(AccessError):
            request_model.create({
                'name': 'Auditor Request',
                'template_id': self.acl_template.id,
            })
        with self.assertRaises(AccessError):
            self.acl_request.with_user(self.open_sign_auditor).write({'name': 'Auditor Update'})
        with self.assertRaises(AccessError):
            self.acl_request.with_user(self.open_sign_auditor).unlink()

    def test_user_can_create_write_but_not_unlink_request(self):
        request_model = self.env['open.sign.request'].with_user(self.open_sign_user)
        self.assertTrue(request_model.has_access('create'))
        self.assertTrue(request_model.has_access('write'))
        self.assertFalse(request_model.has_access('unlink'))

        created_request = request_model.create({
            'name': 'User Request',
            'template_id': self.acl_template.id,
        })
        created_request.write({'ordered_signing': False})
        self.assertFalse(created_request.ordered_signing)

        with self.assertRaises(AccessError):
            created_request.unlink()

    def test_manager_can_unlink_request(self):
        created_request = self.env['open.sign.request'].with_user(self.open_sign_manager).create({
            'name': 'Manager Request',
            'template_id': self.acl_template.id,
        })
        request_id = created_request.id
        created_request.unlink()
        self.assertFalse(self.env['open.sign.request'].browse(request_id).exists())
