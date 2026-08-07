{
    'name': 'Analytic Account Reports (PDF & XLSX)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Print and export Analytic Account reports in PDF and XLSX format',
    'description': """
Analytic Account Reports
=========================
This module adds a wizard to generate Analytic Account reports with:

* Filter by Date From / Date To
* Filter by one or more Analytic Accounts
* Filter by Company
* Filter by Posted Entries or All Entries
* Export the report as a PDF document
* Export the report as an XLSX (Excel) file

No external dependency required other than the standard `xlsxwriter`
library that ships with Odoo.
""",
    'author': 'Elevantra Private Limited',
    'license': 'LGPL-3',
    'depends': ['base', 'analytic', 'account'],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/analytic_report_wizard_views.xml',
        'report/analytic_report_templates.xml',
        'views/account_analytic_account_view.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
