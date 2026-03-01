# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignAuditLog(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_audit_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_audit_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_audit_auditor',
            groups='open_sign.group_open_sign_auditor',
        )

        cls.acl_template = cls._create_template_static(cls.env, 'ACL Audit Template')
        cls.acl_request = cls.env['open.sign.request'].create({
            'name': 'ACL Audit Request',
            'template_id': cls.acl_template.id,
        })
        cls.acl_role = cls.env['open.sign.role'].create({
            'template_id': cls.acl_template.id,
            'name': 'ACL Audit Signer',
            'sequence': 10,
        })
        cls.acl_signer = cls.env['open.sign.request.signer'].create({
            'request_id': cls.acl_request.id,
            'role_id': cls.acl_role.id,
            'email': 'acl.audit.signer@example.com',
            'sequence': 10,
        })
        cls.acl_audit_log = cls.env['open.sign.audit.log'].sudo().create({
            'request_id': cls.acl_request.id,
            'signer_id': cls.acl_signer.id,
            'event_type': 'request_created',
            'event_sequence': 1,
            'hash_chain': 'a' * 64,
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

    def _create_template(self, name='Template'):
        return self._create_template_static(self.env, name)

    def _create_request(self, template, name='Request'):
        return self.env['open.sign.request'].create({
            'name': name,
            'template_id': template.id,
        })

    def _create_role(self, template, name='Signer', sequence=10):
        return self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': name,
            'sequence': sequence,
        })

    def _create_signer(self, request, role, email='signer@example.com', sequence=10):
        return self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': role.id,
            'email': email,
            'sequence': sequence,
        })

    def _create_audit_log(self, request, signer=None, **overrides):
        values = {
            'request_id': request.id,
            'event_type': 'request_created',
            'event_sequence': 1,
            'hash_chain': 'b' * 64,
        }
        if signer:
            values['signer_id'] = signer.id
        values.update(overrides)
        return self.env['open.sign.audit.log'].sudo().create(values)

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

    def test_audit_log_constraints_and_uniqueness(self):
        template = self._create_template('Audit Constraint Template')
        request_a = self._create_request(template, name='Audit Constraint Request A')
        request_b = self._create_request(template, name='Audit Constraint Request B')
        role = self._create_role(template, name='Audit Constraint Signer')
        signer_a = self._create_signer(request_a, role, email='audit.constraint.a@example.com')
        signer_b = self._create_signer(request_b, role, email='audit.constraint.b@example.com')

        self._create_audit_log(
            request_a,
            signer=signer_a,
            event_sequence=1,
            hash_chain='1' * 64,
        )

        with self.assertRaisesRegex(ValidationError, 'Audit event sequence must be unique per request.'):
            self._create_audit_log(
                request_a,
                signer=signer_a,
                event_sequence=1,
                hash_chain='2' * 64,
            )

        with self.assertRaisesRegex(ValidationError, 'Audit hash-chain values must be unique per request.'):
            self._create_audit_log(
                request_a,
                signer=signer_a,
                event_sequence=2,
                hash_chain='1' * 64,
            )

        self._create_audit_log(
            request_b,
            signer=signer_b,
            event_sequence=1,
            hash_chain='3' * 64,
        )

        with self.assertRaisesRegex(ValidationError, 'Audit event sequence must be greater than zero.'):
            self._create_audit_log(
                request_a,
                signer=signer_a,
                event_sequence=0,
                hash_chain='4' * 64,
            )

        with self.assertRaisesRegex(ValidationError, 'Audit hash chain must be a 64-character lowercase hexadecimal string.'):
            self._create_audit_log(
                request_a,
                signer=signer_a,
                event_sequence=3,
                hash_chain='INVALID',
            )

        with self.assertRaisesRegex(ValidationError, 'Audit previous hash must be a 64-character lowercase hexadecimal string.'):
            self._create_audit_log(
                request_a,
                signer=signer_a,
                event_sequence=4,
                hash_chain='5' * 64,
                previous_hash='INVALID',
            )

        with self.assertRaisesRegex(ValidationError, 'Audit consent text hash must be a 64-character lowercase hexadecimal string.'):
            self._create_audit_log(
                request_a,
                signer=signer_a,
                event_sequence=5,
                hash_chain='6' * 64,
                consent_text_hash='INVALID',
            )

        with self.assertRaisesRegex(ValidationError, 'Audit signer must belong to the same request.'):
            self._create_audit_log(
                request_a,
                signer=signer_b,
                event_sequence=6,
                hash_chain='7' * 64,
            )

    def test_audit_log_is_append_only_before_completion(self):
        template = self._create_template('Audit Append Only Template')
        request = self._create_request(template, name='Audit Append Only Request')
        role = self._create_role(template, name='Audit Append Only Signer')
        signer = self._create_signer(request, role, email='append.only@example.com')
        audit_log = self._create_audit_log(
            request,
            signer=signer,
            event_sequence=1,
            hash_chain='8' * 64,
        )

        with self.assertRaisesRegex(ValidationError, 'Audit log records are append-only and cannot be modified directly.'):
            audit_log.sudo().write({'user_agent': 'patched'})

        with self.assertRaisesRegex(ValidationError, 'Audit log records are append-only and cannot be deleted directly.'):
            audit_log.sudo().unlink()

    def test_terminal_request_audit_log_requires_repair_context_for_mutation(self):
        template = self._create_template('Audit Terminal Template')
        request = self._create_request(template, name='Audit Terminal Request')
        role = self._create_role(template, name='Audit Terminal Signer')
        signer = self._create_signer(request, role, email='audit.terminal@example.com')
        self._mark_request_completed(request)
        audit_log = self._create_audit_log(
            request,
            signer=signer,
            event_type='request_completed',
            event_sequence=1,
            hash_chain='9' * 64,
        )

        with self.assertRaisesRegex(ValidationError, 'Audit log records are immutable once the request is completed or voided.'):
            audit_log.sudo().write({'user_agent': 'patched'})

        with self.assertRaisesRegex(ValidationError, 'Audit log records are immutable once the request is completed or voided.'):
            audit_log.sudo().unlink()

        audit_log.sudo().with_context(open_sign_allow_audit_log_repair=True).write({'user_agent': 'patched'})
        self.assertEqual(audit_log.user_agent, 'patched')

        audit_log_id = audit_log.id
        audit_log.sudo().with_context(open_sign_allow_audit_log_repair=True).unlink()
        self.assertFalse(self.env['open.sign.audit.log'].browse(audit_log_id).exists())

    def test_audit_log_acl_is_read_only(self):
        user_model = self.env['open.sign.audit.log'].with_user(self.open_sign_user)
        manager_model = self.env['open.sign.audit.log'].with_user(self.open_sign_manager)
        auditor_model = self.env['open.sign.audit.log'].with_user(self.open_sign_auditor)

        self.assertTrue(user_model.has_access('read'))
        self.assertFalse(user_model.has_access('create'))
        self.assertFalse(user_model.has_access('write'))
        self.assertFalse(user_model.has_access('unlink'))

        self.assertTrue(manager_model.has_access('read'))
        self.assertFalse(manager_model.has_access('create'))
        self.assertFalse(manager_model.has_access('write'))
        self.assertFalse(manager_model.has_access('unlink'))

        self.assertTrue(auditor_model.has_access('read'))
        self.assertFalse(auditor_model.has_access('create'))
        self.assertFalse(auditor_model.has_access('write'))
        self.assertFalse(auditor_model.has_access('unlink'))

        self.assertEqual(
            self.acl_audit_log.with_user(self.open_sign_auditor).read(['event_type'])[0]['event_type'],
            'request_created',
        )

        with self.assertRaises(AccessError):
            user_model.create({
                'request_id': self.acl_request.id,
                'signer_id': self.acl_signer.id,
                'event_type': 'value_saved',
                'event_sequence': 99,
                'hash_chain': 'd' * 64,
            })
        with self.assertRaises(AccessError):
            self.acl_audit_log.with_user(self.open_sign_manager).write({'user_agent': 'manager-update'})
        with self.assertRaises(AccessError):
            self.acl_audit_log.with_user(self.open_sign_manager).unlink()
