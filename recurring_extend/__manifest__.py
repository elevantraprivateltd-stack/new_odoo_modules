# -*- coding: utf-8 -*-
{
    'name': 'Recurring Extend',
    'version': '19.0.1.0.1',
    'category': 'Accounting',
    'summary': 'Expense breakdown lines on recurring payment templates',
    'description': """
Recurring Extend (Odoo 19 Community Edition)
===========================================
This module extends the base accounting kit functionality:
- Adds detailed expense breakdown lines to recurring payment templates.
- Custom views for enhanced recurring template management.
- Fully compatible with Odoo 19 Community Edition.
    """,
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'base_accounting_kit',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/recurring_template_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}