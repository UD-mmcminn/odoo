# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Open Sign',
    'summary': 'Core document signing models and workflows',
    'category': 'Productivity',
    'version': '1.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/open_sign_groups.xml',
        'security/ir.model.access.csv',
        'security/open_sign_security.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
