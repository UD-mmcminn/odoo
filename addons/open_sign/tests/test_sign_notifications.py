# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from unittest.mock import patch

from odoo import fields
from odoo.addons.open_sign.services import notification_service
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignNotifications(TransactionCase):
    QUEUE_FAILURE_WITH_TOKEN = 'SMTP failure for https://example.test/my/sign/42?access_token=abc123'


    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_notification_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.notification.owner@example.com'

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
    def _create_template(cls, env, name):
        template = env['open.sign.template'].create({
            'name': name,
            'source_attachment_id': cls._create_attachment_static(env, f'{name}.pdf').id,
        })
        template.action_publish()
        return template

    def _create_role(self, template, name='Signer', sequence=10):
        return self.env['open.sign.role'].create({
            'template_id': template.id,
            'name': name,
            'sequence': sequence,
        })

    def _create_request_bundle(self, name):
        template = self._create_template(self.env, name)
        request = self.env['open.sign.request'].create({
            'name': f'{name} Request',
            'template_id': template.id,
            'owner_id': self.open_sign_user.id,
        })
        role = self._create_role(template, name=f'{name} Signer')
        signer = self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': role.id,
            'email': f'{name.lower().replace(" ", ".")}@example.com',
            'sequence': role.sequence,
        })
        return request, signer

    def _create_ordered_request_bundle(self, name):
        template = self._create_template(self.env, name)
        request = self.env['open.sign.request'].create({
            'name': f'{name} Request',
            'template_id': template.id,
            'owner_id': self.open_sign_user.id,
            'ordered_signing': True,
        })
        first_role = self._create_role(template, name=f'{name} First', sequence=10)
        second_role = self._create_role(template, name=f'{name} Second', sequence=20)
        first_signer = self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': first_role.id,
            'email': f'{name.lower().replace(" ", ".")}.first@example.com',
            'sequence': first_role.sequence,
        })
        second_signer = self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': second_role.id,
            'email': f'{name.lower().replace(" ", ".")}.second@example.com',
            'sequence': second_role.sequence,
        })
        return request, first_signer, second_signer

    @staticmethod
    def _fake_notification_url(signer):
        return f'https://example.com/my/sign/{signer.id}?access_token=test-token-{signer.id}'

    def _assert_no_url_or_token_leak(self, metadata, *extra_forbidden):
        serialized = str(metadata)
        self.assertNotIn('access_token=', serialized)
        self.assertNotIn('https://example.test/my/sign/42', serialized)
        for fragment in extra_forbidden:
            self.assertNotIn(fragment, serialized)

    def test_action_send_queues_invitation_and_request_sent_audit(self):
        request, signer = self._create_request_bundle('Notification Send')
        request.action_version()

        mail_count_before = self.env['mail.mail'].sudo().search_count([('email_to', '=', signer.email)])
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()

        request.invalidate_recordset(['status', 'sent_at'])
        self.assertEqual(request.status, 'sent')
        self.assertTrue(request.sent_at)
        self.assertEqual(
            self.env['mail.mail'].sudo().search_count([('email_to', '=', signer.email)]),
            mail_count_before + 1,
        )

        request_sent_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('event_type', '=', 'request_sent'),
        ], limit=1)
        self.assertTrue(request_sent_audit)
        self.assertEqual(request_sent_audit.metadata_json['signer_ids'], [signer.id])

        notification_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_queued'),
        ], limit=1)
        self.assertTrue(notification_audit)
        self.assertEqual(notification_audit.metadata_json['notification_type'], 'invitation')

    def test_action_send_rolls_back_when_invitation_queue_fails(self):
        request, signer = self._create_request_bundle('Notification Send Failure')
        request.action_version()

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ), patch(
            'odoo.addons.open_sign.services.notification_service._queue_template',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ):
            with self.assertRaisesRegex(ValidationError, 'Failed to queue the invitation email.'):
                request.action_send()

        request.invalidate_recordset(['status', 'sent_at'])
        self.assertEqual(request.status, 'versioned')
        self.assertFalse(request.sent_at)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', request.id),
            ('event_type', '=', 'request_sent'),
        ]))
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'invitation')
        self.assertEqual(failure_audit.metadata_json['trigger'], 'initial_send')
        self.assertEqual(failure_audit.metadata_json['recipient_email'], signer.email)
        self.assertEqual(failure_audit.metadata_json['template_xmlid'], notification_service.INVITATION_TEMPLATE_XMLID)
        self.assertEqual(
            failure_audit.metadata_json['failure_reason'],
            notification_service.FAILURE_REASON_MAIL_QUEUE_ERROR,
        )
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_action_send_rolls_back_when_signer_notification_url_is_unavailable(self):
        request, signer = self._create_request_bundle('Notification Missing Portal URL')
        request.action_version()

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            return_value=False,
        ):
            with self.assertRaisesRegex(ValidationError, 'Signer notification URL is not available.'):
                request.action_send()

        request.invalidate_recordset(['status', 'sent_at'])
        self.assertEqual(request.status, 'versioned')
        self.assertFalse(request.sent_at)
        self.assertFalse(self.env['mail.mail'].sudo().search_count([('email_to', '=', signer.email)]))
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', request.id),
            ('event_type', '=', 'request_sent'),
        ]))
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'invitation')
        self.assertEqual(failure_audit.metadata_json['trigger'], 'initial_send')
        self.assertEqual(failure_audit.metadata_json['template_xmlid'], notification_service.INVITATION_TEMPLATE_XMLID)
        self.assertEqual(failure_audit.metadata_json['failure_reason'], 'signer_notification_url_unavailable')
        self.assertEqual(failure_audit.metadata_json['recipient_email'], signer.email)
        self.assertNotIn('signer_portal_url', failure_audit.metadata_json)
        self.assertNotIn('access_token', failure_audit.metadata_json)
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_action_send_persists_failure_audit_when_invitation_template_missing(self):
        request, signer = self._create_request_bundle('Notification Missing Template')
        request.action_version()

        with patch(
            'odoo.addons.open_sign.services.notification_service._get_template',
            side_effect=notification_service.NotificationQueueFailure(
                notification_type='invitation',
                recipient_kind='signer',
                recipient_email=False,
                template_xmlid=notification_service.INVITATION_TEMPLATE_XMLID,
                signer_id=False,
                reason='missing_template',
                display_message='Notification template is missing for invitation.',
            ),
        ):
            with self.assertRaisesRegex(ValidationError, 'Notification template is missing for invitation.'):
                request.action_send()

        request.invalidate_recordset(['status', 'sent_at'])
        self.assertEqual(request.status, 'versioned')
        self.assertFalse(request.sent_at)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', request.id),
            ('event_type', '=', 'request_sent'),
        ]))
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertFalse(failure_audit.signer_id)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'invitation')
        self.assertEqual(failure_audit.metadata_json['trigger'], 'initial_send')
        self.assertEqual(failure_audit.metadata_json['template_xmlid'], notification_service.INVITATION_TEMPLATE_XMLID)
        self.assertEqual(
            failure_audit.metadata_json['failure_reason'],
            notification_service.FAILURE_REASON_MISSING_TEMPLATE,
        )
        self.assertFalse(failure_audit.metadata_json['recipient_email'])
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_action_send_queues_current_wave_only_for_ordered_request(self):
        request, first_signer, second_signer = self._create_ordered_request_bundle('Notification Ordered Send')
        request.action_version()

        mail_model = self.env['mail.mail'].sudo()
        first_mail_before = mail_model.search_count([('email_to', '=', first_signer.email)])
        second_mail_before = mail_model.search_count([('email_to', '=', second_signer.email)])

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()

        self.assertEqual(
            mail_model.search_count([('email_to', '=', first_signer.email)]),
            first_mail_before + 1,
        )
        self.assertEqual(
            mail_model.search_count([('email_to', '=', second_signer.email)]),
            second_mail_before,
        )

        request_sent_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('event_type', '=', 'request_sent'),
        ], limit=1)
        self.assertTrue(request_sent_audit)
        self.assertEqual(request_sent_audit.metadata_json['signer_ids'], [first_signer.id])

    def test_action_complete_queues_owner_and_signer_notifications(self):
        request, signer = self._create_request_bundle('Notification Complete')
        request.action_version()
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()
        request.write({
            'status': 'in_progress',
            'final_attachment_id': self._create_attachment_static(
                self.env,
                name='notification_complete_final.pdf',
                res_model='open.sign.request',
            ).id,
            'final_pdf_sha256': 'a' * 64,
        })
        final_attachment = request.final_attachment_id

        owner_email = self.open_sign_user.partner_id.email
        signer_mail_before = self.env['mail.mail'].sudo().search_count([('email_to', '=', signer.email)])
        owner_mail_before = self.env['mail.mail'].sudo().search_count([('email_to', '=', owner_email)])
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_complete()

        request.invalidate_recordset(['status', 'completed_at'])
        self.assertEqual(request.status, 'completed')
        self.assertTrue(request.completed_at)
        self.assertEqual(
            self.env['mail.mail'].sudo().search_count([('email_to', '=', signer.email)]),
            signer_mail_before + 1,
        )
        self.assertEqual(
            self.env['mail.mail'].sudo().search_count([('email_to', '=', owner_email)]),
            owner_mail_before + 1,
        )

        owner_mail = self.env['mail.mail'].sudo().search([('email_to', '=', owner_email)], order='id desc', limit=1)
        signer_mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertIn(request._get_backend_form_url().replace('&', '&amp;'), owner_mail.body_html)
        self.assertIn(self._fake_notification_url(signer), signer_mail.body_html)
        self.assertIn(final_attachment, owner_mail.attachment_ids)
        self.assertIn(final_attachment, signer_mail.attachment_ids)

        completed_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('event_type', '=', 'request_completed'),
        ], limit=1)
        self.assertTrue(completed_audit)

    def test_action_complete_skips_signer_notification_without_portal_url(self):
        request, signer = self._create_request_bundle('Notification Complete No Portal URL')
        request.action_version()
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()
        request.write({
            'status': 'in_progress',
            'final_attachment_id': self._create_attachment_static(
                self.env,
                name='notification_complete_no_portal_final.pdf',
                res_model='open.sign.request',
            ).id,
            'final_pdf_sha256': 'c' * 64,
        })

        owner_email = self.open_sign_user.partner_id.email
        mail_model = self.env['mail.mail'].sudo()
        owner_before = mail_model.search_count([('email_to', '=', owner_email)])
        signer_before = mail_model.search_count([('email_to', '=', signer.email)])

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            return_value=False,
        ):
            request.action_complete()

        self.assertEqual(mail_model.search_count([('email_to', '=', owner_email)]), owner_before + 1)
        self.assertEqual(mail_model.search_count([('email_to', '=', signer.email)]), signer_before)
        skipped_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_skipped'),
        ], order='id desc', limit=1)
        self.assertTrue(skipped_audit)
        self.assertEqual(skipped_audit.metadata_json['notification_type'], 'completion')
        self.assertEqual(skipped_audit.metadata_json['skip_reason'], 'signer_notification_url_unavailable')

    def test_action_complete_preserves_completion_when_notification_queue_raises(self):
        request, _signer = self._create_request_bundle('Notification Complete Failure')
        request.action_version()
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()
        request.write({
            'status': 'in_progress',
            'final_attachment_id': self._create_attachment_static(
                self.env,
                name='notification_complete_failure_final.pdf',
                res_model='open.sign.request',
            ).id,
            'final_pdf_sha256': 'b' * 64,
        })

        with patch('odoo.addons.open_sign.models.sign_request.notification_service.queue_request_completion_notifications') as queue_mock:
            queue_mock.side_effect = RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN)
            request.action_complete()

        request.invalidate_recordset(['status', 'completed_at'])
        self.assertEqual(request.status, 'completed')
        self.assertTrue(request.completed_at)
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('event_type', '=', 'notification_failed'),
        ], limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'completion')
        self.assertEqual(
            failure_audit.metadata_json['failure_reason'],
            notification_service.FAILURE_REASON_NOTIFICATION_SERVICE_ERROR,
        )
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_action_complete_queue_failures_are_sanitized(self):
        request, signer = self._create_request_bundle('Notification Complete Queue Failure')
        request.action_version()
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()
        request.write({
            'status': 'in_progress',
            'final_attachment_id': self._create_attachment_static(
                self.env,
                name='notification_complete_queue_failure_final.pdf',
                res_model='open.sign.request',
            ).id,
            'final_pdf_sha256': 'd' * 64,
        })

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ), patch(
            'odoo.addons.open_sign.services.notification_service._queue_template',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ):
            request.action_complete()

        request.invalidate_recordset(['status', 'completed_at'])
        self.assertEqual(request.status, 'completed')
        self.assertTrue(request.completed_at)
        failure_audits = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('event_type', '=', 'notification_failed'),
            ('metadata_json', '!=', False),
        ])
        self.assertTrue(failure_audits)
        completion_failures = failure_audits.filtered(
            lambda audit: audit.metadata_json.get('notification_type') == 'completion'
        )
        self.assertTrue(completion_failures)
        self.assertTrue(any(audit.metadata_json.get('recipient_kind') == 'owner' for audit in completion_failures))
        self.assertTrue(any(audit.metadata_json.get('recipient_kind') == 'signer' for audit in completion_failures))
        for audit in completion_failures:
            self.assertEqual(
                audit.metadata_json['failure_reason'],
                notification_service.FAILURE_REASON_MAIL_QUEUE_ERROR,
            )
            self._assert_no_url_or_token_leak(audit.metadata_json)

    def test_decline_notification_queues_owner_only_mail(self):
        request, signer = self._create_request_bundle('Notification Decline')
        request.action_version()
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()
        signer.write({
            'state': 'declined',
            'declined_reason': 'Need legal review',
        })
        request._transition_to('declined', {'last_event_at': fields.Datetime.now()})

        owner_email = self.open_sign_user.partner_id.email
        mail_model = self.env['mail.mail'].sudo()
        owner_mail_before = mail_model.search_count([('email_to', '=', owner_email)])
        signer_mail_before = mail_model.search_count([('email_to', '=', signer.email)])

        notification_service.queue_request_decline_notification(request, signer, raise_on_failure=True)

        self.assertEqual(
            mail_model.search_count([('email_to', '=', owner_email)]),
            owner_mail_before + 1,
        )
        self.assertEqual(
            mail_model.search_count([('email_to', '=', signer.email)]),
            signer_mail_before,
        )

        decline_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('event_type', '=', 'notification_queued'),
        ], order='id desc', limit=1)
        self.assertTrue(decline_audit)
        self.assertEqual(decline_audit.metadata_json['notification_type'], 'decline')
        self.assertEqual(decline_audit.metadata_json['recipient_kind'], 'owner')
        self.assertEqual(decline_audit.metadata_json['recipient_email'], owner_email)

    def test_decline_notification_queue_failure_is_sanitized(self):
        request, signer = self._create_request_bundle('Notification Decline Failure')
        request.action_version()
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()
        signer.write({
            'state': 'declined',
            'declined_reason': 'Need legal review',
        })
        request._transition_to('declined', {'last_event_at': fields.Datetime.now()})

        with patch(
            'odoo.addons.open_sign.services.notification_service._queue_template',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ):
            notification_service.queue_request_decline_notification(request, signer, raise_on_failure=False)

        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'decline')
        self.assertEqual(
            failure_audit.metadata_json['failure_reason'],
            notification_service.FAILURE_REASON_MAIL_QUEUE_ERROR,
        )
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_notification_audit_metadata_excludes_urls_and_raw_tokens(self):
        request, signer = self._create_request_bundle('Notification Audit Hygiene')
        request.action_version()
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request.action_send()

        notification_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_queued'),
        ], limit=1)
        self.assertTrue(notification_audit)
        metadata = notification_audit.metadata_json
        self.assertNotIn('signer_portal_url', metadata)
        self.assertNotIn('access_token', metadata)
        self._assert_no_url_or_token_leak(metadata)
