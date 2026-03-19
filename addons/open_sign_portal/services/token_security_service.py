# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import hashlib

import odoo.sql_db
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import ValidationError
from odoo.orm.environments import Transaction


INVALID_TOKEN_ATTEMPT_THRESHOLD = 5
INVALID_TOKEN_ATTEMPT_WINDOW_MINUTES = 15
INVALID_TOKEN_BLOCK_MINUTES = 15
INVALID_TOKEN_BUCKET_RETENTION_HOURS = 24


def _bucket_model(env):
    return env['open.sign.portal.token.throttle'].sudo()


def _attempt_model(env):
    return env['open.sign.portal.token.throttle.attempt'].sudo()


def _normalize_now(now=None):
    return fields.Datetime.to_datetime(now or fields.Datetime.now())


def _window_start(now):
    return now - timedelta(minutes=INVALID_TOKEN_ATTEMPT_WINDOW_MINUTES)


def _block_deadline(now):
    return now + timedelta(minutes=INVALID_TOKEN_BLOCK_MINUTES)


def _cleanup_deadline(now):
    return now - timedelta(hours=INVALID_TOKEN_BUCKET_RETENTION_HOURS)


def _get_signer_company_id(env, signer_id):
    return env['open.sign.request.signer'].sudo().browse(signer_id).company_id.id or None


def _lock_ip_hash(client_ip):
    digest = hashlib.blake2s(client_ip.encode('utf-8'), digest_size=4).digest()
    return int.from_bytes(digest, 'big', signed=True)


def _lock_invalid_token_key(env, signer_id, client_ip):
    env.cr.execute(
        "SELECT pg_advisory_xact_lock(%s, %s)",
        [int(signer_id) & 0x7FFFFFFF, _lock_ip_hash(client_ip)],
    )


def _try_lock_invalid_token_key(env, signer_id, client_ip):
    env.cr.execute(
        "SELECT pg_try_advisory_xact_lock(%s, %s)",
        [int(signer_id) & 0x7FFFFFFF, _lock_ip_hash(client_ip)],
    )
    return bool(env.cr.fetchone()[0])


def _run_in_writable_throttle_env(env, callback, *, force_new_cursor=False):
    if not force_new_cursor and not env.cr.readonly:
        return callback(env)
    cr = odoo.sql_db.db_connect(env.registry.db_name).cursor()
    cr.connection.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
    cr.transaction = Transaction(env.registry)
    writable_env = api.Environment(cr, SUPERUSER_ID, dict(env.context))
    try:
        result = callback(writable_env)
        cr.commit()
        return result
    except Exception:
        cr.rollback()
        raise
    finally:
        writable_env.clear()
        cr.close()


def _get_bucket(env, signer_id, client_ip):
    return _bucket_model(env).search([
        ('request_signer_id', '=', signer_id),
        ('client_ip', '=', client_ip),
    ], limit=1)


def _get_attempts(env, signer_id, client_ip, *, window_start=False):
    domain = [
        ('request_signer_id', '=', signer_id),
        ('client_ip', '=', client_ip),
    ]
    if window_start:
        domain.append(('attempted_at', '>=', window_start))
    return _attempt_model(env).search(domain, order='attempted_at asc, id asc')


def _window_attempt_stats(env, signer_id, client_ip, *, now):
    env.cr.execute(
        f"""
        SELECT COUNT(*), MIN(attempted_at)
          FROM {_attempt_model(env)._table}
         WHERE request_signer_id = %s
           AND client_ip = %s
           AND attempted_at >= %s
           AND attempted_at <= %s
        """,
        [signer_id, client_ip, _window_start(now), now],
    )
    count, oldest_attempt = env.cr.fetchone()
    return count, oldest_attempt


def _insert_attempt(env, signer_id, client_ip, *, now):
    env.cr.execute(
        f"""
        INSERT INTO {_attempt_model(env)._table} (
            attempted_at,
            client_ip,
            company_id,
            create_date,
            create_uid,
            request_signer_id,
            write_date,
            write_uid
        )
        VALUES (%s, %s, %s, NOW(), %s, %s, NOW(), %s)
        """,
        [
            now,
            client_ip,
            _get_signer_company_id(env, signer_id),
            env.uid,
            signer_id,
            env.uid,
        ],
    )
    env.invalidate_all(flush=False)


def _prune_window_attempts(env, signer_id, client_ip, *, now):
    env.cr.execute(
        f"""
        DELETE FROM {_attempt_model(env)._table}
         WHERE request_signer_id = %s
           AND client_ip = %s
           AND attempted_at < %s
        """,
        [signer_id, client_ip, _window_start(now)],
    )
    env.invalidate_all(flush=False)


