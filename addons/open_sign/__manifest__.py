# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Open Sign',
    'summary': 'Core document signing models and workflows',
    'category': 'Productivity',
    'version': '1.1',
    'depends': ['base', 'mail'],
    'application': True,
    'data': [
        'security/open_sign_groups.xml',
        'security/ir.model.access.csv',
        'security/open_sign_security.xml',
        'data/ir_cron.xml',
        'views/sign_template_views.xml',
        'views/sign_role_views.xml',
        'views/sign_template_field_views.xml',
        'views/sign_request_views.xml',
        'views/sign_template_version_views.xml',
        'views/sign_request_signer_views.xml',
        'views/sign_request_value_views.xml',
        'views/sign_audit_log_views.xml',
        'views/sign_menus.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
