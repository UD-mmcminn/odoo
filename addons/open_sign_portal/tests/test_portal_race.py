# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading
from contextlib import contextmanager
from uuid import uuid4
from unittest.mock import patch

import odoo.sql_db
from odoo import api
from odoo.addons.open_sign_portal.controllers.portal_sign import OpenSignPortalController
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.open_sign_portal.tests.common import OpenSignPortalControllerTestMixin


@tagged('post_install', '-at_install', 'open_sign_portal')
class OpenSignPortalRaceCase(TransactionCase, OpenSignPortalControllerTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.public_user_id = cls.env.ref('base.public_user').id
        cls.owner_user_id = cls.env.ref('base.user_admin').id

    def _create_committed_portal_bundle(self, **kwargs):
        with self._fresh_test_env() as env:
            owner = env['res.users'].browse(self.owner_user_id)
            owner.partner_id.email = 'portal.race.owner@example.com'
            bundle = self._create_portal_session(
                env,
                owner=owner,
                **kwargs,
            )
            result = {
                'request_id': bundle['request'].id,
                'signer_id': bundle['signer'].id,
                'token': bundle['token'],
                'signer_email': bundle['signer'].email,
            }
            env.cr.commit()
        return result

    def _create_committed_ordered_bundle(self, **kwargs):
        with self._fresh_test_env() as env:
            owner = env['res.users'].browse(self.owner_user_id)
            owner.partner_id.email = 'portal.race.owner@example.com'
            bundle = self._create_ordered_two_signer_session(
                env,
                owner=owner,
                **kwargs,
            )
            result = {
                'request_id': bundle['request'].id,
                'signer_first_id': bundle['signer_first'].id,
                'signer_second_id': bundle['signer_second'].id,
                'token_first': bundle['token_first'],
                'token_second': bundle['token_second'],
                'signer_first_email': bundle['signer_first'].email,
                'signer_second_email': bundle['signer_second'].email,
            }
            env.cr.commit()
        return result

    def _read_committed(self, callback, *, uid=None):
        with self._fresh_test_env(uid=uid or self.owner_user_id) as env:
            return callback(env)

    def _get_submit_context(self, signer_id):
        def reader(env):
            signer = env['open.sign.request.signer'].sudo().browse(signer_id)
            field = self._get_text_field_for_signer(signer)
            self.assertTrue(field, 'Expected a portal-editable text field for submit tests.')
            return {
                'request_id': signer.request_id.id,
                'signer_id': signer.id,
                'field_id': field.id,
                'request_revision': signer.request_id.lock_version,
                'consent_hash': self._expected_consent_hash(),
            }

        return self._read_committed(reader)

    def _get_decline_context(self, signer_id):
        return self._read_committed(lambda env: {
            'request_id': env['open.sign.request.signer'].sudo().browse(signer_id).request_id.id,
            'request_revision': env['open.sign.request.signer'].sudo().browse(signer_id).request_id.lock_version,
        })

    def _build_submit_payload_for_signer(self, signer_id, *, access_token, idempotency_key, value, request_revision=None):
        context = self._get_submit_context(signer_id)
        return self._build_submit_payload(
            revision=request_revision if request_revision is not None else context['request_revision'],
            field_id=context['field_id'],
            value=value,
            consent_hash=context['consent_hash'],
            access_token=access_token,
            idempotency_key=idempotency_key,
        )

    def _build_decline_payload_for_signer(self, signer_id, *, access_token, idempotency_key, reason, request_revision=None):
        context = self._get_decline_context(signer_id)
        return self._build_decline_payload(
            revision=request_revision if request_revision is not None else context['request_revision'],
            reason=reason,
            access_token=access_token,
            idempotency_key=idempotency_key,
        )

    def _call_submit(self, signer_id, payload):
        return self._call_portal_controller(
            OpenSignPortalController,
            method_name='portal_sign_submit',
            signer_id=signer_id,
            payload=payload,
            uid=self.public_user_id,
        )

    def _call_decline(self, signer_id, payload):
        return self._call_portal_controller(
            OpenSignPortalController,
            method_name='portal_sign_decline',
            signer_id=signer_id,
            payload=payload,
            uid=self.public_user_id,
        )

    def _event_count(self, *, request_id, event_type, signer_id=False):
        def reader(env):
            domain = [
                ('request_id', '=', request_id),
                ('event_type', '=', event_type),
            ]
            if signer_id:
                domain.append(('signer_id', '=', signer_id))
            return env['open.sign.audit.log'].sudo().search_count(domain)

        return self._read_committed(reader)

    def _notification_count(self, *, request_id, signer_id=False, notification_type=False, trigger=False):
        def reader(env):
            domain = [
                ('request_id', '=', request_id),
                ('event_type', '=', 'notification_queued'),
            ]
            if signer_id:
                domain.append(('signer_id', '=', signer_id))
            logs = env['open.sign.audit.log'].sudo().search(domain)
            if notification_type:
                logs = logs.filtered(lambda log: log.metadata_json.get('notification_type') == notification_type)
            if trigger:
                logs = logs.filtered(lambda log: log.metadata_json.get('trigger') == trigger)
            return len(logs)

        return self._read_committed(reader)

    def _idempotency_count(self, *, signer_id, endpoint, idempotency_key, state=False):
        def reader(env):
            domain = [
                ('request_signer_id', '=', signer_id),
                ('endpoint', '=', endpoint),
                ('idempotency_key', '=', idempotency_key),
            ]
            if state:
                domain.append(('state', '=', state))
            return env['open.sign.portal.idempotency'].sudo().search_count(domain)

        return self._read_committed(reader)

    def _signer_snapshot(self, signer_id):
        return self._read_committed(lambda env: {
            'state': env['open.sign.request.signer'].sudo().browse(signer_id).state,
            'request_status': env['open.sign.request.signer'].sudo().browse(signer_id).request_id.status,
            'request_revision': env['open.sign.request.signer'].sudo().browse(signer_id).request_id.lock_version,
        })

    def _assert_error_code(self, response, code):
        self.assertFalse(response['ok'])
        self.assertEqual(response['error_code'], code)

    def _start_controller_thread(self, *, method_name, signer_id, payload, barrier=None):
        outcome = {}
        endpoint = method_name.rsplit('_', 1)[-1]
        cr = odoo.sql_db.db_connect(self.registry.db_name).cursor()
        env = api.Environment(cr, self.public_user_id, {})
        controller = OpenSignPortalController()

        def runner():
            try:
                with self._portal_request_context(env, path=f'/my/sign/{signer_id}/{endpoint}'):
                    if barrier is not None:
                        barrier.wait(timeout=20)
                    outcome['result'] = getattr(controller, method_name)(signer_id, **payload)
                    cr.commit()
            except BaseException as exc:  # pragma: no cover - surfaced by join helper
                cr.rollback()
                outcome['error'] = exc
            finally:
                env.clear()
                cr.close()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        return thread, outcome

    def _join_controller_thread(self, thread, outcome, *, timeout=20):
        thread.join(timeout=timeout)
        self.assertFalse(thread.is_alive(), 'Timed out waiting for concurrent portal controller thread.')
        if 'error' in outcome:
            raise outcome['error']
        return outcome['result']

    def _wait_for_held_event(self, held_event, *thread_outcomes, message):
        if held_event.wait(timeout=20):
            return
        for thread, outcome in thread_outcomes:
            thread.join(timeout=1)
            if 'error' in outcome:
                raise outcome['error']
        alive_count = sum(1 for thread, _outcome in thread_outcomes if thread.is_alive())
        if alive_count:
            self.fail(f'{message} ({alive_count} worker thread(s) still running).')
        self.fail(message)

    @contextmanager
    def _hold_audit_event(self, *, event_type, signer_id):
        held_event = threading.Event()
        release_event = threading.Event()
        original = OpenSignPortalController._append_audit_event

        def wrapped(controller, signer, current_event_type, *, event_at, metadata=None, consent_text_hash=False):
            if current_event_type == event_type and signer.id == signer_id and not held_event.is_set():
                held_event.set()
                if not release_event.wait(timeout=20):
                    raise AssertionError(
                        f'Timed out waiting to release held portal audit event {event_type} for signer {signer_id}.'
                    )
            return original(
                controller,
                signer,
                current_event_type,
                event_at=event_at,
                metadata=metadata,
                consent_text_hash=consent_text_hash,
            )

        with patch.object(OpenSignPortalController, '_append_audit_event', new=wrapped):
            try:
                yield held_event, release_event
            finally:
                release_event.set()


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalRaceDeterministic(OpenSignPortalRaceCase):

    def test_submit_same_key_overlap_returns_request_locked_then_replays_success(self):
        bundle = self._create_committed_ordered_bundle(name='Portal Race Submit Same Key', ordered_signing=True)
        key = str(uuid4())
        payload = self._build_submit_payload_for_signer(
            bundle['signer_first_id'],
            access_token=bundle['token_first'],
            idempotency_key=key,
            value='Race submit same key',
        )

        with self._hold_audit_event(event_type='signer_submitted', signer_id=bundle['signer_first_id']) as (held, release):
            winner_thread, winner_outcome = self._start_controller_thread(
                method_name='portal_sign_submit',
                signer_id=bundle['signer_first_id'],
                payload=dict(payload),
            )
            self._wait_for_held_event(
                held,
                (winner_thread, winner_outcome),
                message='Winner submit never reached the held audit event.',
            )
            locked_response = self._call_submit(bundle['signer_first_id'], dict(payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            winner_response = self._join_controller_thread(winner_thread, winner_outcome)

        self.assertTrue(winner_response['ok'])
        replay_response = self._call_submit(bundle['signer_first_id'], dict(payload))
        self.assertEqual(replay_response, winner_response)
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_first_id'],
            event_type='signer_submitted',
        ), 1)
        self.assertEqual(self._notification_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_second_id'],
            notification_type='invitation',
            trigger='wave_unblocked',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_first_id'],
            endpoint='submit',
            idempotency_key=key,
            state='completed',
        ), 1)

    def test_decline_same_key_overlap_returns_request_locked_then_replays_success(self):
        bundle = self._create_committed_portal_bundle(name='Portal Race Decline Same Key')
        key = str(uuid4())
        payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=key,
            reason='Race decline same key',
        )

        with self._hold_audit_event(event_type='signer_declined', signer_id=bundle['signer_id']) as (held, release):
            winner_thread, winner_outcome = self._start_controller_thread(
                method_name='portal_sign_decline',
                signer_id=bundle['signer_id'],
                payload=dict(payload),
            )
            self._wait_for_held_event(
                held,
                (winner_thread, winner_outcome),
                message='Winner decline never reached the held audit event.',
            )
            locked_response = self._call_decline(bundle['signer_id'], dict(payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            winner_response = self._join_controller_thread(winner_thread, winner_outcome)

        self.assertTrue(winner_response['ok'])
        replay_response = self._call_decline(bundle['signer_id'], dict(payload))
        self.assertEqual(replay_response, winner_response)
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_declined',
        ), 1)
        self.assertEqual(self._notification_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            notification_type='decline',
            trigger='request_declined',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_id'],
            endpoint='decline',
            idempotency_key=key,
            state='completed',
        ), 1)

    def test_submit_same_key_different_payload_overlap_locks_first_then_conflicts_after_commit(self):
        bundle = self._create_committed_portal_bundle(name='Portal Race Submit Conflict')
        key = str(uuid4())
        winner_payload = self._build_submit_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=key,
            value='Winner payload',
        )
        conflict_payload = self._build_submit_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=key,
            value='Conflicting payload',
        )

        with self._hold_audit_event(event_type='signer_submitted', signer_id=bundle['signer_id']) as (held, release):
            winner_thread, winner_outcome = self._start_controller_thread(
                method_name='portal_sign_submit',
                signer_id=bundle['signer_id'],
                payload=dict(winner_payload),
            )
            self._wait_for_held_event(
                held,
                (winner_thread, winner_outcome),
                message='Winner submit never reached the held audit event.',
            )
            locked_response = self._call_submit(bundle['signer_id'], dict(conflict_payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            winner_response = self._join_controller_thread(winner_thread, winner_outcome)

        self.assertTrue(winner_response['ok'])
        conflict_response = self._call_submit(bundle['signer_id'], dict(conflict_payload))
        self._assert_error_code(conflict_response, 'idempotency_conflict')
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_submitted',
        ), 1)
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='idempotency_conflict',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_id'],
            endpoint='submit',
            idempotency_key=key,
            state='completed',
        ), 1)

    def test_decline_same_key_different_reason_overlap_locks_first_then_conflicts_after_commit(self):
        bundle = self._create_committed_portal_bundle(name='Portal Race Decline Conflict')
        key = str(uuid4())
        winner_payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=key,
            reason='Winner reason',
        )
        conflict_payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=key,
            reason='Conflicting reason',
        )

        with self._hold_audit_event(event_type='signer_declined', signer_id=bundle['signer_id']) as (held, release):
            winner_thread, winner_outcome = self._start_controller_thread(
                method_name='portal_sign_decline',
                signer_id=bundle['signer_id'],
                payload=dict(winner_payload),
            )
            self._wait_for_held_event(
                held,
                (winner_thread, winner_outcome),
                message='Winner decline never reached the held audit event.',
            )
            locked_response = self._call_decline(bundle['signer_id'], dict(conflict_payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            winner_response = self._join_controller_thread(winner_thread, winner_outcome)

        self.assertTrue(winner_response['ok'])
        conflict_response = self._call_decline(bundle['signer_id'], dict(conflict_payload))
        self._assert_error_code(conflict_response, 'idempotency_conflict')
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_declined',
        ), 1)
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='idempotency_conflict',
        ), 1)

    def test_submit_different_key_overlap_loser_retries_to_terminal_validation_error(self):
        bundle = self._create_committed_ordered_bundle(name='Portal Race Submit Different Key', ordered_signing=True)
        winner_key = str(uuid4())
        loser_key = str(uuid4())
        winner_payload = self._build_submit_payload_for_signer(
            bundle['signer_first_id'],
            access_token=bundle['token_first'],
            idempotency_key=winner_key,
            value='Winner payload',
        )
        loser_payload = self._build_submit_payload_for_signer(
            bundle['signer_first_id'],
            access_token=bundle['token_first'],
            idempotency_key=loser_key,
            value='Loser payload',
        )

        with self._hold_audit_event(event_type='signer_submitted', signer_id=bundle['signer_first_id']) as (held, release):
            winner_thread, winner_outcome = self._start_controller_thread(
                method_name='portal_sign_submit',
                signer_id=bundle['signer_first_id'],
                payload=dict(winner_payload),
            )
            self._wait_for_held_event(
                held,
                (winner_thread, winner_outcome),
                message='Winner submit never reached the held audit event.',
            )
            locked_response = self._call_submit(bundle['signer_first_id'], dict(loser_payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            winner_response = self._join_controller_thread(winner_thread, winner_outcome)

        self.assertTrue(winner_response['ok'])
        loser_retry_payload = self._build_submit_payload_for_signer(
            bundle['signer_first_id'],
            access_token=bundle['token_first'],
            idempotency_key=loser_key,
            value='Loser payload',
        )
        loser_retry = self._call_submit(bundle['signer_first_id'], loser_retry_payload)
        self._assert_error_code(loser_retry, 'validation_error')
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_first_id'],
            event_type='signer_submitted',
        ), 1)
        self.assertEqual(self._notification_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_second_id'],
            notification_type='invitation',
            trigger='wave_unblocked',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_first_id'],
            endpoint='submit',
            idempotency_key=winner_key,
            state='completed',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_first_id'],
            endpoint='submit',
            idempotency_key=loser_key,
            state='failed',
        ), 1)

    def test_decline_different_key_overlap_loser_retries_to_terminal_validation_error(self):
        bundle = self._create_committed_portal_bundle(name='Portal Race Decline Different Key')
        winner_key = str(uuid4())
        loser_key = str(uuid4())
        winner_payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=winner_key,
            reason='Winner reason',
        )
        loser_payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=loser_key,
            reason='Loser reason',
        )

        with self._hold_audit_event(event_type='signer_declined', signer_id=bundle['signer_id']) as (held, release):
            winner_thread, winner_outcome = self._start_controller_thread(
                method_name='portal_sign_decline',
                signer_id=bundle['signer_id'],
                payload=dict(winner_payload),
            )
            self._wait_for_held_event(
                held,
                (winner_thread, winner_outcome),
                message='Winner decline never reached the held audit event.',
            )
            locked_response = self._call_decline(bundle['signer_id'], dict(loser_payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            winner_response = self._join_controller_thread(winner_thread, winner_outcome)

        self.assertTrue(winner_response['ok'])
        loser_retry_payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=loser_key,
            reason='Loser reason',
        )
        loser_retry = self._call_decline(bundle['signer_id'], loser_retry_payload)
        self._assert_error_code(loser_retry, 'validation_error')
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_declined',
        ), 1)
        self.assertEqual(self._notification_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            notification_type='decline',
            trigger='request_declined',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_id'],
            endpoint='decline',
            idempotency_key=winner_key,
            state='completed',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_id'],
            endpoint='decline',
            idempotency_key=loser_key,
            state='failed',
        ), 1)

    def test_submit_wins_overlapping_decline_then_decline_retry_is_terminal(self):
        bundle = self._create_committed_portal_bundle(name='Portal Race Submit Beats Decline')
        submit_payload = self._build_submit_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=str(uuid4()),
            value='Submit wins',
        )
        decline_payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=str(uuid4()),
            reason='Decline loses',
        )

        with self._hold_audit_event(event_type='signer_submitted', signer_id=bundle['signer_id']) as (held, release):
            winner_thread, winner_outcome = self._start_controller_thread(
                method_name='portal_sign_submit',
                signer_id=bundle['signer_id'],
                payload=dict(submit_payload),
            )
            self._wait_for_held_event(
                held,
                (winner_thread, winner_outcome),
                message='Winner submit never reached the held audit event.',
            )
            locked_response = self._call_decline(bundle['signer_id'], dict(decline_payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            winner_response = self._join_controller_thread(winner_thread, winner_outcome)

        self.assertTrue(winner_response['ok'])
        decline_retry_payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=decline_payload['idempotency_key'],
            reason='Decline loses',
        )
        decline_retry = self._call_decline(bundle['signer_id'], decline_retry_payload)
        self._assert_error_code(decline_retry, 'validation_error')
        snapshot = self._signer_snapshot(bundle['signer_id'])
        self.assertEqual(snapshot['state'], 'signed')
        self.assertEqual(snapshot['request_status'], 'partially_signed')
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_submitted',
        ), 1)
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_declined',
        ), 0)
        self.assertEqual(self._notification_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            notification_type='decline',
            trigger='request_declined',
        ), 0)

    def test_decline_wins_overlapping_submit_then_submit_retry_is_terminal(self):
        bundle = self._create_committed_portal_bundle(name='Portal Race Decline Beats Submit')
        decline_payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=str(uuid4()),
            reason='Decline wins',
        )
        submit_payload = self._build_submit_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=str(uuid4()),
            value='Submit loses',
        )

        with self._hold_audit_event(event_type='signer_declined', signer_id=bundle['signer_id']) as (held, release):
            winner_thread, winner_outcome = self._start_controller_thread(
                method_name='portal_sign_decline',
                signer_id=bundle['signer_id'],
                payload=dict(decline_payload),
            )
            self._wait_for_held_event(
                held,
                (winner_thread, winner_outcome),
                message='Winner decline never reached the held audit event.',
            )
            locked_response = self._call_submit(bundle['signer_id'], dict(submit_payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            winner_response = self._join_controller_thread(winner_thread, winner_outcome)

        self.assertTrue(winner_response['ok'])
        submit_retry_payload = self._build_submit_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=submit_payload['idempotency_key'],
            value='Submit loses',
        )
        submit_retry = self._call_submit(bundle['signer_id'], submit_retry_payload)
        self._assert_error_code(submit_retry, 'validation_error')
        snapshot = self._signer_snapshot(bundle['signer_id'])
        self.assertEqual(snapshot['state'], 'declined')
        self.assertEqual(snapshot['request_status'], 'declined')
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_declined',
        ), 1)
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_submitted',
        ), 0)

    def test_second_signer_submit_during_first_signer_submit_returns_request_locked_then_succeeds_on_retry(self):
        bundle = self._create_committed_ordered_bundle(name='Portal Race Second Signer Submit', ordered_signing=True)
        first_key = str(uuid4())
        second_key = str(uuid4())
        first_payload = self._build_submit_payload_for_signer(
            bundle['signer_first_id'],
            access_token=bundle['token_first'],
            idempotency_key=first_key,
            value='First signer wins',
        )
        second_payload = self._build_submit_payload_for_signer(
            bundle['signer_second_id'],
            access_token=bundle['token_second'],
            idempotency_key=second_key,
            value='Second signer after unlock',
        )

        with self._hold_audit_event(event_type='signer_submitted', signer_id=bundle['signer_first_id']) as (held, release):
            first_thread, first_outcome = self._start_controller_thread(
                method_name='portal_sign_submit',
                signer_id=bundle['signer_first_id'],
                payload=dict(first_payload),
            )
            self._wait_for_held_event(
                held,
                (first_thread, first_outcome),
                message='First signer submit never reached the held audit event.',
            )
            locked_response = self._call_submit(bundle['signer_second_id'], dict(second_payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            first_response = self._join_controller_thread(first_thread, first_outcome)

        self.assertTrue(first_response['ok'])
        current_second_token = self._refresh_bundle_token(
            bundle,
            signer_key='signer_second_id',
            token_key='token_second',
        )
        retry_payload = self._build_submit_payload_for_signer(
            bundle['signer_second_id'],
            access_token=current_second_token,
            idempotency_key=second_key,
            value='Second signer after unlock',
        )
        second_response = self._call_submit(bundle['signer_second_id'], dict(retry_payload))
        self.assertTrue(second_response['ok'])
        second_snapshot = self._signer_snapshot(bundle['signer_second_id'])
        self.assertEqual(second_snapshot['state'], 'signed')
        self.assertEqual(second_snapshot['request_status'], 'partially_signed')
        self.assertEqual(self._notification_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_second_id'],
            notification_type='invitation',
            trigger='wave_unblocked',
        ), 1)

    def test_waiting_signer_decline_during_first_signer_submit_returns_request_locked_then_succeeds_on_retry(self):
        bundle = self._create_committed_ordered_bundle(name='Portal Race Waiting Signer Decline', ordered_signing=True)
        first_payload = self._build_submit_payload_for_signer(
            bundle['signer_first_id'],
            access_token=bundle['token_first'],
            idempotency_key=str(uuid4()),
            value='First signer submit',
        )
        decline_key = str(uuid4())
        second_payload = self._build_decline_payload_for_signer(
            bundle['signer_second_id'],
            access_token=bundle['token_second'],
            idempotency_key=decline_key,
            reason='Waiting signer decline after unlock',
        )

        with self._hold_audit_event(event_type='signer_submitted', signer_id=bundle['signer_first_id']) as (held, release):
            first_thread, first_outcome = self._start_controller_thread(
                method_name='portal_sign_submit',
                signer_id=bundle['signer_first_id'],
                payload=dict(first_payload),
            )
            self._wait_for_held_event(
                held,
                (first_thread, first_outcome),
                message='First signer submit never reached the held audit event.',
            )
            locked_response = self._call_decline(bundle['signer_second_id'], dict(second_payload))
            self._assert_error_code(locked_response, 'request_locked')
            release.set()
            first_response = self._join_controller_thread(first_thread, first_outcome)

        self.assertTrue(first_response['ok'])
        current_second_token = self._refresh_bundle_token(
            bundle,
            signer_key='signer_second_id',
            token_key='token_second',
        )
        retry_payload = self._build_decline_payload_for_signer(
            bundle['signer_second_id'],
            access_token=current_second_token,
            idempotency_key=decline_key,
            reason='Waiting signer decline after unlock',
        )
        decline_response = self._call_decline(bundle['signer_second_id'], dict(retry_payload))
        self.assertTrue(decline_response['ok'])
        second_snapshot = self._signer_snapshot(bundle['signer_second_id'])
        self.assertEqual(second_snapshot['state'], 'declined')
        self.assertEqual(second_snapshot['request_status'], 'declined')
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_second_id'],
            event_type='signer_submitted',
        ), 0)
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_second_id'],
            event_type='signer_declined',
        ), 1)
        self.assertEqual(self._notification_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_second_id'],
            notification_type='decline',
            trigger='request_declined',
        ), 1)


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalRaceSmoke(OpenSignPortalRaceCase):

    def test_real_concurrent_submit_same_key_results_in_one_success_one_request_locked(self):
        bundle = self._create_committed_ordered_bundle(name='Portal Race Smoke Submit', ordered_signing=True)
        key = str(uuid4())
        payload = self._build_submit_payload_for_signer(
            bundle['signer_first_id'],
            access_token=bundle['token_first'],
            idempotency_key=key,
            value='Smoke submit',
        )
        barrier = threading.Barrier(2)

        with self._hold_audit_event(event_type='signer_submitted', signer_id=bundle['signer_first_id']) as (held, release):
            first_thread, first_outcome = self._start_controller_thread(
                method_name='portal_sign_submit',
                signer_id=bundle['signer_first_id'],
                payload=dict(payload),
                barrier=barrier,
            )
            second_thread, second_outcome = self._start_controller_thread(
                method_name='portal_sign_submit',
                signer_id=bundle['signer_first_id'],
                payload=dict(payload),
                barrier=barrier,
            )
            self._wait_for_held_event(
                held,
                (first_thread, first_outcome),
                (second_thread, second_outcome),
                message='Concurrent submit never reached the held audit event.',
            )
            release.set()
            first_response = self._join_controller_thread(first_thread, first_outcome)
            second_response = self._join_controller_thread(second_thread, second_outcome)

        result_codes = sorted('ok' if response['ok'] else response['error_code'] for response in (first_response, second_response))
        self.assertEqual(result_codes, ['ok', 'request_locked'])
        replay_response = self._call_submit(bundle['signer_first_id'], dict(payload))
        self.assertTrue(replay_response['ok'])
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_first_id'],
            event_type='signer_submitted',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_first_id'],
            endpoint='submit',
            idempotency_key=key,
            state='completed',
        ), 1)

    def test_real_concurrent_decline_same_key_results_in_one_success_one_request_locked(self):
        bundle = self._create_committed_portal_bundle(name='Portal Race Smoke Decline')
        key = str(uuid4())
        payload = self._build_decline_payload_for_signer(
            bundle['signer_id'],
            access_token=bundle['token'],
            idempotency_key=key,
            reason='Smoke decline',
        )
        barrier = threading.Barrier(2)

        with self._hold_audit_event(event_type='signer_declined', signer_id=bundle['signer_id']) as (held, release):
            first_thread, first_outcome = self._start_controller_thread(
                method_name='portal_sign_decline',
                signer_id=bundle['signer_id'],
                payload=dict(payload),
                barrier=barrier,
            )
            second_thread, second_outcome = self._start_controller_thread(
                method_name='portal_sign_decline',
                signer_id=bundle['signer_id'],
                payload=dict(payload),
                barrier=barrier,
            )
            self._wait_for_held_event(
                held,
                (first_thread, first_outcome),
                (second_thread, second_outcome),
                message='Concurrent decline never reached the held audit event.',
            )
            release.set()
            first_response = self._join_controller_thread(first_thread, first_outcome)
            second_response = self._join_controller_thread(second_thread, second_outcome)

        result_codes = sorted('ok' if response['ok'] else response['error_code'] for response in (first_response, second_response))
        self.assertEqual(result_codes, ['ok', 'request_locked'])
        replay_response = self._call_decline(bundle['signer_id'], dict(payload))
        self.assertTrue(replay_response['ok'])
        self.assertEqual(self._event_count(
            request_id=bundle['request_id'],
            signer_id=bundle['signer_id'],
            event_type='signer_declined',
        ), 1)
        self.assertEqual(self._idempotency_count(
            signer_id=bundle['signer_id'],
            endpoint='decline',
            idempotency_key=key,
            state='completed',
        ), 1)
