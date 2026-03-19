# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import odoo.sql_db
from psycopg2.errors import LockNotAvailable

from odoo import api, fields
from odoo.addons.open_sign_portal.controllers.portal_sign import OpenSignPortalController
from odoo.addons.open_sign_portal.services import otp_service
from odoo.orm.environments import Transaction
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.open_sign_portal.tests.common import (
    CONSENT_HASH_RE,
    REQUEST_REVISION_RE,
    OpenSignPortalTestMixin,
)


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalContract(TransactionCase):

    def test_error_envelope_shape_helper(self):
        controller = OpenSignPortalController()

        self.assertEqual(
            controller._build_error_response('invalid_token', 'Invalid or expired signing link.'),
            {
                'ok': False,
                'error_code': 'invalid_token',
                'message': 'Invalid or expired signing link.',
            },
        )


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalContractHttp(HttpCase, OpenSignPortalTestMixin):

    OTP_CODE = '123456'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_contract_user',
            password='open_sign_portal_contract_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.contract.user@example.com'

    def _build_save_payload(self, *, revision, field_id, value, access_token=False, idempotency_key=None):
        payload = {
            'idempotency_key': idempotency_key or str(uuid4()),
            'request_revision': revision,
            'values': [{'field_id': field_id, 'value': value}],
        }
        if access_token:
            payload['access_token'] = access_token
        return payload

    def _build_submit_payload(self, *, revision, field_id, value, consent_hash, access_token=False, idempotency_key=None):
        payload = self._build_save_payload(
            revision=revision,
            field_id=field_id,
            value=value,
            access_token=access_token,
            idempotency_key=idempotency_key,
        )
        payload['consent'] = {
            'accepted': True,
            'text_hash': consent_hash,
            'timezone': 'UTC',
        }
        return payload

    def _build_decline_payload(self, *, revision, reason, access_token=False, idempotency_key=None):
        payload = {
            'idempotency_key': idempotency_key or str(uuid4()),
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

    def _open_page_and_extract(self, signer_id, token):
        response = self.url_open(f'/my/sign/{signer_id}?access_token={token}', allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        consent_hash, revision = self._extract_consent_hash_and_revision(response.text)
        return response, consent_hash, revision

    def _expire_signer_token(self, signer):
        signer.sudo().write({'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1)})
        signer.invalidate_recordset(['email_token_expires_at'])

    def _read_committed(self, callback):
        with odoo.sql_db.db_connect(self.registry.db_name).cursor() as cr:
            cr.transaction = Transaction(self.registry)
            env = api.Environment(cr, self.env.uid, {})
            try:
                return callback(env)
            finally:
                env.clear()

    def _get_token_throttle_bucket(self, signer, client_ip=False):
        domain = [('request_signer_id', '=', signer.id)]
        if client_ip:
            domain.append(('client_ip', '=', client_ip))
        self.env.invalidate_all(flush=False)
        records = self.env['open.sign.portal.token.throttle'].sudo().search_read(
            domain,
            ['attempt_count', 'blocked_until', 'first_attempt_at', 'last_attempt_at', 'client_ip'],
            limit=1,
        )
        if not records:
            records = self._read_committed(
                lambda env: env['open.sign.portal.token.throttle'].sudo().search_read(
                    domain,
                    ['attempt_count', 'blocked_until', 'first_attempt_at', 'last_attempt_at', 'client_ip'],
                    limit=1,
                )
            )
        return SimpleNamespace(**records[0]) if records else False

    def _assert_exact_keys(self, payload, expected_keys):
        self.assertEqual(set(payload.keys()), set(expected_keys))

    def _assert_error_envelope(self, response, error_code, *forbidden_values):
        self._assert_exact_keys(response, {'ok', 'error_code', 'message'})
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], error_code)
        self._assert_no_url_or_token_leak(response, *forbidden_values)

    def _assert_redirect_success(self, response, *, signer_id, token=False, query_flag, extra_keys=None):
        expected_keys = {'ok', 'force_refresh', 'redirect_url', 'request_revision'}
        if extra_keys:
            expected_keys |= set(extra_keys)
        self._assert_exact_keys(response, expected_keys)
        self.assertTrue(response['ok'])
        expected_redirect = f'/my/sign/{signer_id}'
        query_params = []
        if token:
            query_params.append(f'access_token={token}')
        if query_flag:
            query_params.append(query_flag)
        if query_params:
            expected_redirect = f"{expected_redirect}?{'&'.join(query_params)}"
        self.assertEqual(response['redirect_url'], expected_redirect)
        if extra_keys and 'otp_verified' in extra_keys:
            self.assertTrue(response['otp_verified'])
        self._assert_no_url_or_token_leak(
            {key: value for key, value in response.items() if key != 'redirect_url'},
            token,
        )

    def _submit_signer_successfully(self, bundle, *, value='Signed Value'):
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        self.authenticate(None, None)
        _page_response, consent_hash, revision = self._open_page_and_extract(signer.id, bundle['token'])
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/submit',
            self._build_submit_payload(
                revision=revision,
                field_id=field.id,
                value=value,
                consent_hash=consent_hash,
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(response['ok'])
        return response

    def _request_otp_successfully(self, bundle, *, code=None):
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        patchers = [
            patch(
                'odoo.addons.open_sign.services.notification_service.queue_request_otp_notification',
                return_value=1,
            ),
        ]
        if code is not None:
            patchers.append(
                patch(
                    'odoo.addons.open_sign_portal.services.otp_service.generate_otp_code',
                    return_value=code,
                )
            )
        with patchers[0]:
            if len(patchers) == 2:
                with patchers[1]:
                    response = self.make_jsonrpc_request(
                        f'/my/sign/{signer.id}/otp/request',
                        self._build_otp_request_payload(
                            revision=signer.request_id.lock_version,
                            access_token=bundle['token'],
                        ),
                    )
            else:
                response = self.make_jsonrpc_request(
                    f'/my/sign/{signer.id}/otp/request',
                    self._build_otp_request_payload(
                        revision=signer.request_id.lock_version,
                        access_token=bundle['token'],
                    ),
                )
        self.assertTrue(response['ok'])
        return response

    def test_save_success_envelope_shape(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract Save Success',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/save',
            self._build_save_payload(
                revision=signer.request_id.lock_version,
                field_id=field.id,
                value='saved value',
                access_token=bundle['token'],
            ),
        )

        self._assert_exact_keys(response, {'ok', 'state', 'request_revision'})
        self.assertTrue(response['ok'])
        self.assertEqual(response['state'], 'in_progress')

    def test_submit_success_envelope_shape(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract Submit Success',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)

        self.authenticate(None, None)
        _page_response, consent_hash, revision = self._open_page_and_extract(signer.id, bundle['token'])
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/submit',
            self._build_submit_payload(
                revision=revision,
                field_id=field.id,
                value='submit value',
                consent_hash=consent_hash,
                access_token=bundle['token'],
            ),
        )

        self._assert_redirect_success(
            response,
            signer_id=signer.id,
            token=bundle['token'],
            query_flag='submitted=1',
        )

    def test_decline_success_envelope_shape(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract Decline Success',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/decline',
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='decline for contract test',
                access_token=bundle['token'],
            ),
        )

        self._assert_redirect_success(
            response,
            signer_id=signer.id,
            token=bundle['token'],
            query_flag='declined=1',
        )
        self.assertNotIn('state', response)

    def test_otp_request_success_envelope_shape(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Request Success',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        response = self._request_otp_successfully(bundle, code=self.OTP_CODE)

        self._assert_redirect_success(
            response,
            signer_id=signer.id,
            token=bundle['token'],
            query_flag='otp_requested=1',
        )

    def test_otp_verify_success_envelope_shape(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Verify Success',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        request_response = self._request_otp_successfully(bundle, code=self.OTP_CODE)
        verify_response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=request_response['request_revision'],
                code=self.OTP_CODE,
                access_token=bundle['token'],
            ),
        )

        self._assert_redirect_success(
            verify_response,
            signer_id=signer.id,
            token=bundle['token'],
            query_flag='otp_verified=1',
            extra_keys={'otp_verified'},
        )

    def test_save_invalid_token_error_envelope(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract Save Invalid', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/save',
            self._build_save_payload(
                revision=signer.request_id.lock_version,
                field_id=field.id,
                value='bad save',
                access_token=wrong_token,
            ),
        )
        self._assert_error_envelope(response, 'invalid_token', wrong_token)

    def test_submit_invalid_token_error_envelope(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract Submit Invalid', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        self.authenticate(None, None)
        _page_response, consent_hash, revision = self._open_page_and_extract(signer.id, bundle['token'])
        wrong_token = self._mutate_token(bundle['token'])
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/submit',
            self._build_submit_payload(
                revision=revision,
                field_id=field.id,
                value='bad submit',
                consent_hash=consent_hash,
                access_token=wrong_token,
            ),
        )
        self._assert_error_envelope(response, 'invalid_token', wrong_token)

    def test_decline_invalid_token_error_envelope(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract Decline Invalid', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/decline',
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='bad decline',
                access_token=wrong_token,
            ),
        )
        self._assert_error_envelope(response, 'invalid_token', wrong_token)

    def test_otp_request_invalid_token_error_envelope(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Request Invalid',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/otp/request',
            self._build_otp_request_payload(
                revision=signer.request_id.lock_version,
                access_token=wrong_token,
            ),
        )
        self._assert_error_envelope(response, 'invalid_token', wrong_token)

    def test_otp_verify_invalid_token_error_envelope(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Verify Invalid',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=signer.request_id.lock_version,
                code=self.OTP_CODE,
                access_token=wrong_token,
            ),
        )
        self._assert_error_envelope(response, 'invalid_token', wrong_token)

    def test_throttled_invalid_attempts_still_use_standard_invalid_token_envelope(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract Throttled Invalid', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        wrong_token = self._mutate_token(bundle['token'])
        client_ip = '203.0.113.40'

        self.authenticate(None, None)
        response = False
        for attempt in range(6):
            response = self.make_jsonrpc_request(
                f'/my/sign/{signer.id}/save',
                self._build_save_payload(
                    revision=signer.request_id.lock_version,
                    field_id=field.id,
                    value=f'invalid throttle {attempt}',
                    access_token=wrong_token,
                ),
                headers=self._ip_headers(client_ip),
            )

        self.assertTrue(self._get_token_throttle_bucket(signer, client_ip))
        self._assert_error_envelope(response, 'invalid_token', wrong_token)

    def test_save_expired_token_error_envelope(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract Save Expired', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        self._expire_signer_token(signer)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/save',
            self._build_save_payload(
                revision=signer.request_id.lock_version,
                field_id=field.id,
                value='expired save',
                access_token=bundle['token'],
            ),
        )
        self._assert_error_envelope(response, 'expired_token', bundle['token'])

    def test_submit_expired_token_error_envelope(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract Submit Expired', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        self.authenticate(None, None)
        _page_response, consent_hash, revision = self._open_page_and_extract(signer.id, bundle['token'])
        self._expire_signer_token(signer)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/submit',
            self._build_submit_payload(
                revision=revision,
                field_id=field.id,
                value='expired submit',
                consent_hash=consent_hash,
                access_token=bundle['token'],
            ),
        )
        self._assert_error_envelope(response, 'expired_token', bundle['token'])

    def test_decline_expired_token_error_envelope(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract Decline Expired', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self._expire_signer_token(signer)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/decline',
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='expired decline',
                access_token=bundle['token'],
            ),
        )
        self._assert_error_envelope(response, 'expired_token', bundle['token'])

    def test_otp_request_expired_token_error_envelope(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Request Expired',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self._expire_signer_token(signer)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/otp/request',
            self._build_otp_request_payload(
                revision=signer.request_id.lock_version,
                access_token=bundle['token'],
            ),
        )
        self._assert_error_envelope(response, 'expired_token', bundle['token'])

    def test_otp_verify_expired_token_error_envelope(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Verify Expired',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self._expire_signer_token(signer)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=signer.request_id.lock_version,
                code=self.OTP_CODE,
                access_token=bundle['token'],
            ),
        )
        self._assert_error_envelope(response, 'expired_token', bundle['token'])

    def test_save_allowed_error_codes(self):
        seen = set()
        self.authenticate(None, None)

        invalid_bundle = self._create_portal_session(self.env, name='Portal Contract Save Codes Invalid', owner=self.open_sign_user)
        invalid_signer = self.env['open.sign.request.signer'].browse(invalid_bundle['signer'].id)
        invalid_field = self._get_text_field_for_signer(invalid_signer)
        invalid_response = self.make_jsonrpc_request(
            f'/my/sign/{invalid_signer.id}/save',
            self._build_save_payload(
                revision=invalid_signer.request_id.lock_version,
                field_id=invalid_field.id,
                value='invalid',
                access_token=self._mutate_token(invalid_bundle['token']),
            ),
        )
        seen.add(invalid_response['error_code'])

        expired_bundle = self._create_portal_session(self.env, name='Portal Contract Save Codes Expired', owner=self.open_sign_user)
        expired_signer = self.env['open.sign.request.signer'].browse(expired_bundle['signer'].id)
        expired_field = self._get_text_field_for_signer(expired_signer)
        self._expire_signer_token(expired_signer)
        expired_response = self.make_jsonrpc_request(
            f'/my/sign/{expired_signer.id}/save',
            self._build_save_payload(
                revision=expired_signer.request_id.lock_version,
                field_id=expired_field.id,
                value='expired',
                access_token=expired_bundle['token'],
            ),
        )
        seen.add(expired_response['error_code'])

        stale_bundle = self._create_portal_session(self.env, name='Portal Contract Save Codes Stale', owner=self.open_sign_user)
        stale_signer = self.env['open.sign.request.signer'].browse(stale_bundle['signer'].id)
        stale_field = self._get_text_field_for_signer(stale_signer)
        stale_revision = stale_signer.request_id.lock_version
        stale_signer.request_id.sudo().write({'lock_version': stale_revision + 1})
        stale_response = self.make_jsonrpc_request(
            f'/my/sign/{stale_signer.id}/save',
            self._build_save_payload(
                revision=stale_revision,
                field_id=stale_field.id,
                value='stale',
                access_token=stale_bundle['token'],
            ),
        )
        seen.add(stale_response['error_code'])

        lock_bundle = self._create_portal_session(self.env, name='Portal Contract Save Codes Lock', owner=self.open_sign_user)
        lock_signer = self.env['open.sign.request.signer'].browse(lock_bundle['signer'].id)
        lock_field = self._get_text_field_for_signer(lock_signer)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            lock_response = self.make_jsonrpc_request(
                f'/my/sign/{lock_signer.id}/save',
                self._build_save_payload(
                    revision=lock_signer.request_id.lock_version,
                    field_id=lock_field.id,
                    value='locked',
                    access_token=lock_bundle['token'],
                ),
            )
        seen.add(lock_response['error_code'])

        order_bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Contract Save Codes Order',
            owner=self.open_sign_user,
        )
        waiting_signer = self.env['open.sign.request.signer'].browse(order_bundle['signer_second'].id)
        waiting_field = self._get_text_field_for_signer(waiting_signer)
        order_response = self.make_jsonrpc_request(
            f'/my/sign/{waiting_signer.id}/save',
            self._build_save_payload(
                revision=waiting_signer.request_id.lock_version,
                field_id=waiting_field.id,
                value='waiting',
                access_token=order_bundle['token_second'],
            ),
        )
        seen.add(order_response['error_code'])

        terminal_bundle = self._create_portal_session(self.env, name='Portal Contract Save Codes Terminal', owner=self.open_sign_user)
        self._submit_signer_successfully(terminal_bundle)
        terminal_signer = self.env['open.sign.request.signer'].browse(terminal_bundle['signer'].id)
        terminal_field = self._get_text_field_for_signer(terminal_signer)
        terminal_response = self.make_jsonrpc_request(
            f'/my/sign/{terminal_signer.id}/save',
            self._build_save_payload(
                revision=terminal_signer.request_id.lock_version,
                field_id=terminal_field.id,
                value='after submit',
                access_token=terminal_bundle['token'],
            ),
        )
        seen.add(terminal_response['error_code'])

        self.assertEqual(
            seen,
            {'invalid_token', 'expired_token', 'stale_revision', 'request_locked', 'signing_order_blocked', 'validation_error'},
        )

    def test_submit_allowed_error_codes(self):
        seen = set()
        self.authenticate(None, None)

        invalid_bundle = self._create_portal_session(self.env, name='Portal Contract Submit Codes Invalid', owner=self.open_sign_user)
        invalid_signer = self.env['open.sign.request.signer'].browse(invalid_bundle['signer'].id)
        invalid_field = self._get_text_field_for_signer(invalid_signer)
        _page_response, consent_hash, revision = self._open_page_and_extract(invalid_signer.id, invalid_bundle['token'])
        invalid_response = self.make_jsonrpc_request(
            f'/my/sign/{invalid_signer.id}/submit',
            self._build_submit_payload(
                revision=revision,
                field_id=invalid_field.id,
                value='invalid',
                consent_hash=consent_hash,
                access_token=self._mutate_token(invalid_bundle['token']),
            ),
        )
        seen.add(invalid_response['error_code'])

        expired_bundle = self._create_portal_session(self.env, name='Portal Contract Submit Codes Expired', owner=self.open_sign_user)
        expired_signer = self.env['open.sign.request.signer'].browse(expired_bundle['signer'].id)
        expired_field = self._get_text_field_for_signer(expired_signer)
        _page_response, expired_consent_hash, expired_revision = self._open_page_and_extract(expired_signer.id, expired_bundle['token'])
        self._expire_signer_token(expired_signer)
        expired_response = self.make_jsonrpc_request(
            f'/my/sign/{expired_signer.id}/submit',
            self._build_submit_payload(
                revision=expired_revision,
                field_id=expired_field.id,
                value='expired',
                consent_hash=expired_consent_hash,
                access_token=expired_bundle['token'],
            ),
        )
        seen.add(expired_response['error_code'])

        stale_bundle = self._create_portal_session(self.env, name='Portal Contract Submit Codes Stale', owner=self.open_sign_user)
        stale_signer = self.env['open.sign.request.signer'].browse(stale_bundle['signer'].id)
        stale_field = self._get_text_field_for_signer(stale_signer)
        _page_response, stale_consent_hash, stale_revision = self._open_page_and_extract(stale_signer.id, stale_bundle['token'])
        stale_signer.request_id.sudo().write({'lock_version': stale_revision + 1})
        stale_response = self.make_jsonrpc_request(
            f'/my/sign/{stale_signer.id}/submit',
            self._build_submit_payload(
                revision=stale_revision,
                field_id=stale_field.id,
                value='stale',
                consent_hash=stale_consent_hash,
                access_token=stale_bundle['token'],
            ),
        )
        seen.add(stale_response['error_code'])

        lock_bundle = self._create_portal_session(self.env, name='Portal Contract Submit Codes Lock', owner=self.open_sign_user)
        lock_signer = self.env['open.sign.request.signer'].browse(lock_bundle['signer'].id)
        lock_field = self._get_text_field_for_signer(lock_signer)
        _page_response, lock_consent_hash, lock_revision = self._open_page_and_extract(lock_signer.id, lock_bundle['token'])
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            lock_response = self.make_jsonrpc_request(
                f'/my/sign/{lock_signer.id}/submit',
                self._build_submit_payload(
                    revision=lock_revision,
                    field_id=lock_field.id,
                    value='locked',
                    consent_hash=lock_consent_hash,
                    access_token=lock_bundle['token'],
                ),
            )
        seen.add(lock_response['error_code'])

        order_bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Contract Submit Codes Order',
            owner=self.open_sign_user,
        )
        waiting_signer = self.env['open.sign.request.signer'].browse(order_bundle['signer_second'].id)
        waiting_field = self._get_text_field_for_signer(waiting_signer)
        order_response = self.make_jsonrpc_request(
            f'/my/sign/{waiting_signer.id}/submit',
            self._build_submit_payload(
                revision=waiting_signer.request_id.lock_version,
                field_id=waiting_field.id,
                value='waiting',
                consent_hash='0' * 64,
                access_token=order_bundle['token_second'],
            ),
        )
        seen.add(order_response['error_code'])

        consent_bundle = self._create_portal_session(self.env, name='Portal Contract Submit Codes Consent', owner=self.open_sign_user)
        consent_signer = self.env['open.sign.request.signer'].browse(consent_bundle['signer'].id)
        consent_field = self._get_text_field_for_signer(consent_signer)
        _page_response, _consent_hash, consent_revision = self._open_page_and_extract(consent_signer.id, consent_bundle['token'])
        consent_response = self.make_jsonrpc_request(
            f'/my/sign/{consent_signer.id}/submit',
            self._build_save_payload(
                revision=consent_revision,
                field_id=consent_field.id,
                value='missing consent',
                access_token=consent_bundle['token'],
            ),
        )
        seen.add(consent_response['error_code'])

        otp_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract Submit Codes OTP',
            owner=self.open_sign_user,
            otp_required=True,
        )
        otp_signer = self.env['open.sign.request.signer'].browse(otp_bundle['signer'].id)
        otp_field = self._get_text_field_for_signer(otp_signer)
        otp_response = self.make_jsonrpc_request(
            f'/my/sign/{otp_signer.id}/submit',
            self._build_submit_payload(
                revision=otp_signer.request_id.lock_version,
                field_id=otp_field.id,
                value='otp blocked',
                consent_hash='0' * 64,
                access_token=otp_bundle['token'],
            ),
        )
        seen.add(otp_response['error_code'])

        conflict_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract Submit Codes Conflict',
            owner=self.open_sign_user,
        )
        conflict_signer = self.env['open.sign.request.signer'].browse(conflict_bundle['signer'].id)
        conflict_field = self._get_text_field_for_signer(conflict_signer)
        _page_response, conflict_consent_hash, conflict_revision = self._open_page_and_extract(
            conflict_signer.id,
            conflict_bundle['token'],
        )
        conflict_key = str(uuid4())
        first_conflict_payload = self._build_submit_payload(
            revision=conflict_revision,
            field_id=conflict_field.id,
            value='first conflict submit',
            consent_hash=conflict_consent_hash,
            access_token=conflict_bundle['token'],
            idempotency_key=conflict_key,
        )
        second_conflict_payload = self._build_submit_payload(
            revision=conflict_revision,
            field_id=conflict_field.id,
            value='second conflict submit',
            consent_hash=conflict_consent_hash,
            access_token=conflict_bundle['token'],
            idempotency_key=conflict_key,
        )
        first_conflict_response = self.make_jsonrpc_request(
            f'/my/sign/{conflict_signer.id}/submit',
            first_conflict_payload,
        )
        self.assertTrue(first_conflict_response['ok'])
        conflict_response = self.make_jsonrpc_request(
            f'/my/sign/{conflict_signer.id}/submit',
            second_conflict_payload,
        )
        seen.add(conflict_response['error_code'])

        self.assertEqual(
            seen,
            {
                'invalid_token',
                'expired_token',
                'stale_revision',
                'request_locked',
                'signing_order_blocked',
                'consent_required',
                'validation_error',
                'idempotency_conflict',
            },
        )

    def test_decline_allowed_error_codes(self):
        seen = set()
        self.authenticate(None, None)

        invalid_bundle = self._create_portal_session(self.env, name='Portal Contract Decline Codes Invalid', owner=self.open_sign_user)
        invalid_signer = self.env['open.sign.request.signer'].browse(invalid_bundle['signer'].id)
        invalid_response = self.make_jsonrpc_request(
            f'/my/sign/{invalid_signer.id}/decline',
            self._build_decline_payload(
                revision=invalid_signer.request_id.lock_version,
                reason='invalid',
                access_token=self._mutate_token(invalid_bundle['token']),
            ),
        )
        seen.add(invalid_response['error_code'])

        expired_bundle = self._create_portal_session(self.env, name='Portal Contract Decline Codes Expired', owner=self.open_sign_user)
        expired_signer = self.env['open.sign.request.signer'].browse(expired_bundle['signer'].id)
        self._expire_signer_token(expired_signer)
        expired_response = self.make_jsonrpc_request(
            f'/my/sign/{expired_signer.id}/decline',
            self._build_decline_payload(
                revision=expired_signer.request_id.lock_version,
                reason='expired',
                access_token=expired_bundle['token'],
            ),
        )
        seen.add(expired_response['error_code'])

        stale_bundle = self._create_portal_session(self.env, name='Portal Contract Decline Codes Stale', owner=self.open_sign_user)
        stale_signer = self.env['open.sign.request.signer'].browse(stale_bundle['signer'].id)
        stale_revision = stale_signer.request_id.lock_version
        stale_signer.request_id.sudo().write({'lock_version': stale_revision + 1})
        stale_response = self.make_jsonrpc_request(
            f'/my/sign/{stale_signer.id}/decline',
            self._build_decline_payload(
                revision=stale_revision,
                reason='stale',
                access_token=stale_bundle['token'],
            ),
        )
        seen.add(stale_response['error_code'])

        lock_bundle = self._create_portal_session(self.env, name='Portal Contract Decline Codes Lock', owner=self.open_sign_user)
        lock_signer = self.env['open.sign.request.signer'].browse(lock_bundle['signer'].id)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            lock_response = self.make_jsonrpc_request(
                f'/my/sign/{lock_signer.id}/decline',
                self._build_decline_payload(
                    revision=lock_signer.request_id.lock_version,
                    reason='locked',
                    access_token=lock_bundle['token'],
                ),
            )
        seen.add(lock_response['error_code'])

        terminal_bundle = self._create_portal_session(self.env, name='Portal Contract Decline Codes Terminal', owner=self.open_sign_user)
        terminal_signer = self.env['open.sign.request.signer'].browse(terminal_bundle['signer'].id)
        first_response = self.make_jsonrpc_request(
            f'/my/sign/{terminal_signer.id}/decline',
            self._build_decline_payload(
                revision=terminal_signer.request_id.lock_version,
                reason='first decline',
                access_token=terminal_bundle['token'],
            ),
        )
        self.assertTrue(first_response['ok'])
        second_response = self.make_jsonrpc_request(
            f'/my/sign/{terminal_signer.id}/decline',
            self._build_decline_payload(
                revision=terminal_signer.request_id.lock_version,
                reason='second decline',
                access_token=terminal_bundle['token'],
            ),
        )
        seen.add(second_response['error_code'])

        conflict_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract Decline Codes Conflict',
            owner=self.open_sign_user,
        )
        conflict_signer = self.env['open.sign.request.signer'].browse(conflict_bundle['signer'].id)
        conflict_key = str(uuid4())
        first_conflict_response = self.make_jsonrpc_request(
            f'/my/sign/{conflict_signer.id}/decline',
            self._build_decline_payload(
                revision=conflict_signer.request_id.lock_version,
                reason='first conflict decline',
                access_token=conflict_bundle['token'],
                idempotency_key=conflict_key,
            ),
        )
        self.assertTrue(first_conflict_response['ok'])
        conflict_response = self.make_jsonrpc_request(
            f'/my/sign/{conflict_signer.id}/decline',
            self._build_decline_payload(
                revision=conflict_signer.request_id.lock_version,
                reason='second conflict decline',
                access_token=conflict_bundle['token'],
                idempotency_key=conflict_key,
            ),
        )
        seen.add(conflict_response['error_code'])

        waiting_bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Contract Decline Codes Waiting',
            owner=self.open_sign_user,
        )
        waiting_signer = self.env['open.sign.request.signer'].browse(waiting_bundle['signer_second'].id)
        waiting_response = self.make_jsonrpc_request(
            f'/my/sign/{waiting_signer.id}/decline',
            self._build_decline_payload(
                revision=waiting_signer.request_id.lock_version,
                reason='waiting decline',
                access_token=waiting_bundle['token_second'],
            ),
        )
        self.assertTrue(waiting_response['ok'])
        self.assertNotIn('error_code', waiting_response)

        self.assertEqual(seen, {'invalid_token', 'expired_token', 'stale_revision', 'request_locked', 'validation_error', 'idempotency_conflict'})
        self.assertNotIn('signing_order_blocked', seen)

    def test_otp_request_allowed_error_codes(self):
        seen = set()
        self.authenticate(None, None)

        invalid_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Request Codes Invalid',
            owner=self.open_sign_user,
            otp_required=True,
        )
        invalid_signer = self.env['open.sign.request.signer'].browse(invalid_bundle['signer'].id)
        invalid_response = self.make_jsonrpc_request(
            f'/my/sign/{invalid_signer.id}/otp/request',
            self._build_otp_request_payload(
                revision=invalid_signer.request_id.lock_version,
                access_token=self._mutate_token(invalid_bundle['token']),
            ),
        )
        seen.add(invalid_response['error_code'])

        expired_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Request Codes Expired',
            owner=self.open_sign_user,
            otp_required=True,
        )
        expired_signer = self.env['open.sign.request.signer'].browse(expired_bundle['signer'].id)
        self._expire_signer_token(expired_signer)
        expired_response = self.make_jsonrpc_request(
            f'/my/sign/{expired_signer.id}/otp/request',
            self._build_otp_request_payload(
                revision=expired_signer.request_id.lock_version,
                access_token=expired_bundle['token'],
            ),
        )
        seen.add(expired_response['error_code'])

        stale_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Request Codes Stale',
            owner=self.open_sign_user,
            otp_required=True,
        )
        stale_signer = self.env['open.sign.request.signer'].browse(stale_bundle['signer'].id)
        stale_revision = stale_signer.request_id.lock_version
        stale_signer.request_id.sudo().write({'lock_version': stale_revision + 1})
        stale_response = self.make_jsonrpc_request(
            f'/my/sign/{stale_signer.id}/otp/request',
            self._build_otp_request_payload(
                revision=stale_revision,
                access_token=stale_bundle['token'],
            ),
        )
        seen.add(stale_response['error_code'])

        lock_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Request Codes Lock',
            owner=self.open_sign_user,
            otp_required=True,
        )
        lock_signer = self.env['open.sign.request.signer'].browse(lock_bundle['signer'].id)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            lock_response = self.make_jsonrpc_request(
                f'/my/sign/{lock_signer.id}/otp/request',
                self._build_otp_request_payload(
                    revision=lock_signer.request_id.lock_version,
                    access_token=lock_bundle['token'],
                ),
            )
        seen.add(lock_response['error_code'])

        order_bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Contract OTP Request Codes Order',
            owner=self.open_sign_user,
            second_otp_required=True,
        )
        waiting_signer = self.env['open.sign.request.signer'].browse(order_bundle['signer_second'].id)
        order_response = self.make_jsonrpc_request(
            f'/my/sign/{waiting_signer.id}/otp/request',
            self._build_otp_request_payload(
                revision=waiting_signer.request_id.lock_version,
                access_token=order_bundle['token_second'],
            ),
        )
        seen.add(order_response['error_code'])

        validation_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Request Codes Validation',
            owner=self.open_sign_user,
            otp_required=False,
        )
        validation_signer = self.env['open.sign.request.signer'].browse(validation_bundle['signer'].id)
        validation_response = self.make_jsonrpc_request(
            f'/my/sign/{validation_signer.id}/otp/request',
            self._build_otp_request_payload(
                revision=validation_signer.request_id.lock_version,
                access_token=validation_bundle['token'],
            ),
        )
        seen.add(validation_response['error_code'])

        self.assertEqual(
            seen,
            {'invalid_token', 'expired_token', 'stale_revision', 'request_locked', 'signing_order_blocked', 'validation_error'},
        )

    def test_otp_verify_allowed_error_codes(self):
        seen = set()
        self.authenticate(None, None)

        invalid_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Verify Codes Invalid',
            owner=self.open_sign_user,
            otp_required=True,
        )
        invalid_signer = self.env['open.sign.request.signer'].browse(invalid_bundle['signer'].id)
        invalid_response = self.make_jsonrpc_request(
            f'/my/sign/{invalid_signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=invalid_signer.request_id.lock_version,
                code=self.OTP_CODE,
                access_token=self._mutate_token(invalid_bundle['token']),
            ),
        )
        seen.add(invalid_response['error_code'])

        expired_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Verify Codes Expired',
            owner=self.open_sign_user,
            otp_required=True,
        )
        expired_signer = self.env['open.sign.request.signer'].browse(expired_bundle['signer'].id)
        self._expire_signer_token(expired_signer)
        expired_response = self.make_jsonrpc_request(
            f'/my/sign/{expired_signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=expired_signer.request_id.lock_version,
                code=self.OTP_CODE,
                access_token=expired_bundle['token'],
            ),
        )
        seen.add(expired_response['error_code'])

        stale_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Verify Codes Stale',
            owner=self.open_sign_user,
            otp_required=True,
        )
        stale_signer = self.env['open.sign.request.signer'].browse(stale_bundle['signer'].id)
        with patch(
            'odoo.addons.open_sign.services.notification_service.queue_request_otp_notification',
            return_value=1,
        ), patch(
            'odoo.addons.open_sign_portal.services.otp_service.generate_otp_code',
            return_value=self.OTP_CODE,
        ):
            request_response = self.make_jsonrpc_request(
                f'/my/sign/{stale_signer.id}/otp/request',
                self._build_otp_request_payload(
                    revision=stale_signer.request_id.lock_version,
                    access_token=stale_bundle['token'],
                ),
            )
        stale_revision = request_response['request_revision']
        stale_signer.request_id.sudo().write({'lock_version': stale_revision + 1})
        stale_response = self.make_jsonrpc_request(
            f'/my/sign/{stale_signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=stale_revision,
                code=self.OTP_CODE,
                access_token=stale_bundle['token'],
            ),
        )
        seen.add(stale_response['error_code'])

        lock_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Verify Codes Lock',
            owner=self.open_sign_user,
            otp_required=True,
        )
        lock_signer = self.env['open.sign.request.signer'].browse(lock_bundle['signer'].id)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            lock_response = self.make_jsonrpc_request(
                f'/my/sign/{lock_signer.id}/otp/verify',
                self._build_otp_verify_payload(
                    revision=lock_signer.request_id.lock_version,
                    code=self.OTP_CODE,
                    access_token=lock_bundle['token'],
                ),
            )
        seen.add(lock_response['error_code'])

        order_bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Contract OTP Verify Codes Order',
            owner=self.open_sign_user,
            second_otp_required=True,
        )
        waiting_signer = self.env['open.sign.request.signer'].browse(order_bundle['signer_second'].id)
        salt = 'ab' * 16
        self.env['open.sign.otp.challenge'].sudo().create({
            'request_signer_id': waiting_signer.id,
            'requested_at': fields.Datetime.now(),
            'expires_at': fields.Datetime.now() + timedelta(minutes=10),
            'attempt_count': 0,
            'code_salt': salt,
            'code_hash': otp_service.hash_otp_code(self.OTP_CODE, salt),
        })
        order_response = self.make_jsonrpc_request(
            f'/my/sign/{waiting_signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=waiting_signer.request_id.lock_version,
                code=self.OTP_CODE,
                access_token=order_bundle['token_second'],
            ),
        )
        seen.add(order_response['error_code'])

        validation_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract OTP Verify Codes Validation',
            owner=self.open_sign_user,
            otp_required=True,
        )
        validation_signer = self.env['open.sign.request.signer'].browse(validation_bundle['signer'].id)
        with patch(
            'odoo.addons.open_sign.services.notification_service.queue_request_otp_notification',
            return_value=1,
        ), patch(
            'odoo.addons.open_sign_portal.services.otp_service.generate_otp_code',
            return_value=self.OTP_CODE,
        ):
            request_response = self.make_jsonrpc_request(
                f'/my/sign/{validation_signer.id}/otp/request',
                self._build_otp_request_payload(
                    revision=validation_signer.request_id.lock_version,
                    access_token=validation_bundle['token'],
                ),
            )
        validation_response = self.make_jsonrpc_request(
            f'/my/sign/{validation_signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=request_response['request_revision'],
                code='654321',
                access_token=validation_bundle['token'],
            ),
        )
        seen.add(validation_response['error_code'])

        self.assertEqual(
            seen,
            {'invalid_token', 'expired_token', 'stale_revision', 'request_locked', 'signing_order_blocked', 'validation_error'},
        )

    def test_error_envelopes_do_not_echo_access_token(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract No Leak Error', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/save',
            self._build_save_payload(
                revision=signer.request_id.lock_version,
                field_id=field.id,
                value='leak test',
                access_token=wrong_token,
            ),
        )
        self._assert_error_envelope(response, 'invalid_token', wrong_token)

    def test_redirect_success_envelopes_only_return_expected_redirect_url(self):
        self.authenticate(None, None)

        decline_bundle = self._create_portal_session(self.env, name='Portal Contract Redirect Decline', owner=self.open_sign_user)
        decline_signer = self.env['open.sign.request.signer'].browse(decline_bundle['signer'].id)
        decline_response = self.make_jsonrpc_request(
            f'/my/sign/{decline_signer.id}/decline',
            self._build_decline_payload(
                revision=decline_signer.request_id.lock_version,
                reason='redirect test decline',
                access_token=decline_bundle['token'],
            ),
        )
        self._assert_redirect_success(
            decline_response,
            signer_id=decline_signer.id,
            token=decline_bundle['token'],
            query_flag='declined=1',
        )

        otp_bundle = self._create_portal_session(
            self.env,
            name='Portal Contract Redirect OTP',
            owner=self.open_sign_user,
            otp_required=True,
        )
        otp_signer = self.env['open.sign.request.signer'].browse(otp_bundle['signer'].id)
        request_response = self._request_otp_successfully(otp_bundle, code=self.OTP_CODE)
        self._assert_redirect_success(
            request_response,
            signer_id=otp_signer.id,
            token=otp_bundle['token'],
            query_flag='otp_requested=1',
        )

        verify_response = self.make_jsonrpc_request(
            f'/my/sign/{otp_signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=request_response['request_revision'],
                code=self.OTP_CODE,
                access_token=otp_bundle['token'],
            ),
        )
        self._assert_redirect_success(
            verify_response,
            signer_id=otp_signer.id,
            token=otp_bundle['token'],
            query_flag='otp_verified=1',
            extra_keys={'otp_verified'},
        )

    def test_decline_contract_matches_doc_not_old_m0_shape(self):
        bundle = self._create_portal_session(self.env, name='Portal Contract Decline Shape', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/decline',
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='doc shape decline',
                access_token=bundle['token'],
            ),
        )

        self.assertTrue(response['ok'])
        self.assertNotIn('state', response)
        self.assertEqual(
            response['redirect_url'],
            f'/my/sign/{signer.id}?access_token={bundle["token"]}&declined=1',
        )
