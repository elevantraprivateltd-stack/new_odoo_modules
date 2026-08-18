{
    'name': 'Asset Excel Report',
    'version': '19.0.1.0.0',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'category': 'Accounting',
    'summary': 'Export Detailed Fixed Asset & Asset Disposal Reports in Excel (XLSX) - Odoo 19 Community',
    'description': """
Asset Excel Report (Odoo 19 Community)
=====================================
Provides Excel (XLSX) reporting capabilities for Asset Management:
- Fixed Asset Detail Excel Report with Filter Wizard
- Asset Disposal & Write-off Report with Filter Wizard
- Extended Asset Management and Disposal Views
    """,
    'depends': ['base', 'account', 'base_accounting_kit', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_action.xml',
        'data/data1.xml',
        'views/asset_extend.xml',
        'views/asset_disposal_view.xml',
        'views/asset_wizard_view.xml',
        'views/disposal_report_wizard.xml',
    ],
    'images': ['static/description/custom_asset_excel_report_banner.png'],
    'installable': True,
    'application': False,
<<<<<<< HEAD
    'license': 'LGPL-3',
}
=======
    'price': 19.99,
    'currency': 'USD',
    'license': 'OPL-1',   # <-- CONFIRM: AGPL-3, LGPL-3, or OPL-1?
}
>>>>>>> b10a5596ffce3e3a1eb854da457a440a3b91ad9e
