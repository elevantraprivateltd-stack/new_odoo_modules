# -*- coding: utf-8 -*-
{
    'name': 'Ele Barcode Stock intake In/Out',
    'version': '2.0',
    'summary': 'Scan a barcode (USB scanner or mobile camera) to add or remove stock directly. '
               'No receipts, no delivery orders.',
    'category': 'Inventory',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'depends': ['base','stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/quick_scan_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
