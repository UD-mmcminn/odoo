# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'open_sign')
class TestOpenSignSecurityRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Open Sign Security Company B'})

        cls.user_owner = new_test_user(
            cls.env,
            login='open_sign_security_owner',
            groups='open_sign.group_open_sign_user',
            company_id=cls.company_a.id,
        )
        cls.user_assignee = new_test_user(
            cls.env,
            login='open_sign_security_assignee',
            groups='open_sign.group_open_sign_user',
            company_id=cls.company_a.id,
        )
        cls.user_outsider = new_test_user(
            cls.env,
            login='open_sign_security_outsider',
            groups='open_sign.group_open_sign_user',
            company_id=cls.company_a.id,
        )
        cls.manager_a = new_test_user(
            cls.env,
            login='open_sign_security_manager_a',
            groups='open_sign.group_open_sign_manager',
            company_id=cls.company_a.id,
        )
        cls.manager_multi = new_test_user(
            cls.env,
            login='open_sign_security_manager_multi',
            groups='open_sign.group_open_sign_manager',
            company_id=cls.company_a.id,
        )
        cls.auditor_a = new_test_user(
            cls.env,
            login='open_sign_security_auditor_a',
            groups='open_sign.group_open_sign_auditor',
            company_id=cls.company_a.id,
        )
        cls.auditor_multi = new_test_user(
            cls.env,
            login='open_sign_security_auditor_multi',
            groups='open_sign.group_open_sign_auditor',
            company_id=cls.company_a.id,
        )

        cls.user_owner.write({
            'email': 'owner.security@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.user_assignee.write({
            'email': 'assignee.security@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.user_outsider.write({
            'email': 'outsider.security@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.manager_a.write({
            'email': 'manager.a.security@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.manager_multi.write({
            'email': 'manager.multi.security@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id, cls.company_b.id])],
        })
        cls.auditor_a.write({
            'email': 'auditor.a.security@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id])],
        })
        cls.auditor_multi.write({
            'email': 'auditor.multi.security@example.com',
            'company_id': cls.company_a.id,
            'company_ids': [Command.set([cls.company_a.id, cls.company_b.id])],
        })

        cls.bundle_a = cls._create_company_bundle_static(
            cls.env,
            company=cls.company_a,
            owner=cls.user_owner,
            signer_email=cls.user_assignee.email,
            signer_partner=cls.user_assignee.partner_id,
            prefix='Company A',
            hash_char='a',
        )
        cls.bundle_b = cls._create_company_bundle_static(
            cls.env,
            company=cls.company_b,
            owner=cls.manager_multi,
            signer_email='company.b.signer@example.com',
            prefix='Company B',
            hash_char='b',
        )

    @classmethod
    def _create_attachment_static(cls, env, company, name='template.pdf', res_model='open.sign.template'):
        return env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(b'%PDF-1.4\n%%EOF\n'),
            'mimetype': 'application/pdf',
            'res_model': res_model,
            'company_id': company.id,
        })

    @classmethod
    def _create_company_bundle_static(cls, env, company, owner, signer_email, prefix, hash_char, signer_partner=None):
        attachment = cls._create_attachment_static(
            env,
            company=company,
            name=f'{prefix}.pdf',
        )
        template = env['open.sign.template'].create({
            'name': f'{prefix} Template',
            'source_attachment_id': attachment.id,
            'company_id': company.id,
            'owner_id': owner.id,
        })
        template.action_publish()
        version = template.action_publish_version()

        role = env['open.sign.role'].create({
            'template_id': template.id,
            'name': f'{prefix} Signer',
            'sequence': 10,
        })
        text_field = env['open.sign.template.field'].create({
            'template_id': template.id,
            'role_id': role.id,
            'type': 'text',
            'label': f'{prefix} Text Field',
            'page': 1,
            'x': 0.1,
            'y': 0.1,
            'width': 0.3,
            'height': 0.05,
            'sequence': 10,
        })
        selection_field = env['open.sign.template.field'].create({
            'template_id': template.id,
            'role_id': role.id,
            'type': 'selection',
            'label': f'{prefix} Selection Field',
            'page': 1,
            'x': 0.2,
            'y': 0.2,
            'width': 0.3,
            'height': 0.05,
            'sequence': 20,
            'option_ids': [Command.create({
                'value': f'{prefix.casefold().replace(" ", "_")}_choice',
                'label': f'{prefix} Choice',
                'sequence': 10,
                'is_default': True,
            })],
        })
        option = selection_field.option_ids[:1]

        request = env['open.sign.request'].create({
            'name': f'{prefix} Request',
            'template_id': template.id,
            'company_id': company.id,
            'owner_id': owner.id,
        })
        signer = env['open.sign.request.signer'].create({
            'request_id': request.id,
            'role_id': role.id,
            'partner_id': signer_partner.id if signer_partner else False,
            'email': signer_email,
            'sequence': 10,
        })
        value = env['open.sign.request.value'].create({
            'request_id': request.id,
            'template_field_id': text_field.id,
            'signer_id': signer.id,
            'value_text': f'{prefix} Value',
        })
        audit_log = env['open.sign.audit.log'].sudo().create({
            'request_id': request.id,
            'signer_id': signer.id,
            'event_type': 'request_created',
            'event_sequence': 1,
            'hash_chain': hash_char * 64,
        })
        return {
            'template': template,
            'version': version,
            'role': role,
            'field': text_field,
            'option': option,
            'request': request,
            'signer': signer,
            'value': value,
            'audit_log': audit_log,
        }

    def _visible_ids(self, model_name, user, ids):
        return set(self.env[model_name].with_user(user).search([('id', 'in', ids)]).ids)

    def test_user_request_scope_is_owner_or_assignee(self):
        request_ids = [self.bundle_a['request'].id, self.bundle_b['request'].id]
        signer_ids = [self.bundle_a['signer'].id, self.bundle_b['signer'].id]
        value_ids = [self.bundle_a['value'].id, self.bundle_b['value'].id]
        audit_ids = [self.bundle_a['audit_log'].id, self.bundle_b['audit_log'].id]

        self.assertEqual(self._visible_ids('open.sign.request', self.user_owner, request_ids), {self.bundle_a['request'].id})
        self.assertEqual(self._visible_ids('open.sign.request', self.user_assignee, request_ids), {self.bundle_a['request'].id})
        self.assertEqual(self._visible_ids('open.sign.request', self.user_outsider, request_ids), set())

        self.assertEqual(self._visible_ids('open.sign.request.signer', self.user_assignee, signer_ids), {self.bundle_a['signer'].id})
        self.assertEqual(self._visible_ids('open.sign.request.signer', self.user_outsider, signer_ids), set())

        self.assertEqual(self._visible_ids('open.sign.request.value', self.user_assignee, value_ids), {self.bundle_a['value'].id})
        self.assertEqual(self._visible_ids('open.sign.request.value', self.user_outsider, value_ids), set())

        self.assertEqual(self._visible_ids('open.sign.audit.log', self.user_owner, audit_ids), {self.bundle_a['audit_log'].id})
        self.assertEqual(self._visible_ids('open.sign.audit.log', self.user_assignee, audit_ids), set())
        self.assertEqual(self._visible_ids('open.sign.audit.log', self.user_outsider, audit_ids), set())

    def test_assignee_can_read_request_content_from_other_signers_without_audit_metadata(self):
        peer_role = self.env['open.sign.role'].create({
            'template_id': self.bundle_a['template'].id,
            'name': 'Company A Peer Signer',
            'sequence': 20,
        })
        peer_field = self.env['open.sign.template.field'].create({
            'template_id': self.bundle_a['template'].id,
            'role_id': peer_role.id,
            'type': 'text',
            'label': 'Company A Peer Text Field',
            'page': 1,
            'x': 0.3,
            'y': 0.3,
            'width': 0.3,
            'height': 0.05,
            'sequence': 30,
        })
        peer_signer = self.env['open.sign.request.signer'].create({
            'request_id': self.bundle_a['request'].id,
            'role_id': peer_role.id,
            'email': 'peer.signer@example.com',
            'sequence': 20,
        })
        peer_value = self.env['open.sign.request.value'].create({
            'request_id': self.bundle_a['request'].id,
            'template_field_id': peer_field.id,
            'signer_id': peer_signer.id,
            'value_text': 'Peer Signer Value',
        })
        peer_audit_log = self.env['open.sign.audit.log'].sudo().create({
            'request_id': self.bundle_a['request'].id,
            'signer_id': peer_signer.id,
            'event_type': 'value_saved',
            'event_sequence': 2,
            'hash_chain': 'c' * 64,
        })

        signer_ids = [self.bundle_a['signer'].id, peer_signer.id]
        value_ids = [self.bundle_a['value'].id, peer_value.id]
        audit_ids = [self.bundle_a['audit_log'].id, peer_audit_log.id]

        self.assertEqual(self._visible_ids('open.sign.request.signer', self.user_assignee, signer_ids), set(signer_ids))
        self.assertEqual(self._visible_ids('open.sign.request.value', self.user_assignee, value_ids), set(value_ids))
        self.assertEqual(self._visible_ids('open.sign.audit.log', self.user_assignee, audit_ids), set())

    def test_email_spoofing_does_not_grant_request_access(self):
        request_ids = [self.bundle_a['request'].id, self.bundle_b['request'].id]
        signer_ids = [self.bundle_a['signer'].id, self.bundle_b['signer'].id]
        value_ids = [self.bundle_a['value'].id, self.bundle_b['value'].id]
        audit_ids = [self.bundle_a['audit_log'].id, self.bundle_b['audit_log'].id]

        self.assertEqual(self._visible_ids('open.sign.request', self.user_outsider, request_ids), set())
        self.assertEqual(self._visible_ids('open.sign.request.signer', self.user_outsider, signer_ids), set())
        self.assertEqual(self._visible_ids('open.sign.request.value', self.user_outsider, value_ids), set())
        self.assertEqual(self._visible_ids('open.sign.audit.log', self.user_outsider, audit_ids), set())

        self.user_outsider.sudo().write({'email': self.user_assignee.email})

        self.assertEqual(self._visible_ids('open.sign.request', self.user_outsider, request_ids), set())
        self.assertEqual(self._visible_ids('open.sign.request.signer', self.user_outsider, signer_ids), set())
        self.assertEqual(self._visible_ids('open.sign.request.value', self.user_outsider, value_ids), set())
        self.assertEqual(self._visible_ids('open.sign.audit.log', self.user_outsider, audit_ids), set())

    def test_user_scope_rules_block_write_and_create_outside_scope(self):
        with self.assertRaises(AccessError):
            self.bundle_a['request'].with_user(self.user_outsider).write({'name': 'Denied Update'})

        with self.assertRaises(AccessError):
            self.env['open.sign.request.signer'].with_user(self.user_outsider).create({
                'request_id': self.bundle_a['request'].id,
                'role_id': self.bundle_a['role'].id,
                'email': 'denied.create.signer@example.com',
                'sequence': 20,
            })

        with self.assertRaises(AccessError):
            self.env['open.sign.request.value'].with_user(self.user_outsider).create({
                'request_id': self.bundle_a['request'].id,
                'template_field_id': self.bundle_a['field'].id,
                'signer_id': self.bundle_a['signer'].id,
                'value_text': 'Denied Value',
            })

    def test_company_scope_is_enforced_on_template_family_models(self):
        template_ids = [self.bundle_a['template'].id, self.bundle_b['template'].id]
        version_ids = [self.bundle_a['version'].id, self.bundle_b['version'].id]
        role_ids = [self.bundle_a['role'].id, self.bundle_b['role'].id]
        field_ids = [self.bundle_a['field'].id, self.bundle_b['field'].id]
        option_ids = [self.bundle_a['option'].id, self.bundle_b['option'].id]

        self.assertEqual(self._visible_ids('open.sign.template', self.user_owner, template_ids), {self.bundle_a['template'].id})
        self.assertEqual(self._visible_ids('open.sign.template.version', self.user_owner, version_ids), {self.bundle_a['version'].id})
        self.assertEqual(self._visible_ids('open.sign.role', self.user_owner, role_ids), {self.bundle_a['role'].id})
        self.assertEqual(self._visible_ids('open.sign.template.field', self.user_owner, field_ids), {self.bundle_a['field'].id})
        self.assertEqual(self._visible_ids('open.sign.template.field.option', self.user_owner, option_ids), {self.bundle_a['option'].id})

    def test_manager_and_auditor_scoping_respects_allowed_companies(self):
        request_ids = [self.bundle_a['request'].id, self.bundle_b['request'].id]

        self.assertEqual(self._visible_ids('open.sign.request', self.manager_a, request_ids), {self.bundle_a['request'].id})
        self.assertEqual(self._visible_ids('open.sign.request', self.manager_multi, request_ids), set(request_ids))

        self.assertEqual(self._visible_ids('open.sign.request', self.auditor_a, request_ids), {self.bundle_a['request'].id})
        self.assertEqual(self._visible_ids('open.sign.request', self.auditor_multi, request_ids), set(request_ids))
