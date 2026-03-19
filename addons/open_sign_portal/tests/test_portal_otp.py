# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from odoo import fields
from odoo.addons.open_sign.services import notification_service
from odoo.addons.open_sign_portal.services import otp_service
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.open_sign_portal.tests.common import (
    CONSENT_HASH_RE,
    REQUEST_REVISION_RE,
    OpenSignPortalTestMixin,
)


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalOtp(TransactionCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_otp_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_otp_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.otp.user@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.otp.manager@example.com'

    def test_otp_required_is_frozen_after_versioned(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Frozen',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        with self.assertRaises(ValidationError):
            signer.with_user(self.open_sign_user).write({'otp_required': True})

    def test_otp_verified_at_is_server_managed(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Verified Field',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        with self.assertRaises(ValidationError):
            signer.with_user(self.open_sign_user).write({'otp_verified_at': fields.Datetime.now()})

    def test_one_active_challenge_per_signer(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Active Challenge',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        now = fields.Datetime.now()
        with patch(
            'odoo.addons.open_sign.services.notification_service.queue_request_otp_notification',
            return_value=1,
        ), patch(
            'odoo.addons.open_sign_portal.services.otp_service.generate_otp_code',
            return_value='123456',
        ):
            otp_service.request_otp_challenge(signer, trigger='otp_request')
        with self.assertRaises(ValidationError):
            self.env['open.sign.otp.challenge'].sudo().create({
                'request_signer_id': signer.id,
                'requested_at': now,
                'expires_at': now + timedelta(minutes=10),
                'attempt_count': 0,
                'code_salt': 'ab' * 16,
                'code_hash': '0' * 64,
            })

    def test_code_hash_never_equals_raw_code(self):
        code = '123456'
        salt = 'ab' * 16
        code_hash = otp_service.hash_otp_code(code, salt)
        self.assertEqual(len(code_hash), 64)
        self.assertNotEqual(code_hash, code)

    def test_token_rotation_invalidates_active_otp_state_on_manual_resend(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Rotation Reset',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        with patch(
            'odoo.addons.open_sign.services.notification_service.queue_request_otp_notification',
            return_value=1,
        ), patch(
            'odoo.addons.open_sign_portal.services.otp_service.generate_otp_code',
            return_value='123456',
        ):
            otp_service.request_otp_challenge(signer, trigger='otp_request')
        self.assertTrue(otp_service.get_active_challenge(signer))

        wizard = self.env['open.sign.signer.contact_correction.wizard'].with_user(self.open_sign_manager).create({
            'signer_id': signer.id,
            'target_email': signer.email,
            'reason': 'Rotate token after OTP request',
        })
        wizard.action_apply_contact_correction()

        self.assertFalse(otp_service.get_active_challenge(signer))

    def test_otp_challenge_model_has_no_user_acl_surface(self):
        with self.assertRaises(AccessError):
            self.env['open.sign.otp.challenge'].with_user(self.open_sign_user).check_access('read')


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalOtpHttp(HttpCase, OpenSignPortalTestMixin):

    OTP_CODE = '123456'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_otp_http_user',
            password='open_sign_portal_otp_http_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_outsider = new_test_user(
            cls.env,
            login='open_sign_portal_otp_http_outsider',
            password='open_sign_portal_otp_http_outsider',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_same_email = new_test_user(
            cls.env,
            login='open_sign_portal_otp_http_same_email',
            password='open_sign_portal_otp_http_same_email',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_otp_http_manager',
            password='open_sign_portal_otp_http_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.otp.http.user@example.com'
        cls.open_sign_outsider.partner_id.email = 'open.sign.portal.otp.http.outsider@example.com'
        cls.open_sign_same_email.partner_id.email = 'open.sign.portal.otp.http.same.email@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.otp.http.manager@example.com'

    def _build_save_payload(self, *, revision, field_id, value, access_token=False):
        payload = {
            'idempotency_key': str(uuid4()),
            'request_revision': revision,
            'values': [{'field_id': field_id, 'value': value}],
        }
        if access_token:
            payload['access_token'] = access_token
        return payload

    def _build_submit_payload(self, *, revision, field_id, value, consent_hash, access_token=False):
        payload = self._build_save_payload(
            revision=revision,
            field_id=field_id,
            value=value,
            access_token=access_token,
        )
        payload['consent'] = {
            'accepted': True,
            'text_hash': consent_hash,
            'timezone': 'UTC',
        }
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

    def _build_otp_request_payload(self, *, revision, access_token=False):
        payload = {'request_revision': revision}
        if access_token:
            payload['access_token'] = access_token
        return payload

    def _build_otp_verify_payload(self, *, revision, code, access_token=False):
        payload = {
            'request_revision': revision,
            'code': code,
        }
        if access_token:
            payload['access_token'] = access_token
        return payload

    def _extract_consent_hash_and_revision(self, html):
        consent_match = CONSENT_HASH_RE.search(html)
        revision_match = REQUEST_REVISION_RE.search(html)
        self.assertTrue(consent_match)
        self.assertTrue(revision_match)
        return consent_match.group(1), int(revision_match.group(1))

    def _get_text_field_for_signer(self, signer):
        return signer.request_id.template_id.field_ids.filtered(
            lambda field: field.role_id == signer.role_id and field.type == 'text'
        )[:1]

    def _open_page_and_extract(self, signer_id, token=False):
        url = f'/my/sign/{signer_id}'
        if token:
            url = f'{url}?access_token={token}'
        response = self.url_open(url, allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        consent_hash, revision = self._extract_consent_hash_and_revision(response.text)
        return response, consent_hash, revision

    def _latest_notification_failure(self, sign_request, *, notification_type):
        return self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1).filtered(lambda audit: audit.metadata_json.get('notification_type') == notification_type)

    def _set_same_email_user_email(self, signer):
        self.open_sign_same_email.partner_id.write({'email': signer.email})

    def _expire_signer_token(self, signer):
        signer.sudo().write({'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1)})
        signer.invalidate_recordset(['email_token_expires_at'])

    def test_portal_page_shows_otp_panel_when_required(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Panel Required',
            owner=self.open_sign_user,
            otp_required=True,
        )
        self.authenticate(None, None)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}", allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Email Verification', response.text)
        self.assertIn('Send verification code', response.text)
        self.assertIn('Verify code', response.text)
        self.assertIn('Email verification is required before submit.', response.text)

    def test_portal_page_does_not_show_otp_panel_for_non_required_signer(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Panel Optional',
            owner=self.open_sign_user,
            otp_required=False,
        )
        self.authenticate(None, None)
        response = self.url_open(f"/my/sign/{bundle['signer'].id}?access_token={bundle['token']}", allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Email Verification', response.text)

    def test_waiting_page_hides_otp_controls(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal OTP Waiting Hidden',
            owner=self.open_sign_user,
            ordered_signing=True,
            second_otp_required=True,
        )
        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer_second'].id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('waiting for its turn', response.text)
        self.assertNotIn('Email Verification', response.text)
        self.assertNotIn('Send verification code', response.text)

    def test_otp_request_queues_code_for_required_signer(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Request',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])

        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            rpc_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )

        self.assertTrue(rpc_response['ok'])
        self.assertTrue(rpc_response['force_refresh'])
        self.assertIn('otp_requested=1', rpc_response['redirect_url'])
        challenge = self.env['open.sign.otp.challenge'].search([
            ('request_signer_id', '=', signer.id),
        ], order='id desc', limit=1)
        self.assertTrue(challenge)
        self.assertFalse(challenge.verified_at)
        self.assertNotEqual(challenge.code_hash, self.OTP_CODE)

        mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertTrue(mail)
        self.assertIn(self.OTP_CODE, mail.body_html)
        self.assertNotIn('/my/sign/', mail.body_html)
        self.assertNotIn('access_token=', mail.body_html)

    def test_submit_requires_otp_when_otp_required(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Submit Gate',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)

        self.authenticate(None, None)
        _response, consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        rpc_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_submit_payload(
                revision=revision,
                field_id=field.id,
                value='Needs OTP',
                consent_hash=consent_hash,
                access_token=bundle['token'],
            ),
        )
        self.assertFalse(rpc_response['ok'])
        self.assertEqual(rpc_response['error_code'], 'validation_error')
        self.assertEqual(rpc_response['message'], 'Email verification is required before submit.')

    def test_otp_verify_success_enables_submit(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Verify Success',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(
                revision=request_response['request_revision'],
                code=self.OTP_CODE,
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(verify_response['ok'])
        self.assertTrue(verify_response['otp_verified'])
        signer.invalidate_recordset(['otp_verified_at'])
        self.assertTrue(signer.otp_verified_at)

        page_response = self.url_open(verify_response['redirect_url'], allow_redirects=False)
        self.assertEqual(page_response.status_code, 200)
        self.assertIn('Email verification complete.', page_response.text)
        self.assertNotIn('Send verification code', page_response.text)

    def test_submit_succeeds_after_otp_verified(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Submit Success',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)

        self.authenticate(None, None)
        _response, consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(
                revision=request_response['request_revision'],
                code=self.OTP_CODE,
                access_token=bundle['token'],
            ),
        )
        submit_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_submit_payload(
                revision=verify_response['request_revision'],
                field_id=field.id,
                value='Verified submit',
                consent_hash=consent_hash,
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(submit_response['ok'])
        signer.invalidate_recordset(['state'])
        self.assertEqual(signer.state, 'signed')

    def test_save_allowed_before_otp_verified(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Save Allowed',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)

        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_save_payload(
                revision=revision,
                field_id=field.id,
                value='Draft before OTP',
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(save_response['ok'])

    def test_decline_allowed_before_otp_verified(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Decline Allowed',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        decline_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=revision,
                reason='Declining without OTP',
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(decline_response['ok'])
        signer.invalidate_recordset(['state'])
        self.assertEqual(signer.state, 'declined')

    def test_waiting_signer_cannot_request_otp(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal OTP Waiting Request',
            owner=self.open_sign_user,
            ordered_signing=True,
            second_otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        self.authenticate(None, None)
        revision = signer.request_id.lock_version
        request_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(revision=revision, access_token=bundle['token_second']),
        )
        self.assertFalse(request_response['ok'])
        self.assertEqual(request_response['error_code'], 'signing_order_blocked')

    def test_waiting_signer_cannot_verify_otp(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal OTP Waiting Verify',
            owner=self.open_sign_user,
            ordered_signing=True,
            second_otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        self.env['open.sign.otp.challenge'].sudo().create({
            'request_signer_id': signer.id,
            'requested_at': fields.Datetime.now(),
            'expires_at': fields.Datetime.now() + timedelta(minutes=10),
            'attempt_count': 0,
            'code_salt': 'cd' * 16,
            'code_hash': otp_service.hash_otp_code(self.OTP_CODE, 'cd' * 16),
        })
        self.authenticate(None, None)
        revision = signer.request_id.lock_version
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(
                revision=revision,
                code=self.OTP_CODE,
                access_token=bundle['token_second'],
            ),
        )
        self.assertFalse(verify_response['ok'])
        self.assertEqual(verify_response['error_code'], 'signing_order_blocked')

    def test_waiting_signer_still_can_decline_with_otp_required(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal OTP Waiting Decline',
            owner=self.open_sign_user,
            ordered_signing=True,
            second_otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        self.authenticate(None, None)
        revision = signer.request_id.lock_version
        decline_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=revision,
                reason='Declining while waiting with OTP',
                access_token=bundle['token_second'],
            ),
        )
        self.assertTrue(decline_response['ok'])

    def test_otp_request_denies_wrong_token(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Wrong Token Request', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        wrong_token = self._mutate_token(bundle['token'])
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        request_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(revision=revision, access_token=wrong_token),
        )
        self.assertFalse(request_response['ok'])
        self.assertEqual(request_response['error_code'], 'invalid_token')
        self._assert_no_url_or_token_leak(request_response, wrong_token)

    def test_internal_exact_partner_can_request_and_verify_without_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Internal Partner',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id)
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision),
            )
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(revision=request_response['request_revision'], code=self.OTP_CODE),
        )
        self.assertTrue(request_response['ok'])
        self.assertTrue(verify_response['ok'])

    def test_internal_exact_partner_can_request_and_verify_with_wrong_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Internal Partner Wrong Token',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id)
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=wrong_token),
            )
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(revision=request_response['request_revision'], code=self.OTP_CODE, access_token=wrong_token),
        )
        self.assertTrue(request_response['ok'])
        self.assertTrue(verify_response['ok'])

    def test_internal_mismatched_partner_denied_on_otp_routes(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Internal Mismatch',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(self.open_sign_outsider.login, self.open_sign_outsider.login)
        request_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(revision=signer.request_id.lock_version),
        )
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(revision=signer.request_id.lock_version, code=self.OTP_CODE),
        )
        self.assertFalse(request_response['ok'])
        self.assertFalse(verify_response['ok'])
        self.assertEqual(request_response['error_code'], 'invalid_token')
        self.assertEqual(verify_response['error_code'], 'invalid_token')

    def test_email_only_signer_same_email_user_denied_on_otp_routes_without_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Same Email Deny',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self._set_same_email_user_email(signer)

        self.authenticate(self.open_sign_same_email.login, self.open_sign_same_email.login)
        request_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(revision=signer.request_id.lock_version),
        )
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(revision=signer.request_id.lock_version, code=self.OTP_CODE),
        )
        self.assertFalse(request_response['ok'])
        self.assertFalse(verify_response['ok'])
        self.assertEqual(request_response['error_code'], 'invalid_token')
        self.assertEqual(verify_response['error_code'], 'invalid_token')

    def test_otp_request_returns_expired_token_for_expired_current_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Expired Request',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self._expire_signer_token(signer)

        self.authenticate(None, None)
        request_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(revision=signer.request_id.lock_version, access_token=bundle['token']),
        )
        self.assertFalse(request_response['ok'])
        self.assertEqual(request_response['error_code'], 'expired_token')

    def test_otp_verify_returns_expired_token_for_expired_current_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Expired Verify',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self._expire_signer_token(signer)

        self.authenticate(None, None)
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(revision=signer.request_id.lock_version, code=self.OTP_CODE, access_token=bundle['token']),
        )
        self.assertFalse(verify_response['ok'])
        self.assertEqual(verify_response['error_code'], 'expired_token')

    def test_exact_partner_internal_otp_verify_redirect_omits_access_token_after_fallback(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal OTP Internal Fallback Redirect',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id)
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=wrong_token),
            )
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(
                revision=request_response['request_revision'],
                code=self.OTP_CODE,
                access_token=wrong_token,
            ),
        )
        self.assertTrue(verify_response['ok'])
        self.assertEqual(verify_response['redirect_url'], f'/my/sign/{signer.id}?otp_verified=1')
        self.assertNotIn('access_token=', verify_response['redirect_url'])

    def test_otp_request_enforces_60_second_cooldown(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Cooldown', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            first_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )
        second_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(revision=first_response['request_revision'], access_token=bundle['token']),
        )
        self.assertTrue(first_response['ok'])
        self.assertFalse(second_response['ok'])
        self.assertEqual(second_response['error_code'], 'validation_error')
        self.assertEqual(second_response['message'], 'Please wait before requesting another verification code.')

    def test_second_allowed_otp_request_rotates_old_code(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Rotate Code', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', side_effect=['111111', '222222']):
            first_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )
            challenge = otp_service.get_active_challenge(signer)
            challenge.sudo().write({'requested_at': fields.Datetime.now() - timedelta(seconds=61)})
            second_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=first_response['request_revision'], access_token=bundle['token']),
            )
        self.assertTrue(second_response['ok'])
        active_challenge = otp_service.get_active_challenge(signer)
        self.assertTrue(active_challenge)
        self.assertTrue(otp_service.verify_otp_code(active_challenge, '222222'))
        self.assertFalse(otp_service.verify_otp_code(active_challenge, '111111'))

    def test_old_code_fails_after_rotated_new_request(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Old Code Fails', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', side_effect=['111111', '222222']):
            first_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )
            first_challenge = otp_service.get_active_challenge(signer)
            first_challenge.sudo().write({'requested_at': fields.Datetime.now() - timedelta(seconds=61)})
            second_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=first_response['request_revision'], access_token=bundle['token']),
            )
        verify_old = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(revision=second_response['request_revision'], code='111111', access_token=bundle['token']),
        )
        self.assertFalse(verify_old['ok'])
        self.assertEqual(verify_old['error_code'], 'validation_error')
        self.assertEqual(verify_old['message'], 'The verification code is invalid.')

    def test_expired_code_is_rejected(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Expired', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )
        challenge = otp_service.get_active_challenge(signer)
        challenge.sudo().write({'expires_at': fields.Datetime.now() - timedelta(minutes=1)})
        verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(revision=request_response['request_revision'], code=self.OTP_CODE, access_token=bundle['token']),
        )
        self.assertFalse(verify_response['ok'])
        self.assertEqual(verify_response['message'], 'The verification code has expired. Request a new code.')

    def test_attempt_limit_reached_then_new_request_required(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Attempt Limit', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )
        verify_response = False
        for _index in range(otp_service.OTP_MAX_ATTEMPTS):
            verify_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/verify",
                self._build_otp_verify_payload(revision=request_response['request_revision'], code='999999', access_token=bundle['token']),
            )
        self.assertFalse(verify_response['ok'])
        self.assertEqual(verify_response['message'], 'Too many invalid verification attempts. Request a new code.')

    def test_otp_request_mail_queue_failure_rolls_back_challenge_and_persists_notification_failed(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Queue Failure', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])

        with patch(
            'odoo.addons.open_sign.services.notification_service._queue_template',
            side_effect=RuntimeError(self.QUEUE_FAILURE_WITH_TOKEN),
        ), patch(
            'odoo.addons.open_sign_portal.services.otp_service.generate_otp_code',
            return_value=self.OTP_CODE,
        ):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )

        self.assertFalse(request_response['ok'])
        self.assertEqual(request_response['error_code'], 'validation_error')
        self.assertEqual(request_response['message'], 'Failed to queue the verification email.')
        self.assertFalse(self.env['open.sign.otp.challenge'].search_count([('request_signer_id', '=', signer.id)]))

        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', signer.request_id.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'otp')
        self.assertEqual(failure_audit.metadata_json['trigger'], 'otp_request')
        self.assertEqual(failure_audit.metadata_json['failure_reason'], notification_service.FAILURE_REASON_MAIL_QUEUE_ERROR)
        self._assert_no_url_or_token_leak(failure_audit.metadata_json, self.OTP_CODE)
        self._assert_no_url_or_token_leak(request_response, self.OTP_CODE)

    def test_otp_request_missing_template_rolls_back_challenge_and_persists_notification_failed(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Missing Template', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])

        with patch(
            'odoo.addons.open_sign.services.notification_service._get_template',
            side_effect=notification_service.NotificationQueueFailure(
                notification_type='otp',
                recipient_kind='signer',
                recipient_email=False,
                template_xmlid=notification_service.OTP_TEMPLATE_XMLID,
                signer_id=signer.id,
                reason=notification_service.FAILURE_REASON_MISSING_TEMPLATE,
                display_message='Notification template is missing for otp.',
            ),
        ):
            request_response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )

        self.assertFalse(request_response['ok'])
        self.assertEqual(request_response['message'], 'Notification template is missing for otp.')
        self.assertFalse(self.env['open.sign.otp.challenge'].search_count([('request_signer_id', '=', signer.id)]))
        failure_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', signer.request_id.id),
            ('event_type', '=', 'notification_failed'),
        ], order='id desc', limit=1)
        self.assertTrue(failure_audit)
        self.assertEqual(failure_audit.metadata_json['notification_type'], 'otp')
        self.assertEqual(failure_audit.metadata_json['failure_reason'], notification_service.FAILURE_REASON_MISSING_TEMPLATE)

    def test_terminal_request_hides_otp_controls_and_denies_routes(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Terminal', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        sign_request.sudo().write({
            'status': 'declined',
            'last_event_at': fields.Datetime.now(),
            'lock_version': sign_request.lock_version + 1,
        })

        self.authenticate(None, None)
        page_response = self.url_open(f"/my/sign/{signer.id}?access_token={bundle['token']}", allow_redirects=False)
        self.assertEqual(page_response.status_code, 200)
        self.assertNotIn('Email Verification', page_response.text)

        otp_request_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(revision=sign_request.lock_version, access_token=bundle['token']),
        )
        otp_verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(revision=sign_request.lock_version, code=self.OTP_CODE, access_token=bundle['token']),
        )
        self.assertFalse(otp_request_response['ok'])
        self.assertFalse(otp_verify_response['ok'])
        self.assertEqual(otp_request_response['error_code'], 'validation_error')
        self.assertEqual(otp_verify_response['error_code'], 'validation_error')

    def test_invitation_template_mentions_otp_when_required(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Invitation Note', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertTrue(mail)
        self.assertIn('This request requires an email verification code before final submit.', mail.body_html)

    def test_reminder_template_mentions_otp_when_required(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Reminder Note', owner=self.open_sign_user, otp_required=True)
        sign_request = self.env['open.sign.request'].browse(bundle['request'].id)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        notification_service.queue_request_reminders(
            sign_request,
            sign_request._get_actionable_signers(),
            trigger='cron_reminder',
            raise_on_failure=False,
        )
        mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertTrue(mail)
        self.assertIn('This request requires an email verification code before final submit.', mail.body_html)

    def test_otp_mail_contains_code_but_not_portal_url(self):
        bundle = self._create_portal_session(self.env, name='Portal OTP Mail Content', owner=self.open_sign_user, otp_required=True)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        _response, _consent_hash, revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        with patch('odoo.addons.open_sign_portal.services.otp_service.generate_otp_code', return_value=self.OTP_CODE):
            self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/otp/request",
                self._build_otp_request_payload(revision=revision, access_token=bundle['token']),
            )
        mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertTrue(mail)
        self.assertIn(self.OTP_CODE, mail.body_html)
        self.assertNotIn('/my/sign/', mail.body_html)
        self.assertNotIn('access_token=', mail.body_html)
