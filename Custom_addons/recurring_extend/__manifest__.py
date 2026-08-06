{
    'name': 'Recurring Extend',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'author': 'Elevantra Private Limited',
    'depends': ['base', 'account', 'base_accounting_kit'], # Ya jis module mein account.recurring.entries.line ho
    'data': [
        'security/ir.model.access.csv',
        'views/recurring_template_views.xml',
    ],
    'installable': True,
    'application': False,
}