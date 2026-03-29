# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from contextlib import contextmanager
import hashlib
import json
import re
from urllib.parse import urljoin

import requests

import odoo.http
import odoo.sql_db
from odoo import SUPERUSER_ID, api
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.orm.environments import Transaction
from odoo.tests import HOST


CONSENT_HASH_RE = re.compile(r'data-consent-hash="([0-9a-f]{64})"')
REQUEST_REVISION_RE = re.compile(r'data-request-revision="(\d+)"')
PDF_RENDER_URL_RE = re.compile(r'data-pdf-render-url="([^"]*)"')
PORTAL_FIELDS_JSON_RE = re.compile(
    r'<script type="application/json" class="o_open_sign_fields_payload">(.*?)</script>',
    re.S,
)


class OpenSignPortalTestMixin:
    QUEUE_FAILURE_WITH_TOKEN = 'SMTP failure for https://example.test/my/sign/42?access_token=abc123'

    @staticmethod
    def _ip_headers(client_ip):
        return {'X-Forwarded-For': client_ip}

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
    def _create_image_attachment_static(
        cls,
        env,
        name='portal_signature.png',
        *,
        res_model='open.sign.request.value',
        res_id=False,
        mimetype='image/png',
        public=False,
        description=False,
        raw_payload=False,
    ):
        attachment_vals = {
            'name': name,
            'datas': base64.b64encode(
                raw_payload or (
                b'\x89PNG\r\n\x1a\n'
                b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
                b'\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x03\x00\x08\xfc\x02\xfe_aH7\x00\x00\x00\x00IEND\xaeB`\x82'
                )
            ),
            'mimetype': mimetype,
            'res_model': res_model,
            'public': public,
            'company_id': env.company.id,
        }
        if res_id:
            attachment_vals['res_id'] = res_id
        if description is not False:
            attachment_vals['description'] = description
        return env['ir.attachment'].create(attachment_vals)

    @classmethod
    def _build_portal_capture_attachment_description(cls, signer, template_field):
        return json.dumps({
            'kind': 'open_sign_portal_capture',
            'request_id': signer.request_id.id,
            'signer_id': signer.id,
            'field_id': template_field.id,
            'field_type': template_field.type,
        }, separators=(',', ':'))

    @classmethod
    def _create_portal_capture_attachment_static(
        cls,
        env,
        signer,
        template_field,
        *,
        name='portal_signature.png',
        mimetype='image/png',
        public=False,
        description=False,
        raw_payload=False,
    ):
        return cls._create_image_attachment_static(
            env,
            name=name,
            res_model='open.sign.request.signer',
            res_id=signer.id,
            mimetype=mimetype,
            public=public,
            description=(
                cls._build_portal_capture_attachment_description(signer, template_field)
                if description is False
                else description
            ),
            raw_payload=raw_payload,
        )

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

    def _run_committed(self, callback, *, uid=False, context=None):
        with odoo.sql_db.db_connect(self.registry.db_name).cursor() as cr:
            cr.transaction = Transaction(self.registry)
            env = api.Environment(cr, uid or self.env.uid, context or {})
            try:
                result = callback(env)
                cr.commit()
                return result
            except Exception:
                cr.rollback()
                raise
            finally:
                env.clear()

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

    @staticmethod
    def _bundle_signer_id(bundle, signer_key):
        signer = bundle[signer_key]
        return signer.id if hasattr(signer, 'id') else signer

    def _refresh_bundle_token(self, bundle, *, signer_key='signer', token_key='token'):
        signer = self.env['open.sign.request.signer'].browse(self._bundle_signer_id(bundle, signer_key))
        signer.invalidate_recordset(['access_token'])
        bundle[token_key] = signer.access_token
        return bundle[token_key]

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
        signer.invalidate_recordset(['access_token', 'email_token_issued_at', 'email_token_expires_at'])
        if not signer.email_token_issued_at or not signer.email_token_expires_at:
            signer._issue_email_portal_token(trigger='initial_send')
            signer.invalidate_recordset(['access_token'])
        return {
            'template': template,
            'role': role,
            'request': sign_request,
            'signer': signer,
            'token': signer.access_token,
        }

    def _create_portal_session_committed(
        self,
        *,
        name,
        owner,
        signer_partner=False,
        with_required_signature=False,
        otp_required=False,
    ):
        owner_id = owner.id if owner else False
        signer_partner_id = signer_partner.id if signer_partner else False

        bundle_data = self._run_committed(
            lambda env: self._serialize_portal_bundle(
                self._create_portal_session(
                    env,
                    name=name,
                    owner=(env['res.users'].browse(owner_id).exists() or env.user) if owner_id else env.user,
                    signer_partner=env['res.partner'].browse(signer_partner_id) if signer_partner_id else False,
                    with_required_signature=with_required_signature,
                    otp_required=otp_required,
                )
            )
        )
        return self._materialize_portal_bundle(bundle_data)

    @staticmethod
    def _serialize_portal_bundle(bundle):
        serialized = {'token': bundle['token']}
        for key, value in bundle.items():
            if key == 'token':
                continue
            serialized[key] = value.id if hasattr(value, 'id') else value
        return serialized

    def _materialize_portal_bundle(self, bundle_data):
        materialized = dict(bundle_data)
        model_by_key = {
            'template': 'open.sign.template',
            'role': 'open.sign.role',
            'request': 'open.sign.request',
            'signer': 'open.sign.request.signer',
            'field_first': 'open.sign.template.field',
            'field_second': 'open.sign.template.field',
            'signer_first': 'open.sign.request.signer',
            'signer_second': 'open.sign.request.signer',
        }
        for key, model_name in model_by_key.items():
            if key in materialized and materialized[key]:
                materialized[key] = self.env[model_name].browse(materialized[key])
        return materialized

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
        signer_first.invalidate_recordset(['access_token', 'email_token_issued_at', 'email_token_expires_at'])
        signer_second.invalidate_recordset(['access_token', 'email_token_issued_at', 'email_token_expires_at'])
        if not signer_first.email_token_issued_at or not signer_first.email_token_expires_at:
            signer_first._issue_email_portal_token(trigger='initial_send')
        if not signer_second.email_token_issued_at or not signer_second.email_token_expires_at:
            signer_second._issue_email_portal_token(trigger='initial_send')
        signer_first.invalidate_recordset(['access_token'])
        signer_second.invalidate_recordset(['access_token'])
        return {
            'template': template,
            'request': sign_request,
            'signer_first': signer_first,
            'signer_second': signer_second,
            'field_first': field_first,
            'field_second': field_second,
            'token_first': signer_first.access_token,
            'token_second': signer_second.access_token,
        }


