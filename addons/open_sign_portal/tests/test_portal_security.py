# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
from unittest.mock import patch
from uuid import uuid4

from psycopg2.errors import LockNotAvailable

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.open_sign_portal.controllers.portal_sign import OpenSignPortalController
from odoo.addons.open_sign_portal.tests.common import (
    CONSENT_HASH_RE,
    REQUEST_REVISION_RE,
    OpenSignPortalTestMixin,
)


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalSecurity(TransactionCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bundle = cls._create_portal_session(
            cls.env,
            name='Portal Security Transaction',
            owner=cls.env.user,
        )

    def test_token_match_requires_exact_token(self):
        signer = self.env['open.sign.request.signer'].browse(self.bundle['signer'].id).sudo()
        token = self.bundle['token']
        controller = OpenSignPortalController()

        self.assertTrue(controller._token_matches_signer(signer, token))
        self.assertFalse(controller._token_matches_signer(signer, self._mutate_token(token)))
        self.assertFalse(controller._token_matches_signer(signer, f'x{token[1:]}'))
        self.assertFalse(controller._token_matches_signer(signer, f'{token}x'))


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalSecurityHttp(HttpCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_security_user',
            password='open_sign_portal_security_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_outsider = new_test_user(
            cls.env,
            login='open_sign_portal_security_outsider',
            password='open_sign_portal_security_outsider',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_security_manager',
            password='open_sign_portal_security_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.security.user@example.com'
        cls.open_sign_outsider.partner_id.email = 'open.sign.portal.security.outsider@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.security.manager@example.com'

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
        consent_match = CONSENT_HASH_RE.search(html)
        revision_match = REQUEST_REVISION_RE.search(html)
        self.assertTrue(consent_match)
        self.assertTrue(revision_match)
        consent_hash = consent_match.group(1)
        revision = int(revision_match.group(1))
        return consent_hash, revision

    @staticmethod
    def _expected_consent_hash():
        return hashlib.sha256(
            b'I agree to sign electronically and confirm my intent to sign this document.'
        ).hexdigest()

    def _get_text_field_for_signer(self, signer):
        return signer.request_id.template_id.field_ids.filtered(
            lambda field: field.role_id == signer.role_id and field.type == 'text'
        )[:1]

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
            'reason': 'Rotate token for portal security test',
        })
        old_token = signer.access_token
        wizard.action_apply_contact_correction()
        signer.invalidate_recordset(['access_token'])
        self.assertNotEqual(signer.access_token, old_token)
        return old_token, signer.access_token

    def _submit_signer_successfully(self, bundle, *, signer_key='signer', token_key='token', value='Signed Value'):
        signer = self.env['open.sign.request.signer'].browse(bundle[signer_key].id)
        field = self._get_text_field_for_signer(signer)
        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={bundle[token_key]}",
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=revision,
                values=[{'field_id': field.id, 'value': value}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle[token_key],
            ),
        )
        self.assertTrue(response['ok'])
        return response

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
        elif status == 'cancelled':
            sign_request.action_cancel()
        elif status == 'voided':
            signer.sudo().write({'state': 'signed', 'signed_at': now})
            sign_request._transition_to('in_progress', {'last_event_at': now})
            attachment = self._create_attachment_static(
                self.env,
                f"{bundle['request'].name}_voided_final.pdf",
                res_model='open.sign.request',
            )
            sign_request.sudo().write({
                'final_attachment_id': attachment.id,
                'final_pdf_sha256': '1' * 64,
            })
            sign_request.action_complete()
            sign_request.action_void()
        else:
            raise AssertionError(f'Unsupported status transition for test helper: {status}')
        sign_request.invalidate_recordset(['status', 'lock_version'])
        signer.invalidate_recordset(['state'])
        return sign_request, signer

    def _assert_no_security_audit_leak(self, sign_request, *forbidden_values):
        audits = self.env['open.sign.audit.log'].search([
            ('request_id', '=', sign_request.id),
            ('event_type', 'in', ('notification_failed', 'notification_skipped', 'notification_queued')),
        ])
        for audit in audits:
            self._assert_no_url_or_token_leak(audit.metadata_json or {}, *forbidden_values)

    def test_signer_page_denies_wrong_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Wrong Token Page',
            owner=self.open_sign_user,
        )
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}?access_token={wrong_token}",
            allow_redirects=False,
        )
        self._assert_redirect_denied(response, wrong_token)

    def test_signer_page_denies_near_match_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Near Match Page',
            owner=self.open_sign_user,
        )
        token = bundle['token']
        bad_tokens = (
            f'x{token[1:]}',
            f'{token[:-1]}{"0" if token[-1] != "0" else "1"}',
            f'{token}x',
        )

        self.authenticate(None, None)
        for bad_token in bad_tokens:
            with self.subTest(bad_token=bad_token):
                response = self.url_open(
                    f"/my/sign/{bundle['signer'].id}?access_token={bad_token}",
                    allow_redirects=False,
                )
                self._assert_redirect_denied(response, bad_token)

    def test_missing_token_public_is_denied_on_page_and_actions(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Missing Token Public',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        consent_hash = self._expected_consent_hash()

        self.authenticate(None, None)

        page_response = self.url_open(f"/my/sign/{signer.id}", allow_redirects=False)
        self._assert_redirect_denied(page_response)

        document_response = self.url_open(f"/my/sign/{signer.id}/document", allow_redirects=False)
        self._assert_redirect_denied(document_response)

        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'missing token save'}],
            ),
        )
        self._assert_json_error(save_response, 'invalid_token')

        submit_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'missing token submit'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
            ),
        )
        self._assert_json_error(submit_response, 'invalid_token')

        decline_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='missing token decline',
            ),
        )
        self._assert_json_error(decline_response, 'invalid_token')

    def test_save_denies_wrong_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Wrong Token Save',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'wrong token save'}],
                access_token=wrong_token,
            ),
        )
        self._assert_json_error(response, 'invalid_token', wrong_token)

    def test_submit_denies_wrong_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Wrong Token Submit',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        wrong_token = self._mutate_token(bundle['token'])
        consent_hash = self._expected_consent_hash()

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'wrong token submit'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=wrong_token,
            ),
        )
        self._assert_json_error(response, 'invalid_token', wrong_token)

    def test_decline_denies_wrong_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Wrong Token Decline',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='wrong token decline',
                access_token=wrong_token,
            ),
        )
        self._assert_json_error(response, 'invalid_token', wrong_token)

    def test_document_denies_wrong_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Wrong Token Document',
            owner=self.open_sign_user,
        )
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{bundle['signer'].id}/document?access_token={wrong_token}",
            allow_redirects=False,
        )
        self._assert_redirect_denied(response, wrong_token)

    def test_internal_mismatched_partner_denied_on_page_and_actions(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Internal Mismatch',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        consent_hash = self._expected_consent_hash()

        self.authenticate(self.open_sign_outsider.login, self.open_sign_outsider.login)

        page_response = self.url_open(f"/my/sign/{signer.id}", allow_redirects=False)
        self._assert_redirect_denied(page_response)

        document_response = self.url_open(f"/my/sign/{signer.id}/document", allow_redirects=False)
        self._assert_redirect_denied(document_response)

        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'outsider save'}],
            ),
        )
        self._assert_json_error(save_response, 'invalid_token')

        submit_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'outsider submit'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
            ),
        )
        self._assert_json_error(submit_response, 'invalid_token')

        decline_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='outsider decline',
            ),
        )
        self._assert_json_error(decline_response, 'invalid_token')

    def test_internal_exact_partner_can_open_and_mutate_without_token(self):
        save_bundle = self._create_portal_session(
            self.env,
            name='Portal Security Internal Save',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        decline_bundle = self._create_portal_session(
            self.env,
            name='Portal Security Internal Decline',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        signer_save = self.env['open.sign.request.signer'].browse(save_bundle['signer'].id)
        signer_decline = self.env['open.sign.request.signer'].browse(decline_bundle['signer'].id)
        save_field = self._get_text_field_for_signer(signer_save)

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)

        page_response = self.url_open(f"/my/sign/{signer_save.id}", allow_redirects=False)
        self.assertEqual(page_response.status_code, 200)

        document_response = self.url_open(f"/my/sign/{signer_save.id}/document", allow_redirects=False)
        self.assertEqual(document_response.status_code, 200)
        self.assertIn('application/pdf', document_response.headers.get('content-type'))

        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer_save.id}/save",
            self._build_payload(
                revision=signer_save.request_id.lock_version,
                values=[{'field_id': save_field.id, 'value': 'internal fallback save'}],
            ),
        )
        self.assertTrue(save_response['ok'])

        decline_response = self.make_jsonrpc_request(
            f"/my/sign/{signer_decline.id}/decline",
            self._build_decline_payload(
                revision=signer_decline.request_id.lock_version,
                reason='internal fallback decline',
            ),
        )
        self.assertTrue(decline_response['ok'])

    def test_rotated_old_token_denied_on_signer_page(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Rotated Page',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_token, new_token = self._rotate_signer_token(signer)

        self.authenticate(None, None)
        old_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={old_token}",
            allow_redirects=False,
        )
        new_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={new_token}",
            allow_redirects=False,
        )
        self._assert_redirect_denied(old_response, old_token)
        self.assertEqual(new_response.status_code, 200)
        self.assertNotIn(old_token, new_response.text)

    def test_rotated_old_token_denied_on_document(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Rotated Document',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_token, new_token = self._rotate_signer_token(signer)

        self.authenticate(None, None)
        old_response = self.url_open(
            f"/my/sign/{signer.id}/document?access_token={old_token}",
            allow_redirects=False,
        )
        new_response = self.url_open(
            f"/my/sign/{signer.id}/document?access_token={new_token}",
            allow_redirects=False,
        )
        self._assert_redirect_denied(old_response, old_token)
        self.assertEqual(new_response.status_code, 200)
        self.assertIn('application/pdf', new_response.headers.get('content-type'))

    def test_rotated_old_token_denied_on_save(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Rotated Save',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        old_token, new_token = self._rotate_signer_token(signer)

        self.authenticate(None, None)
        old_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'old token save'}],
                access_token=old_token,
            ),
        )
        self._assert_json_error(old_response, 'invalid_token', old_token)

        new_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'new token save'}],
                access_token=new_token,
            ),
        )
        self.assertTrue(new_response['ok'])

    def test_rotated_old_token_denied_on_submit(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Rotated Submit',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        old_token, new_token = self._rotate_signer_token(signer)
        consent_hash = self._expected_consent_hash()

        self.authenticate(None, None)
        old_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'old token submit'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=old_token,
            ),
        )
        self._assert_json_error(old_response, 'invalid_token', old_token)

        new_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'new token submit'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=new_token,
            ),
        )
        self.assertTrue(new_response['ok'])

    def test_rotated_old_token_denied_on_decline(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Rotated Decline',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_token, new_token = self._rotate_signer_token(signer)

        self.authenticate(None, None)
        old_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='old token decline',
                access_token=old_token,
            ),
        )
        self._assert_json_error(old_response, 'invalid_token', old_token)

        new_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='new token decline',
                access_token=new_token,
            ),
        )
        self.assertTrue(new_response['ok'])

    def test_stale_submit_returns_stale_revision(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Stale Submit',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        field = self._get_text_field_for_signer(signer)
        stale_revision = sign_request.lock_version
        sign_request.sudo().write({'lock_version': stale_revision + 1})
        consent_hash = self._expected_consent_hash()

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=stale_revision,
                values=[{'field_id': field.id, 'value': 'stale submit'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self._assert_json_error(response, 'stale_revision')
        signer.invalidate_recordset(['state'])
        sign_request.invalidate_recordset(['status'])
        self.assertEqual(signer.state, 'pending')
        self.assertEqual(sign_request.status, 'sent')

    def test_stale_save_returns_stale_revision(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Stale Save',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        field = self._get_text_field_for_signer(signer)
        stale_revision = sign_request.lock_version
        sign_request.sudo().write({'lock_version': stale_revision + 1})

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=stale_revision,
                values=[{'field_id': field.id, 'value': 'stale save'}],
                access_token=bundle['token'],
            ),
        )
        self._assert_json_error(response, 'stale_revision')
        signer.invalidate_recordset(['state'])
        sign_request.invalidate_recordset(['status'])
        self.assertEqual(signer.state, 'pending')
        self.assertEqual(sign_request.status, 'sent')

    def test_stale_decline_returns_stale_revision(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Stale Decline',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        stale_revision = sign_request.lock_version
        sign_request.sudo().write({'lock_version': stale_revision + 1})

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=stale_revision,
                reason='stale decline',
                access_token=bundle['token'],
            ),
        )
        self._assert_json_error(response, 'stale_revision')
        signer.invalidate_recordset(['state'])
        sign_request.invalidate_recordset(['status'])
        self.assertEqual(signer.state, 'pending')
        self.assertEqual(sign_request.status, 'sent')

    def test_stale_revision_beats_order_block(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Security Stale Beats Order',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        sign_request = self.env['open.sign.request'].browse(bundle['request'].id)
        stale_revision = sign_request.lock_version
        sign_request.sudo().write({'lock_version': stale_revision + 1})

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_second'].id}/save",
            self._build_payload(
                revision=stale_revision,
                values=[{'field_id': bundle['field_second'].id, 'value': 'waiting stale save'}],
                access_token=bundle['token_second'],
            ),
        )
        self._assert_json_error(response, 'stale_revision')

    def test_submit_returns_request_locked_under_lock_conflict(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Submit Lock',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        consent_hash = self._expected_consent_hash()

        self.authenticate(None, None)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/submit",
                self._build_payload(
                    revision=signer.request_id.lock_version,
                    values=[{'field_id': field.id, 'value': 'locked submit'}],
                    consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                    access_token=bundle['token'],
                ),
            )
        self._assert_json_error(response, 'request_locked')

    def test_decline_returns_request_locked_under_lock_conflict(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Decline Lock',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._lock_request_for_update',
            side_effect=LockNotAvailable(),
        ):
            response = self.make_jsonrpc_request(
                f"/my/sign/{signer.id}/decline",
                self._build_decline_payload(
                    revision=signer.request_id.lock_version,
                    reason='locked decline',
                    access_token=bundle['token'],
                ),
            )
        self._assert_json_error(response, 'request_locked')

    def test_duplicate_submit_after_submit_is_denied_without_mutation(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Duplicate Submit',
            owner=self.open_sign_user,
        )
        self._submit_signer_successfully(bundle, value='First submit')

        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        field = self._get_text_field_for_signer(signer)
        consent_hash = self._expected_consent_hash()
        sign_request.invalidate_recordset(['lock_version', 'status'])
        signer.invalidate_recordset(['state'])
        lock_version = sign_request.lock_version
        audit_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
        ])

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_payload(
                revision=sign_request.lock_version,
                values=[{'field_id': field.id, 'value': 'Second submit'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle['token'],
            ),
        )
        self._assert_json_validation_error(response)

        signer.invalidate_recordset(['state'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'signed')
        self.assertEqual(sign_request.status, 'partially_signed')
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertEqual(
            self.env['open.sign.audit.log'].search_count([
                ('request_id', '=', sign_request.id),
                ('signer_id', '=', signer.id),
            ]),
            audit_count,
        )

    def test_duplicate_decline_after_decline_is_denied_without_mutation(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Duplicate Decline',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.authenticate(None, None)
        first_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='first decline',
                access_token=bundle['token'],
            ),
        )
        self.assertTrue(first_response['ok'])

        signer.invalidate_recordset(['state'])
        sign_request = signer.request_id
        sign_request.invalidate_recordset(['status', 'lock_version'])
        lock_version = sign_request.lock_version
        audit_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer.id),
        ])

        second_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=sign_request.lock_version,
                reason='second decline',
                access_token=bundle['token'],
            ),
        )
        self._assert_json_error(second_response, 'validation_error')

        signer.invalidate_recordset(['state'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer.state, 'declined')
        self.assertEqual(sign_request.status, 'declined')
        self.assertEqual(sign_request.lock_version, lock_version)
        self.assertEqual(
            self.env['open.sign.audit.log'].search_count([
                ('request_id', '=', sign_request.id),
                ('signer_id', '=', signer.id),
            ]),
            audit_count,
        )

    def test_invalid_token_errors_do_not_echo_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Invalid Token Leak',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={wrong_token}",
            allow_redirects=False,
        )
        self._assert_redirect_denied(page_response, wrong_token)

        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'bad token'}],
                access_token=wrong_token,
            ),
        )
        self._assert_json_error(save_response, 'invalid_token', wrong_token)

    def test_nonexistent_signer_fails_safely(self):
        self.authenticate(None, None)

        page_response = self.url_open('/my/sign/999999?access_token=abc123', allow_redirects=False)
        self._assert_redirect_denied(page_response, 'abc123')

        document_response = self.url_open('/my/sign/999999/document?access_token=abc123', allow_redirects=False)
        self._assert_redirect_denied(document_response, 'abc123')

        save_response = self.make_jsonrpc_request(
            '/my/sign/999999/save',
            self._build_payload(
                revision=0,
                values=[],
                access_token='abc123',
            ),
        )
        self._assert_json_error(save_response, 'invalid_token', 'abc123')

    def test_document_route_allows_waiting_signer_with_valid_token(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Security Waiting Document',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{signer_second.id}/document?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.headers.get('content-type'))

    def test_document_route_denies_cancelled_and_voided_even_with_prior_token(self):
        for status in ('cancelled', 'voided'):
            with self.subTest(status=status):
                bundle = self._create_portal_session(
                    self.env,
                    name=f'Portal Security Document {status.title()}',
                    owner=self.open_sign_user,
                )
                self._transition_bundle_request_to_status(bundle, status)

                self.authenticate(None, None)
                response = self.url_open(
                    f"/my/sign/{bundle['signer'].id}/document?access_token={bundle['token']}",
                    allow_redirects=False,
                )
                self._assert_redirect_denied(response, bundle['token'])

    def test_document_route_allows_terminal_review_with_valid_token(self):
        for status in ('completed', 'declined', 'expired'):
            with self.subTest(status=status):
                bundle = self._create_portal_session(
                    self.env,
                    name=f'Portal Security Terminal Document {status.title()}',
                    owner=self.open_sign_user,
                )
                self._transition_bundle_request_to_status(bundle, status)

                self.authenticate(None, None)
                response = self.url_open(
                    f"/my/sign/{bundle['signer'].id}/document?access_token={bundle['token']}",
                    allow_redirects=False,
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn('application/pdf', response.headers.get('content-type'))

    def test_new_token_works_after_rotation(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security New Token Works',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        old_token, new_token = self._rotate_signer_token(signer)

        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={new_token}",
            allow_redirects=False,
        )
        self.assertEqual(page_response.status_code, 200)

        document_response = self.url_open(
            f"/my/sign/{signer.id}/document?access_token={new_token}",
            allow_redirects=False,
        )
        self.assertEqual(document_response.status_code, 200)

        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'new token works'}],
                access_token=new_token,
            ),
        )
        self.assertTrue(save_response['ok'])
        self._assert_no_url_or_token_leak(save_response, old_token)

    def test_terminal_request_mutation_denials_remain_consistent(self):
        for status in ('completed', 'declined', 'expired'):
            with self.subTest(status=status):
                bundle = self._create_portal_session(
                    self.env,
                    name=f'Portal Security Terminal Mutate {status.title()}',
                    owner=self.open_sign_user,
                )
                self._transition_bundle_request_to_status(bundle, status)
                signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
                field = self._get_text_field_for_signer(signer)
                consent_hash = self._expected_consent_hash()

                self.authenticate(None, None)

                save_response = self.make_jsonrpc_request(
                    f"/my/sign/{signer.id}/save",
                    self._build_payload(
                        revision=signer.request_id.lock_version,
                        values=[{'field_id': field.id, 'value': 'terminal save'}],
                        access_token=bundle['token'],
                    ),
                )
                self._assert_json_validation_error(save_response)

                submit_response = self.make_jsonrpc_request(
                    f"/my/sign/{signer.id}/submit",
                    self._build_payload(
                        revision=signer.request_id.lock_version,
                        values=[{'field_id': field.id, 'value': 'terminal submit'}],
                        consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                        access_token=bundle['token'],
                    ),
                )
                self._assert_json_validation_error(submit_response)

                decline_response = self.make_jsonrpc_request(
                    f"/my/sign/{signer.id}/decline",
                    self._build_decline_payload(
                        revision=signer.request_id.lock_version,
                        reason='terminal decline',
                        access_token=bundle['token'],
                    ),
                )
                self._assert_json_validation_error(decline_response)

    def test_waiting_signer_cannot_save_even_with_direct_jsonrpc(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Security Waiting Save',
            owner=self.open_sign_user,
            ordered_signing=True,
        )

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_second'].id}/save",
            self._build_payload(
                revision=bundle['request'].lock_version,
                values=[{'field_id': bundle['field_second'].id, 'value': 'waiting save'}],
                access_token=bundle['token_second'],
            ),
        )
        self._assert_json_error(response, 'signing_order_blocked')

    def test_waiting_signer_cannot_submit_even_with_direct_jsonrpc(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Security Waiting Submit',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        consent_hash = self._expected_consent_hash()

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{bundle['signer_second'].id}/submit",
            self._build_payload(
                revision=bundle['request'].lock_version,
                values=[{'field_id': bundle['field_second'].id, 'value': 'waiting submit'}],
                consent={'accepted': True, 'text_hash': consent_hash, 'timezone': 'UTC'},
                access_token=bundle['token_second'],
            ),
        )
        self._assert_json_error(response, 'signing_order_blocked')

    def test_waiting_signer_can_still_decline(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Security Waiting Decline',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)

        self.authenticate(None, None)
        response = self.make_jsonrpc_request(
            f"/my/sign/{signer_second.id}/decline",
            self._build_decline_payload(
                revision=signer_second.request_id.lock_version,
                reason='waiting decline',
                access_token=bundle['token_second'],
            ),
        )
        self.assertTrue(response['ok'])

    def test_waiting_page_visit_does_not_create_open_evidence(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Security Waiting Evidence',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id

        self.authenticate(None, None)
        response = self.url_open(
            f"/my/sign/{signer_second.id}?access_token={bundle['token_second']}",
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        signer_second.invalidate_recordset(['state', 'last_opened_at', 'ip_last'])
        sign_request.invalidate_recordset(['status', 'lock_version'])
        self.assertEqual(signer_second.state, 'pending')
        self.assertFalse(signer_second.last_opened_at)
        self.assertFalse(signer_second.ip_last)
        self.assertEqual(sign_request.status, 'sent')
        self.assertEqual(sign_request.lock_version, 0)
        self.assertFalse(self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', sign_request.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'signer_opened'),
        ]))

    def test_rotated_token_denial_does_not_leak_old_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Security Old Token Leak',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_token, _new_token = self._rotate_signer_token(signer)

        self.authenticate(None, None)
        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[],
                access_token=old_token,
            ),
        )
        self._assert_json_error(save_response, 'invalid_token', old_token)
        self._assert_no_security_audit_leak(signer.request_id, old_token)
