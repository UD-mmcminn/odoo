# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignBackendViews(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.open_sign_user = new_test_user(
            cls.env,
            login='open_sign_view_user',
            groups='open_sign.group_open_sign_user',
        )
        cls.open_sign_auditor = new_test_user(
            cls.env,
            login='open_sign_view_auditor',
            groups='open_sign.group_open_sign_auditor',
        )

    def test_actions_include_kanban_mode(self):
        action_xmlids = [
            'open_sign.action_open_sign_template',
            'open_sign.action_open_sign_request',
            'open_sign.action_open_sign_role',
            'open_sign.action_open_sign_template_field',
            'open_sign.action_open_sign_template_version',
            'open_sign.action_open_sign_request_signer',
            'open_sign.action_open_sign_request_value',
            'open_sign.action_open_sign_audit_log',
        ]
        for action_xmlid in action_xmlids:
            action = self.env.ref(action_xmlid)
            modes = {mode.strip() for mode in (action.view_mode or '').split(',') if mode}
            self.assertIn('list', modes, f"{action_xmlid} must include list mode.")
            self.assertIn('kanban', modes, f"{action_xmlid} must include kanban mode.")
            self.assertIn('form', modes, f"{action_xmlid} must include form mode.")
            self.assertTrue(
                self.env[action.res_model].with_user(self.open_sign_user).has_access('read'),
                f"{action_xmlid} model must be readable by Open Sign user.",
            )

    def test_kanban_view_architectures_load(self):
        view_specs = [
            ('open_sign.view_open_sign_template_kanban', 'open.sign.template'),
            ('open_sign.view_open_sign_request_kanban', 'open.sign.request'),
            ('open_sign.view_open_sign_role_kanban', 'open.sign.role'),
            ('open_sign.view_open_sign_template_field_kanban', 'open.sign.template.field'),
            ('open_sign.view_open_sign_template_version_kanban', 'open.sign.template.version'),
            ('open_sign.view_open_sign_request_signer_kanban', 'open.sign.request.signer'),
            ('open_sign.view_open_sign_request_value_kanban', 'open.sign.request.value'),
            ('open_sign.view_open_sign_audit_log_kanban', 'open.sign.audit.log'),
        ]
        for view_xmlid, model_name in view_specs:
            view = self.env.ref(view_xmlid)
            self.env[model_name].get_view(view_id=view.id, view_type='kanban')

    def test_menu_hierarchy_and_audit_read_visibility(self):
        root_menu = self.env.ref('open_sign.menu_open_sign_root')
        self.assertEqual(root_menu.name, 'Open Sign')

        expected_direct_child_xmlids = [
            'open_sign.menu_open_sign_requests',
            'open_sign.menu_open_sign_templates',
            'open_sign.menu_open_sign_signers',
            'open_sign.menu_open_sign_values',
            'open_sign.menu_open_sign_audit_logs',
            'open_sign.menu_open_sign_configuration',
        ]
        expected_direct_child_ids = {self.env.ref(xmlid).id for xmlid in expected_direct_child_xmlids}
        self.assertTrue(
            expected_direct_child_ids.issubset(set(root_menu.child_id.ids)),
            "Open Sign root menu is missing expected direct child menus.",
        )

        audit_action = self.env.ref('open_sign.action_open_sign_audit_log')
        self.assertEqual(audit_action.res_model, 'open.sign.audit.log')
        self.assertTrue(self.env['open.sign.audit.log'].with_user(self.open_sign_auditor).has_access('read'))