def _delete_attempts(env, signer_id, client_ip):
    env.cr.execute(
        f"""
        DELETE FROM {_attempt_model(env)._table}
         WHERE request_signer_id = %s
           AND client_ip = %s
        RETURNING id
        """,
        [signer_id, client_ip],
    )
    deleted_ids = env.cr.fetchall()
    env.invalidate_all(flush=False)
    return len(deleted_ids)


def _delete_bucket(env, signer_id, client_ip):
    env.cr.execute(
        f"""
        DELETE FROM {_bucket_model(env)._table}
         WHERE request_signer_id = %s
           AND client_ip = %s
        RETURNING id
        """,
        [signer_id, client_ip],
    )
    deleted_ids = env.cr.fetchall()
    env.invalidate_all(flush=False)
    return len(deleted_ids)


def _has_throttle_state(env, signer_id, client_ip):
    env.cr.execute(
        f"""
        SELECT EXISTS(
            SELECT 1
              FROM {_bucket_model(env)._table}
             WHERE request_signer_id = %s
               AND client_ip = %s
        )
        OR EXISTS(
            SELECT 1
              FROM {_attempt_model(env)._table}
             WHERE request_signer_id = %s
               AND client_ip = %s
        )
        """,
        [signer_id, client_ip, signer_id, client_ip],
    )
    return bool(env.cr.fetchone()[0])


def _touch_blocked_bucket(env, signer_id, client_ip, *, now):
    env.cr.execute(
        f"""
        UPDATE {_bucket_model(env)._table}
           SET last_attempt_at = GREATEST(last_attempt_at, %s),
               write_date = NOW(),
               write_uid = %s
         WHERE request_signer_id = %s
           AND client_ip = %s
        RETURNING id
        """,
        [now, env.uid, signer_id, client_ip],
    )
    row = env.cr.fetchone()
    env.invalidate_all(flush=False)
    return _bucket_model(env).browse(row[0]) if row else False


def _upsert_bucket(env, signer_id, client_ip, values):
    bucket_model = _bucket_model(env)
    env.cr.execute(
        f"""
        INSERT INTO {bucket_model._table} (
            attempt_count,
            blocked_until,
            client_ip,
            company_id,
            create_date,
            create_uid,
            first_attempt_at,
            last_attempt_at,
            request_signer_id,
            write_date,
            write_uid
        )
        VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s, NOW(), %s)
        ON CONFLICT (request_signer_id, client_ip) DO UPDATE
               SET attempt_count = EXCLUDED.attempt_count,
                   blocked_until = EXCLUDED.blocked_until,
                   company_id = EXCLUDED.company_id,
                   first_attempt_at = EXCLUDED.first_attempt_at,
                   last_attempt_at = EXCLUDED.last_attempt_at,
                   write_date = EXCLUDED.write_date,
                   write_uid = EXCLUDED.write_uid
        RETURNING id
        """,
        [
            values['attempt_count'],
            values.get('blocked_until') or None,
            client_ip,
            _get_signer_company_id(env, signer_id),
            env.uid,
            values['first_attempt_at'],
            values['last_attempt_at'],
            signer_id,
            env.uid,
        ],
    )
    bucket_id = env.cr.fetchone()[0]
    env.invalidate_all(flush=False)
    return bucket_model.browse(bucket_id)


def _recompute_bucket_locked(env, signer_id, client_ip, *, now):
    attempt_count, oldest_attempt = _window_attempt_stats(env, signer_id, client_ip, now=now)
    if not attempt_count:
        _delete_bucket(env, signer_id, client_ip)
        return False
    values = {
        'attempt_count': attempt_count,
        'first_attempt_at': oldest_attempt,
        'last_attempt_at': now,
        'blocked_until': _block_deadline(now) if attempt_count >= INVALID_TOKEN_ATTEMPT_THRESHOLD else False,
    }
    return _upsert_bucket(env, signer_id, client_ip, values)


def _record_invalid_token_attempt_in_env(env, signer_id, client_ip, *, now):
    _lock_invalid_token_key(env, signer_id, client_ip)
    effective_now = _normalize_now(now)
    bucket = _get_bucket(env, signer_id, client_ip)
    if bucket and bucket.blocked_until and fields.Datetime.to_datetime(bucket.blocked_until) > effective_now:
        return _touch_blocked_bucket(env, signer_id, client_ip, now=effective_now)
    _insert_attempt(env, signer_id, client_ip, now=effective_now)
    _prune_window_attempts(env, signer_id, client_ip, now=effective_now)
    return _recompute_bucket_locked(env, signer_id, client_ip, now=effective_now)


