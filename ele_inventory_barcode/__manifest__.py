# -*- coding: utf-8 -*-
{
    'name': 'Ele Inventory Barcode',
    'version': '3.0',
    'summary': 'Scan barcodes (USB scanner or mobile camera): IN updates a Receipt and accounting, '
               'OUT updates a Sales Order, Delivery and inventory.',
    'category': 'Inventory',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'depends': ['base', 'product', 'stock', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/cron.xml',
        'views/scan_doc_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
