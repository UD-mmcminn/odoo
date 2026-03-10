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
            'owner_id': cls.open_sign_user.id,
        })
        cls.acl_role = cls.env['open.sign.role'].create({
            'template_id': cls.acl_template.id,
            'name': 'ACL Signer Role',
            'sequence': 10,
        })
        cls.acl_signer = cls.env['open.sign.request.signer'].create({
            'request_id': cls.acl_request.id,
            'role_id': cls.acl_role.id,
            'email': 'acl.signer@example.com',
            'sequence': 10,
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

    def _create_role(self, template, name='Signer', sequence=10, required=True):
        return self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': name,
            'sequence': sequence,
            'required': required,
        })

    def _create_request(self, template=None, **overrides):
        template = template or self._create_template('Request Template')
        values = {
            'name': f'{template.name} Request',
            'template_id': template.id,
        }
        values.update(overrides)
        return self.env['open.sign.request'].create(values)

    def _mark_request_completed(self, request):
        template_version = request.template_id.action_publish_version()
        final_attachment = self._create_attachment(name=f'{request.name}_final.pdf', res_model='open.sign.request')
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
            request.action_void(reason='terminal state test')
            return
        raise ValueError(f'Unsupported terminal status: {status}')

    def _create_signer(self, request, role=None, **overrides):
        role = role or self._create_role(request.template_id)
        default_local_part = ''.join(
            char if char.isalnum() else '.'
            for char in role.name.casefold()
        ).strip('.') or 'signer'
        values = {
            'request_id': request.id,
            'role_id': role.id,
            'email': f'{default_local_part}@example.com',
            'sequence': role.sequence,
        }
        values.update(overrides)
        return self.env['open.sign.request.signer'].create(values)

    def test_request_action_version_send_complete_void_flow(self):
        template = self._create_template('Request Flow')
        request = self._create_request(template)
        self.assertEqual(request.status, 'draft')

        request.action_version()
        self.assertEqual(request.status, 'versioned')
        self.assertTrue(request.template_version_id)
        self.assertEqual(request.source_pdf_sha256, request.template_version_id.source_pdf_sha256)

        self._create_signer(request, self._create_role(template, name='Primary Signer', sequence=10))
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

        self._create_signer(request, self._create_role(request.template_id, name='Transition Signer', sequence=10))
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
        self._create_signer(request, self._create_role(template_a, name='Binding Signer', sequence=10))
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

    def test_send_requires_at_least_one_signer(self):
        template = self._create_template('Send Signer Requirement')
        request = self._create_request(template)
        request.action_version()

        with self.assertRaisesRegex(ValidationError, 'Cannot send a request without at least one signer.'):
            request.action_send()

        self._create_signer(request, self._create_role(template, name='Send Signer', sequence=10))
        request.action_send()
        self.assertEqual(request.status, 'sent')

    def test_send_requires_actionable_signer(self):
        template = self._create_template('Send Actionable Signer Requirement')
        request = self._create_request(template)
        request.action_version()
        self._create_signer(
            request,
            self._create_role(template, name='Declined Signer', sequence=10),
            state='declined',
        )

        with self.assertRaisesRegex(ValidationError, 'Cannot send a request without at least one pending or opened signer.'):
            request.action_send()

    def test_signer_constraints_sequence_logic_and_counters(self):
        template_a = self._create_template('Signer Logic A')
        template_b = self._create_template('Signer Logic B')
        request = self._create_request(template_a, name='Signer Logic Request')
        role_a_10 = self._create_role(template_a, name='A10', sequence=10)
        role_a_20 = self._create_role(template_a, name='A20', sequence=20)
        role_a_20_bis = self._create_role(template_a, name='A20 BIS', sequence=20)
        role_b = self._create_role(template_b, name='B10', sequence=10)

        signer_1 = self._create_signer(request, role_a_10, email='  FIRST.SIGNER@EXAMPLE.COM  ')
        signer_2 = self._create_signer(request, role_a_20, email='second.signer@example.com')
        signer_3 = self._create_signer(request, role_a_20_bis, email='third.signer@example.com', state='declined')

        self.assertEqual(signer_1.email, 'first.signer@example.com')
        self.assertEqual(request.signed_count, 0)
        self.assertEqual(request.pending_count, 2)
        self.assertEqual(request.declined_count, 1)

        actionable_signers = request._get_actionable_signers()
        self.assertEqual(actionable_signers.ids, signer_1.ids)

        signer_1.write({'state': 'signed', 'signed_at': fields.Datetime.now()})
        self.assertEqual(request.signed_count, 1)
        self.assertEqual(request.pending_count, 1)
        self.assertEqual(request.declined_count, 1)

        actionable_signers = request._get_actionable_signers()
        self.assertEqual(actionable_signers.ids, signer_2.ids)

        request.write({'ordered_signing': False})
        actionable_signers = request._get_actionable_signers()
        self.assertEqual(actionable_signers.ids, signer_2.ids)

        with self.assertRaisesRegex(ValidationError, 'Each role can be assigned only once per request.'):
            self._create_signer(request, role_a_10, email='duplicate@example.com')

        with self.assertRaisesRegex(ValidationError, 'Signer role must belong to the same template as the request.'):
            self._create_signer(request, role_b, email='mismatch@example.com')

        with self.assertRaisesRegex(ValidationError, 'Signed signer state requires signed_at timestamp.'):
            self._create_signer(
                request,
                self._create_role(template_a, name='Signed Missing Timestamp', sequence=40),
                email='signed.missing@example.com',
                state='signed',
            )

        with self.assertRaisesRegex(ValidationError, 'Signer sequence must be zero or greater.'):
            self._create_signer(
                request,
                self._create_role(template_a, name='Negative Sequence', sequence=50),
                email='negative.sequence@example.com',
                sequence=-1,
            )

    def test_signer_actionable_and_waiting_helpers_follow_sequence_waves(self):
        template = self._create_template('Signer Actionable Helpers')
        request = self._create_request(template, name='Signer Actionable Helpers Request')
        role_first = self._create_role(template, name='Wave First', sequence=10)
        role_same_wave = self._create_role(template, name='Wave Same', sequence=10)
        role_second = self._create_role(template, name='Wave Second', sequence=20)

        signer_first = self._create_signer(request, role_first, email='wave.first@example.com')
        signer_same_wave = self._create_signer(request, role_same_wave, email='wave.same@example.com')
        signer_second = self._create_signer(request, role_second, email='wave.second@example.com')

        self.assertTrue(request._is_signer_actionable(signer_first))
        self.assertTrue(request._is_signer_actionable(signer_same_wave))
        self.assertFalse(request._is_signer_actionable(signer_second))
        self.assertFalse(request._is_signer_waiting(signer_first))
        self.assertFalse(request._is_signer_waiting(signer_same_wave))
        self.assertTrue(request._is_signer_waiting(signer_second))

        signer_first.write({'state': 'signed', 'signed_at': fields.Datetime.now()})
        signer_same_wave.write({'state': 'declined'})

        self.assertTrue(request._is_signer_actionable(signer_second))
        self.assertFalse(request._is_signer_waiting(signer_second))

    def test_signer_actionable_helper_supports_parallel_and_terminal_wave_unblocking(self):
        template = self._create_template('Signer Actionable Parallel')

        parallel_request = self._create_request(template, name='Parallel Actionable Request')
        parallel_request.write({'ordered_signing': False})
        parallel_role_first = self._create_role(template, name='Parallel First', sequence=10)
        parallel_role_second = self._create_role(template, name='Parallel Second', sequence=20)
        parallel_signer_first = self._create_signer(
            parallel_request, parallel_role_first, email='parallel.first@example.com'
        )
        parallel_signer_second = self._create_signer(
            parallel_request, parallel_role_second, email='parallel.second@example.com'
        )

        self.assertTrue(parallel_request._is_signer_actionable(parallel_signer_first))
        self.assertTrue(parallel_request._is_signer_actionable(parallel_signer_second))
        self.assertFalse(parallel_request._is_signer_waiting(parallel_signer_first))
        self.assertFalse(parallel_request._is_signer_waiting(parallel_signer_second))

        declined_request = self._create_request(template, name='Declined Unblocks Next Wave')
        declined_role_first = self._create_role(template, name='Declined First', sequence=30)
        declined_role_second = self._create_role(template, name='Declined Second', sequence=40)
        declined_signer_first = self._create_signer(
            declined_request, declined_role_first, email='declined.first@example.com'
        )
        declined_signer_second = self._create_signer(
            declined_request, declined_role_second, email='declined.second@example.com'
        )
        declined_signer_first.write({'state': 'declined'})

        self.assertTrue(declined_request._is_signer_actionable(declined_signer_second))
        self.assertFalse(declined_request._is_signer_waiting(declined_signer_second))

        expired_request = self._create_request(template, name='Expired Unblocks Next Wave')
        expired_role_first = self._create_role(template, name='Expired First', sequence=50)
        expired_role_second = self._create_role(template, name='Expired Second', sequence=60)
        expired_signer_first = self._create_signer(
            expired_request, expired_role_first, email='expired.first@example.com'
        )
        expired_signer_second = self._create_signer(
            expired_request, expired_role_second, email='expired.second@example.com'
        )
        expired_signer_first.write({'state': 'expired'})

        self.assertTrue(expired_request._is_signer_actionable(expired_signer_second))
        self.assertFalse(expired_request._is_signer_waiting(expired_signer_second))

    def test_signer_actionable_and_waiting_require_request_membership(self):
        template_a = self._create_template('Signer Membership A')
        template_b = self._create_template('Signer Membership B')
        request_a = self._create_request(template_a, name='Signer Membership Request A')
        request_b = self._create_request(template_b, name='Signer Membership Request B')
        signer_a = self._create_signer(
            request_a,
            self._create_role(template_a, name='Membership A', sequence=10),
            email='membership.a@example.com',
        )
        signer_b = self._create_signer(
            request_b,
            self._create_role(template_b, name='Membership B', sequence=10),
            email='membership.b@example.com',
        )

        self.assertTrue(request_a._is_signer_actionable(signer_a))
        with self.assertRaisesRegex(ValidationError, 'Signer does not belong to this request.'):
            request_a._is_signer_actionable(signer_b)
        with self.assertRaisesRegex(ValidationError, 'Signer does not belong to this request.'):
            request_a._is_signer_waiting(signer_b)

    def test_signer_default_context_cannot_bypass_lifecycle_guard(self):
        template = self._create_template('Signer Default Context Guard')
        request = self._create_request(
            template,
            name='Signer Default Context Request',
            owner_id=self.open_sign_user.id,
        )
        role = self._create_role(template, name='Default Guard Signer', sequence=10)
        signer_model = self.env['open.sign.request.signer'].with_user(self.open_sign_user)

        with self.assertRaisesRegex(ValidationError, 'Signer lifecycle fields cannot be set directly.'):
            signer_model.with_context(default_state='declined').create({
                'request_id': request.id,
                'role_id': role.id,
                'email': 'guarded.signer@example.com',
                'sequence': 10,
            })

        created_signer = signer_model.with_context(default_email='  DEFAULT.SIGNER@EXAMPLE.COM  ').create({
            'request_id': request.id,
            'role_id': role.id,
            'sequence': 10,
        })
        self.assertEqual(created_signer.email, 'default.signer@example.com')

    def test_signer_evidence_field_format_validation(self):
        template = self._create_template('Signer Evidence Format Validation')
        request = self._create_request(template, name='Signer Evidence Request')
        role = self._create_role(template, name='Evidence Signer', sequence=10)
        signer_model = self.env['open.sign.request.signer'].sudo()

        with self.assertRaisesRegex(ValidationError, 'Signer IP must be a valid IPv4 or IPv6 address.'):
            signer_model.create({
                'request_id': request.id,
                'role_id': role.id,
                'email': 'invalid.ip@example.com',
                'sequence': 10,
                'ip_last': 'not-an-ip',
            })

        with self.assertRaisesRegex(ValidationError, 'Signer consent text hash must be a 64-character lowercase hexadecimal string.'):
            signer_model.create({
                'request_id': request.id,
                'role_id': role.id,
                'email': 'invalid.hash@example.com',
                'sequence': 10,
                'consent_text_hash': 'INVALID',
            })

        with self.assertRaisesRegex(ValidationError, 'Signer timezone must be a valid IANA timezone identifier.'):
            signer_model.create({
                'request_id': request.id,
                'role_id': role.id,
                'email': 'invalid.tz@example.com',
                'sequence': 10,
                'signer_timezone': 'Moon/Base',
            })

        signer = signer_model.create({
            'request_id': request.id,
            'role_id': role.id,
            'email': 'evidence.valid@example.com',
            'sequence': 10,
            'ip_last': ' 2001:0db8:0000:0000:0000:ff00:0042:8329 ',
            'consent_text_hash': 'a' * 64,
            'signer_timezone': ' America/New_York ',
        })
        self.assertEqual(signer.ip_last, '2001:db8::ff00:42:8329')
        self.assertEqual(signer.consent_text_hash, 'a' * 64)
        self.assertEqual(signer.signer_timezone, 'America/New_York')

        with self.assertRaisesRegex(ValidationError, 'Signer IP must be a valid IPv4 or IPv6 address.'):
            signer.write({'ip_last': '999.999.999.999'})

        with self.assertRaisesRegex(ValidationError, 'Signer consent text hash must be a 64-character lowercase hexadecimal string.'):
            signer.write({'consent_text_hash': 'A' * 64})

        with self.assertRaisesRegex(ValidationError, 'Signer timezone must be a valid IANA timezone identifier.'):
            signer.write({'signer_timezone': 'Invalid/Timezone'})

        signer.write({
            'ip_last': ' 192.168.1.10 ',
            'consent_text_hash': 'b' * 64,
            'signer_timezone': 'UTC',
        })
        self.assertEqual(signer.ip_last, '192.168.1.10')
        self.assertEqual(signer.consent_text_hash, 'b' * 64)
        self.assertEqual(signer.signer_timezone, 'UTC')

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
        self.assertEqual(version_1.role_snapshot_json[0]['role_id'], role.id)
        self.assertEqual(version_1.role_snapshot_json[0]['name_normalized'], role.name_normalized)
        self.assertEqual(len(version_1.field_snapshot_json), 1)
        self.assertEqual(version_1.field_snapshot_json[0]['type'], 'selection')
        self.assertEqual(version_1.field_snapshot_json[0]['template_field_id'], template.field_ids.id)
        self.assertEqual(version_1.field_snapshot_json[0]['role_id'], role.id)
        self.assertEqual(version_1.field_snapshot_json[0]['role_name'], role.name)
        self.assertEqual(version_1.field_snapshot_json[0]['role_name_normalized'], role.name_normalized)
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

    def test_auditor_signer_access_is_read_only(self):
        signer_model = self.env['open.sign.request.signer'].with_user(self.open_sign_auditor)
        self.assertTrue(signer_model.has_access('read'))
        self.assertFalse(signer_model.has_access('create'))
        self.assertFalse(signer_model.has_access('write'))
        self.assertFalse(signer_model.has_access('unlink'))
        self.assertEqual(self.acl_signer.with_user(self.open_sign_auditor).read(['email'])[0]['email'], 'acl.signer@example.com')

        with self.assertRaises(AccessError):
            signer_model.create({
                'request_id': self.acl_request.id,
                'role_id': self._create_role(self.acl_template, name='Auditor Signer Role', sequence=31).id,
                'email': 'auditor@example.com',
                'sequence': 10,
            })
        with self.assertRaises(AccessError):
            self.acl_signer.with_user(self.open_sign_auditor).write({'email': 'auditor.update@example.com'})
        with self.assertRaises(AccessError):
            self.acl_signer.with_user(self.open_sign_auditor).unlink()

    def test_user_can_create_write_but_not_unlink_signer(self):
        signer_model = self.env['open.sign.request.signer'].with_user(self.open_sign_user)
        self.assertTrue(signer_model.has_access('create'))
        self.assertTrue(signer_model.has_access('write'))
        self.assertFalse(signer_model.has_access('unlink'))

        created_signer = signer_model.create({
            'request_id': self.acl_request.id,
            'role_id': self._create_role(self.acl_template, name='User Signer Role', sequence=30).id,
            'email': 'user.signer@example.com',
            'sequence': 30,
        })
        created_signer.write({'email': 'user.signer.updated@example.com'})
        self.assertEqual(created_signer.email, 'user.signer.updated@example.com')

        with self.assertRaisesRegex(ValidationError, 'Signer lifecycle fields cannot be modified directly.'):
            created_signer.write({'state': 'declined', 'declined_reason': 'No thanks'})

        with self.assertRaisesRegex(ValidationError, 'Signer lifecycle fields cannot be set directly.'):
            signer_model.create({
                'request_id': self.acl_request.id,
                'role_id': self._create_role(self.acl_template, name='User Signer Lifecycle Role', sequence=32).id,
                'email': 'user.signer.lifecycle@example.com',
                'sequence': 32,
                'state': 'declined',
            })

        with self.assertRaises(AccessError):
            created_signer.unlink()

    def test_signer_mutation_blocked_on_terminal_requests(self):
        for status in ('completed', 'cancelled', 'voided'):
            template = self._create_template(f'Terminal Signer Mutation Template {status}')
            request = self._create_request(template, name=f'Terminal Signer Mutation Request {status}')
            role_a = self._create_role(template, name=f'Terminal Role A {status}', sequence=10)
            role_b = self._create_role(template, name=f'Terminal Role B {status}', sequence=20)
            signer = self._create_signer(request, role_a, email=f'terminal.signer.{status}@example.com')
            self._set_request_terminal_status(request, status)

            with self.assertRaisesRegex(ValidationError, 'Signer contract cannot be modified once the request is versioned.'):
                signer.with_user(self.open_sign_user).write({'email': f'terminal.signer.updated.{status}@example.com'})

            with self.assertRaisesRegex(ValidationError, 'Signer contract cannot be modified once the request is versioned.'):
                self.env['open.sign.request.signer'].with_user(self.open_sign_user).create({
                    'request_id': request.id,
                    'role_id': role_b.id,
                    'email': f'terminal.signer.new.{status}@example.com',
                    'sequence': 20,
                })

            with self.assertRaisesRegex(ValidationError, 'Signer contract cannot be modified once the request is versioned.'):
                signer.with_user(self.open_sign_manager).unlink()

    def test_manager_can_unlink_signer(self):
        created_signer = self.env['open.sign.request.signer'].with_user(self.open_sign_manager).create({
            'request_id': self.acl_request.id,
            'role_id': self._create_role(self.acl_template, name='Manager Signer Role', sequence=40).id,
            'email': 'manager.signer@example.com',
            'sequence': 40,
        })
        signer_id = created_signer.id
        created_signer.unlink()
        self.assertFalse(self.env['open.sign.request.signer'].browse(signer_id).exists())

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

    def test_request_mutation_blocked_on_terminal_statuses(self):
        for status in ('completed', 'cancelled', 'voided'):
            template = self._create_template(f'Terminal Request Mutation Template {status}')
            request = self._create_request(template, name=f'Terminal Request Mutation {status}')
            self._set_request_terminal_status(request, status)
            with self.assertRaisesRegex(
                ValidationError,
                'Completed, cancelled, and voided requests are immutable and cannot be modified directly.',
            ):
                request.with_user(self.open_sign_user).write({'ordered_signing': False})

    def test_manager_unlink_soft_deletes_request_and_retains_related_records(self):
        created_request = self.env['open.sign.request'].with_user(self.open_sign_manager).create({
            'name': 'Manager Request',
            'template_id': self.acl_template.id,
        })
        role = self._create_role(self.acl_template, name='Manager Request Soft Delete Role', sequence=90)
        signer = self.env['open.sign.request.signer'].with_user(self.open_sign_manager).create({
            'request_id': created_request.id,
            'role_id': role.id,
            'email': 'manager.request.soft.delete@example.com',
            'sequence': 90,
        })
        field = self.env['open.sign.template.field'].create({
            'template_id': self.acl_template.id,
            'role_id': role.id,
            'type': 'text',
            'label': 'Soft Delete Field',
            'page': 1,
            'x': 0.1,
            'y': 0.1,
            'width': 0.2,
            'height': 0.05,
            'sequence': 90,
        })
        value = self.env['open.sign.request.value'].with_user(self.open_sign_manager).create({
            'request_id': created_request.id,
            'template_field_id': field.id,
            'signer_id': signer.id,
            'value_text': 'retained',
        })
        audit_log = self.env['open.sign.audit.log'].sudo().create({
            'request_id': created_request.id,
            'event_type': 'request_created',
            'event_sequence': 1,
            'hash_chain': 'a' * 64,
        })
        request_id = created_request.id
        signer_id = signer.id
        value_id = value.id
        audit_log_id = audit_log.id
        created_request.unlink()

        self.assertFalse(self.env['open.sign.request'].search([('id', '=', request_id)]))
        retained_request = self.env['open.sign.request'].with_context(active_test=False).browse(request_id).exists()
        self.assertTrue(retained_request)
        self.assertFalse(retained_request.active)
        self.assertTrue(retained_request.deleted_at)
        self.assertTrue(self.env['open.sign.request.signer'].browse(signer_id).exists())
        self.assertTrue(self.env['open.sign.request.value'].browse(value_id).exists())
        self.assertTrue(self.env['open.sign.audit.log'].sudo().browse(audit_log_id).exists())

    def test_direct_active_write_requires_unlink_permission_and_stamps_deleted_at(self):
        request = self._create_request(self._create_template('Active Write Guard Template'), name='Active Write Guard Request')

        with self.assertRaises(AccessError):
            request.with_user(self.open_sign_user).write({'active': False})

        request.with_user(self.open_sign_manager).write({'active': False})
        archived_request = self.env['open.sign.request'].with_context(active_test=False).browse(request.id)
        self.assertFalse(archived_request.active)
        self.assertTrue(archived_request.deleted_at)

        with self.assertRaisesRegex(ValidationError, 'Request deletion timestamp cannot be modified directly.'):
            archived_request.with_user(self.open_sign_manager).write({'deleted_at': fields.Datetime.now()})

    def test_hard_delete_escape_hatch_is_superuser_only(self):
        request = self.env['open.sign.request'].with_user(self.open_sign_manager).create({
            'name': 'Hard Delete Escape Hatch Request',
            'template_id': self.acl_template.id,
        })
        request.with_user(self.open_sign_manager).with_context(open_sign_allow_request_hard_delete=True).unlink()

        retained_request = self.env['open.sign.request'].with_context(active_test=False).browse(request.id).exists()
        self.assertTrue(retained_request)
        self.assertFalse(retained_request.active)
        self.assertTrue(retained_request.deleted_at)

    def test_signer_access_link_generation_and_open_action(self):
        request = self._create_request(self.acl_template, name='Signer Access Link Request')
        role = self._create_role(self.acl_template, name='Signer Access Link Role', sequence=100)
        signer = self._create_signer(request, role=role, email='access.link.signer@example.com')

        self.assertTrue(signer.sign_access_url)
        self.assertIn(f"id={signer.id}", signer.sign_access_url)
        self.assertIn("model=open.sign.request.signer", signer.sign_access_url)
        self.assertIn("view_type=form", signer.sign_access_url)

        action = signer.action_open_sign_access_link()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(action['url'], signer.sign_access_url)

    def test_signer_contract_create_is_blocked_once_request_is_versioned_or_sent(self):
        template = self._create_template('Signer Contract Create Freeze')
        request = self._create_request(
            template,
            name='Signer Contract Create Freeze Request',
            owner_id=self.open_sign_user.id,
        )
        role_versioned = self._create_role(template, name='Versioned Role', sequence=10)
        role_sent = self._create_role(template, name='Sent Role', sequence=20)
        signer_model = self.env['open.sign.request.signer'].with_user(self.open_sign_user)

        request.action_version()
        with self.assertRaisesRegex(ValidationError, 'Signer contract cannot be modified once the request is versioned.'):
            signer_model.create({
                'request_id': request.id,
                'role_id': role_versioned.id,
                'email': 'versioned.freeze@example.com',
                'sequence': 10,
            })

        self._create_signer(request, role=role_versioned, email='existing.versioned.freeze@example.com')
        request.action_send()
        with self.assertRaisesRegex(ValidationError, 'Signer contract cannot be modified once the request is versioned.'):
            signer_model.create({
                'request_id': request.id,
                'role_id': role_sent.id,
                'email': 'sent.freeze@example.com',
                'sequence': 20,
            })

    def test_signer_contract_write_and_unlink_are_blocked_once_request_is_versioned(self):
        template = self._create_template('Signer Contract Write Freeze')
        request = self._create_request(
            template,
            name='Signer Contract Write Freeze Request',
            owner_id=self.open_sign_user.id,
        )
        role_primary = self._create_role(template, name='Primary Freeze Role', sequence=10)
        role_secondary = self._create_role(template, name='Secondary Freeze Role', sequence=20)
        signer = self._create_signer(
            request,
            role=role_primary,
            email='frozen.contract@example.com',
            partner_id=self.open_sign_user.partner_id.id,
        )
        target_request = self._create_request(
            template,
            name='Signer Contract Move Target',
            owner_id=self.open_sign_user.id,
        )

        request.action_version()
        signer_user = signer.with_user(self.open_sign_user)
        mutation_cases = (
            {'email': 'changed.contract@example.com'},
            {'role_id': role_secondary.id},
            {'sequence': 99},
            {'partner_id': self.open_sign_manager.partner_id.id},
            {'request_id': target_request.id},
        )
        for vals in mutation_cases:
            with self.subTest(vals=vals):
                with self.assertRaisesRegex(ValidationError, 'Signer contract cannot be modified once the request is versioned.'):
                    signer_user.write(vals)

        with self.assertRaisesRegex(ValidationError, 'Signer contract cannot be modified once the request is versioned.'):
            signer_user.unlink()

    def test_sudo_signer_lifecycle_writes_still_work_after_request_is_sent(self):
        template = self._create_template('Signer Lifecycle Sudo')
        request = self._create_request(template, name='Signer Lifecycle Sudo Request')
        role = self._create_role(template, name='Lifecycle Sudo Role', sequence=10)
        signer = self._create_signer(request, role=role, email='lifecycle.sudo@example.com')

        request.action_version()
        request.action_send()

        opened_at = fields.Datetime.now()
        signer.sudo().write({
            'state': 'opened',
            'last_opened_at': opened_at,
            'ip_last': '127.0.0.1',
        })
        signer.invalidate_recordset(['state', 'last_opened_at', 'ip_last'])
        self.assertEqual(signer.state, 'opened')
        self.assertEqual(signer.last_opened_at, opened_at)
        self.assertEqual(signer.ip_last, '127.0.0.1')

    def test_resend_signer_request_link_requires_manager_and_logs_event(self):
        request = self._create_request(self.acl_template, name='Signer Resend Request')
        role = self._create_role(self.acl_template, name='Signer Resend Role', sequence=110)
        signer = self._create_signer(request, role=role, email='resend.signer@example.com')

        with self.assertRaises(AccessError):
            signer.with_user(self.open_sign_user).action_resend_signer_request()

        message_count_before = len(request.message_ids)
        notification = signer.with_user(self.open_sign_manager).action_resend_signer_request()

        self.assertEqual(notification['type'], 'ir.actions.client')
        self.assertEqual(notification['tag'], 'display_notification')
        self.assertEqual(notification['params']['type'], 'success')

        request.invalidate_recordset(['last_event_at', 'message_ids'])
        self.assertTrue(request.last_event_at)
        self.assertEqual(len(request.message_ids), message_count_before + 1)
        self.assertTrue(
            any('resend triggered' in (message.body or '').lower() for message in request.message_ids)
        )

        request.action_cancel()
        with self.assertRaisesRegex(ValidationError, 'Cannot resend signer links once the request is completed, cancelled, or voided.'):
            signer.with_user(self.open_sign_manager).action_resend_signer_request()
