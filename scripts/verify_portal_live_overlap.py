#!/usr/bin/env python3

from __future__ import annotations

import argparse
import contextlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests

from odoo import api
from odoo.orm.registry import Registry
from odoo.orm.utils import SUPERUSER_ID
from odoo.tools import config as odoo_config


REQUEST_TIMEOUT_SECONDS = 20
SERVER_READY_TIMEOUT_SECONDS = 60
HOLD_WAIT_TIMEOUT_SECONDS = 20


_PORTAL_HELPER_CLASS = None


def _portal_helper():
    global _PORTAL_HELPER_CLASS
    if _PORTAL_HELPER_CLASS is None:
        from odoo.addons.open_sign_portal.tests.common import OpenSignPortalHttpTestMixin

        class _PortalHarnessHelper(OpenSignPortalHttpTestMixin):
            """Thin wrapper for reusing portal test helpers from a standalone harness."""

        _PORTAL_HELPER_CLASS = _PortalHarnessHelper
    return _PORTAL_HELPER_CLASS


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Verify live overlapping public HTTP portal submit/decline behavior.",
    )
    parser.add_argument('--db', required=True)
    parser.add_argument('--config', default=os.fspath(ROOT_DIR / '.devcontainer' / 'odoo.conf'))
    parser.add_argument('--db-host', required=True)
    parser.add_argument('--db-port', required=True, type=int)
    parser.add_argument('--db-user', required=True)
    parser.add_argument('--db-password', required=True)
    parser.add_argument('--http-port', default=8088, type=int)
    parser.add_argument('--case', choices=('submit', 'decline', 'all'), default='all')
    parser.add_argument('--log-file')
    return parser.parse_args()


def _configure_odoo(args):
    odoo_config.parse_config([
        '-c', os.fspath(Path(args.config).resolve()),
        '-d', args.db,
        '--db_host', args.db_host,
        '--db_port', str(args.db_port),
        '--db_user', args.db_user,
        '--db_password', args.db_password,
    ])


@contextlib.contextmanager
def _env(db_name, *, uid=SUPERUSER_ID, context=None):
    with Registry(db_name).cursor() as cr:
        env = api.Environment(cr, uid, context or {})
        try:
            yield env
        finally:
            env.clear()


def _run_subprocess(command, *, log_file=None):
    kwargs = {
        'cwd': os.fspath(ROOT_DIR),
        'check': True,
    }
    if log_file:
        with open(log_file, 'a', encoding='utf-8') as handle:
            kwargs['stdout'] = handle
            kwargs['stderr'] = subprocess.STDOUT
            subprocess.run(command, **kwargs)
        return
    subprocess.run(command, **kwargs)


def _make_jsonrpc_payload(params):
    return {
        'id': 0,
        'jsonrpc': '2.0',
        'method': 'call',
        'params': params,
    }


def _base_url(args):
    return f'http://127.0.0.1:{args.http_port}'


def _upgrade_modules(args, *, log_file=None):
    install_mode = not _modules_installed(args.db)
    command = [
        os.fspath(ROOT_DIR / 'odoo-bin'),
        '-c', os.fspath(Path(args.config).resolve()),
        '-d', args.db,
        '--db_host', args.db_host,
        '--db_port', str(args.db_port),
        '--db_user', args.db_user,
        '--db_password', args.db_password,
        '--http-port', str(args.http_port),
        '-i' if install_mode else '-u',
        'open_sign,open_sign_web,open_sign_portal',
        '--stop-after-init',
    ]
    _run_subprocess(command, log_file=log_file)


