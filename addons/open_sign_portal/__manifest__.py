# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Open Sign Portal',
    'summary': 'Portal routes and templates for Open Sign',
    'category': 'Productivity',
    'version': '1.3',
    'depends': ['open_sign', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/open_sign_portal_security.xml',
        'data/ir_cron.xml',
        'views/portal_templates.xml',
        'views/sign_request_signer_portal_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'open_sign_portal/static/src/interactions/portal_sign_session.js',
        ],
        'web.assets_tests': [
            'open_sign_portal/static/tests/**/*',
        ],
        'web.assets_unit_tests': [
            'open_sign_portal/static/src/interactions/portal_sign_session.js',
            'open_sign_portal/static/tests/**/*.test.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
