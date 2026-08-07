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
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}