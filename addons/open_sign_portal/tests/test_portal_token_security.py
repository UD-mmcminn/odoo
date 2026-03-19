# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from contextlib import contextmanager
import threading
import time
from types import SimpleNamespace

import odoo.sql_db
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
from odoo import api, fields
from odoo.addons.open_sign_portal.controllers.portal_sign import OpenSignPortalController
from odoo.addons.open_sign_portal.services import token_security_service
from odoo.orm.environments import Transaction
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.open_sign_portal.tests.common import OpenSignPortalControllerTestMixin, OpenSignPortalTestMixin


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalTokenSecurity(TransactionCase, OpenSignPortalTestMixin):

    def _read_committed(self, callback):
        with odoo.sql_db.db_connect(self.registry.db_name).cursor() as cr:
            env = api.Environment(cr, self.env.uid, {})
            try:
                return callback(env)
            finally:
                env.clear()

    def _create_committed_portal_session(self, *, name):
        with odoo.sql_db.db_connect(self.registry.db_name).cursor() as cr:
            env = api.Environment(cr, self.env.uid, {})
            try:
                bundle = self._create_portal_session(env, name=name, owner=env.user)
                cr.commit()
                return {
                    'signer_id': bundle['signer'].id,
                    'token': bundle['token'],
                }
            finally:
                env.clear()

    @contextmanager
    def _locked_invalid_token_key(self, signer_id, client_ip):
        with odoo.sql_db.db_connect(self.registry.db_name).cursor() as cr:
            cr.connection.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
            cr.transaction = Transaction(self.registry)
            env = api.Environment(cr, self.env.uid, {})
            try:
                token_security_service._lock_invalid_token_key(env, signer_id, client_ip)
                yield env
            finally:
                cr.rollback()
                env.clear()

    def _get_token_throttle_bucket(self, signer, client_ip=False):
        self.env.invalidate_all(flush=False)
        domain = [('request_signer_id', '=', signer.id)]
        if client_ip:
            domain.append(('client_ip', '=', client_ip))
        return self.env['open.sign.portal.token.throttle'].sudo().search(domain, limit=1)

    def _get_token_throttle_attempts(self, signer, client_ip=False):
        self.env.invalidate_all(flush=False)
        domain = [('request_signer_id', '=', signer.id)]
        if client_ip:
            domain.append(('client_ip', '=', client_ip))
        return self.env['open.sign.portal.token.throttle.attempt'].sudo().search(domain, order='attempted_at asc, id asc')

    def _start_invalid_token_record_thread(self, *, signer_id, client_ip, now, start_event=None):
        outcome = {}

        def runner():
            cr = odoo.sql_db.db_connect(self.registry.db_name).cursor()
            cr.connection.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
            cr.transaction = Transaction(self.registry)
            env = api.Environment(cr, self.env.uid, {})
            try:
                signer = env['open.sign.request.signer'].browse(signer_id)
                if start_event is not None:
                    self.assertTrue(start_event.wait(timeout=20))
                bucket = token_security_service.record_invalid_token_attempt(
                    signer,
                    client_ip,
                    now=now,
                )
                cr.commit()
                outcome['bucket_id'] = bucket.id if bucket else False
            except BaseException as exc:  # pragma: no cover - surfaced by join helper
                cr.rollback()
                outcome['error'] = exc
            finally:
                env.clear()
                cr.close()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        return thread, outcome

    def _join_invalid_token_record_thread(self, thread, outcome, *, timeout=20):
        thread.join(timeout=timeout)
        self.assertFalse(thread.is_alive(), 'Timed out waiting for token throttle worker thread.')
        if 'error' in outcome:
            raise outcome['error']
        return outcome.get('bucket_id')

    def test_classify_current_token_valid(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Valid', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)

        self.assertEqual(signer._classify_current_email_token_access(bundle['token']), 'valid')
        self.assertTrue(signer._is_current_email_token_active())

    def test_classify_current_token_expired(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Expired', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        signer.sudo().write({'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1)})

        self.assertEqual(signer._classify_current_email_token_access(bundle['token']), 'expired')
        self.assertFalse(signer._is_current_email_token_active())

    def test_classify_current_token_revoked(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Revoked', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        signer.sudo()._revoke_email_portal_token()
        signer.invalidate_recordset(['access_token', 'email_token_revoked_at'])

        self.assertEqual(signer._classify_current_email_token_access(signer.access_token), 'revoked')
        self.assertFalse(signer._is_current_email_token_active())

    def test_classify_current_token_missing_metadata_is_invalid(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Missing Metadata', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        signer.sudo().write({
            'email_token_issued_at': False,
            'email_token_expires_at': False,
            'email_token_revoked_at': False,
        })

        self.assertEqual(signer._classify_current_email_token_access(bundle['token']), 'invalid')
        self.assertFalse(signer._is_current_email_token_active())

    def test_invalid_token_throttle_rolling_window_blocks_when_five_attempts_exist_in_last_fifteen_minutes(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Rolling Block', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        client_ip = '203.0.113.8'
        base = fields.Datetime.now()
        offsets = [0, 10 * 60, 14 * 60, 14 * 60 + 30, 15 * 60 + 6, 15 * 60 + 12]

        for offset in offsets:
            token_security_service.record_invalid_token_attempt(
                signer,
                client_ip,
                now=base + timedelta(seconds=offset),
            )

        bucket = self._get_token_throttle_bucket(signer, client_ip)
        attempts = self._get_token_throttle_attempts(signer, client_ip)
        self.assertEqual(len(attempts), 5)
        self.assertEqual(bucket.attempt_count, 5)
        self.assertEqual(fields.Datetime.to_datetime(bucket.first_attempt_at), base + timedelta(minutes=10))
        self.assertEqual(fields.Datetime.to_datetime(bucket.last_attempt_at), base + timedelta(minutes=15, seconds=12))
        self.assertTrue(bucket.blocked_until)
        self.assertTrue(
            token_security_service.is_invalid_token_blocked(
                signer,
                client_ip,
                now=base + timedelta(minutes=15, seconds=12),
            )
        )

    def test_invalid_token_window_stats_ignore_future_attempt_rows(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Future Rows', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        client_ip = '203.0.113.70'
        chosen_now = fields.Datetime.now()
        past_attempt = chosen_now - timedelta(minutes=5)
        future_attempt = chosen_now + timedelta(minutes=1)

        self.env['open.sign.portal.token.throttle.attempt'].sudo().create([
            {
                'request_signer_id': signer.id,
                'client_ip': client_ip,
                'attempted_at': past_attempt,
            },
            {
                'request_signer_id': signer.id,
                'client_ip': client_ip,
                'attempted_at': future_attempt,
            },
        ])

        token_security_service.record_invalid_token_attempt(
            signer,
            client_ip,
            now=chosen_now,
        )

        bucket = self._get_token_throttle_bucket(signer, client_ip)
        attempts = self._get_token_throttle_attempts(signer, client_ip)
        self.assertEqual(bucket.attempt_count, 2)
        self.assertEqual(fields.Datetime.to_datetime(bucket.first_attempt_at), past_attempt)
        self.assertEqual(fields.Datetime.to_datetime(bucket.last_attempt_at), chosen_now)
        self.assertEqual(
            [fields.Datetime.to_datetime(attempt.attempted_at) for attempt in attempts],
            [past_attempt, chosen_now, future_attempt],
        )

    def test_invalid_token_throttle_resets_when_only_one_new_attempt_remains_after_window_prune(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Rolling Reset', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        client_ip = '203.0.113.9'
        base = fields.Datetime.now()

        for minutes in (0, 1, 2):
            token_security_service.record_invalid_token_attempt(
                signer,
                client_ip,
                now=base + timedelta(minutes=minutes),
            )

        token_security_service.record_invalid_token_attempt(
            signer,
            client_ip,
            now=base + timedelta(minutes=20),
        )

        bucket = self._get_token_throttle_bucket(signer, client_ip)
        attempts = self._get_token_throttle_attempts(signer, client_ip)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(bucket.attempt_count, 1)
        self.assertEqual(fields.Datetime.to_datetime(bucket.first_attempt_at), base + timedelta(minutes=20))
        self.assertFalse(bucket.blocked_until)

    def test_record_invalid_token_attempt_prunes_old_rows_but_keeps_newer_window_rows(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Prune Old Rows', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        client_ip = '203.0.113.71'
        chosen_now = fields.Datetime.now()
        stale_attempt = chosen_now - timedelta(minutes=16)
        retained_attempt = chosen_now - timedelta(minutes=4)
        future_attempt = chosen_now + timedelta(minutes=2)

        self.env['open.sign.portal.token.throttle.attempt'].sudo().create([
            {
                'request_signer_id': signer.id,
                'client_ip': client_ip,
                'attempted_at': stale_attempt,
            },
            {
                'request_signer_id': signer.id,
                'client_ip': client_ip,
                'attempted_at': retained_attempt,
            },
            {
                'request_signer_id': signer.id,
                'client_ip': client_ip,
                'attempted_at': future_attempt,
            },
        ])

        token_security_service.record_invalid_token_attempt(
            signer,
            client_ip,
            now=chosen_now,
        )

        bucket = self._get_token_throttle_bucket(signer, client_ip)
        attempts = self._get_token_throttle_attempts(signer, client_ip)
        self.assertEqual(bucket.attempt_count, 2)
        self.assertEqual(fields.Datetime.to_datetime(bucket.first_attempt_at), retained_attempt)
        self.assertEqual(
            [fields.Datetime.to_datetime(attempt.attempted_at) for attempt in attempts],
            [retained_attempt, chosen_now, future_attempt],
        )

    def test_blocked_invalid_attempt_does_not_extend_blocked_until(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Block Preserve', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        client_ip = '203.0.113.10'
        base = fields.Datetime.now()

        for offset in range(5):
            token_security_service.record_invalid_token_attempt(
                signer,
                client_ip,
                now=base + timedelta(minutes=offset),
            )
        original_blocked_until = fields.Datetime.to_datetime(self._get_token_throttle_bucket(signer, client_ip).blocked_until)

        token_security_service.record_invalid_token_attempt(
            signer,
            client_ip,
            now=base + timedelta(minutes=5),
        )

        blocked_bucket = self._get_token_throttle_bucket(signer, client_ip)
        self.assertEqual(fields.Datetime.to_datetime(blocked_bucket.blocked_until), original_blocked_until)
        self.assertEqual(fields.Datetime.to_datetime(blocked_bucket.last_attempt_at), base + timedelta(minutes=5))
        self.assertEqual(blocked_bucket.attempt_count, 5)
        self.assertEqual(len(self._get_token_throttle_attempts(signer, client_ip)), 5)

    def test_clear_invalid_token_attempts_deletes_bucket_and_attempt_rows(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Clear', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        client_ip = '203.0.113.11'
        now = fields.Datetime.now()

        token_security_service.record_invalid_token_attempt(signer, client_ip, now=now)
        deleted_count = token_security_service.clear_invalid_token_attempts(signer, client_ip)

        self.assertEqual(deleted_count, 1)
        self.assertFalse(self._get_token_throttle_bucket(signer, client_ip))
        self.assertFalse(self._get_token_throttle_attempts(signer, client_ip))

    def test_clear_invalid_token_attempts_skips_busy_lock_without_blocking(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Clear Busy Lock', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        client_ip = '203.0.113.72'
        now = fields.Datetime.now()
        self.env['open.sign.portal.token.throttle.attempt'].sudo().create({
            'request_signer_id': signer.id,
            'client_ip': client_ip,
            'attempted_at': now,
        })
        self.env['open.sign.portal.token.throttle'].sudo().create({
            'request_signer_id': signer.id,
            'client_ip': client_ip,
            'attempt_count': 1,
            'first_attempt_at': now,
            'last_attempt_at': now,
            'blocked_until': False,
        })

        with self._locked_invalid_token_key(signer.id, client_ip):
            started_at = time.monotonic()
            deleted_count = token_security_service.clear_invalid_token_attempts(signer, client_ip)
            elapsed = time.monotonic() - started_at

        self.assertEqual(deleted_count, 0)
        self.assertLess(elapsed, 2.0)
        self.assertTrue(self._get_token_throttle_bucket(signer, client_ip))
        self.assertTrue(self._get_token_throttle_attempts(signer, client_ip))

        deleted_after = token_security_service.clear_invalid_token_attempts(signer, client_ip)
        self.assertEqual(deleted_after, 1)
        self.assertFalse(self._get_token_throttle_bucket(signer, client_ip))
        self.assertFalse(self._get_token_throttle_attempts(signer, client_ip))

    def test_invalid_token_throttle_is_isolated_by_signer(self):
        bundle_a = self._create_portal_session(self.env, name='Portal Token Security Signer A', owner=self.env.user)
        bundle_b = self._create_portal_session(self.env, name='Portal Token Security Signer B', owner=self.env.user)
        signer_a = self.env['open.sign.request.signer'].browse(bundle_a['signer'].id)
        signer_b = self.env['open.sign.request.signer'].browse(bundle_b['signer'].id)
        client_ip = '203.0.113.12'
        now = fields.Datetime.now()

        for offset in range(5):
            token_security_service.record_invalid_token_attempt(signer_a, client_ip, now=now + timedelta(minutes=offset))

        self.assertTrue(token_security_service.is_invalid_token_blocked(signer_a, client_ip, now=now + timedelta(minutes=4)))
        self.assertFalse(token_security_service.is_invalid_token_blocked(signer_b, client_ip, now=now + timedelta(minutes=4)))

    def test_invalid_token_throttle_is_isolated_by_ip(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security IP Isolation', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        now = fields.Datetime.now()

        for offset in range(5):
            token_security_service.record_invalid_token_attempt(signer, '203.0.113.13', now=now + timedelta(minutes=offset))

        self.assertTrue(token_security_service.is_invalid_token_blocked(signer, '203.0.113.13', now=now + timedelta(minutes=4)))
        self.assertFalse(token_security_service.is_invalid_token_blocked(signer, '203.0.113.14', now=now + timedelta(minutes=4)))

    def test_valid_token_access_clears_invalid_token_throttle(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Valid Clear', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        client_ip = '203.0.113.15'
        now = fields.Datetime.now()

        token_security_service.record_invalid_token_attempt(signer, client_ip, now=now)
        cleared = token_security_service.clear_invalid_token_attempts(signer, client_ip)

        self.assertEqual(cleared, 1)
        self.assertFalse(token_security_service.is_invalid_token_blocked(signer, client_ip, now=now))

    def test_expired_token_does_not_increment_invalid_token_throttle(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security Expired No Throttle', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        signer.sudo().write({'email_token_expires_at': fields.Datetime.now() - timedelta(minutes=1)})

        self.assertEqual(signer._classify_current_email_token_access(bundle['token']), 'expired')
        self.assertFalse(self._get_token_throttle_bucket(signer, '203.0.113.16'))
        self.assertFalse(self._get_token_throttle_attempts(signer, '203.0.113.16'))

    def test_gc_removes_stale_attempt_rows_and_bucket_rows_after_24h(self):
        bundle = self._create_portal_session(self.env, name='Portal Token Security GC', owner=self.env.user)
        signer = self.env['open.sign.request.signer'].browse(bundle['signer'].id)
        stale_at = fields.Datetime.now() - timedelta(hours=25)
        bucket = self.env['open.sign.portal.token.throttle'].sudo().create({
            'request_signer_id': signer.id,
            'client_ip': '203.0.113.17',
            'attempt_count': 2,
            'first_attempt_at': stale_at,
            'last_attempt_at': stale_at,
            'blocked_until': False,
        })
        attempts = self.env['open.sign.portal.token.throttle.attempt'].sudo().create([
            {
                'request_signer_id': signer.id,
                'client_ip': '203.0.113.17',
                'attempted_at': stale_at,
            },
            {
                'request_signer_id': signer.id,
                'client_ip': '203.0.113.17',
                'attempted_at': stale_at,
            },
        ])

        deleted_bucket_count = token_security_service.cleanup_stale_invalid_token_buckets(self.env)
        deleted_attempt_count = token_security_service.cleanup_stale_invalid_token_attempts(self.env)
        self.assertEqual(deleted_bucket_count, 1)
        self.assertEqual(deleted_attempt_count, 2)
        self.assertFalse(bucket.exists())
        self.assertFalse(attempts.exists())

    def test_invalid_token_throttle_concurrent_first_attempts_do_not_raise_or_undercount(self):
        bundle = self._create_committed_portal_session(name='Portal Token Security Concurrent Pair')
        client_ip = '203.0.113.18'
        start_event = threading.Event()
        now = fields.Datetime.now()

        first_thread, first_outcome = self._start_invalid_token_record_thread(
            signer_id=bundle['signer_id'],
            client_ip=client_ip,
            now=now,
            start_event=start_event,
        )
        second_thread, second_outcome = self._start_invalid_token_record_thread(
            signer_id=bundle['signer_id'],
            client_ip=client_ip,
            now=now,
            start_event=start_event,
        )
        start_event.set()

        self._join_invalid_token_record_thread(first_thread, first_outcome)
        self._join_invalid_token_record_thread(second_thread, second_outcome)

        bucket = self._read_committed(
            lambda env: env['open.sign.portal.token.throttle'].sudo().search_read([
                ('request_signer_id', '=', bundle['signer_id']),
                ('client_ip', '=', client_ip),
            ], ['attempt_count'], limit=1)
        )
        self.assertTrue(bucket)
        self.assertEqual(bucket[0]['attempt_count'], 2)
        attempts = self._read_committed(
            lambda env: env['open.sign.portal.token.throttle.attempt'].sudo().search_count([
                ('request_signer_id', '=', bundle['signer_id']),
                ('client_ip', '=', client_ip),
            ])
        )
        self.assertEqual(attempts, 2)

    def test_invalid_token_throttle_concurrent_burst_reaches_threshold_exactly_once(self):
        bundle = self._create_committed_portal_session(name='Portal Token Security Concurrent Burst')
        client_ip = '203.0.113.19'
        start_event = threading.Event()
        now = fields.Datetime.now()

        thread_outcomes = [
            self._start_invalid_token_record_thread(
                signer_id=bundle['signer_id'],
                client_ip=client_ip,
                now=now,
                start_event=start_event,
            )
            for _index in range(5)
        ]
        start_event.set()

        for thread, outcome in thread_outcomes:
            self._join_invalid_token_record_thread(thread, outcome)

        buckets = self._read_committed(
            lambda env: env['open.sign.portal.token.throttle'].sudo().search_read([
                ('request_signer_id', '=', bundle['signer_id']),
                ('client_ip', '=', client_ip),
            ], ['attempt_count', 'blocked_until'])
        )
        self.assertEqual(len(buckets), 1)
        self.assertEqual(buckets[0]['attempt_count'], 5)
        self.assertTrue(buckets[0]['blocked_until'])
        attempts = self._read_committed(
            lambda env: env['open.sign.portal.token.throttle.attempt'].sudo().search_count([
                ('request_signer_id', '=', bundle['signer_id']),
                ('client_ip', '=', client_ip),
            ])
        )
        self.assertEqual(attempts, 5)


@tagged('post_install', '-at_install', 'open_sign_portal')
class TestOpenSignPortalDocumentThrottleController(TransactionCase, OpenSignPortalControllerTestMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.public_user_id = cls.env.ref('base.public_user').id
        cls.owner_user_id = cls.env.ref('base.user_admin').id

    def _create_committed_portal_bundle(self, *, name):
        with self._fresh_test_env() as env:
            owner = env['res.users'].browse(self.owner_user_id)
            owner.partner_id.email = 'portal.document.throttle.owner@example.com'
            bundle = self._create_portal_session(env, name=name, owner=owner)
            result = {
                'signer_id': bundle['signer'].id,
                'token': bundle['token'],
            }
            env.cr.commit()
        return result

    @contextmanager
    def _fresh_readonly_test_env(self, *, uid):
        with odoo.sql_db.db_connect(self.registry.db_name, readonly=True).cursor() as cr:
            cr.transaction = Transaction(self.registry)
            env = api.Environment(cr, uid, {})
            try:
                yield env
            finally:
                env.clear()

    def _read_committed(self, callback, *, uid=None):
        with self._fresh_test_env(uid=uid or self.owner_user_id) as env:
            return callback(env)

    def _get_token_throttle_bucket(self, signer_id, client_ip):
        records = self._read_committed(
            lambda env: env['open.sign.portal.token.throttle'].sudo().search_read([
                ('request_signer_id', '=', signer_id),
                ('client_ip', '=', client_ip),
            ], ['attempt_count', 'blocked_until'], limit=1)
        )
        return SimpleNamespace(**records[0]) if records else False

    def _get_token_throttle_attempts(self, signer_id, client_ip):
        return self._read_committed(
            lambda env: env['open.sign.portal.token.throttle.attempt'].sudo().search_read([
                ('request_signer_id', '=', signer_id),
                ('client_ip', '=', client_ip),
            ], ['attempted_at', 'client_ip'], order='attempted_at asc, id asc')
        )

    def _seed_document_throttle_state(self, signer_id, client_ip):
        def writer(env):
            now = fields.Datetime.now()
            for offset in range(5):
                env['open.sign.portal.token.throttle.attempt'].sudo().create({
                    'request_signer_id': signer_id,
                    'client_ip': client_ip,
                    'attempted_at': now - timedelta(minutes=offset),
                })
            env['open.sign.portal.token.throttle'].sudo().create({
                'request_signer_id': signer_id,
                'client_ip': client_ip,
                'attempt_count': 5,
                'first_attempt_at': now - timedelta(minutes=4),
                'last_attempt_at': now,
                'blocked_until': now + timedelta(minutes=15),
            })
            env.cr.commit()

        self._read_committed(writer)

    def _call_document(self, signer_id, *, access_token, client_ip):
        with self._fresh_readonly_test_env(uid=self.public_user_id) as env:
            controller = OpenSignPortalController()
            with self._portal_request_context(env, path=f'/my/sign/{signer_id}/document', remote_addr='127.0.0.1') as mocked_request:
                mocked_request.httprequest.args = {'access_token': access_token}
                mocked_request.httprequest.headers['X-Forwarded-For'] = client_ip
                response = controller.portal_sign_document(signer_id, access_token=access_token)
                env.cr.commit()
                return response

    def test_document_invalid_token_attempts_create_and_update_throttle_bucket(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Security Document Throttle')
        wrong_token = self._mutate_token(bundle['token'])
        client_ip = '203.0.113.30'

        for _attempt in range(5):
            response = self._call_document(
                bundle['signer_id'],
                access_token=wrong_token,
                client_ip=client_ip,
            )
            self.assertEqual(response.status_code, 303)

        bucket = self._get_token_throttle_bucket(bundle['signer_id'], client_ip)
        attempts = self._get_token_throttle_attempts(bundle['signer_id'], client_ip)
        self.assertTrue(bucket)
        self.assertEqual(bucket.attempt_count, 5)
        self.assertTrue(bucket.blocked_until)
        self.assertEqual(len(attempts), 5)

    def test_document_valid_token_access_clears_existing_throttle_bucket(self):
        bundle = self._create_committed_portal_bundle(name='Portal Token Security Document Clear')
        client_ip = '127.0.0.1'
        self._seed_document_throttle_state(bundle['signer_id'], client_ip)

        response = self._call_document(
            bundle['signer_id'],
            access_token=bundle['token'],
            client_ip=client_ip,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.headers.get('content-type'))
        self.assertFalse(self._get_token_throttle_bucket(bundle['signer_id'], client_ip))
        self.assertFalse(self._get_token_throttle_attempts(bundle['signer_id'], client_ip))
