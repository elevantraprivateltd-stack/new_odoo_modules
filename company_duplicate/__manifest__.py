{
    "name": "Company Master Data Clone",
    "version": "19.0.3.0.0",
    "category": "Accounting",
    "summary": "Clone a company's settings, chart of accounts and master data",
    "depends": [
        "base",
        "account",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/company_duplicate_wizard_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
