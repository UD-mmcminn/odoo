# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import hashlib
from pathlib import Path
import runpy
from unittest.mock import patch
from uuid import uuid4

from psycopg2.errors import LockNotAvailable

from odoo import fields
from odoo.addons.open_sign.services import notification_service
from odoo.addons.open_sign_portal.services import otp_service
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.open_sign_portal.tests.common import OpenSignPortalTestMixin


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalEmailToken(TransactionCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_email_token_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_email_token_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_portal_email_token_auditor',
            groups='open_sign.group_open_sign_auditor',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.email.token.user@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.email.token.manager@example.com'
        cls.open_sign_auditor.partner_id.email = 'open.sign.portal.email.token.auditor@example.com'

    @classmethod
    def _create_versioned_request_bundle(cls, env, *, name, owner, signer_partner=False):
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
            partner=signer_partner,
        )
        sign_request.action_version()
        return {
            'template': template,
            'role': role,
            'request': sign_request,
            'signer': signer,
        }

    def _create_contact_correction_wizard(self, signer, *, target_email=False, reason='Rotate invitation'):
        return self.env['open.sign.signer.contact_correction.wizard'].with_user(self.open_sign_manager).create({
            'signer_id': signer.id,
            'target_email': target_email or signer.email,
            'reason': reason,
        })

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

    def test_backend_portal_sign_url_blank_before_initial_issue(self):
        bundle = self._create_versioned_request_bundle(
            self.env,
            name='Portal Email Token Copy Link Before Issue',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']

        self.assertFalse(signer.with_user(self.open_sign_manager).portal_sign_url)
        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertFalse(signer.sudo().access_token)
        self.assertFalse(signer.email_token_issued_at)
        self.assertFalse(signer.email_token_expires_at)
        self.assertFalse(signer.email_token_revoked_at)

    def test_backend_portal_sign_url_available_after_initial_send(self):
        bundle = self._create_versioned_request_bundle(
            self.env,
            name='Portal Email Token Copy Link After Issue',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']
        bundle['request'].action_send()

        signer.invalidate_recordset([
            'portal_sign_url',
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertEqual(
            signer.with_user(self.open_sign_manager).portal_sign_url,
            f"/my/sign/{signer.id}?access_token={signer.access_token}",
        )
        self.assertTrue(signer.email_token_issued_at)
        self.assertTrue(signer.email_token_expires_at)
        self.assertFalse(signer.email_token_revoked_at)

    def test_backend_portal_sign_url_blank_when_metadata_expired(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Copy Link Expired',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        token_before = signer.access_token
        issued_before = signer.email_token_issued_at
        signer.sudo().write({
            'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1),
        })

        signer.invalidate_recordset([
            'portal_sign_url',
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertFalse(signer.with_user(self.open_sign_manager).portal_sign_url)
        self.assertEqual(signer.access_token, token_before)
        self.assertEqual(signer.email_token_issued_at, issued_before)
        self.assertFalse(signer.email_token_revoked_at)

    def test_backend_portal_sign_url_read_does_not_backfill_lifecycle_state(self):
        bundle = self._create_versioned_request_bundle(
            self.env,
            name='Portal Email Token Copy Link No Backfill',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']
        access_token = str(uuid4())
        signer.sudo().write({
            'access_token': access_token,
            'email_token_issued_at': False,
            'email_token_expires_at': False,
            'email_token_revoked_at': False,
        })

        self.assertFalse(signer.with_user(self.open_sign_manager).portal_sign_url)
        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertEqual(signer.access_token, access_token)
        self.assertFalse(signer.email_token_issued_at)
        self.assertFalse(signer.email_token_expires_at)
        self.assertFalse(signer.email_token_revoked_at)

    def test_initial_send_rotates_preexisting_token_and_sets_lifecycle_fields(self):
        bundle = self._create_versioned_request_bundle(
            self.env,
            name='Portal Email Token Initial Send',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']
        sign_request = bundle['request']
        old_token = signer._portal_ensure_token()

        sign_request.action_send()

        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertNotEqual(signer.access_token, old_token)
        self.assertTrue(signer.email_token_issued_at)
        self.assertTrue(signer.email_token_expires_at)
        self.assertFalse(signer.email_token_revoked_at)

        queued_mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertIn(f"/my/sign/{signer.id}?access_token={signer.access_token}", queued_mail.body_html)
        self.assertNotIn(old_token, queued_mail.body_html)

    def test_wave_unblocked_invitation_rotates_fresh_token(self):
        bundle = self._create_ordered_two_signer_session(
            self.env,
            name='Portal Email Token Wave',
            owner=self.open_sign_user,
            ordered_signing=True,
        )
        signer_second = self.env['open.sign.request.signer'].browse(bundle['signer_second'].id)
        sign_request = signer_second.request_id
        old_token = signer_second._portal_ensure_token()

        notification_service.queue_request_invitations(
            sign_request,
            signer_second,
            trigger='wave_unblocked',
            raise_on_failure=True,
        )

        signer_second.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertNotEqual(signer_second.access_token, old_token)
        self.assertTrue(signer_second.email_token_issued_at)
        self.assertTrue(signer_second.email_token_expires_at)
        self.assertFalse(signer_second.email_token_revoked_at)

    def test_manual_resend_updates_lifecycle_fields(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Manual Resend',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_token = signer.access_token
        old_issued_at = signer.email_token_issued_at
        event_at = fields.Datetime.now() + timedelta(minutes=5)

        wizard = self._create_contact_correction_wizard(signer)
        with patch(
            'odoo.addons.open_sign.wizards.signer_contact_correction_wizard.fields.Datetime.now',
            return_value=event_at,
        ):
            wizard.action_apply_contact_correction()

        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertNotEqual(signer.access_token, old_token)
        self.assertNotEqual(signer.email_token_issued_at, old_issued_at)
        self.assertEqual(signer.email_token_issued_at, event_at)
        self.assertTrue(signer.email_token_expires_at)
        self.assertFalse(signer.email_token_revoked_at)

    def test_revoke_rotates_hidden_token_and_sets_revoked_at(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Revoke',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_public_token = signer.access_token
        old_issued_at = signer.email_token_issued_at
        old_expires_at = signer.email_token_expires_at

        action = signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()

        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertNotEqual(signer.access_token, old_public_token)
        self.assertEqual(signer.email_token_issued_at, old_issued_at)
        self.assertEqual(signer.email_token_expires_at, old_expires_at)
        self.assertTrue(signer.email_token_revoked_at)
        self.assertEqual(action['tag'], 'display_notification')

    def test_revoke_invalidates_active_otp_state(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Revoke OTP',
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

        signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()

        self.assertFalse(otp_service.get_active_challenge(signer))

    def test_portal_sign_url_is_blank_when_revoked(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Blank Copy Link',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()

        signer.invalidate_recordset(['portal_sign_url'])
        self.assertFalse(signer.with_user(self.open_sign_manager).portal_sign_url)

    def test_completion_notification_skips_signer_after_revoke(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Completion Skip After Revoke',
            owner=self.open_sign_manager,
            signer_partner=self.open_sign_user.partner_id,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        request = signer.request_id
        owner_email = self.open_sign_manager.partner_id.email
        mail_model = self.env['mail.mail'].sudo()
        signer_mail_before = mail_model.search_count([('email_to', '=', signer.email)])
        owner_mail_before = mail_model.search_count([('email_to', '=', owner_email)])

        signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()
        request.write({
            'status': 'in_progress',
            'final_attachment_id': self._create_attachment_static(
                self.env,
                name='portal_email_token_completion_skip_after_revoke.pdf',
                res_model='open.sign.request',
            ).id,
            'final_pdf_sha256': 'e' * 64,
        })
        request.action_complete()

        self.assertEqual(mail_model.search_count([('email_to', '=', owner_email)]), owner_mail_before + 1)
        self.assertEqual(mail_model.search_count([('email_to', '=', signer.email)]), signer_mail_before)
        skipped_audit = self.env['open.sign.audit.log'].search([
            ('request_id', '=', request.id),
            ('signer_id', '=', signer.id),
            ('event_type', '=', 'notification_skipped'),
        ], order='id desc', limit=1)
        self.assertTrue(skipped_audit)
        self.assertEqual(skipped_audit.metadata_json['notification_type'], 'completion')
        self.assertEqual(skipped_audit.metadata_json['skip_reason'], 'signer_notification_url_unavailable')

    def test_completion_notification_after_revoke_does_not_expose_hidden_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Completion Hidden Token',
            owner=self.open_sign_manager,
            signer_partner=self.open_sign_user.partner_id,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        request = signer.request_id
        owner_email = self.open_sign_manager.partner_id.email
        mail_model = self.env['mail.mail'].sudo()
        signer_mail_before = mail_model.search_count([('email_to', '=', signer.email)])
        old_public_token, hidden_token = self._revoke_signer_token(signer)

        request.write({
            'status': 'in_progress',
            'final_attachment_id': self._create_attachment_static(
                self.env,
                name='portal_email_token_completion_hidden_token.pdf',
                res_model='open.sign.request',
            ).id,
            'final_pdf_sha256': 'f' * 64,
        })
        request.action_complete()

        signer.invalidate_recordset(['access_token'])
        self.assertEqual(signer.access_token, hidden_token)
        self.assertEqual(mail_model.search_count([('email_to', '=', signer.email)]), signer_mail_before)
        owner_mail = mail_model.search([('email_to', '=', owner_email)], order='id desc', limit=1)
        self.assertTrue(owner_mail)
        self.assertNotIn(old_public_token, owner_mail.body_html)
        self.assertNotIn(hidden_token, owner_mail.body_html)

    def test_completion_notification_still_uses_distributed_token_when_not_revoked(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Completion Distributed Token',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        request = signer.request_id
        current_token = signer.access_token
        owner_email = self.open_sign_user.partner_id.email
        mail_model = self.env['mail.mail'].sudo()
        signer_mail_before = mail_model.search_count([('email_to', '=', signer.email)])
        owner_mail_before = mail_model.search_count([('email_to', '=', owner_email)])

        request.write({
            'status': 'in_progress',
            'final_attachment_id': self._create_attachment_static(
                self.env,
                name='portal_email_token_completion_distributed_token.pdf',
                res_model='open.sign.request',
            ).id,
            'final_pdf_sha256': '1' * 64,
        })
        request.action_complete()

        self.assertEqual(mail_model.search_count([('email_to', '=', signer.email)]), signer_mail_before + 1)
        self.assertEqual(mail_model.search_count([('email_to', '=', owner_email)]), owner_mail_before + 1)
        signer_mail = mail_model.search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertIn(f"/my/sign/{signer.id}?access_token={current_token}", signer_mail.body_html)

    def test_lifecycle_fields_visible_only_to_manager(self):
        signer = self.env['open.sign.request.signer']
        manager_fields = signer.with_user(self.open_sign_manager).fields_get()
        user_fields = signer.with_user(self.open_sign_user).fields_get()
        auditor_fields = signer.with_user(self.open_sign_auditor).fields_get()

        for field_name in ('email_token_issued_at', 'email_token_expires_at', 'email_token_revoked_at'):
            self.assertIn(field_name, manager_fields)
            self.assertNotIn(field_name, user_fields)
            self.assertNotIn(field_name, auditor_fields)

    def test_non_manager_cannot_revoke_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Non Manager Revoke',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        with self.assertRaises(AccessError):
            signer.with_user(self.open_sign_user).action_revoke_signer_portal_token()

    def test_revoke_denied_for_opened_signer(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Opened Revoke',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        signer.sudo().write({
            'state': 'opened',
            'last_opened_at': fields.Datetime.now(),
        })

        with self.assertRaisesRegex(ValidationError, 'Only pending signer links can be revoked.'):
            signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()

    def test_revoke_denied_for_terminal_request(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Terminal Revoke',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        signer.request_id.action_cancel()

        with self.assertRaisesRegex(ValidationError, 'Signer links can only be revoked'):
            signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()

    def test_existing_token_rows_are_backfilled_on_upgrade(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Upgrade',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id).sudo()
        signer.request_id.write({'expires_at': fields.Datetime.now() + timedelta(hours=1)})
        signer.write({
            'email_token_issued_at': False,
            'email_token_expires_at': False,
            'email_token_revoked_at': False,
        })
        self.env.flush_all()

        migration = runpy.run_path(
            str(Path(__file__).resolve().parents[1] / 'upgrades' / '1.1' / 'post-migrate.py')
        )
        migration['migrate'](self.env.cr, '1.1')
        self.env.flush_all()
        self.env.invalidate_all()
        signer = self.env['open.sign.request.signer'].sudo().browse(signer.id)

        self.assertTrue(signer.email_token_issued_at)
        self.assertTrue(signer.email_token_expires_at)
        self.assertFalse(signer.email_token_revoked_at)
        self.assertLessEqual(signer.email_token_expires_at, signer.request_id.expires_at)

    def test_revoke_button_visible_only_to_manager_in_backend_views(self):
        signer_view_manager = self.env['open.sign.request.signer'].with_user(self.open_sign_manager).get_view(
            self.env.ref('open_sign.view_open_sign_request_signer_form').id,
            'form',
        )
        signer_view_user = self.env['open.sign.request.signer'].with_user(self.open_sign_user).get_view(
            self.env.ref('open_sign.view_open_sign_request_signer_form').id,
            'form',
        )
        request_view_manager = self.env['open.sign.request'].with_user(self.open_sign_manager).get_view(
            self.env.ref('open_sign.view_open_sign_request_form').id,
            'form',
        )
        request_view_user = self.env['open.sign.request'].with_user(self.open_sign_user).get_view(
            self.env.ref('open_sign.view_open_sign_request_form').id,
            'form',
        )

        self.assertIn('name="action_revoke_signer_portal_token"', signer_view_manager['arch'])
        self.assertNotIn('name="action_revoke_signer_portal_token"', signer_view_user['arch'])
        self.assertIn('name="action_revoke_signer_portal_token"', request_view_manager['arch'])
        self.assertNotIn('name="action_revoke_signer_portal_token"', request_view_user['arch'])

    def test_revoke_request_lock_conflict_returns_backend_validation_error(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Lock Conflict',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        with patch.object(
            type(signer),
            '_lock_request_for_update_nowait',
            autospec=True,
            side_effect=LockNotAvailable(),
        ):
            with self.assertRaisesRegex(ValidationError, 'currently locked'):
                signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalEmailTokenHttp(HttpCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_email_token_http_user',
            password='open_sign_portal_email_token_http_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_email_token_http_manager',
            password='open_sign_portal_email_token_http_manager',
            groups='open_sign.group_open_sign_manager',
        )
        cls.open_sign_user.partner_id.email = 'open.sign.portal.email.token.http.user@example.com'
        cls.open_sign_manager.partner_id.email = 'open.sign.portal.email.token.http.manager@example.com'

    @classmethod
    def _create_versioned_request_bundle(cls, env, *, name, owner, signer_partner=False):
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
            partner=signer_partner,
        )
        sign_request.action_version()
        return {
            'template': template,
            'role': role,
            'request': sign_request,
            'signer': signer,
        }

    @staticmethod
    def _expected_consent_hash():
        return hashlib.sha256(
            b'I agree to sign electronically and confirm my intent to sign this document.'
        ).hexdigest()

    def _build_save_payload(self, *, revision, field_id, value, access_token=False):
        payload = {
            'idempotency_key': str(uuid4()),
            'request_revision': revision,
            'values': [{'field_id': field_id, 'value': value}],
        }
        if access_token:
            payload['access_token'] = access_token
        return payload

    def _build_submit_payload(self, *, revision, field_id, value, access_token=False):
        payload = self._build_save_payload(
            revision=revision,
            field_id=field_id,
            value=value,
            access_token=access_token,
        )
        payload['consent'] = {
            'accepted': True,
            'text_hash': self._expected_consent_hash(),
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

    def _build_otp_verify_payload(self, *, revision, access_token=False):
        payload = {'request_revision': revision, 'code': '123456'}
        if access_token:
            payload['access_token'] = access_token
        return payload

    def _get_text_field_for_signer(self, signer):
        return signer.request_id.template_id.field_ids.filtered(
            lambda field: field.role_id == signer.role_id and field.type == 'text'
        )[:1]

    def _create_contact_correction_wizard(self, signer, *, reason='Rotate invitation'):
        return self.env['open.sign.signer.contact_correction.wizard'].with_user(self.open_sign_manager).create({
            'signer_id': signer.id,
            'target_email': signer.email,
            'reason': reason,
        })

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

    def test_initial_send_email_contains_fresh_token_not_preissued_token(self):
        bundle = self._create_versioned_request_bundle(
            self.env,
            name='Portal Email Token HTTP Initial Send',
            owner=self.open_sign_user,
        )
        signer = bundle['signer']
        old_token = signer._portal_ensure_token()

        bundle['request'].action_send()

        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
        ])
        queued_mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertIn(f"/my/sign/{signer.id}?access_token={signer.access_token}", queued_mail.body_html)
        self.assertNotIn(old_token, queued_mail.body_html)

    def test_manual_resend_old_token_invalid_new_token_valid(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token HTTP Manual Resend',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_token = signer.access_token

        wizard = self._create_contact_correction_wizard(signer)
        wizard.action_apply_contact_correction()
        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        new_token = signer.access_token

        self.authenticate(None, None)
        old_response = self.url_open(f"/my/sign/{signer.id}?access_token={old_token}", allow_redirects=False)
        new_response = self.url_open(f"/my/sign/{signer.id}?access_token={new_token}", allow_redirects=False)
        self.assertEqual(old_response.status_code, 303)
        self.assertEqual(new_response.status_code, 200)
        self.assertTrue(signer.email_token_issued_at)
        self.assertTrue(signer.email_token_expires_at)
        self.assertFalse(signer.email_token_revoked_at)

    def test_revoke_old_token_denies_signer_page_document_and_jsonrpc(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token HTTP Revoke Deny',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        old_token, _hidden_token = self._revoke_signer_token(signer)

        self.authenticate(None, None)
        page_response = self.url_open(f"/my/sign/{signer.id}?access_token={old_token}", allow_redirects=False)
        document_response = self.url_open(f"/my/sign/{signer.id}/document?access_token={old_token}", allow_redirects=False)
        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_save_payload(
                revision=signer.request_id.lock_version,
                field_id=field.id,
                value='revoked save',
                access_token=old_token,
            ),
        )
        submit_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/submit",
            self._build_submit_payload(
                revision=signer.request_id.lock_version,
                field_id=field.id,
                value='revoked submit',
                access_token=old_token,
            ),
        )
        decline_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/decline",
            self._build_decline_payload(
                revision=signer.request_id.lock_version,
                reason='revoked decline',
                access_token=old_token,
            ),
        )
        otp_request_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(
                revision=signer.request_id.lock_version,
                access_token=old_token,
            ),
        )
        otp_verify_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/verify",
            self._build_otp_verify_payload(
                revision=signer.request_id.lock_version,
                access_token=old_token,
            ),
        )

        self.assertEqual(page_response.status_code, 303)
        self.assertEqual(document_response.status_code, 303)
        for response in (
            save_response,
            submit_response,
            decline_response,
            otp_request_response,
            otp_verify_response,
        ):
            self.assertFalse(response['ok'])
            self.assertEqual(response['error_code'], 'invalid_token')

    def test_hidden_revoked_current_token_is_denied_as_invalid_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token Hidden Revoked Current Token',
            owner=self.open_sign_user,
            otp_required=True,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        field = self._get_text_field_for_signer(signer)
        _old_public_token, hidden_token = self._revoke_signer_token(signer)

        self.authenticate(None, None)
        page_response = self.url_open(f"/my/sign/{signer.id}?access_token={hidden_token}", allow_redirects=False)
        document_response = self.url_open(f"/my/sign/{signer.id}/document?access_token={hidden_token}", allow_redirects=False)
        save_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/save",
            self._build_save_payload(
                revision=signer.request_id.lock_version,
                field_id=field.id,
                value='hidden revoked save',
                access_token=hidden_token,
            ),
        )
        otp_request_response = self.make_jsonrpc_request(
            f"/my/sign/{signer.id}/otp/request",
            self._build_otp_request_payload(
                revision=signer.request_id.lock_version,
                access_token=hidden_token,
            ),
        )

        self.assertEqual(page_response.status_code, 303)
        self.assertEqual(document_response.status_code, 303)
        self.assertFalse(save_response['ok'])
        self.assertEqual(save_response['error_code'], 'invalid_token')
        self.assertFalse(otp_request_response['ok'])
        self.assertEqual(otp_request_response['error_code'], 'invalid_token')

    def test_revoke_does_not_change_request_or_signer_business_state(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token HTTP Revoke State',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        request_status_before = sign_request.status
        signer_state_before = signer.state
        value_count_before = self.env['open.sign.request.value'].search_count([('signer_id', '=', signer.id)])

        signer.with_user(self.open_sign_manager).action_revoke_signer_portal_token()

        sign_request.invalidate_recordset(['status'])
        signer.invalidate_recordset(['state'])
        self.assertEqual(sign_request.status, request_status_before)
        self.assertEqual(signer.state, signer_state_before)
        self.assertEqual(
            self.env['open.sign.request.value'].search_count([('signer_id', '=', signer.id)]),
            value_count_before,
        )

    def test_reminder_reuses_active_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token HTTP Reminder Reuse',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        mail_before = self.env['mail.mail'].sudo().search_count([('email_to', '=', signer.email)])
        token_before = signer.access_token
        issued_before = signer.email_token_issued_at
        expires_before = signer.email_token_expires_at

        notification_service.queue_request_reminders(
            sign_request,
            signer,
            trigger='cron_reminder',
            raise_on_failure=False,
        )

        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertEqual(signer.access_token, token_before)
        self.assertEqual(signer.email_token_issued_at, issued_before)
        self.assertEqual(signer.email_token_expires_at, expires_before)
        self.assertFalse(signer.email_token_revoked_at)
        queued_mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertEqual(
            self.env['mail.mail'].sudo().search_count([('email_to', '=', signer.email)]),
            mail_before + 1,
        )
        self.assertIn(f"/my/sign/{signer.id}?access_token={token_before}", queued_mail.body_html)

    def test_reminder_refreshes_revoked_token(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token HTTP Reminder Refresh',
            owner=self.open_sign_user,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        sign_request = signer.request_id
        old_public_token, revoked_hidden_token = self._revoke_signer_token(signer)

        notification_service.queue_request_reminders(
            sign_request,
            signer,
            trigger='cron_reminder',
            raise_on_failure=False,
        )

        signer.invalidate_recordset([
            'access_token',
            'email_token_issued_at',
            'email_token_expires_at',
            'email_token_revoked_at',
        ])
        self.assertNotEqual(signer.access_token, revoked_hidden_token)
        self.assertFalse(signer.email_token_revoked_at)

        queued_mail = self.env['mail.mail'].sudo().search([('email_to', '=', signer.email)], order='id desc', limit=1)
        self.assertIn(f"/my/sign/{signer.id}?access_token={signer.access_token}", queued_mail.body_html)
        self.assertNotIn(old_public_token, queued_mail.body_html)

        self.authenticate(None, None)
        old_response = self.url_open(f"/my/sign/{signer.id}?access_token={old_public_token}", allow_redirects=False)
        self.assertEqual(old_response.status_code, 303)

    def test_partner_linked_internal_fallback_still_works_after_token_revoke(self):
        bundle = self._create_portal_session(
            self.env,
            name='Portal Email Token HTTP Partner Fallback',
            owner=self.open_sign_manager,
            signer_partner=self.open_sign_user.partner_id,
        )
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        old_public_token, _hidden_token = self._revoke_signer_token(signer)

        self.authenticate(None, None)
        denied = self.url_open(f"/my/sign/{signer.id}?access_token={old_public_token}", allow_redirects=False)
        self.assertEqual(denied.status_code, 303)

        self.authenticate(self.open_sign_user.login, self.open_sign_user.login)
        allowed = self.url_open(f"/my/sign/{signer.id}", allow_redirects=False)
        self.assertEqual(allowed.status_code, 200)
