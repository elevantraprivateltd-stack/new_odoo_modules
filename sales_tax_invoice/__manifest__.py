# -*- coding: utf-8 -*-
{
    'name': 'Sales Tax Invoice Report',
    'version': '19.0.1.1.0',
    'category': 'Accounting',
    'summary': 'Reference-matched Global Pharmaceuticals Sales Tax Invoice report',
    'depends': ['account', 'sale', 'stock'],
    'data': [
        'report/report_sales_tax_invoice.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
