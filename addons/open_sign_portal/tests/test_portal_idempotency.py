# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from uuid import uuid4

from odoo import Command
from odoo.addons.open_sign_portal.services import idempotency_service
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.open_sign_portal.tests.common import (
    CONSENT_HASH_RE,
    REQUEST_REVISION_RE,
    OpenSignPortalTestMixin,
)


SHA256_HEX_RE = re.compile(r'^[0-9a-f]{64}$')


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalIdempotency(TransactionCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Open Sign Idempotency Company B'})

        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_idempotency_user',
            groups='open_sign.group_open_sign_user',
            company_id=cls.company_a.id,
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_idempotency_manager',
            groups='open_sign.group_open_sign_manager',
            company_id=cls.company_a.id,
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_portal_idempotency_auditor',
            groups='open_sign.group_open_sign_auditor',
            company_id=cls.company_a.id,
        )
        cls.system_user_single = new_test_user(
            cls.env,
            login='open_sign_portal_idempotency_system_single',
            groups='base.group_system',
            company_id=cls.company_a.id,
        )
        cls.system_user_multi = new_test_user(
            cls.env,
            login='open_sign_portal_idempotency_system_multi',
            groups='base.group_system',
            company_id=cls.company_a.id,
        )

        for user in (cls.open_sign_user, cls.open_sign_manager, cls.open_sign_auditor, cls.system_user_single):
            user.write({
                'company_id': cls.company_a.id,
                'company_ids': [Command.set([cls.company_a.id])],
            })
        cls.system_user_multi.write({
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id, cls.company_b.id])],
        })

        cls.bundle_a = cls._create_portal_session(
            cls.env,
            name='Portal Idempotency Company A',
            owner=cls.env.user,
        )
        env_company_b = cls.env['open.sign.request'].with_company(cls.company_b).env
        cls.bundle_b = cls._create_portal_session(
            env_company_b,
            name='Portal Idempotency Company B',
            owner=cls.env.user,
        )

        cls.existing_record_a = cls.env['open.sign.portal.idempotency'].sudo().create({
            'request_signer_id': cls.bundle_a['signer'].id,
            'endpoint': 'submit',
            'idempotency_key': str(uuid4()),
            'request_hash': '0' * 64,
            'response_json': {'ok': True},
            'state': 'completed',
            'expires_at': '2099-01-01 00:00:00',
        })
        cls.existing_record_b = cls.env['open.sign.portal.idempotency'].sudo().create({
            'request_signer_id': cls.bundle_b['signer'].id,
            'endpoint': 'decline',
            'idempotency_key': str(uuid4()),
            'request_hash': '1' * 64,
            'response_json': {'ok': True},
            'state': 'completed',
            'expires_at': '2099-01-01 00:00:00',
        })

    def test_portal_idempotency_unique_key_per_signer_endpoint(self):
        key = str(uuid4())
        submit_hash = idempotency_service.build_submit_request_hash(
            [{'field_id': 10, 'value': 'alpha'}],
            consent_accepted=True,
            consent_hash='a' * 64,
            signer_timezone='UTC',
        )
        decline_hash = idempotency_service.build_decline_request_hash('decline reason')

        submit_result, _submit_record = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='submit',
            idempotency_key=key,
            request_hash=submit_hash,
        )
        decline_result, _decline_record = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='decline',
            idempotency_key=key,
            request_hash=decline_hash,
        )

        self.assertEqual(submit_result, 'claimed')
        self.assertEqual(decline_result, 'claimed')

    def test_portal_idempotency_request_hash_format(self):
        request_hash = idempotency_service.build_submit_request_hash(
            [{'field_id': 10, 'value': 'alpha'}],
            consent_accepted=True,
            consent_hash='a' * 64,
            signer_timezone='UTC',
        )
        self.assertRegex(request_hash, SHA256_HEX_RE)
        with self.assertRaises(ValidationError):
            self.env['open.sign.portal.idempotency'].sudo().create({
                'request_signer_id': self.bundle_a['signer'].id,
                'endpoint': 'submit',
                'idempotency_key': str(uuid4()),
                'request_hash': 'not-a-hash',
                'state': 'failed',
                'expires_at': '2099-01-02 00:00:00',
            })

    def test_failed_row_can_be_reclaimed_with_same_hash(self):
        key = str(uuid4())
        request_hash = idempotency_service.build_decline_request_hash('reclaim me')
        _result, record = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='decline',
            idempotency_key=key,
            request_hash=request_hash,
        )
        idempotency_service.mark_failed(record)

        result_again, record_again = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='decline',
            idempotency_key=key,
            request_hash=request_hash,
        )

        self.assertEqual(result_again, 'claimed')
        self.assertEqual(record_again.id, record.id)
        self.assertEqual(record_again.state, 'in_progress')
        self.assertFalse(record_again.response_json)

    def test_same_key_different_hash_is_conflict(self):
        key = str(uuid4())
        first_hash = idempotency_service.build_decline_request_hash('first')
        second_hash = idempotency_service.build_decline_request_hash('second')
        _result, record = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='decline',
            idempotency_key=key,
            request_hash=first_hash,
        )
        idempotency_service.mark_failed(record)

        conflict_result, conflict_record = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='decline',
            idempotency_key=key,
            request_hash=second_hash,
        )

        self.assertEqual(conflict_result, 'conflict')
        self.assertEqual(conflict_record.id, record.id)

    def test_expired_row_is_ignored_and_reclaimed_as_new_claim(self):
        key = str(uuid4())
        request_hash = idempotency_service.build_decline_request_hash('expired replay')
        expired_record = self.env['open.sign.portal.idempotency'].sudo().create({
            'request_signer_id': self.bundle_a['signer'].id,
            'endpoint': 'decline',
            'idempotency_key': key,
            'request_hash': request_hash,
            'response_json': {'ok': True},
            'state': 'completed',
            'expires_at': '2000-01-01 00:00:00',
        })

        result, record = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='decline',
            idempotency_key=key,
            request_hash=request_hash,
        )

        self.assertEqual(result, 'claimed')
        self.assertNotEqual(record.id, expired_record.id)
        self.assertFalse(self.env['open.sign.portal.idempotency'].sudo().browse(expired_record.id).exists())
        self.assertEqual(record.state, 'in_progress')

    def test_expired_row_does_not_conflict(self):
        key = str(uuid4())
        expired_record = self.env['open.sign.portal.idempotency'].sudo().create({
            'request_signer_id': self.bundle_a['signer'].id,
            'endpoint': 'decline',
            'idempotency_key': key,
            'request_hash': idempotency_service.build_decline_request_hash('expired first'),
            'state': 'failed',
            'expires_at': '2000-01-01 00:00:00',
        })

        result, record = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='decline',
            idempotency_key=key,
            request_hash=idempotency_service.build_decline_request_hash('fresh second'),
        )

        self.assertEqual(result, 'claimed')
        self.assertNotEqual(record.id, expired_record.id)
        self.assertFalse(self.env['open.sign.portal.idempotency'].sudo().browse(expired_record.id).exists())

    def test_expired_in_progress_row_does_not_return_request_locked(self):
        key = str(uuid4())
        request_hash = idempotency_service.build_decline_request_hash('expired locked')
        expired_record = self.env['open.sign.portal.idempotency'].sudo().create({
            'request_signer_id': self.bundle_a['signer'].id,
            'endpoint': 'decline',
            'idempotency_key': key,
            'request_hash': request_hash,
            'state': 'in_progress',
            'expires_at': '2000-01-01 00:00:00',
        })

        result, record = idempotency_service.claim_or_resolve(
            self.bundle_a['signer'],
            endpoint='decline',
            idempotency_key=key,
            request_hash=request_hash,
        )

        self.assertEqual(result, 'claimed')
        self.assertNotEqual(record.id, expired_record.id)
        self.assertFalse(self.env['open.sign.portal.idempotency'].sudo().browse(expired_record.id).exists())

    def test_idempotency_model_is_system_only(self):
        model_user = self.env['open.sign.portal.idempotency'].with_user(self.open_sign_user)
        model_manager = self.env['open.sign.portal.idempotency'].with_user(self.open_sign_manager)
        model_auditor = self.env['open.sign.portal.idempotency'].with_user(self.open_sign_auditor)

        for model in (model_user, model_manager, model_auditor):
            with self.assertRaises(AccessError):
                model.check_access('read')
            with self.assertRaises(AccessError):
                model.create({
                    'request_signer_id': self.bundle_a['signer'].id,
                    'endpoint': 'submit',
                    'idempotency_key': str(uuid4()),
                    'request_hash': '2' * 64,
                    'expires_at': '2099-01-02 00:00:00',
                })
            with self.assertRaises(AccessError):
                self.existing_record_a.with_user(model.env.user).write({'state': 'failed'})
            with self.assertRaises(AccessError):
                self.existing_record_a.with_user(model.env.user).unlink()

        system_model = self.env['open.sign.portal.idempotency'].with_user(self.system_user_single)
        system_record = system_model.create({
            'request_signer_id': self.bundle_a['signer'].id,
            'endpoint': 'submit',
            'idempotency_key': str(uuid4()),
            'request_hash': '3' * 64,
            'expires_at': '2099-01-03 00:00:00',
        })
        self.assertTrue(system_model.search([('id', '=', system_record.id)]))
        system_record.write({'state': 'failed'})
        system_record.unlink()

    def test_idempotency_model_system_access_is_company_scoped(self):
        visible_single = set(
            self.env['open.sign.portal.idempotency'].with_user(self.system_user_single).search([
                ('id', 'in', [self.existing_record_a.id, self.existing_record_b.id]),
            ]).ids
        )
        visible_multi = set(
            self.env['open.sign.portal.idempotency'].with_user(self.system_user_multi).search([
                ('id', 'in', [self.existing_record_a.id, self.existing_record_b.id]),
            ]).ids
        )
        self.assertEqual(visible_single, {self.existing_record_a.id})
        self.assertEqual(visible_multi, {self.existing_record_a.id, self.existing_record_b.id})

    def test_idempotency_response_json_is_system_only(self):
        user_fields = self.env['open.sign.portal.idempotency'].with_user(self.open_sign_user).fields_get()
        manager_fields = self.env['open.sign.portal.idempotency'].with_user(self.open_sign_manager).fields_get()
        system_fields = self.env['open.sign.portal.idempotency'].fields_get()

        self.assertNotIn('response_json', user_fields)
        self.assertNotIn('response_json', manager_fields)
        self.assertIn('response_json', system_fields)

    def test_conflict_audit_marker_field_is_system_only(self):
        user_fields = self.env['open.sign.portal.idempotency'].with_user(self.open_sign_user).fields_get()
        manager_fields = self.env['open.sign.portal.idempotency'].with_user(self.open_sign_manager).fields_get()
        system_fields = self.env['open.sign.portal.idempotency'].fields_get()

        self.assertNotIn('conflict_logged_at', user_fields)
        self.assertNotIn('conflict_logged_at', manager_fields)
        self.assertIn('conflict_logged_at', system_fields)

    def test_idempotency_model_has_no_operator_ui_surface(self):
        self.assertEqual(
            self.env['ir.actions.act_window'].sudo().search_count([
                ('res_model', '=', 'open.sign.portal.idempotency'),
            ]),
            0,
        )
        for menu in self.env['ir.ui.menu'].sudo().search([('action', '!=', False)]):
            action = menu.action
            if action and action._name == 'ir.actions.act_window':
                self.assertNotEqual(action.res_model, 'open.sign.portal.idempotency')


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalIdempotencyHttp(HttpCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_idempotency_http_user',
            password='open_sign_portal_idempotency_http_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.idempotency@example.com'

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

    def _build_submit_payload(self, *, revision, field_id, value, consent_hash, access_token, idempotency_key):
        return {
            'values': [{'field_id': field_id, 'value': value}],
            'consent': {
                'accepted': True,
                'text_hash': consent_hash,
                'timezone': 'UTC',
            },
            'idempotency_key': idempotency_key,
            'request_revision': revision,
            'access_token': access_token,
        }

    def _build_decline_payload(self, *, revision, reason, access_token, idempotency_key):
        return {
            'reason': reason,
            'idempotency_key': idempotency_key,
            'request_revision': revision,
            'access_token': access_token,
        }

    def _open_submit_context(self, bundle, *, signer_key='signer', token_key='token'):
        signer = self.env['open.sign.request.signer'].browse(bundle[signer_key].id)
        field = self._get_text_field_for_signer(signer)
        self.assertTrue(field)
        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer.id}?access_token={bundle[token_key]}",
            allow_redirects=False,
        )
        self.assertEqual(page_response.status_code, 200)
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        return signer, field, consent_hash, revision

    def _submit_with_payload(self, signer, payload):
        return self.make_jsonrpc_request(f'/my/sign/{signer.id}/submit', payload)

    def _decline_with_payload(self, signer, payload):
        return self.make_jsonrpc_request(f'/my/sign/{signer.id}/decline', payload)

    def test_submit_exact_duplicate_replays_committed_success(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Submit Replay', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Replay submit',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )

        first_response = self._submit_with_payload(signer, dict(payload))
        second_response = self._submit_with_payload(signer, dict(payload))

        self.assertTrue(first_response['ok'])
        self.assertEqual(second_response, first_response)

    def test_submit_duplicate_same_key_different_payload_returns_idempotency_conflict(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Submit Conflict', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        first_payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='First payload',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )
        conflict_payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Second payload',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )

        self.assertTrue(self._submit_with_payload(signer, first_payload)['ok'])
        conflict_response = self._submit_with_payload(signer, conflict_payload)

        self.assertFalse(conflict_response['ok'])
        self.assertEqual(conflict_response['error_code'], 'idempotency_conflict')
        self.assertEqual(conflict_response['message'], 'This action conflicts with an earlier request. Refresh and try again.')

    def test_submit_repeated_conflict_logs_one_idempotency_conflict_audit(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Submit Conflict Audit', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        first_payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='First conflict audit payload',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )
        second_payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Second conflict audit payload',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )

        self.assertTrue(self._submit_with_payload(signer, first_payload)['ok'])
        first_conflict = self._submit_with_payload(signer, dict(second_payload))
        second_conflict = self._submit_with_payload(signer, dict(second_payload))

        self.assertEqual(first_conflict['error_code'], 'idempotency_conflict')
        self.assertEqual(second_conflict['error_code'], 'idempotency_conflict')
        self.assertEqual(
            self.env['open.sign.audit.log'].search_count([
                ('request_id', '=', signer.request_id.id),
                ('signer_id', '=', signer.id),
                ('event_type', '=', 'idempotency_conflict'),
            ]),
            1,
        )

    def test_submit_replay_does_not_duplicate_signer_submitted_audit(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Submit Audit', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Audit replay',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )

        self.assertTrue(self._submit_with_payload(signer, dict(payload))['ok'])
        audit_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', signer.request_id.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_submitted'),
        ])
        self.assertEqual(audit_count, 1)

        replay_response = self._submit_with_payload(signer, dict(payload))
        self.assertTrue(replay_response['ok'])
        self.assertEqual(
            self.env['open.sign.audit.log'].search_count([
                ('request_id', '=', signer.request_id.id),
                ('signer_id', '=', signer.id),
                ('event_type', '=', 'signer_submitted'),
            ]),
            audit_count,
        )

    def test_submit_replay_does_not_duplicate_next_wave_invitation_queueing(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Idempotency Next Wave Replay',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_first = self.env['open.sign.request.signer'].browse(bundle['signer_first'].id)
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        self.authenticate(None, None)
        page_response = self.url_open(
            f"/my/sign/{signer_first.id}?access_token={bundle['token_first']}",
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        key = str(uuid4())
        payload = self._build_submit_payload(
            revision=revision,
            field_id=bundle['field_first'].id,
            value='Wave one',
            consent_hash=consent_hash,
            access_token=bundle['token_first'],
            idempotency_key=key,
        )
        mail_model = self.env['mail.mail'].sudo()
        mail_count_before = mail_model.search_count([('email_to', '=', signer_second.email)])

        self.assertTrue(self._submit_with_payload(signer_first, dict(payload))['ok'])
        notification_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', signer_first.request_id.id),
            ('signer_id', '=', signer_second.id),
            ('event_type', '=', 'notification_queued'),
        ])
        self.assertEqual(
            mail_model.search_count([('email_to', '=', signer_second.email)]),
            mail_count_before + 1,
        )

        replay_response = self._submit_with_payload(signer_first, dict(payload))
        self.assertTrue(replay_response['ok'])
        self.assertEqual(
            mail_model.search_count([('email_to', '=', signer_second.email)]),
            mail_count_before + 1,
        )
        self.assertEqual(
            self.env['open.sign.audit.log'].search_count([
                ('request_id', '=', signer_first.request_id.id),
                ('signer_id', '=', signer_second.id),
                ('event_type', '=', 'notification_queued'),
            ]),
            notification_count,
        )

    def test_submit_same_key_after_failed_validation_can_retry_with_same_hash(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Retry Same Hash', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        stale_payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Retry me',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )
        signer.request_id.sudo().write({'lock_version': revision + 1})

        stale_response = self._submit_with_payload(signer, dict(stale_payload))
        self.assertFalse(stale_response['ok'])
        self.assertEqual(stale_response['error_code'], 'stale_revision')

        retry_payload = self._build_submit_payload(
            revision=revision + 1,
            field_id=field.id,
            value='Retry me',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )
        retry_response = self._submit_with_payload(signer, retry_payload)
        self.assertTrue(retry_response['ok'])

    def test_submit_same_key_after_failed_validation_with_changed_payload_conflicts(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Retry Conflict', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        stale_payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Retry value',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )
        signer.request_id.sudo().write({'lock_version': revision + 1})

        stale_response = self._submit_with_payload(signer, dict(stale_payload))
        self.assertFalse(stale_response['ok'])
        self.assertEqual(stale_response['error_code'], 'stale_revision')

        conflict_payload = self._build_submit_payload(
            revision=revision + 1,
            field_id=field.id,
            value='Changed retry value',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )
        conflict_response = self._submit_with_payload(signer, conflict_payload)
        self.assertFalse(conflict_response['ok'])
        self.assertEqual(conflict_response['error_code'], 'idempotency_conflict')

    def test_submit_exact_duplicate_success_replay_beats_stale_revision(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Submit Replay Stale', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Replay stale',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )

        first_response = self._submit_with_payload(signer, dict(payload))
        replay_response = self._submit_with_payload(signer, dict(payload))
        self.assertTrue(first_response['ok'])
        self.assertEqual(replay_response, first_response)

    def test_submit_exact_duplicate_success_replay_beats_terminal_state_denial(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Submit Replay Terminal', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Replay terminal',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )

        first_response = self._submit_with_payload(signer, dict(payload))
        signer.invalidate_recordset(['state'])
        self.assertEqual(signer.state, 'signed')
        replay_response = self._submit_with_payload(signer, dict(payload))
        self.assertEqual(replay_response, first_response)

    def test_decline_exact_duplicate_replays_committed_success(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Decline Replay', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        key = str(uuid4())
        payload = self._build_decline_payload(
            revision=signer.request_id.lock_version,
            reason='Replay decline',
            access_token=bundle['token'],
            idempotency_key=key,
        )

        first_response = self._decline_with_payload(signer, dict(payload))
        second_response = self._decline_with_payload(signer, dict(payload))
        self.assertTrue(first_response['ok'])
        self.assertEqual(second_response, first_response)

    def test_decline_duplicate_same_key_different_reason_returns_idempotency_conflict(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Decline Conflict', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        key = str(uuid4())
        first_payload = self._build_decline_payload(
            revision=signer.request_id.lock_version,
            reason='First reason',
            access_token=bundle['token'],
            idempotency_key=key,
        )
        second_payload = self._build_decline_payload(
            revision=signer.request_id.lock_version,
            reason='Second reason',
            access_token=bundle['token'],
            idempotency_key=key,
        )

        self.assertTrue(self._decline_with_payload(signer, first_payload)['ok'])
        conflict_response = self._decline_with_payload(signer, second_payload)
        self.assertFalse(conflict_response['ok'])
        self.assertEqual(conflict_response['error_code'], 'idempotency_conflict')

    def test_decline_repeated_conflict_logs_one_idempotency_conflict_audit(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Decline Conflict Audit', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        key = str(uuid4())
        first_payload = self._build_decline_payload(
            revision=signer.request_id.lock_version,
            reason='First decline conflict audit',
            access_token=bundle['token'],
            idempotency_key=key,
        )
        second_payload = self._build_decline_payload(
            revision=signer.request_id.lock_version,
            reason='Second decline conflict audit',
            access_token=bundle['token'],
            idempotency_key=key,
        )

        self.assertTrue(self._decline_with_payload(signer, first_payload)['ok'])
        first_conflict = self._decline_with_payload(signer, dict(second_payload))
        second_conflict = self._decline_with_payload(signer, dict(second_payload))

        self.assertEqual(first_conflict['error_code'], 'idempotency_conflict')
        self.assertEqual(second_conflict['error_code'], 'idempotency_conflict')
        self.assertEqual(
            self.env['open.sign.audit.log'].search_count([
                ('request_id', '=', signer.request_id.id),
                ('signer_id', '=', signer.id),
                ('event_type', '=', 'idempotency_conflict'),
            ]),
            1,
        )

    def test_decline_replay_does_not_duplicate_signer_declined_audit(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Decline Audit', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        key = str(uuid4())
        payload = self._build_decline_payload(
            revision=signer.request_id.lock_version,
            reason='Decline audit',
            access_token=bundle['token'],
            idempotency_key=key,
        )

        self.assertTrue(self._decline_with_payload(signer, dict(payload))['ok'])
        audit_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', signer.request_id.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'signer_declined'),
        ])
        self.assertEqual(audit_count, 1)

        replay_response = self._decline_with_payload(signer, dict(payload))
        self.assertTrue(replay_response['ok'])
        self.assertEqual(
            self.env['open.sign.audit.log'].search_count([
                ('request_id', '=', signer.request_id.id),
                ('signer_id', '=', signer.id),
                ('event_type', '=', 'signer_declined'),
            ]),
            audit_count,
        )

    def test_decline_replay_does_not_duplicate_owner_notification_queueing(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Decline Notify', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        key = str(uuid4())
        payload = self._build_decline_payload(
            revision=signer.request_id.lock_version,
            reason='Decline notify',
            access_token=bundle['token'],
            idempotency_key=key,
        )
        mail_model = self.env['mail.mail'].sudo()
        owner_mail_before = mail_model.search_count([('email_to', '=', self.open_sign_user.partner_id.email)])

        self.assertTrue(self._decline_with_payload(signer, dict(payload))['ok'])
        notification_count = self.env['open.sign.audit.log'].search_count([
            ('request_id', '=', signer.request_id.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_queued'),
        ])
        self.assertEqual(
            mail_model.search_count([('email_to', '=', self.open_sign_user.partner_id.email)]),
            owner_mail_before + 1,
        )

        replay_response = self._decline_with_payload(signer, dict(payload))
        self.assertTrue(replay_response['ok'])
        self.assertEqual(
            mail_model.search_count([('email_to', '=', self.open_sign_user.partner_id.email)]),
            owner_mail_before + 1,
        )
        self.assertEqual(
            self.env['open.sign.audit.log'].search_count([
                ('request_id', '=', signer.request_id.id),
                ('signer_id', '=', signer.id),
                ('event_type', '=', 'notification_queued'),
            ]),
            notification_count,
        )

    def test_decline_exact_duplicate_success_replay_beats_terminal_state_denial(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Decline Replay Terminal', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        key = str(uuid4())
        payload = self._build_decline_payload(
            revision=signer.request_id.lock_version,
            reason='Replay terminal decline',
            access_token=bundle['token'],
            idempotency_key=key,
        )

        first_response = self._decline_with_payload(signer, dict(payload))
        replay_response = self._decline_with_payload(signer, dict(payload))
        self.assertEqual(replay_response, first_response)

    def test_submit_same_key_in_progress_returns_request_locked(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Submit Locked', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        request_hash = idempotency_service.build_submit_request_hash(
            [{'field_id': field.id, 'value': 'Locked submit'}],
            consent_accepted=True,
            consent_hash=consent_hash,
            signer_timezone='UTC',
        )
        self.env['open.sign.portal.idempotency'].sudo().create({
            'request_signer_id': signer.id,
            'endpoint': 'submit',
            'idempotency_key': key,
            'request_hash': request_hash,
            'state': 'in_progress',
            'expires_at': '2099-01-01 00:00:00',
        })

        response = self._submit_with_payload(
            signer,
            self._build_submit_payload(
                revision=revision,
                field_id=field.id,
                value='Locked submit',
                consent_hash=consent_hash,
                access_token=bundle['token'],
                idempotency_key=key,
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'request_locked')

    def test_decline_same_key_in_progress_returns_request_locked(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Decline Locked', owner=self.open_sign_user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        self.authenticate(None, None)
        key = str(uuid4())
        request_hash = idempotency_service.build_decline_request_hash('Locked decline')
        self.env['open.sign.portal.idempotency'].sudo().create({
            'request_signer_id': signer.id,
            'endpoint': 'decline',
            'idempotency_key': key,
            'request_hash': request_hash,
            'state': 'in_progress',
            'expires_at': '2099-01-01 00:00:00',
        })

        response = self._decline_with_payload(
            signer,
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='Locked decline',
                access_token=bundle['token'],
                idempotency_key=key,
            ),
        )
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], 'request_locked')

    def test_idempotency_conflict_error_does_not_echo_payload_or_token(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency No Leak', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        first_payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='First no leak',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )
        second_payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Second no leak',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )
        self.assertTrue(self._submit_with_payload(signer, first_payload)['ok'])
        conflict_response = self._submit_with_payload(signer, second_payload)

        self.assertFalse(conflict_response['ok'])
        self.assertEqual(conflict_response['error_code'], 'idempotency_conflict')
        self._assert_no_url_or_token_leak(conflict_response, bundle['token'], 'Second no leak')

    def test_replayed_success_envelope_uses_stored_contract_shape_only(self):
        bundle = self._create_portal_session(self.env, name='Portal Idempotency Replay Shape', owner=self.open_sign_user)
        signer, field, consent_hash, revision = self._open_submit_context(bundle)
        key = str(uuid4())
        payload = self._build_submit_payload(
            revision=revision,
            field_id=field.id,
            value='Replay shape',
            consent_hash=consent_hash,
            access_token=bundle['token'],
            idempotency_key=key,
        )

        first_response = self._submit_with_payload(signer, dict(payload))
        second_response = self._submit_with_payload(signer, dict(payload))

        self.assertEqual(set(second_response.keys()), {'ok', 'force_refresh', 'redirect_url', 'request_revision'})
        self.assertEqual(second_response, first_response)
