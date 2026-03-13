# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re


CONSENT_HASH_RE = re.compile(r'data-consent-hash="([0-9a-f]{64})"')
REQUEST_REVISION_RE = re.compile(r'data-request-revision="(\d+)"')


class OpenSignPortalTestMixin:
    QUEUE_FAILURE_WITH_TOKEN = 'SMTP failure for https://example.test/my/sign/42?access_token=abc123'

    @classmethod
    def _create_attachment_static(cls, env, name='portal_template.pdf', *, res_model='open.sign.template'):
        return env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(b'%PDF-1.4\n%%EOF\n'),
            'mimetype': 'application/pdf',
            'res_model': res_model,
            'company_id': env.company.id,
        })

    @classmethod
    def _create_template(cls, env, name):
        template = env['open.sign.template'].create({
            'name': name,
            'source_attachment_id': cls._create_attachment_static(env, f'{name}.pdf').id,
        })
        template.action_publish()
        return template

    @classmethod
    def _create_role(cls, env, template, name, sequence):
        return env['open.sign.role'].create({
            'template_id': template.id,
            'name': name,
            'sequence': sequence,
        })

    @classmethod
    def _create_field(cls, env, template, role, *, type='text', label='Portal Field', required=True, sequence=10, **overrides):
        values = {
            'template_id': template.id,
            'role_id': role.id,
            'type': type,
            'label': label,
            'required': required,
            'page': 1,
            'x': 0.1,
            'y': 0.1,
            'width': 0.2,
            'height': 0.05,
            'sequence': sequence,
        }
        values.update(overrides)
        return env['open.sign.template.field'].create(values)

    @classmethod
    def _create_request(cls, env, template, owner):
        return env['open.sign.request'].create({
            'name': f'{template.name} Request',
            'template_id': template.id,
            'owner_id': owner.id,
        })

    @classmethod
    def _create_signer(cls, env, sign_request, role, *, email, sequence=10, partner=False):
        vals = {
            'request_id': sign_request.id,
            'role_id': role.id,
            'email': email,
            'sequence': sequence,
        }
        if partner:
            vals['partner_id'] = partner.id
        return env['open.sign.request.signer'].create(vals)

    @classmethod
    def _prepare_request_for_portal(cls, sign_request, *, send=True):
        sign_request.action_version()
        if send:
            sign_request.action_send()
        return sign_request

    def _assert_no_url_or_token_leak(self, payload, *extra_forbidden):
        serialized = str(payload)
        self.assertNotIn('access_token=', serialized)
        self.assertNotIn('https://example.test/my/sign/42', serialized)
        for forbidden in extra_forbidden:
            if forbidden:
                self.assertNotIn(forbidden, serialized)

    @staticmethod
    def _mutate_token(token):
        if not token:
            return token
        replacement = '0' if token[-1] != '0' else '1'
        return f'{token[:-1]}{replacement}'

    @classmethod
    def _create_portal_session(
        cls,
        env,
        *,
        name,
        owner,
        signer_partner=False,
        with_required_signature=False,
        otp_required=False,
    ):
        template = cls._create_template(env, name)
        role = cls._create_role(env, template, f'{name} Signer', 10)
        if with_required_signature:
            cls._create_field(
                env,
                template,
                role,
                type='signature',
                label=f'{name} Signature',
                required=True,
                sequence=10,
            )
        else:
            cls._create_field(
                env,
                template,
                role,
                type='text',
                label=f'{name} Text',
                required=True,
                sequence=10,
            )
            cls._create_field(
                env,
                template,
                role,
                type='checkbox',
                label=f'{name} Checkbox',
                required=False,
                sequence=20,
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
        if otp_required:
            signer.write({'otp_required': True})
        cls._prepare_request_for_portal(sign_request)
        return {
            'template': template,
            'role': role,
            'request': sign_request,
            'signer': signer,
            'token': signer._portal_ensure_token(),
        }

    @classmethod
    def _create_ordered_two_signer_session(
        cls,
        env,
        *,
        name,
        owner,
        first_signer_partner=False,
        second_signer_partner=False,
        first_sequence=10,
        second_sequence=20,
        ordered_signing=True,
        first_otp_required=False,
        second_otp_required=False,
    ):
        template = cls._create_template(env, name)
        role_first = cls._create_role(env, template, f'{name} First', first_sequence)
        role_second = cls._create_role(env, template, f'{name} Second', second_sequence)
        field_first = cls._create_field(
            env,
            template,
            role_first,
            type='text',
            label=f'{name} First Text',
            required=True,
            sequence=10,
        )
        field_second = cls._create_field(
            env,
            template,
            role_second,
            type='text',
            label=f'{name} Second Text',
            required=True,
            sequence=10,
        )
        sign_request = cls._create_request(env, template, owner=owner)
        sign_request.write({'ordered_signing': ordered_signing})
        signer_first = cls._create_signer(
            env,
            sign_request,
            role_first,
            email=f'{name.lower().replace(" ", ".")}.first@example.com',
            sequence=first_sequence,
            partner=first_signer_partner,
        )
        signer_second = cls._create_signer(
            env,
            sign_request,
            role_second,
            email=f'{name.lower().replace(" ", ".")}.second@example.com',
            sequence=second_sequence,
            partner=second_signer_partner,
        )
        if first_otp_required:
            signer_first.write({'otp_required': True})
        if second_otp_required:
            signer_second.write({'otp_required': True})
        cls._prepare_request_for_portal(sign_request)
        return {
            'template': template,
            'request': sign_request,
            'signer_first': signer_first,
            'signer_second': signer_second,
            'field_first': field_first,
            'field_second': field_second,
            'token_first': signer_first._portal_ensure_token(),
            'token_second': signer_second._portal_ensure_token(),
        }
