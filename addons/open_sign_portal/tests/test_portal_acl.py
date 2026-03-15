# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from odoo.addons.open_sign_portal.tests.common import OpenSignPortalTestMixin


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalAcl(TransactionCase, OpenSignPortalTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Open Sign Portal ACL Company B'})

        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_portal_acl_user',
            groups='open_sign.group_open_sign_user',
            company_id=cls.company_a.id,
        )
        cls.open_sign_manager = new_test_user(
            cls.env,
            login='open_sign_portal_acl_manager',
            groups='open_sign.group_open_sign_manager',
            company_id=cls.company_a.id,
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_portal_acl_auditor',
            groups='open_sign.group_open_sign_auditor',
            company_id=cls.company_a.id,
        )
        cls.system_user_single = new_test_user(
            cls.env,
            login='open_sign_portal_acl_system_single',
            groups='base.group_system',
            company_id=cls.company_a.id,
        )
        cls.system_user_multi = new_test_user(
            cls.env,
            login='open_sign_portal_acl_system_multi',
            groups='base.group_system',
            company_id=cls.company_a.id,
        )

        cls.open_sign_user.write({
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.open_sign_manager.write({
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.open_sign_auditor.write({
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.system_user_single.write({
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.system_user_multi.write({
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id, cls.company_b.id])],
        })

        cls.bundle_a = cls._create_portal_session(
            cls.env,
            name='Portal ACL Company A',
            owner=cls.env.user,
            otp_required=True,
        )
        env_company_b = cls.env['open.sign.request'].with_company(cls.company_b).env
        cls.bundle_b = cls._create_portal_session(
            env_company_b,
            name='Portal ACL Company B',
            owner=cls.env.user,
            otp_required=True,
        )

        cls.challenge_a = cls.env['open.sign.otp.challenge'].sudo().create({
            'request_signer_id': cls.bundle_a['signer'].id,
            'expires_at': '2099-01-01 00:00:00',
            'code_salt': 'ab' * 16,
            'code_hash': '0' * 64,
        })
        cls.challenge_b = cls.env['open.sign.otp.challenge'].sudo().create({
            'request_signer_id': cls.bundle_b['signer'].id,
            'expires_at': '2099-01-01 00:00:00',
            'code_salt': 'cd' * 16,
            'code_hash': '1' * 64,
        })

    def _assert_challenge_model_denied(self, user):
        challenge_model = self.env['open.sign.otp.challenge'].with_user(user)
        with self.assertRaises(AccessError):
            challenge_model.check_access('read')
        with self.assertRaises(AccessError):
            challenge_model.create({
                'request_signer_id': self.bundle_a['signer'].id,
                'expires_at': '2099-01-02 00:00:00',
                'code_salt': 'ef' * 16,
                'code_hash': '2' * 64,
            })
        with self.assertRaises(AccessError):
            self.challenge_a.with_user(user).write({'attempt_count': 1})
        with self.assertRaises(AccessError):
            self.challenge_a.with_user(user).unlink()

    def test_otp_challenge_denies_open_sign_user_all_model_access(self):
        self._assert_challenge_model_denied(self.open_sign_user)

    def test_otp_challenge_denies_open_sign_manager_all_model_access(self):
        self._assert_challenge_model_denied(self.open_sign_manager)

    def test_otp_challenge_denies_open_sign_auditor_all_model_access(self):
        self._assert_challenge_model_denied(self.open_sign_auditor)

    def test_otp_challenge_allows_system_group_access(self):
        model = self.env['open.sign.otp.challenge'].with_user(self.system_user_single)
        fresh_bundle = self._create_portal_session(
            self.env,
            name='Portal ACL System Access',
            owner=self.env.user,
            otp_required=True,
        )
        challenge = model.create({
            'request_signer_id': fresh_bundle['signer'].id,
            'expires_at': '2099-01-03 00:00:00',
            'code_salt': '12' * 16,
            'code_hash': '3' * 64,
        })
        self.assertTrue(model.search([('id', '=', self.challenge_a.id)]))
        challenge.write({'attempt_count': 2})
        self.assertEqual(challenge.attempt_count, 2)
        challenge.unlink()

    def test_otp_challenge_system_access_is_company_scoped(self):
        visible_single = set(
            self.env['open.sign.otp.challenge'].with_user(self.system_user_single).search([
                ('id', 'in', [self.challenge_a.id, self.challenge_b.id]),
            ]).ids
        )
        visible_multi = set(
            self.env['open.sign.otp.challenge'].with_user(self.system_user_multi).search([
                ('id', 'in', [self.challenge_a.id, self.challenge_b.id]),
            ]).ids
        )
        self.assertEqual(visible_single, {self.challenge_a.id})
        self.assertEqual(visible_multi, {self.challenge_a.id, self.challenge_b.id})

    def test_otp_challenge_hash_fields_are_system_only(self):
        user_fields = self.env['open.sign.otp.challenge'].with_user(self.open_sign_user).fields_get()
        manager_fields = self.env['open.sign.otp.challenge'].with_user(self.open_sign_manager).fields_get()
        system_fields = self.env['open.sign.otp.challenge'].fields_get()

        self.assertNotIn('code_hash', user_fields)
        self.assertNotIn('code_salt', user_fields)
        self.assertNotIn('code_hash', manager_fields)
        self.assertNotIn('code_salt', manager_fields)
        self.assertIn('code_hash', system_fields)
        self.assertIn('code_salt', system_fields)

    def test_signer_portal_fields_visible_to_open_sign_user(self):
        signer_fields = self.bundle_a['signer'].with_user(self.open_sign_user).fields_get()
        self.assertIn('portal_sign_url', signer_fields)
        self.assertIn('otp_required', signer_fields)
        self.assertIn('otp_verified_at', signer_fields)

        signer_view = self.env['open.sign.request.signer'].with_user(self.open_sign_user).get_view(
            self.env.ref('open_sign.view_open_sign_request_signer_form').id,
            'form',
        )['arch']
        request_view = self.env['open.sign.request'].with_user(self.open_sign_user).get_view(
            self.env.ref('open_sign.view_open_sign_request_form').id,
            'form',
        )['arch']
        self.assertIn('name="portal_sign_url"', signer_view)
        self.assertIn('name="otp_required"', signer_view)
        self.assertIn('name="otp_verified_at"', signer_view)
        self.assertIn('name="portal_sign_url"', request_view)
        self.assertIn('name="otp_required"', request_view)
        self.assertIn('name="otp_verified_at"', request_view)

    def test_signer_portal_fields_visible_to_open_sign_manager(self):
        signer_fields = self.bundle_a['signer'].with_user(self.open_sign_manager).fields_get()
        self.assertIn('portal_sign_url', signer_fields)
        self.assertIn('otp_required', signer_fields)
        self.assertIn('otp_verified_at', signer_fields)

        signer_view = self.env['open.sign.request.signer'].with_user(self.open_sign_manager).get_view(
            self.env.ref('open_sign.view_open_sign_request_signer_form').id,
            'form',
        )['arch']
        request_view = self.env['open.sign.request'].with_user(self.open_sign_manager).get_view(
            self.env.ref('open_sign.view_open_sign_request_form').id,
            'form',
        )['arch']
        self.assertIn('name="portal_sign_url"', signer_view)
        self.assertIn('name="otp_required"', signer_view)
        self.assertIn('name="otp_verified_at"', signer_view)
        self.assertIn('name="portal_sign_url"', request_view)
        self.assertIn('name="otp_required"', request_view)
        self.assertIn('name="otp_verified_at"', request_view)

    def test_signer_portal_fields_hidden_from_open_sign_auditor(self):
        signer_fields = self.bundle_a['signer'].with_user(self.open_sign_auditor).fields_get()
        self.assertNotIn('portal_sign_url', signer_fields)
        self.assertNotIn('otp_required', signer_fields)
        self.assertNotIn('otp_verified_at', signer_fields)

        signer_view = self.env['open.sign.request.signer'].with_user(self.open_sign_auditor).get_view(
            self.env.ref('open_sign.view_open_sign_request_signer_form').id,
            'form',
        )['arch']
        request_view = self.env['open.sign.request'].with_user(self.open_sign_auditor).get_view(
            self.env.ref('open_sign.view_open_sign_request_form').id,
            'form',
        )['arch']
        self.assertNotIn('name="portal_sign_url"', signer_view)
        self.assertNotIn('name="otp_required"', signer_view)
        self.assertNotIn('name="otp_verified_at"', signer_view)
        self.assertNotIn('name="portal_sign_url"', request_view)
        self.assertNotIn('name="otp_required"', request_view)
        self.assertNotIn('name="otp_verified_at"', request_view)

    def test_access_token_field_remains_system_only(self):
        user_fields = self.bundle_a['signer'].with_user(self.open_sign_user).fields_get()
        manager_fields = self.bundle_a['signer'].with_user(self.open_sign_manager).fields_get()
        auditor_fields = self.bundle_a['signer'].with_user(self.open_sign_auditor).fields_get()
        system_fields = self.env['open.sign.request.signer'].fields_get()

        self.assertNotIn('access_token', user_fields)
        self.assertNotIn('access_token', manager_fields)
        self.assertNotIn('access_token', auditor_fields)
        self.assertIn('access_token', system_fields)

    def test_no_action_window_exists_for_otp_challenge(self):
        action_count = self.env['ir.actions.act_window'].sudo().search_count([
            ('res_model', '=', 'open.sign.otp.challenge'),
        ])
        self.assertEqual(action_count, 0)

    def test_no_menu_entry_exists_for_otp_challenge(self):
        for menu in self.env['ir.ui.menu'].sudo().search([('action', '!=', False)]):
            action = menu.action
            if action and action._name == 'ir.actions.act_window':
                self.assertNotEqual(action.res_model, 'open.sign.otp.challenge')
