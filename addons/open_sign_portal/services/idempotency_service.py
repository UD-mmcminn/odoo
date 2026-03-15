# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import hashlib
import json

from odoo import fields


IDEMPOTENCY_RETENTION_DAYS = 30


def _model(env):
    return env['open.sign.portal.idempotency'].sudo()


def _canonical_sha256(payload):
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def build_submit_request_hash(normalized_values, *, consent_accepted, consent_hash, signer_timezone):
    canonical_values = [
        {
            'field_id': int(value['field_id']),
            'value': value.get('value', False),
        }
        for value in normalized_values
    ]
    canonical_values.sort(key=lambda value: value['field_id'])
    return _canonical_sha256({
        'values': canonical_values,
        'consent': {
            'accepted': bool(consent_accepted),
            'text_hash': (consent_hash or '').strip(),
            'timezone': (signer_timezone or '').strip() or False,
        },
    })


def build_decline_request_hash(normalized_reason):
    return _canonical_sha256({'reason': (normalized_reason or '').strip()})


def _create_claimed_record(model, request_signer, *, endpoint, idempotency_key, request_hash, ttl_days, now):
    return model.create({
        'request_signer_id': request_signer.id,
        'endpoint': endpoint,
        'idempotency_key': idempotency_key,
        'request_hash': request_hash,
        'state': 'in_progress',
        'expires_at': now + timedelta(days=ttl_days),
    })


def claim_or_resolve(request_signer, *, endpoint, idempotency_key, request_hash, ttl_days=IDEMPOTENCY_RETENTION_DAYS):
    request_signer.ensure_one()
    model = _model(request_signer.env)
    now = fields.Datetime.now()
    record = model.search([
        ('request_signer_id', '=', request_signer.id),
        ('endpoint', '=', endpoint),
        ('idempotency_key', '=', idempotency_key),
    ], limit=1)
    if record and record.expires_at and record.expires_at < now:
        record.unlink()
        record = False
    if not record:
        record = _create_claimed_record(
            model,
            request_signer,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            ttl_days=ttl_days,
            now=now,
        )
        return 'claimed', record

    if record.request_hash != request_hash:
        return 'conflict', record
    if record.state == 'completed':
        return 'replay', record
    if record.state == 'in_progress':
        return 'locked', record

    record.write({
        'state': 'in_progress',
        'response_json': False,
    })
    return 'claimed', record


def mark_completed(record, response_json):
    record.ensure_one()
    record.sudo().write({
        'state': 'completed',
        'response_json': response_json,
    })
    return record


def mark_failed(record):
    record.ensure_one()
    record.sudo().write({
        'state': 'failed',
        'response_json': False,
    })
    return record


def mark_conflict_logged(record, when=None):
    record.ensure_one()
    record.sudo().write({
        'conflict_logged_at': when or fields.Datetime.now(),
    })
    return record


def cleanup_expired_records(env, limit=None):
    expired_records = _model(env).search([
        ('expires_at', '!=', False),
        ('expires_at', '<', fields.Datetime.now()),
    ], order='id', limit=limit)
    deleted_count = len(expired_records)
    if expired_records:
        expired_records.unlink()
    return deleted_count