class OpenSignPortalHttpTestMixin(OpenSignPortalTestMixin):

    def _new_isolated_http_session(self):
        session = requests.Session()
        session.cookies.update(self.opener.cookies)
        return session

    @staticmethod
    def _extract_consent_hash_and_revision(html):
        consent_match = CONSENT_HASH_RE.search(html)
        revision_match = REQUEST_REVISION_RE.search(html)
        assert consent_match, "Expected consent hash marker on portal page"
        assert revision_match, "Expected request revision marker on portal page"
        return consent_match.group(1), int(revision_match.group(1))

    @staticmethod
    def _extract_pdf_render_url(html):
        url_match = PDF_RENDER_URL_RE.search(html or "")
        return url_match.group(1) if url_match else False

    @staticmethod
    def _extract_portal_fields_payload(html):
        payload_match = PORTAL_FIELDS_JSON_RE.search(html or "")
        if not payload_match:
            return []
        return json.loads(payload_match.group(1))

    @staticmethod
    def _expected_consent_hash():
        return hashlib.sha256(
            b'I agree to sign electronically and confirm my intent to sign this document.'
        ).hexdigest()

    @staticmethod
    def _get_text_field_for_signer(signer):
        return signer.request_id.template_id.field_ids.filtered(
            lambda field: field.role_id == signer.role_id and field.type == 'text'
        )[:1]

    @staticmethod
    def _build_submit_payload(*, revision, field_id, value, consent_hash, access_token, idempotency_key):
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

    @staticmethod
    def _build_decline_payload(*, revision, reason, access_token, idempotency_key):
        return {
            'reason': reason,
            'idempotency_key': idempotency_key,
            'request_revision': revision,
            'access_token': access_token,
        }

    def _make_public_get_request(self, path, *, session=None, timeout=12, allow_redirects=False):
        if session is None:
            with self._new_isolated_http_session() as temp_session:
                return self._make_public_get_request(
                    path,
                    session=temp_session,
                    timeout=timeout,
                    allow_redirects=allow_redirects,
                )
        response = session.get(
            urljoin(self.base_url(), path),
            timeout=timeout,
            allow_redirects=allow_redirects,
        )
        response.raise_for_status()
        return response

    def _make_public_jsonrpc_request(self, route, payload, *, session=None, timeout=12):
        if session is None:
            with self._new_isolated_http_session() as temp_session:
                return self._make_public_jsonrpc_request(
                    route,
                    payload,
                    session=temp_session,
                    timeout=timeout,
                )
        response = session.post(
            urljoin(self.base_url(), route),
            json={
                'id': 0,
                'jsonrpc': '2.0',
                'method': 'call',
                'params': payload,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        decoded_response = response.json()
        if 'error' in decoded_response:
            raise AssertionError(f"Unexpected JSON-RPC error payload: {decoded_response['error']}")
        return decoded_response.get('result')

    def _public_jsonrpc_worker(self, route, payload, *, barrier=None, timeout=20):
        with self._new_isolated_http_session() as session:
            if barrier is not None:
                barrier.wait(timeout=timeout)
            return self._make_public_jsonrpc_request(
                route,
                payload,
                session=session,
                timeout=timeout,
            )

    def _open_public_submit_context(self, bundle, *, signer_key='signer', token_key='token', session=None, timeout=12):
        signer = self.env['open.sign.request.signer'].browse(bundle[signer_key].id)
        field = self._get_text_field_for_signer(signer)
        assert field, "Expected a portal-editable text field for submit tests"
        page_response = self._make_public_get_request(
            f"/my/sign/{signer.id}?access_token={bundle[token_key]}",
            session=session,
            timeout=timeout,
            allow_redirects=False,
        )
        consent_hash, revision = self._extract_consent_hash_and_revision(page_response.text)
        return signer, field, consent_hash, revision


class OpenSignPortalControllerTestMixin(OpenSignPortalHttpTestMixin):

    @contextmanager
    def _fresh_test_env(self, *, uid=SUPERUSER_ID, context=None):
        with odoo.sql_db.db_connect(self.registry.db_name).cursor() as cr:
            env = api.Environment(cr, uid, context or {})
            try:
                yield env
            finally:
                env.clear()

    @contextmanager
    def _portal_request_context(self, env, *, path, remote_addr=HOST, user_agent='PortalRaceTest/1.0'):
        with MockRequest(env, path=path, remote_addr=remote_addr) as mocked_request:
            mocked_request.type = 'jsonrpc'
            mocked_request.httprequest.args = {}
            mocked_request.httprequest.cookies = {}
            mocked_request.httprequest.headers = {
                'User-Agent': user_agent,
            }
            yield mocked_request

    def _call_portal_controller(self, controller_cls, *, method_name, signer_id, payload, uid, barrier=None, timeout=20):
        endpoint = method_name.rsplit('_', 1)[-1]
        with self._fresh_test_env(uid=uid) as env:
            controller = controller_cls()
            with self._portal_request_context(env, path=f'/my/sign/{signer_id}/{endpoint}'):
                if barrier is not None:
                    barrier.wait(timeout=timeout)
                try:
                    result = getattr(controller, method_name)(signer_id, **payload)
                    env.cr.commit()
                except Exception:
                    env.cr.rollback()
                    raise
        return result

    def _refresh_bundle_token(self, bundle, *, signer_key='signer', token_key='token'):
        signer_id = self._bundle_signer_id(bundle, signer_key)
        token = self._read_committed(
            lambda env: env['open.sign.request.signer'].sudo().browse(signer_id).access_token
        )
        bundle[token_key] = token
        return token
