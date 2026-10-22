{
    'name': 'Company Approval',
    'version': '20.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Internal request and approval workflow',
    'description': """
Internal approval requests (purchase, payment, leave, other).

This module is a starting template for company-specific development:
new model, sequence, workflow buttons, security groups, chatter,
views, menus and tests.
    """,
    'author': 'My Company',
    'license': 'LGPL-3',
    'depends': ['mail'],
    'data': [
        'security/company_approval_security.xml',
        'security/ir.access.csv',
        'data/ir_sequence_data.xml',
        'views/company_approval_request_views.xml',
        'views/company_approval_menus.xml',
    ],
    'application': True,
    'installable': True,
}