def _start_jsonrpc_request_thread(base_url, route, payload):
    outcome = {}
    session = requests.Session()

    def runner():
        try:
            response = session.post(
                f'{base_url}{route}',
                json=_make_jsonrpc_payload(payload),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
            if 'error' in body:
                raise AssertionError(f'Unexpected JSON-RPC error payload: {body["error"]}')
            outcome['result'] = body.get('result')
        except BaseException as exc:  # pragma: no cover - surfaced by join helper
            outcome['error'] = exc
        finally:
            session.close()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return thread, outcome


def _join_request_thread(thread, outcome, *, timeout=REQUEST_TIMEOUT_SECONDS + 10):
    thread.join(timeout=timeout)
    if thread.is_alive():
        raise AssertionError('Timed out waiting for live HTTP request thread.')
    if 'error' in outcome:
        raise outcome['error']
    return outcome['result']


def _call_jsonrpc(base_url, route, payload):
    response = requests.post(
        f'{base_url}{route}',
        json=_make_jsonrpc_payload(payload),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    body = response.json()
    if 'error' in body:
        raise AssertionError(f'Unexpected JSON-RPC error payload: {body["error"]}')
    return body.get('result')


def _tail_log(log_file, *, lines=80):
    path = Path(log_file)
    if not path.exists():
        return '<log file missing>'
    content = path.read_text(encoding='utf-8', errors='replace').splitlines()
    return '\n'.join(content[-lines:])


def _wait_for_server_ready(base_url, process, log_file):
    deadline = time.monotonic() + SERVER_READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f'Live overlap server exited early with code {process.returncode}.\n'
                f'Log tail:\n{_tail_log(log_file)}'
            )
        try:
            response = requests.get(f'{base_url}/web/health', timeout=1)
            if response.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise RuntimeError(
        f'Timed out waiting for live overlap server at {base_url}.\n'
        f'Log tail:\n{_tail_log(log_file)}'
    )


@contextlib.contextmanager
def _live_server(args, *, hold_event_type, hold_signer_id, log_file):
    with tempfile.TemporaryDirectory(prefix='portal_live_overlap_') as temp_dir:
        hold_started_file = Path(temp_dir) / 'hold_started'
        release_file = Path(temp_dir) / 'release'
        command = [
            sys.executable,
            os.fspath(ROOT_DIR / 'scripts' / 'run_portal_live_overlap_server.py'),
            '--hold-event-type', hold_event_type,
            '--hold-signer-id', str(hold_signer_id),
            '--hold-start-file', os.fspath(hold_started_file),
            '--hold-release-file', os.fspath(release_file),
            '--',
            '-c', os.fspath(Path(args.config).resolve()),
            '-d', args.db,
            '--db_host', args.db_host,
            '--db_port', str(args.db_port),
            '--db_user', args.db_user,
            '--db_password', args.db_password,
            '--http-interface', '127.0.0.1',
            '--http-port', str(args.http_port),
            '--db-filter', f'^{args.db}$',
            '--max-cron-threads', '0',
        ]
        with open(log_file, 'a', encoding='utf-8') as handle:
            process = subprocess.Popen(
                command,
                cwd=os.fspath(ROOT_DIR),
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
        try:
            _wait_for_server_ready(_base_url(args), process, log_file)
            yield hold_started_file, release_file
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def _wait_for_path(path, *, timeout, failure_message, thread_outcomes=()):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        for thread, outcome in thread_outcomes:
            if not thread.is_alive() and 'error' in outcome:
                raise outcome['error']
        time.sleep(0.05)
    raise AssertionError(failure_message)


def _set_base_url_parameter(db_name, base_url):
    with _env(db_name) as env:
        env['ir.config_parameter'].sudo().set_param('web.base.url', base_url)
        env.cr.commit()


def _modules_installed(db_name):
    with _env(db_name) as env:
        installed = env['ir.module.module'].sudo().search_count([
            ('name', 'in', ['open_sign', 'open_sign_web', 'open_sign_portal']),
            ('state', '=', 'installed'),
        ])
        return installed == 3


def _create_committed_ordered_bundle(db_name, *, name, base_url):
    helper = _portal_helper()
    _set_base_url_parameter(db_name, base_url)
    with _env(db_name) as env:
        owner = env.ref('base.user_admin')
        owner.partner_id.email = 'portal.live.overlap.owner@example.com'
        bundle = helper._create_ordered_two_signer_session(
            env,
            name=name,
            owner=owner,
            ordered_signing=True,
        )
        serialized = {
            'request': bundle['request'].id,
            'signer_first': bundle['signer_first'].id,
            'signer_second': bundle['signer_second'].id,
            'field_first': bundle['field_first'].id,
            'field_second': bundle['field_second'].id,
            'token_first': bundle['token_first'],
            'token_second': bundle['token_second'],
        }
        env.cr.commit()
        return serialized


def _create_committed_portal_bundle(db_name, *, name, base_url):
    helper = _portal_helper()
    _set_base_url_parameter(db_name, base_url)
    with _env(db_name) as env:
        owner = env.ref('base.user_admin')
        owner.partner_id.email = 'portal.live.overlap.owner@example.com'
        bundle = helper._create_portal_session(
            env,
            name=name,
            owner=owner,
        )
        serialized = helper._serialize_portal_bundle(bundle)
        env.cr.commit()
        return serialized


def _build_submit_case_data(db_name, *, base_url):
    helper = _portal_helper()
    bundle = _create_committed_ordered_bundle(
        db_name,
        name=f'Portal Live Overlap Submit {uuid4().hex[:8]}',
        base_url=base_url,
    )
    with _env(db_name) as env:
        signer = env['open.sign.request.signer'].sudo().browse(bundle['signer_first'])
        field = helper._get_text_field_for_signer(signer)
        if not field:
            raise AssertionError('Expected a text field for the first signer in the live submit case.')
        initial_revision = signer.request_id.lock_version
        payload = helper._build_submit_payload(
            revision=initial_revision,
            field_id=field.id,
            value='Live overlap submit',
            consent_hash=helper._expected_consent_hash(),
            access_token=bundle['token_first'],
            idempotency_key=str(uuid4()),
        )
        return {
            'request_id': signer.request_id.id,
            'signer_id': signer.id,
            'initial_revision': initial_revision,
            'payload': payload,
            'route': f'/my/sign/{signer.id}/submit',
        }


def _build_decline_case_data(db_name, *, base_url):
    helper = _portal_helper()
    bundle = _create_committed_portal_bundle(
        db_name,
        name=f'Portal Live Overlap Decline {uuid4().hex[:8]}',
        base_url=base_url,
    )
    with _env(db_name) as env:
        signer = env['open.sign.request.signer'].sudo().browse(bundle['signer'])
        initial_revision = signer.request_id.lock_version
        payload = helper._build_decline_payload(
            revision=initial_revision,
            reason='Live overlap decline',
            access_token=bundle['token'],
            idempotency_key=str(uuid4()),
        )
        return {
            'request_id': signer.request_id.id,
            'signer_id': signer.id,
            'initial_revision': initial_revision,
            'payload': payload,
            'route': f'/my/sign/{signer.id}/decline',
        }


def _get_event_count(db_name, *, request_id, signer_id, event_type):
    with _env(db_name) as env:
        return env['open.sign.audit.log'].sudo().search_count([
            ('request_id', '=', request_id),
            ('signer_id', '=', signer_id),
            ('event_type', '=', event_type),
        ])


def _get_idempotency_count(db_name, *, signer_id, endpoint, idempotency_key, state):
    with _env(db_name) as env:
        return env['open.sign.portal.idempotency'].sudo().search_count([
            ('request_signer_id', '=', signer_id),
            ('endpoint', '=', endpoint),
            ('idempotency_key', '=', idempotency_key),
            ('state', '=', state),
        ])


def _get_signer_snapshot(db_name, *, signer_id):
    with _env(db_name) as env:
        signer = env['open.sign.request.signer'].sudo().browse(signer_id)
        return {
            'signer_state': signer.state,
            'request_status': signer.request_id.status,
            'request_revision': signer.request_id.lock_version,
        }


def _assert_ok(result):
    if not result or not result.get('ok'):
        raise AssertionError(f'Expected success JSON-RPC result, got: {result}')


def _assert_error_code(result, code):
    if not result or result.get('ok') is not False or result.get('error_code') != code:
        raise AssertionError(f'Expected error_code={code}, got: {result}')


def _run_submit_case(args, *, log_file):
    base_url = _base_url(args)
    case = _build_submit_case_data(args.db, base_url=base_url)
    payload = dict(case['payload'])
    idempotency_key = payload['idempotency_key']

    with _live_server(
        args,
        hold_event_type='signer_submitted',
        hold_signer_id=case['signer_id'],
        log_file=log_file,
    ) as (hold_started_file, release_file):
        first_thread, first_outcome = _start_jsonrpc_request_thread(base_url, case['route'], dict(payload))
        _wait_for_path(
            hold_started_file,
            timeout=HOLD_WAIT_TIMEOUT_SECONDS,
            failure_message='Submit case never reached the held signer_submitted audit event.',
            thread_outcomes=((first_thread, first_outcome),),
        )
        locked_result = _call_jsonrpc(base_url, case['route'], dict(payload))
        _assert_error_code(locked_result, 'request_locked')
        release_file.write_text('release\n', encoding='utf-8')
        first_result = _join_request_thread(first_thread, first_outcome)
        replay_result = _call_jsonrpc(base_url, case['route'], dict(payload))

    _assert_ok(first_result)
    _assert_ok(replay_result)
    if replay_result != first_result:
        raise AssertionError(
            f'Submit replay did not return the stored success response.\n'
            f'first={first_result}\nreplay={replay_result}'
        )

    snapshot = _get_signer_snapshot(args.db, signer_id=case['signer_id'])
    if snapshot['signer_state'] != 'signed':
        raise AssertionError(f'Expected signed signer state after live submit overlap, got {snapshot}')
    if snapshot['request_status'] != 'partially_signed':
        raise AssertionError(f'Expected partially_signed request status after live submit overlap, got {snapshot}')
    if snapshot['request_revision'] != case['initial_revision'] + 1:
        raise AssertionError(
            'Expected exactly one request revision increment for live submit overlap. '
            f'initial={case["initial_revision"]} final={snapshot["request_revision"]}'
        )
    if _get_event_count(args.db, request_id=case['request_id'], signer_id=case['signer_id'], event_type='signer_submitted') != 1:
        raise AssertionError('Expected exactly one signer_submitted audit row after live submit overlap.')
    if _get_event_count(args.db, request_id=case['request_id'], signer_id=case['signer_id'], event_type='signer_declined') != 0:
        raise AssertionError('Unexpected signer_declined audit row after live submit overlap.')
    if _get_idempotency_count(
        args.db,
        signer_id=case['signer_id'],
        endpoint='submit',
        idempotency_key=idempotency_key,
        state='completed',
    ) != 1:
        raise AssertionError('Expected exactly one completed submit idempotency row after live overlap.')


def _run_decline_case(args, *, log_file):
    base_url = _base_url(args)
    case = _build_decline_case_data(args.db, base_url=base_url)
    payload = dict(case['payload'])
    idempotency_key = payload['idempotency_key']

    with _live_server(
        args,
        hold_event_type='signer_declined',
        hold_signer_id=case['signer_id'],
        log_file=log_file,
    ) as (hold_started_file, release_file):
        first_thread, first_outcome = _start_jsonrpc_request_thread(base_url, case['route'], dict(payload))
        _wait_for_path(
            hold_started_file,
            timeout=HOLD_WAIT_TIMEOUT_SECONDS,
            failure_message='Decline case never reached the held signer_declined audit event.',
            thread_outcomes=((first_thread, first_outcome),),
        )
        locked_result = _call_jsonrpc(base_url, case['route'], dict(payload))
        _assert_error_code(locked_result, 'request_locked')
        release_file.write_text('release\n', encoding='utf-8')
        first_result = _join_request_thread(first_thread, first_outcome)
        replay_result = _call_jsonrpc(base_url, case['route'], dict(payload))

    _assert_ok(first_result)
    _assert_ok(replay_result)
    if replay_result != first_result:
        raise AssertionError(
            f'Decline replay did not return the stored success response.\n'
            f'first={first_result}\nreplay={replay_result}'
        )

    snapshot = _get_signer_snapshot(args.db, signer_id=case['signer_id'])
    if snapshot['signer_state'] != 'declined':
        raise AssertionError(f'Expected declined signer state after live decline overlap, got {snapshot}')
    if snapshot['request_status'] != 'declined':
        raise AssertionError(f'Expected declined request status after live decline overlap, got {snapshot}')
    if snapshot['request_revision'] != case['initial_revision'] + 1:
        raise AssertionError(
            'Expected exactly one request revision increment for live decline overlap. '
            f'initial={case["initial_revision"]} final={snapshot["request_revision"]}'
        )
    if _get_event_count(args.db, request_id=case['request_id'], signer_id=case['signer_id'], event_type='signer_declined') != 1:
        raise AssertionError('Expected exactly one signer_declined audit row after live decline overlap.')
    if _get_event_count(args.db, request_id=case['request_id'], signer_id=case['signer_id'], event_type='signer_submitted') != 0:
        raise AssertionError('Unexpected signer_submitted audit row after live decline overlap.')
    if _get_idempotency_count(
        args.db,
        signer_id=case['signer_id'],
        endpoint='decline',
        idempotency_key=idempotency_key,
        state='completed',
    ) != 1:
        raise AssertionError('Expected exactly one completed decline idempotency row after live overlap.')


def main():
    args = _parse_args()
    _configure_odoo(args)

    log_file = args.log_file
    if not log_file:
        fd, log_file = tempfile.mkstemp(prefix='portal_live_overlap_', suffix='.log')
        os.close(fd)
    log_file = os.fspath(Path(log_file).resolve())

    cases = ('submit', 'decline') if args.case == 'all' else (args.case,)

    print(f'[live-overlap] using db={args.db} http_port={args.http_port} log={log_file}')
    _upgrade_modules(args, log_file=log_file)

    for case in cases:
        print(f'[live-overlap] running case={case}')
        if case == 'submit':
            _run_submit_case(args, log_file=log_file)
        elif case == 'decline':
            _run_decline_case(args, log_file=log_file)
        else:  # pragma: no cover - argparse constrains values
            raise AssertionError(f'Unsupported case: {case}')
        print(f'[live-overlap] case={case} passed')

    print('[live-overlap] all requested cases passed')


if __name__ == '__main__':
    main()
