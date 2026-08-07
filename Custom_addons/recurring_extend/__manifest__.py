# -*- coding: utf-8 -*-
{
    'name': 'Recurring Extend',
    'version': '19.0.1.0.1',
    'category': 'Accounting',
    'summary': 'Expense breakdown lines on recurring payment templates',
    'author': 'Elevantra Private Limited',
    'wesite':'https://www.elevantra.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'base_accounting_kit',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/recurring_template_views.xml',
    ],
    'installable': True,
    'application': False,
}
