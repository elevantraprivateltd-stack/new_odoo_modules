# -*- coding: utf-8 -*-
{
    'name': 'Ele CashBasis Profit and Loss',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Payment-basis (cash basis) Profit and Loss report for NGOs / projects',
    'description': """
NGO Cash Basis Profit and Loss
===============================
Adds a "Profit and Loss (Cash Basis)" report that is built ONLY from actual
Receipts (incoming payments) and Payments (outgoing payments) - never from
invoice/bill posting dates, and never from depreciation or other non-cash
journal entries.

Features
--------
* New "Income / Expense Category" field on Payments (account.payment) so every
  receipt/payment can be tagged (Donations, Grants, Salaries, Rent, etc.).
* Income & Expense categories are configurable (Accounting > Configuration).
* A wizard (Accounting > Reporting > Profit and Loss (Cash Basis)) where you
  pick a Start Date / End Date and click Print - exactly like the standard
  Profit and Loss wizard, but based purely on money actually received/paid.
* PDF report shows Total Income, Total Expenses, Net Surplus/(Deficit) and an
  optional Cash & Bank position (Opening + Receipts - Payments = Closing).
""",
    'author': 'Elevantra Private limited',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/cash_pnl_category_data.xml',
        'views/cash_pnl_category_views.xml',
        'views/account_payment_views.xml',
        'wizard/cash_pnl_wizard_views.xml',
        'report/cash_pnl_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
