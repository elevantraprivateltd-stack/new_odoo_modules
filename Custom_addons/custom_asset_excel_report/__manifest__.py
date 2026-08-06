{
    "name": "Asset Excel Report",
    'author': "Elevantra Private Limited",
    'website': "https://www.Elevantra.cloud",
    "version": "19.0.1.0.0",
    "depends": ['base', 'account', 'base_accounting_kit', "report_xlsx"],
    "data": [
        'security/ir.model.access.csv',
        'report/report_action.xml',
        'data/data1.xml',
        'views/asset_extend.xml',
        'views/asset_disposal_view.xml',
        'views/asset_wizard_view.xml',
        'views/disposal_report_wizard.xml',

    ],
    "installable": True,
    'applicable': True,
}
