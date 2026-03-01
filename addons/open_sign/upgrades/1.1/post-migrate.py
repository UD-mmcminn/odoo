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

    if _table_exists(cr, 'open_sign_request') and _column_exists(cr, 'open_sign_request', 'reminder_count'):
        cr.execute(
            """
            UPDATE open_sign_request
               SET reminder_count = 0
             WHERE reminder_count IS NULL
                OR reminder_count < 0
            """
        )

    if _table_exists(cr, 'ir_cron'):
        cr.execute(
            """
            UPDATE ir_cron
               SET active = TRUE
             WHERE id IN (
                SELECT data.res_id
                  FROM ir_model_data data
                 WHERE data.model = 'ir.cron'
                   AND data.module = 'open_sign'
                   AND data.name IN (
                        'ir_cron_open_sign_send_reminders',
                        'ir_cron_open_sign_expire_requests'
                   )
             )
            """
        )