def _clear_invalid_token_attempts_in_env(env, signer_id, client_ip):
    if not _has_throttle_state(env, signer_id, client_ip):
        return 0
    # Clearing throttle state is best-effort and must not delay the primary
    # request path. If another request currently owns the key, leave cleanup
    # for that transaction or a later valid access.
    if not _try_lock_invalid_token_key(env, signer_id, client_ip):
        return 0
    _delete_attempts(env, signer_id, client_ip)
    return _delete_bucket(env, signer_id, client_ip)


def normalize_client_ip(env, ip_value):
    signer_model = env['open.sign.request.signer']
    try:
        return signer_model._sanitize_ip_last(ip_value)
    except ValidationError:
        return False


def get_or_create_invalid_token_bucket(signer, client_ip, *, now=None):
    signer.ensure_one()
    if not client_ip:
        return False

    def _callback(writable_env):
        signer_id = writable_env['open.sign.request.signer'].sudo().browse(signer.id).exists().id
        if not signer_id:
            return False
        _lock_invalid_token_key(writable_env, signer_id, client_ip)
        bucket = _get_bucket(writable_env, signer_id, client_ip)
        if bucket:
            return bucket
        normalized_now = _normalize_now(now)
        return _upsert_bucket(
            writable_env,
            signer_id,
            client_ip,
            {
                'attempt_count': 0,
                'first_attempt_at': normalized_now,
                'last_attempt_at': normalized_now,
                'blocked_until': False,
            },
        )

    return _run_in_writable_throttle_env(signer.env, _callback)


def is_invalid_token_blocked(signer, client_ip, *, now=None):
    signer.ensure_one()
    if not client_ip:
        return False
    signer.env.invalidate_all(flush=False)
    bucket = _bucket_model(signer.env).search([
        ('request_signer_id', '=', signer.id),
        ('client_ip', '=', client_ip),
    ], limit=1)
    if not bucket or not bucket.blocked_until:
        return False
    normalized_now = _normalize_now(now)
    return fields.Datetime.to_datetime(bucket.blocked_until) > normalized_now


def record_invalid_token_attempt(signer, client_ip, *, now=None, force_isolated=False):
    signer.ensure_one()
    if not client_ip:
        return False

    def _callback(writable_env):
        signer_id = writable_env['open.sign.request.signer'].sudo().browse(signer.id).exists().id
        if not signer_id:
            return False
        return _record_invalid_token_attempt_in_env(
            writable_env,
            signer_id,
            client_ip,
            now=now,
        )

    return _run_in_writable_throttle_env(
        signer.env,
        _callback,
        force_new_cursor=force_isolated or signer.env.cr.readonly,
    )


def clear_invalid_token_attempts(signer, client_ip, *, now=None, force_isolated=False):
    del now
    signer.ensure_one()
    if not client_ip:
        return 0

    def _callback(writable_env):
        signer_id = writable_env['open.sign.request.signer'].sudo().browse(signer.id).exists().id
        if not signer_id:
            return 0
        return _clear_invalid_token_attempts_in_env(writable_env, signer_id, client_ip)

    return _run_in_writable_throttle_env(
        signer.env,
        _callback,
        force_new_cursor=force_isolated or signer.env.cr.readonly,
    )


def cleanup_stale_invalid_token_buckets(env, limit=None):
    deadline = _cleanup_deadline(_normalize_now())
    limit_clause = "LIMIT %s" if limit else ""
    params = [deadline]
    if limit:
        params.append(limit)
    env.cr.execute(
        f"""
        DELETE FROM {_bucket_model(env)._table}
         WHERE id IN (
               SELECT id
                 FROM {_bucket_model(env)._table}
                WHERE last_attempt_at < %s
                ORDER BY id
                {limit_clause}
         )
        RETURNING id
        """,
        params,
    )
    deleted_ids = env.cr.fetchall()
    env.invalidate_all(flush=False)
    return len(deleted_ids)


def cleanup_stale_invalid_token_attempts(env, limit=None):
    deadline = _cleanup_deadline(_normalize_now())
    limit_clause = "LIMIT %s" if limit else ""
    params = [deadline]
    if limit:
        params.append(limit)
    env.cr.execute(
        f"""
        DELETE FROM {_attempt_model(env)._table}
         WHERE id IN (
               SELECT id
                 FROM {_attempt_model(env)._table}
                WHERE attempted_at < %s
                ORDER BY id
                {limit_clause}
         )
        RETURNING id
        """,
        params,
    )
    deleted_ids = env.cr.fetchall()
    env.invalidate_all(flush=False)
    return len(deleted_ids)
