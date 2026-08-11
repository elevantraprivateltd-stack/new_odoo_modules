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
<<<<<<< HEAD
<<<<<<< HEAD
    'images': ['static/description/banner.png'],
=======
    'images': ['static/description/recurring_extend_banner.png'],
>>>>>>> 60ba4e1 (Updated custom module names and code)
=======
    'images': ['static/description/recurring_extend_banner.png'],
>>>>>>> 2ed8e4ca64924ae72e17bd413679bdc5df704d95
    'installable': True,
    'application': False,
    'auto_install': False,
}