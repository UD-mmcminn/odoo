# Part of Odoo. See LICENSE file for full copyright and licensing details.


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", [table_name])
    return bool(cr.fetchone()[0])


def migrate(cr, version):
    del version

    if _table_exists(cr, 'open_sign_portal_token_throttle'):
        cr.execute("DELETE FROM open_sign_portal_token_throttle")
