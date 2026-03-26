# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import odoo.sql_db
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
from odoo import SUPERUSER_ID, api, fields
from odoo.addons.open_sign.services import notification_service
from odoo.addons.open_sign_portal.controllers.portal_sign import (
    INLINE_PDF_VIEWER_SCOPE,
    OpenSignPortalController,
)
from odoo.exceptions import ValidationError
from odoo.orm.environments import Transaction
from odoo.tools.misc import hash_sign
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.open_sign_portal.tests.common import (
    OpenSignPortalControllerTestMixin,
    OpenSignPortalHttpTestMixin,
    OpenSignPortalTestMixin,
)


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalTokenAudit(TransactionCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_token_audit_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_token_audit_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.token.audit.user@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.token.audit.manager@example.com'

    @classmethod
    def _create_versioned_request_bundle(cls, env, *, name, owner):
        template = cls._create_template(env, name)
        role = cls._create_role(env, template, f'{name} Signer', 10)
        cls._create_field(
            env,
            template,
            role,
            type='text',
            label=f'{name} Text',
            required=True,
            sequence=10,
        )
        sign_request = cls._create_request(env, template, owner=owner)
        signer = cls._create_signer(
            env,
            sign_request,
            role,
            email=f'{name.lower().replace(" ", ".")}@example.com',
            sequence=10,
        )
        sign_request.action_version()
        return {
            'request': sign_request,
            'signer': signer,
        }

    def _get_token_event_logs(self, signer, event_type):
        return self.env['open.sign.audit.log'].sudo().search([
            ('request_id', '=', signer.request_id.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', event_type),
        ], order='event_sequence asc, id asc')

    def _assert_token_event_metadata_is_safe(self, signer, event_type, *extra_forbidden):
        for audit_log in self._get_token_event_logs(signer, event_type):
            self._assert_no_url_or_token_leak(audit_log.metadata_json or {}, *extra_forbidden)

    def test_initial_send_appends_token_issued_audit(self):
        bundle = self._create_versioned_request_bundle(
            self.env,
            name='Portal Token Audit Initial Send',
            owner=self.open_sign_user,
        )

        bundle['request'].action_send()

        audit_logs = self._get_token_event_logs(bundle['signer'], 'token_issued')
        self.assertEqual(len(audit_logs), 1)
        metadata = audit_logs.metadata_json
        self.assertEqual(metadata['trigger'], 'initial_send')
        self.assertEqual(metadata['request_status_before'], 'sent')
        self.assertEqual(metadata['signer_state_before'], 'pending')
        self.assertTrue(metadata['token_issued_at_utc'])
        self.assertTrue(metadata['token_expires_at_utc'])
        self._assert_token_event_metadata_is_safe(bundle['signer'], 'token_issued', bundle['signer'].access_token)

    def test_wave_unblocked_appends_token_issued_audit(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Token Audit Wave',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        existing_count = len(self._get_token_event_logs(signer_second, 'token_issued'))

        notification_service.queue_request_invitations(
            signer_second.request_id,
            signer_second,
            trigger='wave_unblocked',
            raise_on_failure=True,
        )

        audit_logs = self._get_token_event_logs(signer_second, 'token_issued')
        self.assertEqual(len(audit_logs), existing_count + 1)
        self.assertEqual(audit_logs[-1].metadata_json['trigger'], 'wave_unblocked')

    def test_manual_resend_appends_token_issued_audit(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Manual Resend',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        existing_count = len(self._get_token_event_logs(signer, 'token_issued'))

        wizard = self.env['open.sign.signer.contact_correction.wizard'].with_user(self.open_sign_manager).create({
            'signer_id': signer.id,
            'target_email': signer.email,
            'reason': 'Manual resend for token audit',
        })
        wizard.action_apply_contact_correction()

        audit_logs = self._get_token_event_logs(signer, 'token_issued')
        self.assertEqual(len(audit_logs), existing_count + 1)
        self.assertEqual(audit_logs[-1].metadata_json['trigger'], 'manual_resend')
        self.assertFalse(self._get_token_event_logs(signer, 'token_revoked'))

    def test_reminder_reuse_does_not_append_token_issued(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Reminder Reuse',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        existing_logs = self._get_token_event_logs(signer, 'token_issued')

        notification_service.queue_request_reminders(
            signer.request_id,
            signer,
            trigger='cron_reminder',
            raise_on_failure=True,
        )

        self.assertEqual(len(self._get_token_event_logs(signer, 'token_issued')), len(existing_logs))

    def test_reminder_refresh_appends_token_issued_when_rotating(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Reminder Refresh',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        existing_count = len(self._get_token_event_logs(signer, 'token_issued'))
        signer.sudo().write({'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1)})

        notification_service.queue_request_reminders(
            signer.request_id,
            signer,
            trigger='cron_reminder',
            raise_on_failure=True,
        )

        audit_logs = self._get_token_event_logs(signer, 'token_issued')
        self.assertEqual(len(audit_logs), existing_count + 1)
        self.assertEqual(audit_logs[-1].metadata_json['trigger'], 'cron_reminder')

    def test_manager_revoke_appends_token_revoked_audit(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Revoke',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()

        audit_logs = self._get_token_event_logs(signer, 'token_revoked')
        self.assertEqual(len(audit_logs), 1)
        metadata = audit_logs.metadata_json
        self.assertEqual(metadata['reason'], 'manager_revoke')
        self.assertTrue(metadata['token_issued_at_utc'])
        self.assertTrue(metadata['token_expires_at_utc'])
        self.assertTrue(metadata['token_revoked_at_utc'])
        self._assert_token_event_metadata_is_safe(signer, 'token_revoked', bundle['token'])

    def test_revoke_without_prior_distribution_does_not_append_token_revoked(self):
        bundle = self._create_versioned_request_bundle(
            self.env,
            name='Portal Token Audit Revoke No Distribution',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']

        signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()

        self.assertFalse(self._get_token_event_logs(signer, 'token_revoked'))


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalTokenAuditController(TransactionCase, OpenSignPortalControllerTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner_user_id = cls.env.ref('base.user_admin').id
        cls.public_user_id = cls.env.ref('base.public_user').id

    @contextmanager
    def _fresh_read_committed_test_env(self, *, uid):
        with odoo.sql_db.db_connect(self.registry.db_name).cursor() as cr:
            cr.connection.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
            cr.transaction = Transaction(self.registry)
            env = api.Environment(cr, uid, {})
            try:
                yield env
            finally:
                env.clear()

    def _create_committed_portal_bundle(self, *, name):
        with self._fresh_test_env(uid=SUPERUSER_ID) as env:
            bundle = self._serialize_portal_bundle(
                self._create_portal_session(
                    env,
                    name=name,
                    owner=env['res.users'].browse(self.owner_user_id),
                )
            )
            env.cr.commit()
        return bundle

    def _get_token_event_logs_committed(self, *, request_id, signer_id, event_type):
        with self._fresh_test_env(uid=SUPERUSER_ID) as env:
            return env['open.sign.audit.log'].sudo().search_read(
                [
                    ('request_id', '=', request_id),
                    ('signer_id', '=', signer_id),
                    ('event_type', '=', event_type),
                ],
                ['metadata_json', 'ip', 'user_agent', 'event_sequence'],
                order='event_sequence asc, id asc',
            )

    def _call_public_http_controller(self, *, method_name, signer_id, access_token, path, extra_args=None):
        with self._fresh_read_committed_test_env(uid=self.public_user_id) as env:
            controller = OpenSignPortalController()
            with self._portal_request_context(env, path=path, user_agent='python-requests/2.31.0') as mocked_request:
                mocked_request.type = 'http'
                mocked_request.httprequest.args = {'access_token': access_token, **(extra_args or {})}
                result = getattr(controller, method_name)(signer_id, access_token=access_token)
                env.cr.commit()
        return result

    def _call_public_document_controller(self, signer_id, *, access_token, extra_args=None):
        return self._call_public_http_controller(
            method_name='portal_sign_document',
            signer_id=signer_id,
            access_token=access_token,
            path=f'/my/sign/{signer_id}/document',
            extra_args=extra_args,
        )

    def _call_public_page_controller(self, signer_id, *, access_token):
        return self._call_public_http_controller(
            method_name='portal_sign_page',
            signer_id=signer_id,
            access_token=access_token,
            path=f'/my/sign/{signer_id}',
        )

    def _get_page_pdf_render_args(self, signer_id, *, access_token):
        with self._fresh_read_committed_test_env(uid=self.public_user_id) as env:
            controller = OpenSignPortalController()
            with self._portal_request_context(env, path=f'/my/sign/{signer_id}') as mocked_request:
                mocked_request.type = 'http'
                mocked_request.httprequest.args = {'access_token': access_token}
                auth_context = controller._check_signer_read_access(
                    signer_id,
                    access_token=access_token,
                    entrypoint='page',
                )
                values = controller._build_portal_page_values(auth_context)
        query_params = parse_qs(urlparse(values['pdf_render_url']).query)
        return {key: items[-1] for key, items in query_params.items()}

    def _get_signer_document_attachment_id(self, signer_id):
        return self._run_committed(
            lambda env: (
                env['open.sign.request.signer'].browse(signer_id).request_id.template_version_id.source_attachment_id
                or env['open.sign.request.signer'].browse(signer_id).request_id.template_id.source_attachment_id
            ).id
        )

    def _call_token_opened_after_auth_capture(self, signer_id, *, access_token, entrypoint='page', before_append=None):
        with self._fresh_read_committed_test_env(uid=self.public_user_id) as env:
            controller = OpenSignPortalController()
            with self._portal_request_context(env, path=f'/my/sign/{signer_id}') as mocked_request:
                mocked_request.type = 'http'
                mocked_request.httprequest.args = {'access_token': access_token}
                auth_context = controller._check_signer_read_access(
                    signer_id,
                    access_token=access_token,
                    entrypoint=entrypoint,
                )
                if before_append:
                    before_append()
                controller._append_token_opened_from_auth_context(auth_context, entrypoint=entrypoint)
                env.cr.commit()
        return auth_context.token_audit_identity

    def _call_token_rejected_after_snapshot_capture(
        self,
        signer_id,
        *,
        access_token,
        entrypoint='page',
        before_append=None,
    ):
        with self._fresh_read_committed_test_env(uid=self.public_user_id) as env:
            controller = OpenSignPortalController()
            with self._portal_request_context(env, path=f'/my/sign/{signer_id}') as mocked_request:
                mocked_request.type = 'http'
                mocked_request.httprequest.args = {'access_token': access_token}
                signer_sudo = controller._get_signer_sudo(signer_id)
                token_state = signer_sudo._classify_current_email_token_access(access_token)
                token_identity = controller._capture_token_audit_identity(
                    signer_sudo,
                    access_token,
                    token_state=token_state,
                )
                rejection_code = 'expired_token' if token_state == 'expired' else 'invalid_token'
                if before_append:
                    before_append()
                controller._append_token_rejected_from_snapshot(
                    signer_sudo,
                    entrypoint=entrypoint,
                    token_state=token_state,
                    rejection_code=rejection_code,
                    token_audit_identity=token_identity,
                )
                env.cr.commit()
        return {
            'token_state': token_state,
            'token_audit_identity': token_identity,
        }

    def test_token_opened_document_emits_once_when_document_is_first_surface(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Audit Open Document')

        response = self._call_public_document_controller(bundle['signer'], access_token=bundle['token'])

        self.assertEqual(response.status_code, 200)
        audit_logs = self._get_token_event_logs_committed(
            request_id=bundle['request'],
            signer_id=bundle['signer'],
            event_type='token_opened',
        )
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(audit_logs[0]['metadata_json']['entrypoint'], 'document')

    def test_inline_viewer_document_fetch_does_not_append_document_token_opened(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Audit Viewer Fetch')
        viewer_args = self._get_page_pdf_render_args(bundle['signer'], access_token=bundle['token'])

        response = self._call_public_document_controller(
            bundle['signer'],
            access_token=bundle['token'],
            extra_args=viewer_args,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self._get_token_event_logs_committed(
            request_id=bundle['request'],
            signer_id=bundle['signer'],
            event_type='token_opened',
        ))

    def test_viewer_flag_without_signed_token_still_appends_document_token_opened(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Audit Bare Viewer Flag')

        response = self._call_public_document_controller(
            bundle['signer'],
            access_token=bundle['token'],
            extra_args={'viewer': '1'},
        )

        self.assertEqual(response.status_code, 200)
        audit_logs = self._get_token_event_logs_committed(
            request_id=bundle['request'],
            signer_id=bundle['signer'],
            event_type='token_opened',
        )
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(audit_logs[0]['metadata_json']['entrypoint'], 'document')

    def test_invalid_or_expired_or_mismatched_viewer_token_falls_back_to_document_open_audit(self):
        other_bundle = self._create_committed_portal_bundle(name='Portal Token Audit Viewer Mismatch Other')
        mismatched_viewer_args = self._get_page_pdf_render_args(other_bundle['signer'], access_token=other_bundle['token'])

        def build_expired_viewer_token(signer_id):
            attachment_id = self._get_signer_document_attachment_id(signer_id)
            return hash_sign(
                self.env['ir.config_parameter'].sudo().env,
                INLINE_PDF_VIEWER_SCOPE,
                {
                    'signer_id': signer_id,
                    'attachment_id': attachment_id,
                    'viewer_context': 'token',
                },
                expiration=timedelta(seconds=-1),
            )

        for label, extra_args in (
            ('invalid', {'viewer': '1', 'viewer_token': 'broken-viewer-token'}),
            ('expired', None),
            ('mismatched', {'viewer': '1', 'viewer_token': mismatched_viewer_args['viewer_token']}),
        ):
            with self.subTest(case=label):
                bundle = self._create_committed_portal_bundle(name=f'Portal Token Audit Viewer {label.title()}')
                if label == 'expired':
                    extra_args = {
                        'viewer': '1',
                        'viewer_token': build_expired_viewer_token(bundle['signer']),
                    }

                response = self._call_public_document_controller(
                    bundle['signer'],
                    access_token=bundle['token'],
                    extra_args=extra_args,
                )

                self.assertEqual(response.status_code, 200)
                audit_logs = self._get_token_event_logs_committed(
                    request_id=bundle['request'],
                    signer_id=bundle['signer'],
                    event_type='token_opened',
                )
                self.assertEqual(len(audit_logs), 1)
                self.assertEqual(audit_logs[0]['metadata_json']['entrypoint'], 'document')

    def test_document_missing_attachment_does_not_append_token_opened(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Audit Missing Document')

        with patch(
            'odoo.addons.open_sign_portal.controllers.portal_sign.OpenSignPortalController._get_signer_document_attachment',
            return_value=False,
        ):
            response = self._call_public_document_controller(bundle['signer'], access_token=bundle['token'])

        self.assertEqual(response.status_code, 303)
        self.assertFalse(self._get_token_event_logs_committed(
            request_id=bundle['request'],
            signer_id=bundle['signer'],
            event_type='token_opened',
        ))

    def test_token_opened_reissued_token_can_emit_again_after_new_issue(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Audit Open Reissue')

        first_response = self._call_public_document_controller(bundle['signer'], access_token=bundle['token'])
        self.assertEqual(first_response.status_code, 200)

        def rotate_token(env):
            signer = env['open.sign.request.signer'].browse(bundle['signer'])
            signer._issue_email_portal_token(trigger='manual_resend', force_rotate=True)
            return signer.access_token

        new_token = self._run_committed(rotate_token)
        second_response = self._call_public_document_controller(bundle['signer'], access_token=new_token)
        self.assertEqual(second_response.status_code, 200)

        audit_logs = self._get_token_event_logs_committed(
            request_id=bundle['request'],
            signer_id=bundle['signer'],
            event_type='token_opened',
        )
        self.assertEqual(len(audit_logs), 2)
        self.assertNotEqual(
            audit_logs[0]['metadata_json']['token_audit_sequence'],
            audit_logs[1]['metadata_json']['token_audit_sequence'],
        )

    def test_token_opened_auth_snapshot_survives_rotation_before_append(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Audit Open Snapshot')
        original_sequence = self._run_committed(
            lambda env: env['open.sign.audit.log'].sudo().search([
                ('request_id', '=', bundle['request']),
                ('signer_id', '=', bundle['signer']),
                ('event_type', '=', 'token_issued'),
            ], order='event_sequence desc, id desc', limit=1).event_sequence
        )

        snapshot = self._call_token_opened_after_auth_capture(
            bundle['signer'],
            access_token=bundle['token'],
            before_append=lambda: self._run_committed(
                lambda env: env['open.sign.request.signer'].browse(bundle['signer'])._issue_email_portal_token(
                    trigger='manual_resend',
                    force_rotate=True,
                )
            ),
        )

        audit_logs = self._get_token_event_logs_committed(
            request_id=bundle['request'],
            signer_id=bundle['signer'],
            event_type='token_opened',
        )
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(snapshot['token_audit_sequence'], original_sequence)
        self.assertEqual(audit_logs[0]['metadata_json']['token_audit_sequence'], original_sequence)
        current_sequence = self._run_committed(
            lambda env: env['open.sign.audit.log'].sudo().search([
                ('request_id', '=', bundle['request']),
                ('signer_id', '=', bundle['signer']),
                ('event_type', '=', 'token_issued'),
            ], order='event_sequence desc, id desc', limit=1).event_sequence
        )
        self.assertNotEqual(current_sequence, original_sequence)

    def test_token_rejected_auth_snapshot_survives_rotation_before_append(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Audit Reject Snapshot')

        def expire_token(env):
            signer = env['open.sign.request.signer'].browse(bundle['signer'])
            signer.sudo().write({'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1)})

        self._run_committed(expire_token)
        original_sequence = self._run_committed(
            lambda env: env['open.sign.audit.log'].sudo().search([
                ('request_id', '=', bundle['request']),
                ('signer_id', '=', bundle['signer']),
                ('event_type', '=', 'token_issued'),
            ], order='event_sequence desc, id desc', limit=1).event_sequence
        )

        snapshot = self._call_token_rejected_after_snapshot_capture(
            bundle['signer'],
            access_token=bundle['token'],
            before_append=lambda: self._run_committed(
                lambda env: env['open.sign.request.signer'].browse(bundle['signer'])._issue_email_portal_token(
                    trigger='manual_resend',
                    force_rotate=True,
                )
            ),
        )

        audit_logs = self._get_token_event_logs_committed(
            request_id=bundle['request'],
            signer_id=bundle['signer'],
            event_type='token_rejected',
        )
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(snapshot['token_state'], 'expired')
        self.assertEqual(snapshot['token_audit_identity']['token_audit_sequence'], original_sequence)
        self.assertEqual(audit_logs[0]['metadata_json']['token_audit_sequence'], original_sequence)

    def test_page_token_opened_rolls_back_with_request_transaction(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Audit Page Rollback')

        with self._fresh_test_env(uid=self.public_user_id) as env:
            controller = OpenSignPortalController()
            with self._portal_request_context(env, path=f"/my/sign/{bundle['signer']}") as mocked_request:
                mocked_request.type = 'http'
                mocked_request.httprequest.args = {'access_token': bundle['token']}
                with patch.object(
                    OpenSignPortalController,
                    '_build_portal_page_values',
                    side_effect=RuntimeError('force page rollback after token_opened append'),
                ):
                    with self.assertRaisesRegex(RuntimeError, 'force page rollback'):
                        controller.portal_sign_page(bundle['signer'], access_token=bundle['token'])
                    env.cr.rollback()

        self.assertFalse(self._get_token_event_logs_committed(
            request_id=bundle['request'],
            signer_id=bundle['signer'],
            event_type='token_opened',
        ))


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalTokenAuditHttp(HttpCase, OpenSignPortalHttpTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_token_audit_http_user',
            password='open_sign_portal_token_audit_http_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_outsider = new_test_user(
            cls.env,
            login='open_sign_portal_token_audit_http_outsider',
            password='open_sign_portal_token_audit_http_outsider',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_token_audit_http_manager',
            password='open_sign_portal_token_audit_http_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.token.audit.http.user@example.com'
        cls.open_sign_outsider.partner_id.email = 'open.sign.portal.token.audit.http.outsider@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.token.audit.http.manager@example.com'

    def _get_token_event_logs(self, signer, event_type):
        self.env.invalidate_all(flush=False)
        return self.env['open.sign.audit.log'].sudo().search([
            ('request_id', '=', signer.request_id.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', event_type),
        ], order='event_sequence asc, id asc')

    def _expire_signer_token(self, signer):
        signer.sudo().write({'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1)})
        signer.invalidate_recordset(['email_token_expires_at'])

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

    def _create_contact_correction_wizard(self, signer, *, reason='Rotate invitation'):
        return self.env['open.sign.signer.contact_correction.wizard'].with_user(self.open_sign_manager).create({
            'signer_id': signer.id,
            'target_email': signer.email,
            'reason': reason,
        })

    def test_token_opened_page_emits_once_per_distributed_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Open Page',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']

        self.authenticate(None, None)
        first = self.url_open(f"/my/sign/{signer.id}?access_token={bundle['token']}", allow_redirects=False)
        second = self.url_open(f"/my/sign/{signer.id}?access_token={bundle['token']}", allow_redirects=False)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        audit_logs = self._get_token_event_logs(signer, 'token_opened')
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(audit_logs.metadata_json['entrypoint'], 'page')
        self.assertEqual(audit_logs.ip, '127.0.0.1')
        self.assertTrue(audit_logs.user_agent)
        self._assert_no_url_or_token_leak(audit_logs.metadata_json or {}, bundle['token'])

    def test_token_opened_not_emitted_for_internal_fallback(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Internal Open',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        signer = bundle['signer']

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{signer.id}", allow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self._get_token_event_logs(signer, 'token_opened'))

    def test_token_opened_not_emitted_for_preview(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Preview Open',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        signer = bundle['signer']

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{signer.id}/preview", allow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self._get_token_event_logs(signer, 'token_opened'))

    def test_expired_current_token_page_redirect_appends_token_rejected_once(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Expired Reject',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']
        field = self._get_text_field_for_signer(signer)
        self._expire_signer_token(signer)

        self.authenticate(None, None)
        page_response = self.url_open(f"/my/sign/{signer.id}?access_token={bundle['token']}", allow_redirects=False)
        json_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_payload(
                revision=signer.request_id.lock_version,
                values=[{'field_id': field.id, 'value': 'expired token save'}],
                access_token=bundle['token'],
            ),
        )

        self.assertEqual(page_response.status_code, 303)
        self.assertFalse(json_response['ok'])
        self.assertEqual(json_response['error_code'], 'expired_token')
        audit_logs = self._get_token_event_logs(signer, 'token_rejected')
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(audit_logs.metadata_json['rejection_code'], 'expired_token')
        self.assertEqual(audit_logs.metadata_json['token_state'], 'expired')
        self._assert_no_url_or_token_leak(audit_logs.metadata_json or {}, bundle['token'])

    def test_revoked_hidden_current_token_denial_appends_token_rejected_once(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Revoked Reject',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']
        signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()
        signer.invalidate_recordset(['access_token'])
        hidden_token = signer.access_token

        self.authenticate(None, None)
        response = self.url_open(f"/my/sign/{signer.id}?access_token={hidden_token}", allow_redirects=False)
        second = self.url_open(f"/my/sign/{signer.id}?access_token={hidden_token}", allow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(second.status_code, 303)
        audit_logs = self._get_token_event_logs(signer, 'token_rejected')
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(audit_logs.metadata_json['rejection_code'], 'invalid_token')
        self.assertEqual(audit_logs.metadata_json['token_state'], 'revoked')
        self._assert_no_url_or_token_leak(audit_logs.metadata_json or {}, hidden_token, bundle['token'])

    def test_invalid_or_rotated_token_denial_does_not_append_token_rejected(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Invalid Reject',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']
        wrong_token = self._mutate_token(bundle['token'])
        wizard = self._create_contact_correction_wizard(
            signer,
            reason='Rotate token for invalid token audit coverage',
        )
        old_token = signer.access_token
        wizard.action_apply_contact_correction()
        signer.invalidate_recordset(['access_token'])

        self.authenticate(None, None)
        wrong_response = self.url_open(f"/my/sign/{signer.id}?access_token={wrong_token}", allow_redirects=False)
        rotated_response = self.url_open(f"/my/sign/{signer.id}?access_token={old_token}", allow_redirects=False)

        self.assertEqual(wrong_response.status_code, 303)
        self.assertEqual(rotated_response.status_code, 303)
        self.assertFalse(self._get_token_event_logs(signer, 'token_rejected'))

    def test_internal_fallback_with_bad_token_does_not_append_token_rejected(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Token Audit Internal Reject Bypass',
            owner=self.open_sign_user,
            signer_partner=self.open_sign_user.partner_id,
        )
        signer = bundle['signer']
        wrong_token = self._mutate_token(bundle['token'])

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        response = self.url_open(f"/my/sign/{signer.id}?access_token={wrong_token}", allow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self._get_token_event_logs(signer, 'token_rejected'))
