# Part of Odoo. See LICENSE file for full copyright and licensing details.


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", [table_name])
    return bool(cr.fetchone()[0])


def _column_exists(cr, table_name, column_name):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name = %s
        """,
        [table_name, column_name],
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    del version

    if not _table_exists(cr, 'open_sign_request_signer'):
        return

    required_signer_columns = {
        'access_token',
        'email_token_issued_at',
        'email_token_expires_at',
        'email_token_revoked_at',
        'request_id',
    }
    if any(not _column_exists(cr, 'open_sign_request_signer', column) for column in required_signer_columns):
        return

    request_has_expiry = _table_exists(cr, 'open_sign_request') and _column_exists(cr, 'open_sign_request', 'expires_at')
    if request_has_expiry:
        cr.execute(
            """
            UPDATE open_sign_request_signer signer
               SET email_token_issued_at = NOW(),
                   email_token_expires_at = CASE
                       WHEN request.expires_at IS NOT NULL THEN LEAST(request.expires_at, NOW() + INTERVAL '72 hours')
                       ELSE NOW() + INTERVAL '72 hours'
                   END,
                   email_token_revoked_at = NULL
              FROM open_sign_request request
             WHERE signer.request_id = request.id
               AND signer.access_token IS NOT NULL
               AND btrim(signer.access_token) <> ''
               AND (
                   signer.email_token_issued_at IS NULL
                   OR signer.email_token_expires_at IS NULL
               )
            """
        )
        return

    cr.execute(
        """
        UPDATE open_sign_request_signer
           SET email_token_issued_at = NOW(),
               email_token_expires_at = NOW() + INTERVAL '72 hours',
               email_token_revoked_at = NULL
         WHERE access_token IS NOT NULL
           AND btrim(access_token) <> ''
           AND (
               email_token_issued_at IS NULL
               OR email_token_expires_at IS NULL
           )
        """
    )
