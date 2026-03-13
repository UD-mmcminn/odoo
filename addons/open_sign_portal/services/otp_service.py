# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import hashlib
import hmac
import secrets

from odoo import _, fields
from odoo.addons.open_sign.services import notification_service
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


OTP_CODE_LENGTH = 6
OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_HASH_ITERATIONS = 120000


def generate_otp_code():
    return f"{secrets.randbelow(10 ** OTP_CODE_LENGTH):0{OTP_CODE_LENGTH}d}"


def mask_email_address(email):
    normalized_email = email_normalize((email or '').strip()) or (email or '').strip()
    local_part, at, domain = normalized_email.partition('@')
    if not at:
        return normalized_email
    if not local_part:
        return f"***@{domain}"
    return f"{local_part[0]}***@{domain}"


def _generate_otp_salt():
    return secrets.token_hex(16)


def hash_otp_code(code, salt):
    normalized_code = (code or '').strip().encode('utf-8')
    normalized_salt = (salt or '').strip().encode('utf-8')
    return hashlib.pbkdf2_hmac(
        'sha256',
        normalized_code,
        normalized_salt,
        OTP_HASH_ITERATIONS,
    ).hex()


def verify_otp_code(challenge, code):
    expected_hash = hash_otp_code(code, challenge.code_salt)
    return hmac.compare_digest(expected_hash, challenge.code_hash or '')


def _challenge_model(env):
    return env['open.sign.otp.challenge'].sudo()


def get_active_challenge(signer):
    signer.ensure_one()
    return _challenge_model(signer.env).search([
        ('request_signer_id', '=', signer.id),
        ('verified_at', '=', False),
        ('expires_at', '>', fields.Datetime.now()),
    ], order='requested_at desc, id desc', limit=1)


def _get_latest_challenge(signer):
    signer.ensure_one()
    return _challenge_model(signer.env).search([
        ('request_signer_id', '=', signer.id),
    ], order='requested_at desc, id desc', limit=1)


def invalidate_active_challenges(signer, *, verified_too=False):
    signer.ensure_one()
    domain = [
        ('request_signer_id', '=', signer.id),
        ('expires_at', '>', fields.Datetime.now()),
    ]
    if not verified_too:
        domain.append(('verified_at', '=', False))
    challenges = _challenge_model(signer.env).search(domain)
    if challenges:
        challenges.write({'expires_at': fields.Datetime.now()})
    return challenges


def request_otp_challenge(signer, *, trigger):
    signer.ensure_one()
    now = fields.Datetime.now()
    latest_challenge = _get_latest_challenge(signer)
    cooldown_deadline = now - timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)
    if latest_challenge and latest_challenge.requested_at and latest_challenge.requested_at > cooldown_deadline:
        raise ValidationError(_('Please wait before requesting another verification code.'))

    invalidate_active_challenges(signer)

    otp_code = generate_otp_code()
    salt = _generate_otp_salt()
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
    challenge = _challenge_model(signer.env).create({
        'request_signer_id': signer.id,
        'requested_at': now,
        'expires_at': expires_at,
        'attempt_count': 0,
        'code_salt': salt,
        'code_hash': hash_otp_code(otp_code, salt),
    })
    notification_service.queue_request_otp_notification(
        signer.request_id.sudo(),
        signer.sudo(),
        otp_code=otp_code,
        expires_at=expires_at,
        trigger=trigger,
        raise_on_failure=True,
    )
    return challenge


def verify_otp_challenge(signer, code, *, trigger):
    signer.ensure_one()
    del trigger
    now = fields.Datetime.now()
    challenge = _get_latest_challenge(signer)
    if not challenge or challenge.verified_at:
        raise ValidationError(_('The verification code has expired. Request a new code.'))
    if challenge.attempt_count >= OTP_MAX_ATTEMPTS:
        raise ValidationError(_('Too many invalid verification attempts. Request a new code.'))
    if not challenge.expires_at or challenge.expires_at <= now:
        raise ValidationError(_('The verification code has expired. Request a new code.'))

    attempt_count_before = challenge.attempt_count
    if not verify_otp_code(challenge, code):
        updated_attempt_count = challenge.attempt_count + 1
        vals = {'attempt_count': updated_attempt_count}
        if updated_attempt_count >= OTP_MAX_ATTEMPTS:
            vals['expires_at'] = now
            challenge.write(vals)
            raise ValidationError(_('Too many invalid verification attempts. Request a new code.'))
        challenge.write(vals)
        raise ValidationError(_('The verification code is invalid.'))

    challenge.write({'verified_at': now})
    return challenge, attempt_count_before, now
