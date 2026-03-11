# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.open_sign.services import notification_service
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignCron(TransactionCase):
    QUEUE_FAILURE_WITH_TOKEN = 'SMTP failure for https://example.test/my/sign/42?access_token=abc123'


    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls._create_template_static(cls.env, 'Cron Template')
        cls.role = cls.env['open.sign.role'].create({
            'template_id': cls.template.id,
            'name': 'Cron Signer',
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

    def _create_sent_request(self, name, sent_at, expires_at, signer_state='pending'):
        request = self.env['open.sign.request'].create({
            'name': name,
            'template_id': self.template.id,
        })
        signer = self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': self.role.id,
            'email': f'{name.lower().replace(" ", ".")}@example.com',
            'sequence': self.role.sequence,
        })
        request.action_version()
        request.action_send()
        request.sudo().with_context(open_sign_skip_transition_check=True).write({
            'sent_at': sent_at,
            'expires_at': expires_at,
        })
        if signer_state == 'signed':
            signer.sudo().write({
                'state': 'signed',
                'signed_at': fields.Datetime.now(),
            })
        return request

    def _create_ordered_sent_request(self, name, sent_at, expires_at):
        request = self.env['open.sign.request'].create({
            'name': name,
            'template_id': self.template.id,
            'ordered_signing': True,
        })
        second_role = self.env['open.sign.role'].create({
            'template_id': self.template.id,
            'name': f'{name} Second',
            'sequence': 20,
        })
        first_signer = self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': self.role.id,
            'email': f'{name.lower().replace(" ", ".")}.first@example.com',
            'sequence': self.role.sequence,
        })
        second_signer = self.env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': second_role.id,
            'email': f'{name.lower().replace(" ", ".")}.second@example.com',
            'sequence': second_role.sequence,
        })
        request.action_version()
        request.action_send()
        request.sudo().with_context(open_sign_skip_transition_check=True).write({
            'sent_at': sent_at,
            'expires_at': expires_at,
        })
        return request, first_signer, second_signer

    @staticmethod
    def _fake_notification_url(signer):
        return f'https://example.com/my/sign/{signer.id}?access_token=test-token-{signer.id}'

    def _assert_no_url_or_token_leak(self, metadata):
        serialized = str(metadata)
        self.assertNotIn('access_token=', serialized)
        self.assertNotIn('https://example.test/my/sign/42', serialized)

    def test_cron_records_are_loaded(self):
        reminder_cron = self.env.ref('open_sign.ir_cron_open_sign_send_reminders')
        expire_cron = self.env.ref('open_sign.ir_cron_open_sign_expire_requests')

        self.assertEqual(reminder_cron.model_id.model, 'open.sign.request')
        self.assertEqual(reminder_cron.state, 'code')
        self.assertEqual(reminder_cron.code, 'model._cron_send_reminders()')
        self.assertEqual(expire_cron.model_id.model, 'open.sign.request')
        self.assertEqual(expire_cron.state, 'code')
        self.assertEqual(expire_cron.code, 'model._cron_expire_requests()')

    def test_cron_expire_requests_transitions_eligible_records(self):
        now = fields.Datetime.now()
        due_request = self._create_sent_request(
            'Due Request',
            sent_at=now - timedelta(days=2),
            expires_at=now - timedelta(hours=1),
        )
        pending_request = self._create_sent_request(
            'Pending Request',
            sent_at=now - timedelta(days=2),
            expires_at=now + timedelta(days=1),
        )

        self.env['open.sign.request']._cron_expire_requests()
        due_request.invalidate_recordset()
        pending_request.invalidate_recordset()

        self.assertEqual(due_request.status, 'expired')
        self.assertTrue(due_request.last_event_at)
        self.assertEqual(pending_request.status, 'sent')

    def test_cron_send_reminders_respects_due_and_throttle_rules(self):
        now = fields.Datetime.now()
        self.env['ir.config_parameter'].sudo().set_param('open_sign.reminder_interval_hours', '24')

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            due_request = self._create_sent_request(
                'Reminder Due',
                sent_at=now - timedelta(days=2),
                expires_at=now + timedelta(days=2),
            )
            too_early_request = self._create_sent_request(
                'Reminder Too Early',
                sent_at=now - timedelta(hours=2),
                expires_at=now + timedelta(days=2),
            )
            no_actionable_request = self._create_sent_request(
                'Reminder No Actionable',
                sent_at=now - timedelta(days=2),
                expires_at=now + timedelta(days=2),
                signer_state='signed',
            )

        due_email = due_request.signer_ids.email
        early_email = too_early_request.signer_ids.email
        no_actionable_email = no_actionable_request.signer_ids.email
        mail_model = self.env['mail.mail'].sudo()
        due_mail_count = mail_model.search_count([('email_to', '=', due_email)])
        early_mail_count = mail_model.search_count([('email_to', '=', early_email)])
        no_actionable_mail_count = mail_model.search_count([('email_to', '=', no_actionable_email)])

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            self.env['open.sign.request']._cron_send_reminders()
        due_request.invalidate_recordset()
        too_early_request.invalidate_recordset()
        no_actionable_request.invalidate_recordset()

        self.assertEqual(due_request.reminder_count, 1)
        self.assertTrue(due_request.last_reminder_at)
        self.assertEqual(mail_model.search_count([('email_to', '=', due_email)]), due_mail_count + 1)

        self.assertEqual(too_early_request.reminder_count, 0)
        self.assertFalse(too_early_request.last_reminder_at)
        self.assertEqual(mail_model.search_count([('email_to', '=', early_email)]), early_mail_count)

        self.assertEqual(no_actionable_request.reminder_count, 0)
        self.assertFalse(no_actionable_request.last_reminder_at)
        self.assertEqual(mail_model.search_count([('email_to', '=', no_actionable_email)]), no_actionable_mail_count)

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            self.env['open.sign.request']._cron_send_reminders()
        due_request.invalidate_recordset()
        self.assertEqual(due_request.reminder_count, 1)

    def test_cron_send_reminders_only_targets_current_ordered_wave(self):
        now = fields.Datetime.now()
        self.env['ir.config_parameter'].sudo().set_param('open_sign.reminder_interval_hours', '24')

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request, first_signer, second_signer = self._create_ordered_sent_request(
                'Ordered Reminder Wave',
                sent_at=now - timedelta(days=2),
                expires_at=now + timedelta(days=2),
            )
        mail_model = self.env['mail.mail'].sudo()
        first_before = mail_model.search_count([('email_to', '=', first_signer.email)])
        second_before = mail_model.search_count([('email_to', '=', second_signer.email)])

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            self.env['open.sign.request']._cron_send_reminders()

        request.invalidate_recordset(['reminder_count', 'last_reminder_at'])
        self.assertEqual(request.reminder_count, 1)
        self.assertTrue(request.last_reminder_at)
        self.assertEqual(
            mail_model.search_count([('email_to', '=', first_signer.email)]),
            first_before + 1,
        )
        self.assertEqual(
            mail_model.search_count([('email_to', '=', second_signer.email)]),
            second_before,
        )

    def test_cron_send_reminders_skips_when_signer_notification_url_is_unavailable(self):
        now = fields.Datetime.now()
        self.env['ir.config_parameter'].sudo().set_param('open_sign.reminder_interval_hours', '24')

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request = self._create_sent_request(
                'Reminder Missing Portal URL',
                sent_at=now - timedelta(days=2),
                expires_at=now + timedelta(days=2),
            )

        signer = request.signer_ids
        mail_model = self.env['mail.mail'].sudo()
        mail_before = mail_model.search_count([('email_to', '=', signer.email)])

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            return_value=False,
        ):
            self.env['open.sign.request']._cron_send_reminders()

        request.invalidate_recordset(['reminder_count', 'last_reminder_at'])
        self.assertEqual(request.reminder_count, 0)
        self.assertFalse(request.last_reminder_at)
        self.assertEqual(mail_model.search_count([('email_to', '=', signer.email)]), mail_before)
        skipped_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_skipped'),
        ], order='id desc', limit=1)
        self.assertTrue(skipped_audit)
        self.assertEqual(skipped_audit.metadata_json['notification_type'], 'reminder')
        self.assertEqual(skipped_audit.metadata_json['skip_reason'], 'signer_notification_url_unavailable')

    def test_cron_send_reminders_queue_failure_is_sanitized(self):
        now = fields.Datetime.now()
        self.env['ir.config_parameter'].sudo().set_param('open_sign.reminder_interval_hours', '24')

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request = self._create_sent_request(
                'Reminder Queue Failure',
                sent_at=now - timedelta(days=2),
                expires_at=now + timedelta(days=2),
            )

        signer = request.signer_ids
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ), patch(
            'odoo.addons.open_sign.services.notification_service._queue_template',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ):
            self.env['open.sign.request']._cron_send_reminders()

        request.invalidate_recordset(['reminder_count', 'last_reminder_at'])
        self.assertEqual(request.reminder_count, 0)
        self.assertFalse(request.last_reminder_at)
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'reminder')
        self.assertEqual(
            failure_audit.metadata_json['failure_reason'],
            notification_service.FAILURE_REASON_MAIL_QUEUE_ERROR,
        )
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_cron_send_reminders_service_failure_is_sanitized(self):
        now = fields.Datetime.now()
        self.env['ir.config_parameter'].sudo().set_param('open_sign.reminder_interval_hours', '24')

        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            side_effect=lambda signer_record: self._fake_notification_url(signer_record),
        ):
            request = self._create_sent_request(
                'Reminder Service Failure',
                sent_at=now - timedelta(days=2),
                expires_at=now + timedelta(days=2),
            )

        with patch(
            'odoo.addons.open_sign.models.sign_request.notification_service.queue_request_reminders',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ):
            self.env['open.sign.request']._cron_send_reminders()

        request.invalidate_recordset(['reminder_count', 'last_reminder_at'])
        self.assertEqual(request.reminder_count, 0)
        self.assertFalse(request.last_reminder_at)
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'reminder')
        self.assertEqual(
            failure_audit.metadata_json['failure_reason'],
            notification_service.FAILURE_REASON_NOTIFICATION_SERVICE_ERROR,
        )
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)
