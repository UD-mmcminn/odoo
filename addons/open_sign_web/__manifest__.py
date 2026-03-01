# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Open Sign Web',
    'summary': 'Web editor components for Open Sign',
    'category': 'Productivity',
    'version': '1.0',
    'depends': ['open_sign', 'web'],
    'data': [
        'views/open_sign_web_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'open_sign_web/static/src/js/**/*',
            'open_sign_web/static/src/xml/**/*',
            'open_sign_web/static/src/scss/open_sign.scss',
        ],
        'web.assets_tests': [
            'open_sign_web/static/tests/**/*',
        ],
        'web.assets_unit_tests': [
            'open_sign_web/static/tests/**/*.test.js',
        ],
    },
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
