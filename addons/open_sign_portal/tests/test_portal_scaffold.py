# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from psycopg2.errors import LockNotAvailable

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.open_sign_portal.controllers.portal_sign import OpenSignPortalController
from odoo.addons.open_sign_portal.tests.common import (
    CONSENT_HASH_RE,
    REQUEST_REVISION_RE,
    OpenSignPortalTestMixin,
)


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalScaffold(TransactionCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.signer_bundle = cls._create_portal_session(
            cls.env,
            name='Portal Scaffold',
            owner=cls.env.user,
        )
        cls.signer = cls.signer_bundle['signer']
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_token_user',
            password='open_sign_portal_token_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_token_manager',
            password='open_sign_portal_token_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.token.user@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.token.manager@example.com'
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_portal_auditor',
            password='open_sign_portal_auditor',
            groups='open_sign.group_open_sign_auditor',
        )
        cls.owner_scoped_bundle = cls._create_portal_session(
            cls.env,
            name='Portal Token Guard',
            owner=cls.open_sign_user,
            signer_partner=cls.open_sign_user.partner_id,
        )

    def test_portal_templates_and_helpers_loaded(self):
        self.env.ref('open_sign_portal.portal_my_sign')
        self.env.ref('open_sign_portal.portal_sign_page')
        self.assertEqual(self.signer._get_portal_sign_path(), f'/my/sign/{self.signer.id}')
        self.assertEqual(self.signer.access_url, f'/my/sign/{self.signer.id}')
        self.assertIn(f'/my/sign/{self.signer.id}?access_token=', self.signer.get_portal_url())
        self.assertTrue(self.signer.access_token)
        self.assertEqual(self.signer.portal_sign_url, self.signer.get_portal_url())

    def test_error_envelope_shape(self):
        controller = OpenSignPortalController()
        error = controller._build_error_response('validation_error', 'test')
        self.assertFalse(error['ok'])
        self.assertEqual(error['error_code'], 'validation_error')
        self.assertEqual(error['message'], 'test')

    def test_auditor_cannot_read_tokenized_fields(self):
        signer_fields = self.signer.with_user(self.open_sign_auditor).fields_get()
        self.assertNotIn('access_token', signer_fields)
        self.assertNotIn('portal_sign_url', signer_fields)

    def test_manager_backend_views_expose_copy_link_and_resend(self):
        signer_view = self.env['open.sign.request.signer'].with_user(self.open_sign_manager).get_view(
            self.env.ref('open_sign.view_open_sign_request_signer_form').id,
            'form',
        )
        signer_arch = signer_view['arch']
        self.assertIn('name="portal_sign_url"', signer_arch)
        self.assertIn('string="Copy Link"', signer_arch)
        self.assertIn('name="sign_access_url"', signer_arch)
        self.assertIn('string="Internal Link"', signer_arch)

        request_view = self.env['open.sign.request'].with_user(self.open_sign_manager).get_view(
            self.env.ref('open_sign.view_open_sign_request_form').id,
            'form',
        )
        request_arch = request_view['arch']
        self.assertIn('name="portal_sign_url"', request_arch)
        self.assertIn('name="action_resend_signer_request"', request_arch)

    def test_user_backend_views_hide_resend_and_keep_copy_link(self):
        signer_view = self.env['open.sign.request.signer'].with_user(self.open_sign_user).get_view(
            self.env.ref('open_sign.view_open_sign_request_signer_form').id,
            'form',
        )
        signer_arch = signer_view['arch']
        self.assertIn('name="portal_sign_url"', signer_arch)
        self.assertIn('string="Copy Link"', signer_arch)
        self.assertIn('name="sign_access_url"', signer_arch)
        self.assertIn('string="Internal Link"', signer_arch)

        request_view = self.env['open.sign.request'].with_user(self.open_sign_user).get_view(
            self.env.ref('open_sign.view_open_sign_request_form').id,
            'form',
        )
        request_arch = request_view['arch']
        self.assertIn('name="portal_sign_url"', request_arch)
        self.assertNotIn('name="action_resend_signer_request"', request_arch)

    def test_non_superusers_cannot_write_access_token(self):
        signer = self.owner_scoped_bundle['signer']
        token_before = signer._portal_ensure_token()
        for user in (self.open_sign_user, self.open_sign_manager):
            with self.subTest(login=user.login):
                with self.assertRaises(AccessError):
                    signer.with_user(user).write({'access_token': 'forced-token'})
        self.assertEqual(signer.access_token, token_before)

    def _create_contact_correction_wizard(self, signer, *, user, target_email=False, reason='Retry invitation'):
        return self.env['open.sign.signer.contact_correction.wizard'].with_user(user).create({
            'signer_id': signer.id,
            'target_email': target_email or signer.email,
            'reason': reason,
        })

    def test_contact_correction_same_email_resend_rotates_token_and_queues_invitation(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contact Correction Immediate',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        old_token = signer.access_token
        mail_model = self.env['mail.mail'].sudo()
        mail_before = mail_model.search_count([('email_to', '=', signer.email)])

        wizard = self._create_contact_correction_wizard(signer, user=self.open_sign_manager)
        action = wizard.action_apply_contact_correction()

        signer.invalidate_recordset(['email', 'access_token'])
        sign_request.invalidate_recordset(['last_event_at'])
        self.assertEqual(signer.email, bundle['signer'].email)
        self.assertNotEqual(signer.access_token, old_token)
        self.assertEqual(action['tag'], 'display_notification')
        self.assertEqual(action['params']['message'], 'Invitation queued.')
        self.assertEqual(
            mail_model.search_count([('email_to', '=', signer.email)]),
            mail_before + 1,
        )

        queued_mail = mail_model.search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertIn(f"/my/sign/{signer.id}?access_token={signer.access_token}", queued_mail.body_html)
        self.assertNotIn(old_token, queued_mail.body_html)

        correction_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_contact_corrected'),
        ], limit=1)
        self.assertTrue(correction_audit)
        self.assertEqual(correction_audit.metadata_json['old_email'], signer.email)
        self.assertEqual(correction_audit.metadata_json['new_email'], signer.email)
        self.assertEqual(correction_audit.metadata_json['delivery_disposition'], 'queued_now')

    def test_contact_correction_updates_email_and_defers_when_request_is_versioned(self):
        template = self._create_template(self.env, 'Portal Contact Correction Versioned')
        role = self._create_role(self.env, template, 'Portal Contact Correction Versioned Signer', 10)
        sign_request = self._create_request(self.env, template, owner=self.open_sign_user)
        signer = self._create_signer(
            self.env,
            sign_request,
            role,
            email='portal.contact.versioned.old@example.com',
            sequence=10,
        )
        sign_request.action_version()
        signer._portal_ensure_token()
        old_token = signer.access_token

        wizard = self._create_contact_correction_wizard(
            signer,
            user=self.open_sign_manager,
            target_email='portal.contact.versioned.new@example.com',
            reason='Correcting address before send',
        )
        action = wizard.action_apply_contact_correction()

        signer.invalidate_recordset(['email', 'access_token'])
        self.assertEqual(signer.email, 'portal.contact.versioned.new@example.com')
        self.assertNotEqual(signer.access_token, old_token)
        self.assertEqual(
            action['params']['message'],
            'Contact update recorded. Invitation will be sent when eligible.',
        )
        self.assertFalse(self.env['mail.mail'].sudo().search_count([('email_to', '=', signer.email)]))

        correction_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_contact_corrected'),
        ], limit=1)
        self.assertTrue(correction_audit)
        self.assertEqual(correction_audit.metadata_json['old_email'], 'portal.contact.versioned.old@example.com')
        self.assertEqual(correction_audit.metadata_json['new_email'], 'portal.contact.versioned.new@example.com')
        self.assertEqual(correction_audit.metadata_json['delivery_disposition'], 'deferred_until_send')

        skipped_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_skipped'),
        ], order='id desc', limit=1)
        self.assertTrue(skipped_audit)
        self.assertEqual(skipped_audit.metadata_json['trigger'], 'manual_resend')
        self.assertEqual(skipped_audit.metadata_json['skip_reason'], 'deferred_until_send')

    def test_contact_correction_defers_for_future_wave_signer(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Contact Correction Waiting',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        old_token = signer_second.access_token
        mail_model = self.env['mail.mail'].sudo()
        mail_before = mail_model.search_count([('email_to', '=', signer_second.email)])

        wizard = self._create_contact_correction_wizard(
            signer_second,
            user=self.open_sign_manager,
            reason='Correct future-wave recipient before turn',
        )
        action = wizard.action_apply_contact_correction()

        signer_second.invalidate_recordset(['access_token'])
        self.assertNotEqual(signer_second.access_token, old_token)
        self.assertEqual(
            action['params']['message'],
            'Contact update recorded. Invitation will be sent when eligible.',
        )
        self.assertEqual(
            mail_model.search_count([('email_to', '=', signer_second.email)]),
            mail_before,
        )

        skipped_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', bundle['request'].id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'notification_skipped'),
        ], order='id desc', limit=1)
        self.assertTrue(skipped_audit)
        self.assertEqual(skipped_audit.metadata_json['trigger'], 'manual_resend')
        self.assertEqual(skipped_audit.metadata_json['skip_reason'], 'deferred_future_wave')

    def test_contact_correction_rolls_back_email_and_token_when_queue_fails(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contact Correction Rollback',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        old_email = signer.email
        old_token = signer.access_token

        wizard = self._create_contact_correction_wizard(
            signer,
            user=self.open_sign_manager,
            target_email='portal.contact.rollback.new@example.com',
            reason='Retry after queue failure',
        )
        with patch(
            'odoo.addons.open_sign.services.notification_service._queue_template',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ):
            with self.assertRaisesRegex(ValidationError, 'Failed to queue the invitation email.'):
                wizard.action_apply_contact_correction()

        signer.invalidate_recordset(['email', 'access_token'])
        self.assertEqual(signer.email, old_email)
        self.assertEqual(signer.access_token, old_token)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_contact_corrected'),
        ]))
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'invitation')
        self.assertEqual(failure_audit.metadata_json['trigger'], 'manual_resend')
        self.assertEqual(
            failure_audit.metadata_json['recipient_email'],
            'portal.contact.rollback.new@example.com',
        )
        self.assertEqual(
            failure_audit.metadata_json['failure_reason'],
            'mail_queue_error',
        )
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_actionable_manual_resend_missing_portal_url_persists_failure_audit(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contact Correction Missing Portal URL',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        old_email = signer.email
        old_token = signer.access_token

        wizard = self._create_contact_correction_wizard(
            signer,
            user=self.open_sign_manager,
            target_email='portal.contact.missing-url.new@example.com',
            reason='Retry after portal URL loss',
        )
        with patch.object(
            type(self.env['open.sign.request.signer']),
            '_get_notification_sign_url',
            autospec=True,
            return_value=False,
        ):
            with self.assertRaisesRegex(ValidationError, 'Signer notification URL is not available.'):
                wizard.action_apply_contact_correction()

        signer.invalidate_recordset(['email', 'access_token'])
        self.assertEqual(signer.email, old_email)
        self.assertEqual(signer.access_token, old_token)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_contact_corrected'),
        ]))
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'invitation')
        self.assertEqual(failure_audit.metadata_json['trigger'], 'manual_resend')
        self.assertEqual(
            failure_audit.metadata_json['recipient_email'],
            'portal.contact.missing-url.new@example.com',
        )
        self.assertEqual(
            failure_audit.metadata_json['failure_reason'],
            'signer_notification_url_unavailable',
        )
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalHttp(HttpCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_user',
            password='open_sign_portal_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_outsider = new_test_user(
            cls.env,
            login='open_sign_portal_outsider',
            password='open_sign_portal_outsider',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_manager',
            password='open_sign_portal_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.http.user@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.http.manager@example.com'
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_portal_auditor_http',
            password='open_sign_portal_auditor_http',
            groups='open_sign.group_open_sign_auditor',
        )

    def _build_payload(self, *, revision, values=None, consent=None, access_token=False):
        payload = {
            'idempotency_key': str(uuid4()),
            'request_revision': revision,
            'values': values if values is not None else [],
        }
        if consent is not None:
            payload['consent'] = consent
        if access_token:
            payload['access_token'] = access_token
        return payload

    def _build_decline_payload(self, *, revision, reason, access_token=False):
        payload = {
            'idempotency_key': str(uuid4()),
            'request_revision': revision,
            'reason': reason,
        }
        if access_token:
            payload['access_token'] = access_token
        return payload

    def _extract_consent_hash_and_revision(self, html):
        hash_match = CONSENT_HASH_RE.search(html or '')
        revision_match = REQUEST_REVISION_RE.search(html or '')
        self.assertTrue(hash_match)
        self.assertTrue(revision_match)
        return hash_match.group(1), int(revision_match.group(1))

    def _submit_text_signer_successfully(self, bundle, *, value='Signed Value'):
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]
        self.assertTrue(text_field)

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        page_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        submit_response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/submit",
            self._build_payload(
                revision=revision,
                values=[{'field_id': text_field.id, 'value': value}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(submit_response['ok'])
        return text_field, consent_hash, submit_response

    def _transition_bundle_request_to_status(self, bundle, status):
        sign_request = self.env['open.sign.request'].browse(bundle['request'].id)
        if status == 'completed':
            self._submit_text_signer_successfully(bundle)
            final_attachment = self._create_attachment_static(
                self.env,
                f'{sign_request.name}_final.pdf',
                res_model='open.sign.request',
            )
            sign_request.write({
                'final_attachment_id': final_attachment.id,
                'final_pdf_sha256': 'f' * 64,
            })
            sign_request.action_complete()
        elif status == 'declined':
            sign_request._transition_to('declined', {'last_event_at': fields.Datetime.now()})
        elif status == 'expired':
            sign_request._transition_to('expired', {'last_event_at': fields.Datetime.now()})
        elif status == 'cancelled':
            sign_request.action_cancel()
        elif status == 'voided':
            self._transition_bundle_request_to_status(bundle, 'completed')
            sign_request.invalidate_recordset(['status', 'lock_version'])
            sign_request.action_void()
        else:
            raise AssertionError(f'Unsupported request status for test helper: {status}')
        sign_request.invalidate_recordset(['status', 'lock_version'])
        return sign_request

    def _assert_terminal_readonly_response(self, bundle, expected_message):
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        last_opened_at = signer.last_opened_at
        ip_last = signer.ip_last
        lock_version = sign_request.lock_version
        signer_opened_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ])

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{signer.id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(expected_message, response.text)
        self.assertNotIn('o_open_sign_save', response.text)
        self.assertNotIn('o_open_sign_submit', response.text)
        self.assertNotIn('open_sign_consent', response.text)

        signer.invalidate_recordset(['last_opened_at', 'ip_last'])
        sign_request.invalidate_recordset(['lock_version'])
        self.assertEqual(signer.last_opened_at, last_opened_at)
        self.assertEqual(signer.ip_last, ip_last)
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ]), signer_opened_count)

    def _submit_ordered_signer_successfully(
        self,
        bundle,
        *,
        signer_key='signer_first',
        field_key='field_first',
        token_key='token_first',
        value='Signed Value',
    ):
        signer = bundle[signer_key]
        field = bundle[field_key]
        token = bundle[token_key]

        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={token}",
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        submit_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=revision,
                values=[{'field_id': field.id, 'value': value}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=token,
            ),
        )
        self.assertTrue(submit_response['ok'])
        return field, consent_hash, submit_response

    def _assert_waiting_page_is_non_mutating(self, bundle, *, signer_key='signer_second', token_key='token_second'):
        signer = self.env['open.sign.request.signer'].browse(bundle[signer_key].id)
        sign_request = signer.request_id
        last_opened_at = signer.last_opened_at
        ip_last = signer.ip_last
        lock_version = sign_request.lock_version
        signer_opened_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ])

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{signer.id}?access_token={bundle[token_key]}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('This signer session is waiting for its turn.', response.text)
        self.assertIn(
            'This request uses sequential signing. Another signer must complete before your turn begins. Refresh this page later.',
            response.text,
        )
        self.assertNotIn('o_open_sign_save', response.text)
        self.assertNotIn('o_open_sign_submit', response.text)
        self.assertNotIn('open_sign_consent', response.text)
        self.assertIn('Decline to Sign', response.text)
        self.assertIn('Refresh status', response.text)
        self.assertIn('View PDF', response.text)
        self.assertRegex(
            response.text,
            rf'(?s)data-field-id="{bundle["field_second"].id}".*?<input[^>]*o_open_sign_input[^>]*disabled',
        )

        signer.invalidate_recordset(['last_opened_at', 'ip_last', 'state'])
        sign_request.invalidate_recordset(['lock_version', 'status'])
        self.assertEqual(signer.state, 'pending')
        self.assertEqual(signer.last_opened_at, last_opened_at)
        self.assertEqual(signer.ip_last, ip_last)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ]), signer_opened_count)

    def _assert_terminal_preview_response_is_non_mutating(self, bundle):
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        last_opened_at = signer.last_opened_at
        ip_last = signer.ip_last
        lock_version = sign_request.lock_version
        signer_opened_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ])

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{signer.id}/preview", allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Preview Mode', response.text)

        signer.invalidate_recordset(['last_opened_at', 'ip_last'])
        sign_request.invalidate_recordset(['lock_version'])
        self.assertEqual(signer.last_opened_at, last_opened_at)
        self.assertEqual(signer.ip_last, ip_last)
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ]), signer_opened_count)

    def _assert_terminal_scaffold_endpoint_is_non_mutating(self, bundle, endpoint, expected_message, *, payload=None):
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        signer_state = signer.state
        lock_version = sign_request.lock_version
        audit_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
        ])

        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/{endpoint}",
            payload if payload is not None else {'access_token': bundle['token']},
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], expected_message)

        signer.invalidate_recordset(['state'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, signer_state)
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
        ]), audit_count)

    def test_portal_sign_route_denies_public_without_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal HTTP No Token',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}", allow_redirects=False)
        self.assertEqual(response.status_code, 303)

    def test_portal_sign_route_allows_public_with_valid_token_and_opens_session(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal HTTP Open Session',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        self.assertEqual(signer.state, 'opened')
        self.assertEqual(sign_request.status, 'opened')
        self.assertEqual(sign_request.lock_version, 1)
        self.assertTrue(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ]))

    def test_portal_sign_route_renders_for_internal_user(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal HTTP Internal View',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}", allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sign Document', response.text)

    def test_portal_sign_route_denies_internal_non_signer_without_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal HTTP Internal Deny',
            owner=self.open_sign_user,
        )
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}", allow_redirects=False)
        self.assertEqual(response.status_code, 303)

    def test_preview_route_allows_internal_staff_without_mutation(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Preview Route',
            owner=self.open_sign_user,
        )
        users = (
            self.open_sign_user,
            self.open_sign_manager,
            self.open_sign_auditor,
        )
        for user in users:
            with self.subTest(login=user.login):
                self.authenticate(user.login, user.login)
                response = self.url_open(f"/my/sign/{bundle['signer'].id}/preview", allow_redirects=False)
                self.assertEqual(response.status_code, 200)
                self.assertIn('Preview Mode', response.text)

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.last_opened_at)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ]))

    def test_signer_route_denies_versioned_request_while_preview_allows_it(self):
        template = self._create_template(self.env, 'Portal Versioned Only')
        role = self._create_role(self.env, template, 'Versioned Signer', 10)
        self._create_field(self.env, template, role, type='text', label='Versioned Field', required=True)
        sign_request = self._create_request(self.env, template, owner=self.open_sign_user)
        signer = self._create_signer(
            self.env,
            sign_request,
            role,
            email='versioned.signer@example.com',
            sequence=10,
        )
        self._prepare_request_for_portal(sign_request, send=False)
        token = signer._portal_ensure_token()

        self.authenticate(None, None)
        response = self.url_open(f"/my/sign/{signer.id}?access_token={token}", allow_redirects=False)
        self.assertEqual(response.status_code, 303)

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        preview_response = self.url_open(f"/my/sign/{signer.id}/preview", allow_redirects=False)
        self.assertEqual(preview_response.status_code, 200)
        self.assertIn('Preview Mode', preview_response.text)

        signer.invalidate_recordset(['state', 'last_opened_at'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.last_opened_at)
        self.assertEqual(sign_request.status, 'versioned')
        self.assertEqual(sign_request.lock_version, 0)

    def test_jsonrpc_save_denies_public_without_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Public Deny',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/save",
            self._build_payload(revision=0),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'invalid_token')

    def test_jsonrpc_save_rejects_internal_without_partner_binding(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Internal Deny',
            owner=self.open_sign_user,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/save",
            self._build_payload(
                revision=0,
                values=[{'field_id': text_field.id, 'value': 'Signed'}],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'invalid_token')

    def test_jsonrpc_save_accepts_internal_partner_binding(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Internal Allow',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/save",
            self._build_payload(
                revision=0,
                values=[{'field_id': text_field.id, 'value': '  Portal Value  '}],
            ),
        )
        self.assertTrue(response['ok'])
        self.assertEqual(response['state'], 'in_progress')
        self.assertEqual(response['request_revision'], 1)

        request_value = self.env['open.sign.request.value'].search([
            ('request_id', '=', bundle['request'].id),
            ('signer_id', '=', bundle['signer'].id),
            ('template_field_id', '=', text_field.id),
        ], limit=1)
        self.assertEqual(request_value.value_text, 'Portal Value')
        self.assertTrue(request_value.is_valid)

    def test_jsonrpc_save_invalid_field_rolls_back_session_open(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Rollback',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/save",
            self._build_payload(
                revision=0,
                values=[{'field_id': 999999, 'value': 'Portal Value'}],
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.last_opened_at)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(sign_request.value_ids)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', 'in', ('signer_opened', 'value_saved')),
        ]))

    def test_jsonrpc_save_stale_revision(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Stale',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/save",
            self._build_payload(
                revision=99,
                values=[{'field_id': text_field.id, 'value': 'Portal Value'}],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'stale_revision')

    def test_jsonrpc_save_lock_conflict_returns_request_locked(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Lock',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            response = self.make_jsonrpc_request(
                f"/my/sign/{bundle['signer'].id}/save",
                self._build_payload(
                    revision=0,
                    values=[{'field_id': text_field.id, 'value': 'Portal Value'}],
                ),
            )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'request_locked')

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.last_opened_at)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(sign_request.value_ids)

    def test_jsonrpc_submit_requires_consent(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Submit Consent',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/submit",
            self._build_payload(
                revision=0,
                values=[{'field_id': text_field.id, 'value': 'Portal Value'}],
                consent={'accepted': False, 'text_hash': 'x' * 64, 'timezone': 'UTC'},
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'consent_required')

    def test_jsonrpc_submit_rejects_consent_hash_mismatch(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Submit Hash',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/submit",
            self._build_payload(
                revision=0,
                values=[{'field_id': text_field.id, 'value': 'Portal Value'}],
                consent={'accepted': True, 'text_hash': '0' * 64, 'timezone': 'UTC'},
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.last_opened_at)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(sign_request.value_ids)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', 'in', ('signer_opened', 'signer_submitted')),
        ]))

    def test_jsonrpc_submit_missing_required_field_rolls_back_session_open(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Submit Required Rollback',
            owner=self.open_sign_user,
        )
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        preview_response = self.url_open(f"/my/sign/{bundle['signer'].id}/preview", allow_redirects=False)
        self.assertEqual(preview_response.status_code, 200)
        consent_hash_match = CONSENT_HASH_RE.search(preview_response.text or '')
        self.assertTrue(consent_hash_match)
        consent_hash = consent_hash_match.group(1)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/submit",
            self._build_payload(
                revision=0,
                values=[],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.last_opened_at)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(sign_request.value_ids)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', 'in', ('signer_opened', 'signer_submitted')),
        ]))

    def test_jsonrpc_submit_signing_order_blocked(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Ordered Submit',
            owner=self.open_sign_user,
            second_signer_partner=self.open_sign_user.partner_id,
        )

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_second'].id}/submit",
            self._build_payload(
                revision=0,
                values=[{'field_id': bundle['field_second'].id, 'value': 'Second Value'}],
                consent={'accepted': True, 'text_hash': '0' * 64, 'timezone': 'UTC'},
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'signing_order_blocked')

        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id
        self.assertEqual(signer_second.state, 'pending')
        self.assertFalse(signer_second.last_opened_at)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(sign_request.value_ids)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', 'in', ('signer_opened', 'signer_submitted')),
        ]))

    def test_ordered_waiting_signer_page_is_readonly_and_non_mutating(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Ordered Waiting Page',
            owner=self.open_sign_user,
        )
        self._assert_waiting_page_is_non_mutating(bundle)

    def test_ordered_waiting_signer_save_is_blocked(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Ordered Waiting Save',
            owner=self.open_sign_user,
        )

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_second'].id}/save",
            self._build_payload(
                revision=0,
                values=[{'field_id': bundle['field_second'].id, 'value': 'Second Value'}],
                access_token=bundle['token_second'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'signing_order_blocked')
        self.assertEqual(
            response['message'],
            'This request uses sequential signing. Another signer must complete before your turn begins. Refresh this page later.',
        )

        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id
        self.assertEqual(signer_second.state, 'pending')
        self.assertFalse(signer_second.last_opened_at)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(sign_request.value_ids)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', 'in', ('signer_opened', 'value_saved')),
        ]))

    def test_ordered_waiting_signer_stale_revision_wins_over_order_block(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Ordered Waiting Stale',
            owner=self.open_sign_user,
        )

        self.authenticate(None, None)
        waiting_response = self.url_open(
            f"/my/sign/{bundle['signer_second'].id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(waiting_response.status_code, 200)
        stale_revision = bundle['request'].lock_version

        opener_response = self.url_open(
            f"/my/sign/{bundle['signer_first'].id}?access_token={bundle['token_first']}",
            allow_redirects=False,
        )
        self.assertEqual(opener_response.status_code, 200)

        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_second'].id}/save",
            self._build_payload(
                revision=stale_revision,
                values=[{'field_id': bundle['field_second'].id, 'value': 'Second Value'}],
                access_token=bundle['token_second'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'stale_revision')

        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id
        self.assertEqual(signer_second.state, 'pending')
        self.assertFalse(signer_second.last_opened_at)
        self.assertEqual(sign_request.status, 'opened')
        self.assertEqual(sign_request.lock_version, 1)
        self.assertFalse(sign_request.value_ids.filtered(lambda value: value.signer_id == signer_second))
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'value_saved'),
        ]))

    def test_jsonrpc_submit_sets_signer_evidence_and_request_state(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Submit Success',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field, consent_hash, submit_response = self._submit_text_signer_successfully(bundle)
        self.assertTrue(submit_response['force_refresh'])
        self.assertIn('/my/sign/', submit_response['redirect_url'])

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        self.assertEqual(signer.state, 'signed')
        self.assertTrue(signer.signed_at)
        self.assertTrue(signer.consent_accepted_at)
        self.assertEqual(signer.consent_text_hash, consent_hash)
        self.assertEqual(signer.signer_timezone, 'UTC')
        self.assertEqual(sign_request.status, 'partially_signed')
        self.assertEqual(sign_request.lock_version, submit_response['request_revision'])
        self.assertTrue(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_submitted'),
        ]))

    def test_signed_signer_page_is_read_only(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Signed Readonly',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        self._submit_text_signer_successfully(bundle)

        readonly_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(readonly_response.status_code, 200)
        self.assertIn('Your submission has already been recorded. This session is read-only.', readonly_response.text)
        self.assertNotIn('o_open_sign_save', readonly_response.text)
        self.assertNotIn('o_open_sign_submit', readonly_response.text)
        self.assertNotIn('open_sign_consent', readonly_response.text)

    def test_signer_route_allows_completed_request_readonly_review(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Completed Review',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        self._transition_bundle_request_to_status(bundle, 'completed')
        self._assert_terminal_readonly_response(
            bundle,
            'This signing request has already been completed and is now read-only.',
        )

    def test_signer_route_allows_declined_request_readonly_review(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Declined Review',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'declined')
        self._assert_terminal_readonly_response(
            bundle,
            'This signing request has already been declined and is now read-only.',
        )

    def test_signer_route_allows_expired_request_readonly_review(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Expired Review',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'expired')
        self._assert_terminal_readonly_response(
            bundle,
            'This signing request has expired and is now read-only.',
        )

    def test_signed_signer_page_does_not_refresh_open_evidence(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Signed No Evidence Refresh',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        _, _consent_hash, submit_response = self._submit_text_signer_successfully(bundle)

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        last_opened_at = signer.last_opened_at
        ip_last = signer.ip_last
        lock_version = sign_request.lock_version
        signer_opened_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ])

        readonly_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(readonly_response.status_code, 200)

        signer.invalidate_recordset(['last_opened_at', 'ip_last', 'state'])
        sign_request.invalidate_recordset(['lock_version'])
        self.assertEqual(signer.last_opened_at, last_opened_at)
        self.assertEqual(signer.ip_last, ip_last)
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertEqual(sign_request.lock_version, submit_response['request_revision'])
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ]), signer_opened_count)

    def test_save_rejected_after_signer_submitted(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Denied After Submit',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field, _consent_hash, submit_response = self._submit_text_signer_successfully(bundle)

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        request_value = self.env['open.sign.request.value'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('template_field_id', '=', text_field.id),
        ], limit=1)
        self.assertEqual(request_value.value_text, 'Signed Value')
        value_saved_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'value_saved'),
        ])

        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/save",
            self._build_payload(
                revision=submit_response['request_revision'],
                values=[{'field_id': text_field.id, 'value': 'Tampered Value'}],
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing session is read-only because it has already been submitted.')

        request_value.invalidate_recordset(['value_text'])
        sign_request.invalidate_recordset(['lock_version'])
        self.assertEqual(request_value.value_text, 'Signed Value')
        self.assertEqual(sign_request.lock_version, submit_response['request_revision'])
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'value_saved'),
        ]), value_saved_count)

    def test_submit_rejected_after_signer_submitted(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Resubmit Denied',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field, consent_hash, submit_response = self._submit_text_signer_successfully(bundle)

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        request_value = self.env['open.sign.request.value'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('template_field_id', '=', text_field.id),
        ], limit=1)
        signed_at = signer.signed_at
        consent_accepted_at = signer.consent_accepted_at
        signer_submitted_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_submitted'),
        ])

        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/submit",
            self._build_payload(
                revision=submit_response['request_revision'],
                values=[{'field_id': text_field.id, 'value': 'Tampered Value'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing session is read-only because it has already been submitted.')

        signer.invalidate_recordset(['signed_at', 'consent_accepted_at'])
        request_value.invalidate_recordset(['value_text'])
        sign_request.invalidate_recordset(['lock_version'])
        self.assertEqual(request_value.value_text, 'Signed Value')
        self.assertEqual(signer.signed_at, signed_at)
        self.assertEqual(signer.consent_accepted_at, consent_accepted_at)
        self.assertEqual(sign_request.lock_version, submit_response['request_revision'])
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_submitted'),
        ]), signer_submitted_count)

    def test_ordered_waiting_signer_becomes_editable_after_prior_signer_submits(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Ordered Unlock Submit',
            owner=self.open_sign_user,
        )
        self._assert_waiting_page_is_non_mutating(bundle)
        self._submit_ordered_signer_successfully(bundle)

        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{signer_second.id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('This signer session is waiting for its turn.', response.text)
        self.assertIn('o_open_sign_save', response.text)
        self.assertIn('o_open_sign_submit', response.text)
        self.assertIn('open_sign_consent', response.text)

        signer_second.invalidate_recordset(['state', 'last_opened_at'])
        signer_second.request_id.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer_second.state, 'opened')
        self.assertTrue(signer_second.last_opened_at)
        self.assertEqual(signer_second.request_id.status, 'partially_signed')

    def test_ordered_waiting_signer_becomes_editable_after_prior_signer_declines(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Ordered Unlock Decline',
            owner=self.open_sign_user,
        )
        self._assert_waiting_page_is_non_mutating(bundle)

        signer_first = self.env['open.sign.request.signer'].browse(bundle['signer_first'].id)
        signer_first.write({'state': 'declined', 'declined_reason': 'Declined for test'})

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer_second'].id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('This signer session is waiting for its turn.', response.text)
        self.assertIn('o_open_sign_save', response.text)
        self.assertIn('o_open_sign_submit', response.text)
        self.assertIn('open_sign_consent', response.text)

    def test_ordered_waiting_signer_becomes_editable_after_prior_signer_expires(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Ordered Unlock Expire',
            owner=self.open_sign_user,
        )
        self._assert_waiting_page_is_non_mutating(bundle)

        signer_first = self.env['open.sign.request.signer'].browse(bundle['signer_first'].id)
        signer_first.write({'state': 'expired'})

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer_second'].id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('This signer session is waiting for its turn.', response.text)
        self.assertIn('o_open_sign_save', response.text)
        self.assertIn('o_open_sign_submit', response.text)
        self.assertIn('open_sign_consent', response.text)

    def test_ordered_same_sequence_wave_is_editable_for_all_wave_signers(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Ordered Same Wave',
            owner=self.open_sign_user,
            second_sequence=10,
        )

        self.authenticate(None, None)
        response_first = self.url_open(
            f"/my/sign/{bundle['signer_first'].id}?access_token={bundle['token_first']}",
            allow_redirects=False,
        )
        response_second = self.url_open(
            f"/my/sign/{bundle['signer_second'].id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response_first.status_code, 200)
        self.assertEqual(response_second.status_code, 200)
        self.assertNotIn('This signer session is waiting for its turn.', response_first.text)
        self.assertNotIn('This signer session is waiting for its turn.', response_second.text)
        self.assertIn('o_open_sign_save', response_first.text)
        self.assertIn('o_open_sign_submit', response_first.text)
        self.assertIn('o_open_sign_save', response_second.text)
        self.assertIn('o_open_sign_submit', response_second.text)

    def test_parallel_second_signer_page_is_editable_before_first_signs(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Parallel Editable Page',
            owner=self.open_sign_user,
            ordered_signing=False,
        )

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer_second'].id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('This signer session is waiting for its turn.', response.text)
        self.assertIn('o_open_sign_save', response.text)
        self.assertIn('o_open_sign_submit', response.text)
        self.assertIn('open_sign_consent', response.text)

    def test_parallel_second_signer_save_allowed_before_first_signs(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Parallel Save',
            owner=self.open_sign_user,
            ordered_signing=False,
        )

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_second'].id}/save",
            self._build_payload(
                revision=0,
                values=[{'field_id': bundle['field_second'].id, 'value': 'Parallel Save'}],
                access_token=bundle['token_second'],
            ),
        )
        self.assertTrue(response['ok'])

        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id
        request_value = sign_request.value_ids.filtered(
            lambda value: value.signer_id == signer_second and value.template_field_id == bundle['field_second']
        )[:1]
        self.assertEqual(sign_request.status, 'in_progress')
        self.assertEqual(sign_request.lock_version, response['request_revision'])
        self.assertEqual(request_value.value_text, 'Parallel Save')

    def test_parallel_second_signer_submit_allowed_before_first_signs(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Parallel Submit',
            owner=self.open_sign_user,
            ordered_signing=False,
        )

        field_second, _consent_hash, submit_response = self._submit_ordered_signer_successfully(
            bundle,
            signer_key='signer_second',
            field_key='field_second',
            token_key='token_second',
            value='Parallel Submit',
        )

        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id
        request_value = sign_request.value_ids.filtered(
            lambda value: value.signer_id == signer_second and value.template_field_id == field_second
        )[:1]
        self.assertEqual(signer_second.state, 'signed')
        self.assertEqual(sign_request.status, 'partially_signed')
        self.assertEqual(sign_request.lock_version, submit_response['request_revision'])
        self.assertEqual(request_value.value_text, 'Parallel Submit')

    def test_waiting_signer_document_access_still_allowed(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Waiting Document Access',
            owner=self.open_sign_user,
        )

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer_second'].id}/document?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.headers.get('content-type'))

    def test_jsonrpc_submit_blocks_required_signature_field(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Signature Block',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
            with_required_signature=True,
        )

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        page_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)

        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/submit",
            self._build_payload(
                revision=revision,
                values=[],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')

    def test_document_route_returns_pdf_and_denies_invalid_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Document Route',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        self.authenticate(None, None)
        ok_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}/document?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(ok_response.status_code, 200)
        self.assertIn('application/pdf', ok_response.headers.get('content-type'))

        denied_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}/document?access_token=bad-token",
            allow_redirects=False,
        )
        self.assertEqual(denied_response.status_code, 303)

    def test_document_route_allows_completed_readonly_signer_access(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Completed Document',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        self._transition_bundle_request_to_status(bundle, 'completed')
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}/document?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.headers.get('content-type'))

    def test_document_route_allows_declined_readonly_signer_access(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Declined Document',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'declined')
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}/document?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.headers.get('content-type'))

    def test_document_route_allows_expired_readonly_signer_access(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Expired Document',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'expired')
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}/document?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.headers.get('content-type'))

    def test_repeated_open_refreshes_evidence_without_duplicate_open_audit(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Repeat Open',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        first_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(first_response.status_code, 200)

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_opened_at = fields.Datetime.now() - timedelta(hours=1)
        signer.sudo().write({
            'last_opened_at': old_opened_at,
            'ip_last': '10.0.0.1',
        })

        second_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(second_response.status_code, 200)

        signer.invalidate_recordset(['last_opened_at', 'ip_last', 'state'])
        sign_request = signer.request_id
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'opened')
        self.assertEqual(sign_request.status, 'opened')
        self.assertEqual(sign_request.lock_version, 1)
        self.assertGreater(signer.last_opened_at, old_opened_at)
        self.assertNotEqual(signer.ip_last, '10.0.0.1')
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ]), 1)

    def test_portal_uses_snapshot_contract_after_live_template_edits(self):
        template = self._create_template(self.env, 'Portal Snapshot Contract')
        role = self._create_role(self.env, template, 'Snapshot Signer', 10)
        selection_field = self._create_field(
            self.env,
            template,
            role,
            type='selection',
            label='Plan',
            required=True,
            option_ids=[
                Command.create({'value': 'basic', 'label': 'Basic', 'sequence': 10, 'is_default': True}),
                Command.create({'value': 'pro', 'label': 'Pro', 'sequence': 20, 'is_default': False}),
            ],
        )
        sign_request = self._create_request(self.env, template, owner=self.open_sign_user)
        signer = self._create_signer(
            self.env,
            sign_request,
            role,
            email='snapshot.signer@example.com',
            sequence=10,
            partner=self.open_sign_user.partner_id,
        )
        self._prepare_request_for_portal(sign_request)
        token = signer._portal_ensure_token()

        selection_field.write({'label': 'Live Plan'})
        selection_field.option_ids.filtered(lambda option: option.value == 'basic').write({
            'value': 'enterprise',
            'label': 'Enterprise',
        })
        selection_field.option_ids.filtered(lambda option: option.value == 'pro').write({
            'value': 'team',
            'label': 'Team',
        })

        self.authenticate(None, None)
        page_response = self.url_open(f"/my/sign/{signer.id}?access_token={token}", allow_redirects=False)
        self.assertEqual(page_response.status_code, 200)
        self.assertIn('Plan', page_response.text)
        self.assertIn('Basic', page_response.text)
        self.assertNotIn('Live Plan', page_response.text)
        self.assertNotIn('Enterprise', page_response.text)

        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        submit_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=revision,
                values=[{'field_id': selection_field.id, 'value': 'basic'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=token,
            ),
        )
        self.assertTrue(submit_response['ok'])

        request_value = self.env['open.sign.request.value'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('template_field_id', '=', selection_field.id),
        ], limit=1)
        self.assertEqual(request_value.value_text, 'basic')

    def test_portal_rejects_field_from_another_signer_role(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Snapshot Role Guard',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_first'].id}/save",
            self._build_payload(
                revision=0,
                values=[{'field_id': bundle['field_second'].id, 'value': 'Invalid'}],
                access_token=bundle['token_first'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')

        signer = self.env['open.sign.request.signer'].browse(bundle['signer_first'].id)
        sign_request = signer.request_id
        self.assertEqual(signer.state, 'pending')
        self.assertEqual(sign_request.status, 'sent')
        self.assertFalse(sign_request.value_ids)

    def test_portal_resolves_legacy_snapshot_without_ids(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Legacy Snapshot',
            owner=self.open_sign_user,
        )
        sign_request = bundle['request']
        template_version = sign_request.template_version_id
        field_snapshot = [
            {
                key: value
                for key, value in snapshot.items()
                if key != 'template_field_id'
            }
            for snapshot in template_version.field_snapshot_json
        ]
        role_snapshot = [
            {
                key: value
                for key, value in snapshot.items()
                if key != 'role_id'
            }
            for snapshot in template_version.role_snapshot_json
        ]
        template_version.sudo().with_context(open_sign_allow_template_version_mutation=True).write({
            'field_snapshot_json': field_snapshot,
            'role_snapshot_json': role_snapshot,
        })

        text_field = bundle['template'].field_ids.filtered(lambda field: field.type == 'text')[:1]
        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/save",
            self._build_payload(
                revision=0,
                values=[{'field_id': text_field.id, 'value': 'Legacy Value'}],
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(response['ok'])

    def test_portal_fails_closed_for_unresolvable_legacy_snapshot(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Broken Snapshot',
            owner=self.open_sign_user,
        )
        sign_request = bundle['request']
        template_version = sign_request.template_version_id
        broken_snapshot = []
        for snapshot in template_version.field_snapshot_json:
            updated_snapshot = {
                key: value
                for key, value in snapshot.items()
                if key != 'template_field_id'
            }
            updated_snapshot['label'] = 'Broken Snapshot Label'
            broken_snapshot.append(updated_snapshot)
        template_version.sudo().with_context(open_sign_allow_template_version_mutation=True).write({
            'field_snapshot_json': broken_snapshot,
        })

        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(page_response.status_code, 200)
        self.assertIn('This signing request definition is no longer available. Contact the sender.', page_response.text)

        text_field = bundle['template'].field_ids.filtered(lambda field: field.type == 'text')[:1]
        save_response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/save",
            self._build_payload(
                revision=0,
                values=[{'field_id': text_field.id, 'value': 'Broken'}],
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(save_response['ok'])
        self.assertEqual(save_response['error_code'], 'validation_error')
        self.assertIn('This signing request definition is no longer available. Contact the sender.', save_response['message'])

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'pending')
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)

    def test_optional_unsupported_field_value_is_preserved_across_save(self):
        template = self._create_template(self.env, 'Portal Unsupported Preserve')
        role = self._create_role(self.env, template, 'Unsupported Signer', 10)
        text_field = self._create_field(
            self.env,
            template,
            role,
            type='text',
            label='Visible Text',
            required=True,
            sequence=10,
        )
        signature_field = self._create_field(
            self.env,
            template,
            role,
            type='signature',
            label='Optional Signature',
            required=False,
            sequence=20,
        )
        sign_request = self._create_request(self.env, template, owner=self.open_sign_user)
        signer = self._create_signer(
            self.env,
            sign_request,
            role,
            email='unsupported.signer@example.com',
            sequence=10,
        )
        self._prepare_request_for_portal(sign_request)
        token = signer._portal_ensure_token()
        self.env['open.sign.request.value'].sudo().with_context(
            open_sign_trusted_portal_value_payload=True
        ).create({
            'request_id': sign_request.id,
            'template_field_id': signature_field.id,
            'signer_id': signer.id,
            'value_text': False,
            'value_json': {'signature': 'existing'},
            'signed_payload_attachment_id': False,
            'is_valid': True,
        })

        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={token}",
            allow_redirects=False,
        )
        self.assertEqual(page_response.status_code, 200)
        self.assertNotIn(f'data-field-id="{signature_field.id}"', page_response.text)
        self.assertIn('This field type is not supported on the portal yet.', page_response.text)

        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=revision,
                values=[{'field_id': text_field.id, 'value': 'Preserved'}],
                access_token=token,
            ),
        )
        self.assertTrue(save_response['ok'])

        signature_value = self.env['open.sign.request.value'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('template_field_id', '=', signature_field.id),
        ], limit=1)
        self.assertTrue(signature_value)
        self.assertEqual(signature_value.value_json, {'signature': 'existing'})

    def test_multiple_initials_fields_remain_editable_before_submit_and_lock_after_submit(self):
        template = self._create_template(self.env, 'Portal Initials Lock')
        role = self._create_role(self.env, template, 'Initials Signer', 10)
        primary_initials = self._create_field(
            self.env,
            template,
            role,
            type='initials',
            label='Primary Initials',
            required=True,
            sequence=10,
        )
        secondary_initials = self._create_field(
            self.env,
            template,
            role,
            type='initials',
            label='Secondary Initials',
            required=False,
            sequence=20,
        )
        sign_request = self._create_request(self.env, template, owner=self.open_sign_user)
        signer = self._create_signer(
            self.env,
            sign_request,
            role,
            email='initials.lock@example.com',
            sequence=10,
        )
        self._prepare_request_for_portal(sign_request)
        token = signer._portal_ensure_token()

        self.authenticate(None, None)
        first_save = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=0,
                values=[
                    {'field_id': primary_initials.id, 'value': 'ab'},
                    {'field_id': secondary_initials.id, 'value': 'cd'},
                ],
                access_token=token,
            ),
        )
        self.assertTrue(first_save['ok'])

        second_save = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=first_save['request_revision'],
                values=[{'field_id': secondary_initials.id, 'value': ''}],
                access_token=token,
            ),
        )
        self.assertTrue(second_save['ok'])

        primary_value = self.env['open.sign.request.value'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('template_field_id', '=', primary_initials.id),
        ], limit=1)
        secondary_value = self.env['open.sign.request.value'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('template_field_id', '=', secondary_initials.id),
        ], limit=1)
        self.assertEqual(primary_value.value_text, 'AB')
        self.assertFalse(secondary_value)

        page_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={token}",
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        submit_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=revision,
                values=[{'field_id': primary_initials.id, 'value': 'ab'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=token,
            ),
        )
        self.assertTrue(submit_response['ok'])

        locked_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=submit_response['request_revision'],
                values=[
                    {'field_id': primary_initials.id, 'value': 'zz'},
                    {'field_id': secondary_initials.id, 'value': 'ef'},
                ],
                access_token=token,
            ),
        )
        self.assertFalse(locked_response['ok'])
        self.assertEqual(locked_response['error_code'], 'validation_error')

        primary_value.invalidate_recordset(['value_text'])
        secondary_value = self.env['open.sign.request.value'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('template_field_id', '=', secondary_initials.id),
        ], limit=1)
        sign_request.invalidate_recordset(['lock_version'])
        self.assertEqual(primary_value.value_text, 'AB')
        self.assertFalse(secondary_value)
        self.assertEqual(sign_request.lock_version, submit_response['request_revision'])

    def test_save_rejected_on_completed_request_with_valid_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Completed Deny',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]
        sign_request = self._transition_bundle_request_to_status(bundle, 'completed')
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        request_value = sign_request.value_ids.filtered(
            lambda value: value.signer_id == signer and value.template_field_id == text_field
        )[:1]
        signer_opened_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=sign_request.lock_version,
                values=[{'field_id': text_field.id, 'value': 'Tampered Completed'}],
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing request has already been completed and is now read-only.')

        request_value.invalidate_recordset(['value_text'])
        sign_request.invalidate_recordset(['lock_version'])
        self.assertEqual(request_value.value_text, 'Signed Value')
        self.assertEqual(sign_request.lock_version, bundle['request'].lock_version)
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_opened'),
        ]), signer_opened_count)

    def test_save_rejected_on_declined_request_with_valid_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Declined Deny',
            owner=self.open_sign_user,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]
        sign_request = self._transition_bundle_request_to_status(bundle, 'declined')
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        lock_version = sign_request.lock_version

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=lock_version,
                values=[{'field_id': text_field.id, 'value': 'Tampered Declined'}],
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing request has already been declined and is now read-only.')

        sign_request.invalidate_recordset(['lock_version'])
        self.assertFalse(sign_request.value_ids)
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'value_saved'),
        ]))

    def test_save_rejected_on_expired_request_with_valid_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Save Expired Deny',
            owner=self.open_sign_user,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]
        sign_request = self._transition_bundle_request_to_status(bundle, 'expired')
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        lock_version = sign_request.lock_version

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=lock_version,
                values=[{'field_id': text_field.id, 'value': 'Tampered Expired'}],
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing request has expired and is now read-only.')

        sign_request.invalidate_recordset(['lock_version'])
        self.assertFalse(sign_request.value_ids)
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'value_saved'),
        ]))

    def test_submit_rejected_on_completed_request_with_valid_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Submit Completed Deny',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]
        sign_request = self._transition_bundle_request_to_status(bundle, 'completed')
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        request_value = sign_request.value_ids.filtered(
            lambda value: value.signer_id == signer and value.template_field_id == text_field
        )[:1]
        signer_submitted_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_submitted'),
        ])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=sign_request.lock_version,
                values=[{'field_id': text_field.id, 'value': 'Tampered Completed'}],
                consent={'accepted': True, 'text_hash': '0' * 64, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing request has already been completed and is now read-only.')

        request_value.invalidate_recordset(['value_text'])
        sign_request.invalidate_recordset(['lock_version'])
        self.assertEqual(request_value.value_text, 'Signed Value')
        self.assertEqual(sign_request.lock_version, bundle['request'].lock_version)
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_submitted'),
        ]), signer_submitted_count)

    def test_submit_rejected_on_declined_request_with_valid_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Submit Declined Deny',
            owner=self.open_sign_user,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]
        sign_request = self._transition_bundle_request_to_status(bundle, 'declined')
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        lock_version = sign_request.lock_version

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=lock_version,
                values=[{'field_id': text_field.id, 'value': 'Tampered Declined'}],
                consent={'accepted': True, 'text_hash': '0' * 64, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing request has already been declined and is now read-only.')

        sign_request.invalidate_recordset(['lock_version'])
        self.assertFalse(sign_request.value_ids)
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_submitted'),
        ]))

    def test_submit_rejected_on_expired_request_with_valid_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Submit Expired Deny',
            owner=self.open_sign_user,
        )
        text_field = bundle['request'].template_id.field_ids.filtered(lambda field: field.type == 'text')[:1]
        sign_request = self._transition_bundle_request_to_status(bundle, 'expired')
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        lock_version = sign_request.lock_version

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=lock_version,
                values=[{'field_id': text_field.id, 'value': 'Tampered Expired'}],
                consent={'accepted': True, 'text_hash': '0' * 64, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing request has expired and is now read-only.')

        sign_request.invalidate_recordset(['lock_version'])
        self.assertFalse(sign_request.value_ids)
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_submitted'),
        ]))

    def test_preview_route_allows_completed_historical_review(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Preview Completed',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        self._transition_bundle_request_to_status(bundle, 'completed')
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}/preview", allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Preview Mode', response.text)

    def test_preview_route_terminal_historical_review_is_non_mutating(self):
        for status in ('completed', 'declined', 'expired'):
            with self.subTest(status=status):
                bundle = self._create_portal_session(
                    self.env,
                    name=f'Portal Preview Non Mutating {status}',
                    owner=self.open_sign_user,
                    signer_partner=self.open_sign_user.partner_id if status == 'completed' else False,
                )
                self._transition_bundle_request_to_status(bundle, status)
                self._assert_terminal_preview_response_is_non_mutating(bundle)

    def test_preview_route_allows_declined_historical_review(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Preview Declined',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'declined')
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}/preview", allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Preview Mode', response.text)

    def test_preview_route_allows_expired_historical_review(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Preview Expired',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'expired')
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}/preview", allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Preview Mode', response.text)

    def test_signer_route_denies_cancelled_request(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Cancelled Route Deny',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'cancelled')
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def test_signer_route_denies_voided_request(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Voided Route Deny',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'voided')
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def test_preview_route_denies_cancelled_request(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Cancelled Preview Deny',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'cancelled')
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}/preview", allow_redirects=False)
        self.assertEqual(response.status_code, 303)

    def test_preview_route_denies_voided_request(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Voided Preview Deny',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'voided')
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}/preview", allow_redirects=False)
        self.assertEqual(response.status_code, 303)

    def test_document_route_denies_cancelled_request(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Cancelled Document Deny',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'cancelled')
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}/document?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def test_document_route_denies_voided_request(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Voided Document Deny',
            owner=self.open_sign_user,
        )
        self._transition_bundle_request_to_status(bundle, 'voided')
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}/document?access_token={bundle['token']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def test_jsonrpc_decline_accepts_valid_public_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Public Token',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='  I cannot approve these terms.  ',
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(response['ok'])
        self.assertTrue(response['force_refresh'])
        self.assertIn('declined=1', response['redirect_url'])

        signer.invalidate_recordset(['state', 'declined_reason', 'ip_last', 'last_opened_at'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'declined')
        self.assertEqual(signer.declined_reason, 'I cannot approve these terms.')
        self.assertTrue(signer.ip_last)
        self.assertFalse(signer.last_opened_at)
        self.assertEqual(sign_request.status, 'declined')
        self.assertEqual(sign_request.lock_version, response['request_revision'])

        decline_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_declined'),
        ], limit=1)
        self.assertTrue(decline_audit)
        self.assertEqual(decline_audit.metadata_json['reason'], 'I cannot approve these terms.')
        self.assertEqual(decline_audit.metadata_json['request_status_before'], 'sent')
        self.assertEqual(decline_audit.metadata_json['signer_state_before'], 'pending')

    def test_jsonrpc_decline_accepts_internal_partner_binding(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Internal Binding',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='Internal decline reason',
            ),
        )
        self.assertTrue(response['ok'])
        self.assertEqual(response['redirect_url'], f'/my/sign/{signer.id}?declined=1')

        signer.invalidate_recordset(['state', 'declined_reason'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'declined')
        self.assertEqual(signer.declined_reason, 'Internal decline reason')
        self.assertEqual(sign_request.status, 'declined')

    def test_jsonrpc_decline_denies_public_without_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Public Deny',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='Public without token',
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'invalid_token')

    def test_jsonrpc_decline_rejects_internal_without_partner_binding(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Internal Deny',
            owner=self.open_sign_user,
        )
        self.authenticate(self.open_sign_outsider.login, self.open_sign_outsider.login)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='Outsider decline',
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'invalid_token')

    def test_jsonrpc_decline_requires_reason(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Reason Required',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            {
                'idempotency_key': str(uuid4()),
                'request_revision': 0,
                'access_token': bundle['token'],
            },
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'Decline reason is required.')

        signer.invalidate_recordset(['state', 'declined_reason'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.declined_reason)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_declined'),
        ]))

    def test_jsonrpc_decline_rejects_blank_reason(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Blank Reason',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=0,
                reason=' \r\n\t ',
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'Decline reason is required.')

        signer.invalidate_recordset(['state', 'declined_reason'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.declined_reason)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)

    def test_jsonrpc_decline_rejects_reason_too_long(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Long Reason',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='a' * 4001,
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'Decline reason cannot exceed 4000 characters.')

        signer.invalidate_recordset(['state', 'declined_reason'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.declined_reason)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)

    def test_jsonrpc_decline_stale_revision(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Stale Revision',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/decline",
            self._build_decline_payload(
                revision=99,
                reason='Stale decline',
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'stale_revision')

    def test_jsonrpc_decline_lock_conflict_returns_request_locked(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Lock Conflict',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id

        self.authenticate(None, None)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/decline",
                self._build_decline_payload(
                    revision=0,
                    reason='Lock conflict',
                    access_token=bundle['token'],
                ),
            )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'request_locked')

        signer.invalidate_recordset(['state', 'declined_reason'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'pending')
        self.assertFalse(signer.declined_reason)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)

    def test_jsonrpc_decline_rejected_after_signer_submitted(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline After Submit',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        _text_field, _consent_hash, submit_response = self._submit_text_signer_successfully(bundle)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        signer_declined_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_declined'),
        ])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=submit_response['request_revision'],
                reason='Too late',
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'validation_error')
        self.assertEqual(response['message'], 'This signing session is read-only because it has already been submitted.')

        signer.invalidate_recordset(['state', 'declined_reason'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'signed')
        self.assertFalse(signer.declined_reason)
        self.assertEqual(sign_request.status, 'partially_signed')
        self.assertEqual(sign_request.lock_version, submit_response['request_revision'])
        self.assertEqual(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_declined'),
        ]), signer_declined_count)

    def test_jsonrpc_decline_rejected_on_terminal_request_with_valid_token(self):
        expected_messages = {
            'completed': 'This signing request has already been completed and is now read-only.',
            'declined': 'This signing request has already been declined and is now read-only.',
            'expired': 'This signing request has expired and is now read-only.',
        }
        for status, expected_message in expected_messages.items():
            with self.subTest(status=status):
                bundle = self._create_portal_session(
                    self.env,
                    name=f'Portal Decline Terminal {status}',
                    owner=self.open_sign_user,
                    signer_partner=self.open_sign_user.partner_id if status == 'completed' else False,
                )
                sign_request = self._transition_bundle_request_to_status(bundle, status)
                signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
                signer_declined_count = self.env['open.sign.audit.log'].search_count([
                    ('request_id', '=', sign_request.id),
                    ('signer_id', '=', signer.id),
                    ('event_type', '=', 'signer_declined'),
                ])

                self.authenticate(None, None)
                response = self.make_jsonrpc_request(
                    f"/my/sign/{signer.id}/decline",
                    self._build_decline_payload(
                        revision=sign_request.lock_version,
                        reason='Terminal decline attempt',
                        access_token=bundle['token'],
                    ),
                )
                self.assertFalse(response['ok'])
                self.assertEqual(response['error_code'], 'validation_error')
                self.assertEqual(response['message'], expected_message)

                signer.invalidate_recordset(['state', 'declined_reason'])
                sign_request.invalidate_recordset(['status', 'lock_version'])
                self.assertEqual(sign_request.status, status)
                self.assertEqual(self.env['open.sign.audit.log'].search_count([
                    ('request_id', '=', sign_request.id),
                    ('signer_id', '=', signer.id),
                    ('event_type', '=', 'signer_declined'),
                ]), signer_declined_count)

    def test_ordered_waiting_signer_decline_is_allowed(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Waiting Decline Allowed',
            owner=self.open_sign_user,
        )
        sign_request = self.env['open.sign.request'].browse(bundle['request'].id)
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        signer_first = self.env['open.sign.request.signer'].browse(bundle['signer_first'].id)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer_second.id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='Waiting signer decline',
                access_token=bundle['token_second'],
            ),
        )
        self.assertTrue(response['ok'])

        signer_second.invalidate_recordset(['state', 'declined_reason', 'last_opened_at'])
        signer_first.invalidate_recordset(['state'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer_second.state, 'declined')
        self.assertEqual(signer_second.declined_reason, 'Waiting signer decline')
        self.assertFalse(signer_second.last_opened_at)
        self.assertEqual(signer_first.state, 'pending')
        self.assertEqual(sign_request.status, 'declined')
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'signer_opened'),
        ]))
        self.assertTrue(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'signer_declined'),
        ]))

    def test_ordered_waiting_signer_decline_keeps_waiting_page_non_opening(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Waiting Decline Non Opening',
            owner=self.open_sign_user,
        )
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id

        self.authenticate(None, None)
        waiting_response = self.url_open(
            f"/my/sign/{signer_second.id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(waiting_response.status_code, 200)

        response = self.make_jsonrpc_request(
            f"/my/sign/{signer_second.id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='Waiting page decline',
                access_token=bundle['token_second'],
            ),
        )
        self.assertTrue(response['ok'])

        signer_second.invalidate_recordset(['state', 'declined_reason', 'last_opened_at', 'ip_last'])
        sign_request.invalidate_recordset(['status'])
        self.assertEqual(signer_second.state, 'declined')
        self.assertEqual(signer_second.declined_reason, 'Waiting page decline')
        self.assertFalse(signer_second.last_opened_at)
        self.assertTrue(signer_second.ip_last)
        self.assertEqual(sign_request.status, 'declined')
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'signer_opened'),
        ]))
        self.assertTrue(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'signer_declined'),
        ]))

    def test_parallel_signer_decline_is_allowed(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Parallel Decline',
            owner=self.open_sign_user,
            ordered_signing=False,
        )
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer_second.id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='Parallel signer decline',
                access_token=bundle['token_second'],
            ),
        )
        self.assertTrue(response['ok'])

        signer_second.invalidate_recordset(['state', 'declined_reason'])
        sign_request.invalidate_recordset(['status'])
        self.assertEqual(signer_second.state, 'declined')
        self.assertEqual(signer_second.declined_reason, 'Parallel signer decline')
        self.assertEqual(sign_request.status, 'declined')

    def test_declined_signer_page_shows_decline_success_and_reason(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Review Page',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        decline_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='  First line\r\nSecond line \r ',
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(decline_response['ok'])

        page_response = self.url_open(decline_response['redirect_url'], allow_redirects=False)
        self.assertEqual(page_response.status_code, 200)
        self.assertIn('Your decline was recorded.', page_response.text)
        self.assertIn('This signing request has already been declined and is now read-only.', page_response.text)
        self.assertIn('Decline Reason', page_response.text)
        self.assertIn('First line', page_response.text)
        self.assertIn('Second line', page_response.text)
        self.assertNotIn('Decline to Sign', page_response.text)

        signer.invalidate_recordset(['declined_reason'])
        self.assertEqual(signer.declined_reason, 'First line\nSecond line')

    def test_other_signer_page_after_request_declined_is_readonly(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Other Signer After Decline',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        decline_response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_first'].id}/decline",
            self._build_decline_payload(
                revision=0,
                reason='Declined by first signer',
                access_token=bundle['token_first'],
            ),
        )
        self.assertTrue(decline_response['ok'])

        response = self.url_open(
            f"/my/sign/{bundle['signer_second'].id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('This signing request has already been declined and is now read-only.', response.text)
        self.assertNotIn('o_open_sign_save', response.text)
        self.assertNotIn('o_open_sign_submit', response.text)
        self.assertNotIn('Decline to Sign', response.text)
        self.assertNotIn('Decline Reason', response.text)
        self.assertNotIn('Declined by first signer', response.text)

    def test_jsonrpc_otp_endpoints_require_payload_validation(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Payload Validation',
            owner=self.open_sign_user,
        )
        self.authenticate(None, None)
        request_response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/otp/request",
            {'access_token': bundle['token']},
        )
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer'].id}/otp/verify",
            {'access_token': bundle['token']},
        )
        self.assertFalse(request_response['ok'])
        self.assertFalse(verify_response['ok'])
        self.assertEqual(request_response['error_code'], 'validation_error')
        self.assertEqual(verify_response['error_code'], 'validation_error')
        self.assertEqual(request_response['message'], 'request_revision must be an integer.')
        self.assertEqual(verify_response['message'], 'request_revision must be an integer.')

    def test_jsonrpc_scaffold_endpoints_reject_terminal_requests_without_mutation(self):
        expected_messages = {
            'completed': 'This signing request has already been completed and is now read-only.',
            'declined': 'This signing request has already been declined and is now read-only.',
            'expired': 'This signing request has expired and is now read-only.',
        }
        for status, expected_message in expected_messages.items():
            for endpoint in ('otp/request', 'otp/verify'):
                with self.subTest(status=status, endpoint=endpoint):
                    bundle = self._create_portal_session(
                        self.env,
                        name=f'Portal Scaffold Terminal {status} {endpoint}',
                        owner=self.open_sign_user,
                        signer_partner=self.open_sign_user.partner_id if status == 'completed' else False,
                    )
                    self._transition_bundle_request_to_status(bundle, status)
                    self.authenticate(None, None)
                    payload = {
                        'access_token': bundle['token'],
                        'request_revision': bundle['request'].lock_version,
                    }
                    if endpoint == 'otp/verify':
                        payload['code'] = '123456'
                    self._assert_terminal_scaffold_endpoint_is_non_mutating(
                        bundle,
                        endpoint,
                        expected_message,
                        payload=payload,
                    )

    def test_submit_queues_invitation_for_newly_actionable_next_wave(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Next Wave Invite',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_first = self.env['open.sign.request.signer'].browse(bundle['signer_first'].id)
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_first.request_id
        mail_model = self.env['mail.mail'].sudo()
        second_mail_before = mail_model.search_count([('email_to', '=', signer_second.email)])

        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer_first.id}?access_token={bundle['token_first']}",
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer_first.id}/submit",
            self._build_payload(
                revision=revision,
                values=[{'field_id': bundle['field_first'].id, 'value': 'Wave one done'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle['token_first'],
            ),
        )

        self.assertTrue(response['ok'])
        sign_request.invalidate_recordset(['status'])
        self.assertEqual(sign_request.status, 'partially_signed')
        self.assertEqual(
            mail_model.search_count([('email_to', '=', signer_second.email)]),
            second_mail_before + 1,
        )

        queued_mail = mail_model.search([('email_to', '=', signer_second.email)], order='id desc', limit=1)
        self.assertIn(f"/my/sign/{signer_second.id}?access_token={bundle['token_second']}", queued_mail.body_html)
        notification_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'notification_queued'),
        ], order='id desc', limit=1)
        self.assertTrue(notification_audit)
        self.assertEqual(notification_audit.metadata_json['notification_type'], 'invitation')
        self.assertEqual(notification_audit.metadata_json['trigger'], 'wave_unblocked')

    def test_submit_preserves_success_when_next_wave_invitation_queue_fails(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Next Wave Invite Failure',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_first = self.env['open.sign.request.signer'].browse(bundle['signer_first'].id)
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_first.request_id
        mail_model = self.env['mail.mail'].sudo()
        second_mail_before = mail_model.search_count([('email_to', '=', signer_second.email)])

        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer_first.id}?access_token={bundle['token_first']}",
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.notification_service.queue_request_invitations',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ):
            response = self.make_jsonrpc_request(
                f"/my/sign/{signer_first.id}/submit",
                self._build_payload(
                    revision=revision,
                    values=[{'field_id': bundle['field_first'].id, 'value': 'Wave one done'}],
                    consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                    access_token=bundle['token_first'],
                ),
            )

        self.assertTrue(response['ok'])
        sign_request.invalidate_recordset(['status'])
        self.assertEqual(sign_request.status, 'partially_signed')
        self.assertEqual(
            mail_model.search_count([('email_to', '=', signer_second.email)]),
            second_mail_before,
        )
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'invitation')
        self.assertEqual(failure_audit.metadata_json['trigger'], 'wave_unblocked')
        self.assertEqual(failure_audit.metadata_json['failure_reason'], 'notification_service_error')
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_decline_queues_owner_only_notification(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Owner Notification',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        mail_model = self.env['mail.mail'].sudo()
        owner_mail_before = mail_model.search_count([('email_to', '=', self.open_sign_user.partner_id.email)])
        signer_mail_before = mail_model.search_count([('email_to', '=', signer.email)])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=sign_request.lock_version,
                reason='Owner notification decline',
                access_token=bundle['token'],
            ),
        )

        self.assertTrue(response['ok'])
        self.assertEqual(
            mail_model.search_count([('email_to', '=', self.open_sign_user.partner_id.email)]),
            owner_mail_before + 1,
        )
        self.assertEqual(
            mail_model.search_count([('email_to', '=', signer.email)]),
            signer_mail_before,
        )

        notification_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_queued'),
        ], order='id desc', limit=1)
        self.assertTrue(notification_audit)
        self.assertEqual(notification_audit.metadata_json['notification_type'], 'decline')
        self.assertEqual(notification_audit.metadata_json['recipient_kind'], 'owner')

    def test_decline_preserves_success_when_owner_notification_service_fails(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Decline Owner Notification Failure',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id

        self.authenticate(None, None)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.notification_service.queue_request_decline_notification',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ):
            response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/decline",
                self._build_decline_payload(
                    revision=sign_request.lock_version,
                    reason='Decline with wrapper failure',
                    access_token=bundle['token'],
                ),
            )

        self.assertTrue(response['ok'])
        sign_request.invalidate_recordset(['status'])
        self.assertEqual(sign_request.status, 'declined')
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'decline')
        self.assertEqual(failure_audit.metadata_json['trigger'], 'request_declined')
        self.assertEqual(failure_audit.metadata_json['failure_reason'], 'notification_service_error')
        self._assert_no_url_or_token_leak(failure_audit.metadata_json)

    def test_manual_resend_rotation_invalidates_old_portal_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Manual Resend Token Rotation',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_token = bundle['token']

        wizard = self.env['open.sign.signer.contact_correction.wizard'].with_user(self.open_sign_manager).create({
            'signer_id': signer.id,
            'target_email': signer.email,
            'reason': 'Rotate token after manual resend',
        })
        wizard.action_apply_contact_correction()

        signer.invalidate_recordset(['access_token'])
        self.assertNotEqual(signer.access_token, old_token)

        self.authenticate(None, None)
        old_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={old_token}",
            allow_redirects=False,
        )
        new_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={signer.access_token}",
            allow_redirects=False,
        )
        self.assertEqual(old_response.status_code, 303)
        self.assertEqual(new_response.status_code, 200)
