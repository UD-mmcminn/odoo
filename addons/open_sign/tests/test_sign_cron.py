# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignCron(TransactionCase):

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

        due_messages = len(due_request.message_ids)
        early_messages = len(too_early_request.message_ids)
        no_actionable_messages = len(no_actionable_request.message_ids)

        self.env['open.sign.request']._cron_send_reminders()
        due_request.invalidate_recordset()
        too_early_request.invalidate_recordset()
        no_actionable_request.invalidate_recordset()

        self.assertEqual(due_request.reminder_count, 1)
        self.assertTrue(due_request.last_reminder_at)
        self.assertEqual(len(due_request.message_ids), due_messages + 1)

        self.assertEqual(too_early_request.reminder_count, 0)
        self.assertFalse(too_early_request.last_reminder_at)
        self.assertEqual(len(too_early_request.message_ids), early_messages)

        self.assertEqual(no_actionable_request.reminder_count, 0)
        self.assertFalse(no_actionable_request.last_reminder_at)
        self.assertEqual(len(no_actionable_request.message_ids), no_actionable_messages)

        self.env['open.sign.request']._cron_send_reminders()
        due_request.invalidate_recordset()
        self.assertEqual(due_request.reminder_count, 1)
