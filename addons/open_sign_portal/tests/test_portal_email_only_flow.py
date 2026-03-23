# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from uuid import uuid4

from odoo import fields
from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.open_sign_portal.tests.common import OpenSignPortalHttpTestMixin


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalEmailOnlyFlow(HttpCase, OpenSignPortalHttpTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_email_only_flow_user',
            password='open_sign_portal_email_only_flow_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_outsider = new_test_user(
            cls.env,
            login='open_sign_portal_email_only_flow_outsider',
            password='open_sign_portal_email_only_flow_outsider',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_email_only_flow_manager',
            password='open_sign_portal_email_only_flow_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.email.only.flow.user@example.com'
        cls.open_sign_outsider.partner_id.email = 'open.sign.portal.email.only.flow.outsider@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.email.only.flow.manager@example.com'

    def _build_save_payload(self, *, revision, field_id, value, access_token):
        return {
            'values': [{'field_id': field_id, 'value': value}],
            'idempotency_key': str(uuid4()),
            'request_revision': revision,
            'access_token': access_token,
        }

    def _build_otp_request_payload(self, *, revision, access_token):
        return {
            'request_revision': revision,
            'access_token': access_token,
        }

    def _build_otp_verify_payload(self, *, revision, access_token, code='123456'):
        return {
            'request_revision': revision,
            'code': code,
            'access_token': access_token,
        }

    def _open_page_and_extract(self, signer_id, *, token):
        response = self.url_open(f'/my/sign/{signer_id}?access_token={token}', allow_redirects=False)
        self.assertEqual(response.status_code, 200)
        consent_hash, revision = self._extract_consent_hash_and_revision(response.text)
        return response, consent_hash, revision

    def _assert_redirect_denied(self, response, *forbidden_values):
        self.assertEqual(response.status_code, 303)
        self._assert_no_url_or_token_leak(response.headers.get('Location', ''), *forbidden_values)

    def _assert_json_error(self, response, error_code, *forbidden_values):
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], error_code)
        self._assert_no_url_or_token_leak(response, *forbidden_values)

    def _assert_json_validation_error(self, response, *forbidden_values):
        self._assert_json_error(response, 'validation_error', *forbidden_values)

    def _rotate_signer_token(self, signer):
        wizard = self.env['open.sign.signer.contact_correction.wizard'].with_user(self.open_sign_manager).create({
            'signer_id': signer.id,
            'target_email': signer.email,
            'reason': 'Rotate token for T315 email-only flow coverage',
        })
        old_token = signer.access_token
        wizard.action_apply_contact_correction()
        signer.invalidate_recordset(['access_token'])
        self.assertNotEqual(signer.access_token, old_token)
        return old_token, signer.access_token

    def _revoke_signer_token(self, signer):
        old_public_token = signer.access_token
        signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()
        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        return old_public_token, signer.access_token

    def _expire_signer_token(self, signer):
        signer.sudo().write({'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1)})
        signer.invalidate_recordset(['email_token_expires_at'])

    def _expire_request(self, sign_request):
        now = fields.Datetime.now()
        sign_request.sudo().write({
            'status': 'expired',
            'expires_at': now,
            'last_event_at': now,
            'lock_version': sign_request.lock_version + 1,
        })
        sign_request.invalidate_recordset(['status', 'lock_version'])

    def _transition_bundle_request_to_status(self, bundle, status):
        sign_request = self.env['open.sign.request'].browse(bundle['request'].id)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        now = fields.Datetime.now()

        if status == 'completed':
            signer.sudo().write({'state': 'signed', 'signed_at': now})
            sign_request._transition_to('in_progress', {'last_event_at': now})
            attachment = self._create_attachment_static(
                self.env,
                f"{bundle['request'].name}_final.pdf",
                res_model='open.sign.request',
            )
            sign_request.sudo().write({
                'final_attachment_id': attachment.id,
                'final_pdf_sha256': '0' * 64,
            })
            sign_request.action_complete()
        elif status == 'declined':
            sign_request.sudo().write({
                'status': 'declined',
                'last_event_at': now,
                'lock_version': sign_request.lock_version + 1,
            })
        elif status == 'expired':
            sign_request.sudo().write({
                'status': 'expired',
                'expires_at': now,
                'last_event_at': now,
                'lock_version': sign_request.lock_version + 1,
            })
        else:  # pragma: no cover - guard for future edits
            raise AssertionError(f'Unsupported status transition for T315 helper: {status}')

        sign_request.invalidate_recordset(['status', 'lock_version'])
        signer.invalidate_recordset(['state'])
        return sign_request, signer

    def test_external_email_only_token_flow_end_to_end_is_multi_use_until_terminal(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Only Flow E2E',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)

        self.authenticate(None, None)
        first_page, _first_consent_hash, first_revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        second_page, _second_consent_hash, second_revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        self.assertEqual(first_revision, second_revision)
        self.assertIn(f'data-access-token="{bundle["token"]}"', first_page.text)
        self.assertIn(f'data-access-token="{bundle["token"]}"', second_page.text)

        save_response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/save',
            self._build_save_payload(
                revision=second_revision,
                field_id=field.id,
                value='email-only save before submit',
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(save_response['ok'])

        third_page, consent_hash, submit_revision = self._open_page_and_extract(signer.id, token=bundle['token'])
        self.assertIn(f'data-access-token="{bundle["token"]}"', third_page.text)
        submit_response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/submit',
            self._build_submit_payload(
                revision=submit_revision,
                field_id=field.id,
                value='email-only submitted value',
                consent_hash=consent_hash,
                access_token=bundle['token'],
                idempotency_key=str(uuid4()),
            ),
        )
        self.assertTrue(submit_response['ok'])
        self.assertEqual(
            submit_response['redirect_url'],
            f'/my/sign/{signer.id}?access_token={bundle["token"]}&submitted=1',
        )

        readonly_page = self.url_open(f'/my/sign/{signer.id}?access_token={bundle["token"]}', allow_redirects=False)
        self.assertEqual(readonly_page.status_code, 200)
        self.assertIn('This signer session is available for review only.', readonly_page.text)
        self.assertIn('Your submission has already been recorded. This session is read-only.', readonly_page.text)
        self.assertNotIn('o_open_sign_save', readonly_page.text)
        self.assertNotIn('o_open_sign_submit', readonly_page.text)

        document_response = self.url_open(
            f'/my/sign/{signer.id}/document?access_token={bundle["token"]}',
            allow_redirects=False,
        )
        self.assertEqual(document_response.status_code, 200)
        self.assertIn('application/pdf', document_response.headers.get('content-type'))

        post_terminal_revision = submit_response['request_revision']
        post_terminal_save = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/save',
            self._build_save_payload(
                revision=post_terminal_revision,
                field_id=field.id,
                value='post terminal save',
                access_token=bundle['token'],
            ),
        )
        post_terminal_submit = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/submit',
            self._build_submit_payload(
                revision=post_terminal_revision,
                field_id=field.id,
                value='post terminal submit',
                consent_hash=self._expected_consent_hash(),
                access_token=bundle['token'],
                idempotency_key=str(uuid4()),
            ),
        )
        post_terminal_decline = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/decline',
            self._build_decline_payload(
                revision=post_terminal_revision,
                reason='post terminal decline',
                access_token=bundle['token'],
                idempotency_key=str(uuid4()),
            ),
        )
        self._assert_json_validation_error(post_terminal_save, bundle['token'])
        self._assert_json_validation_error(post_terminal_submit, bundle['token'])
        self._assert_json_validation_error(post_terminal_decline, bundle['token'])

    def test_forwarded_link_unrelated_authenticated_user_can_act_via_token_path(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Only Forwarded Link',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)

        self.authenticate(self.open_sign_outsider.login, self.open_sign_outsider.login)
        page_response = self.url_open(f'/my/sign/{signer.id}?access_token={bundle["token"]}', allow_redirects=False)
        self.assertEqual(page_response.status_code, 200)
        self.assertIn(f'data-access-token="{bundle["token"]}"', page_response.text)
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)

        submit_response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/submit',
            self._build_submit_payload(
                revision=revision,
                field_id=field.id,
                value='forwarded link token path submit',
                consent_hash=consent_hash,
                access_token=bundle['token'],
                idempotency_key=str(uuid4()),
            ),
        )
        self.assertTrue(submit_response['ok'])
        self.assertEqual(
            submit_response['redirect_url'],
            f'/my/sign/{signer.id}?access_token={bundle["token"]}&submitted=1',
        )

    def test_hidden_revoked_current_token_denies_submit_decline_and_otp_verify(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Only Hidden Revoked Missing Endpoints',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        _old_public_token, hidden_token = self._revoke_signer_token(signer)

        self.authenticate(None, None)
        submit_response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/submit',
            self._build_submit_payload(
                revision=signer.request_id.lock_version,
                field_id=field.id,
                value='hidden revoked submit',
                consent_hash=self._expected_consent_hash(),
                access_token=hidden_token,
                idempotency_key=str(uuid4()),
            ),
        )
        decline_response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/decline',
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='hidden revoked decline',
                access_token=hidden_token,
                idempotency_key=str(uuid4()),
            ),
        )
        otp_verify_response = self.make_jsonrpc_request(
            f'/my/sign/{signer.id}/otp/verify',
            self._build_otp_verify_payload(
                revision=signer.request_id.lock_version,
                access_token=hidden_token,
            ),
        )

        self._assert_json_error(submit_response, 'invalid_token', hidden_token)
        self._assert_json_error(decline_response, 'invalid_token', hidden_token)
        self._assert_json_error(otp_verify_response, 'invalid_token', hidden_token)

    def test_email_only_token_denial_matrix_preserves_redirect_vs_jsonrpc_contract(self):
        cases = (
            'tampered',
            'expired_current',
            'rotated_old',
            'hidden_revoked_current',
        )

        for case_name in cases:
            with self.subTest(case=case_name):
                bundle = self._create_portal_session(
                    self.env,
                    name=f'Portal Email Only Denial Matrix {case_name}',
                    owner=self.open_sign_user,
                    otp_required=True,
                )
                signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
                field = self._get_text_field_for_signer(signer)
                expected_code = 'invalid_token'

                if case_name == 'tampered':
                    token = self._mutate_token(bundle['token'])
                elif case_name == 'expired_current':
                    self._expire_signer_token(signer)
                    token = bundle['token']
                    expected_code = 'expired_token'
                elif case_name == 'rotated_old':
                    token, _new_token = self._rotate_signer_token(signer)
                elif case_name == 'hidden_revoked_current':
                    _old_public_token, token = self._revoke_signer_token(signer)
                else:  # pragma: no cover - guard for future edits
                    raise AssertionError(f'Unsupported T315 denial case: {case_name}')

                self.authenticate(None, None)
                page_response = self.url_open(f'/my/sign/{signer.id}?access_token={token}', allow_redirects=False)
                document_response = self.url_open(
                    f'/my/sign/{signer.id}/document?access_token={token}',
                    allow_redirects=False,
                )
                self._assert_redirect_denied(page_response, token)
                self._assert_redirect_denied(document_response, token)

                route_payloads = (
                    (
                        'save',
                        self._build_save_payload(
                            revision=signer.request_id.lock_version,
                            field_id=field.id,
                            value=f'{case_name} save',
                            access_token=token,
                        ),
                    ),
                    (
                        'submit',
                        self._build_submit_payload(
                            revision=signer.request_id.lock_version,
                            field_id=field.id,
                            value=f'{case_name} submit',
                            consent_hash=self._expected_consent_hash(),
                            access_token=token,
                            idempotency_key=str(uuid4()),
                        ),
                    ),
                    (
                        'decline',
                        self._build_decline_payload(
                            revision=signer.request_id.lock_version,
                            reason=f'{case_name} decline',
                            access_token=token,
                            idempotency_key=str(uuid4()),
                        ),
                    ),
                    (
                        'otp/request',
                        self._build_otp_request_payload(
                            revision=signer.request_id.lock_version,
                            access_token=token,
                        ),
                    ),
                    (
                        'otp/verify',
                        self._build_otp_verify_payload(
                            revision=signer.request_id.lock_version,
                            access_token=token,
                        ),
                    ),
                )
                for route, payload in route_payloads:
                    with self.subTest(case=case_name, route=route):
                        response = self.make_jsonrpc_request(f'/my/sign/{signer.id}/{route}', payload)
                        self._assert_json_error(response, expected_code, token)

    def test_email_only_replay_after_terminal_is_review_only_not_mutating(self):
        expected_messages = {
            'completed': 'This signing request has already been completed and is now read-only.',
            'declined': 'This signing request has already been declined and is now read-only.',
            'expired': 'This signing request has expired and is now read-only.',
        }

        for status, readonly_message in expected_messages.items():
            with self.subTest(status=status):
                bundle = self._create_portal_session(
                    self.env,
                    name=f'Portal Email Only Replay {status}',
                    owner=self.open_sign_user,
                )
                self._transition_bundle_request_to_status(bundle, status)
                signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
                field = self._get_text_field_for_signer(signer)
                self.authenticate(None, None)
                first_page = self.url_open(f'/my/sign/{signer.id}?access_token={bundle["token"]}', allow_redirects=False)
                second_page = self.url_open(f'/my/sign/{signer.id}?access_token={bundle["token"]}', allow_redirects=False)
                document_response = self.url_open(
                    f'/my/sign/{signer.id}/document?access_token={bundle["token"]}',
                    allow_redirects=False,
                )
                self.assertEqual(first_page.status_code, 200)
                self.assertEqual(second_page.status_code, 200)
                self.assertIn(readonly_message, first_page.text)
                self.assertIn(readonly_message, second_page.text)
                self.assertEqual(document_response.status_code, 200)
                self.assertIn('application/pdf', document_response.headers.get('content-type'))

                save_response = self.make_jsonrpc_request(
                    f'/my/sign/{signer.id}/save',
                    self._build_save_payload(
                        revision=signer.request_id.lock_version,
                        field_id=field.id,
                        value=f'{status} replay save',
                        access_token=bundle['token'],
                    ),
                )
                submit_response = self.make_jsonrpc_request(
                    f'/my/sign/{signer.id}/submit',
                    self._build_submit_payload(
                        revision=signer.request_id.lock_version,
                        field_id=field.id,
                        value=f'{status} replay submit',
                        consent_hash=self._expected_consent_hash(),
                        access_token=bundle['token'],
                        idempotency_key=str(uuid4()),
                    ),
                )
                decline_response = self.make_jsonrpc_request(
                    f'/my/sign/{signer.id}/decline',
                    self._build_decline_payload(
                        revision=signer.request_id.lock_version,
                        reason=f'{status} replay decline',
                        access_token=bundle['token'],
                        idempotency_key=str(uuid4()),
                    ),
                )
                self._assert_json_validation_error(save_response, bundle['token'])
                self._assert_json_validation_error(submit_response, bundle['token'])
                self._assert_json_validation_error(decline_response, bundle['token'])
