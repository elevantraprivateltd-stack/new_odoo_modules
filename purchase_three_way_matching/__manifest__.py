{
    'name': 'Purchase 3-Way Matching',
    'version': '19.0.1.4.0',
    'category': 'Accounting/Purchase',
    'summary': 'Enterprise-style 3-way matching (PO / Receipt / Vendor Bill) for Odoo Community',
    'description': """
Purchase 3-Way Matching
=======================
* Enable / disable from Settings > Purchase > 3-Way Matching.
* Bills linked to a Purchase Order are matched against Ordered and Received quantities.
* Bills without a Purchase Order (Non-PO) are never blocked.
* Payment status on every vendor bill: Ready to Pay / Waiting for Receipt / Exception.
* Payment of a bill that is not ready is blocked.
* Receipts: choosing a vendor automatically loads all of its open POs;
  the pending products are loaded automatically and Source Document is filled.
    """,
    'author': 'Elevantra Private Ltd',
    'website':'https://www.elevantra.cloud',
    'depends': ['base','purchase', 'purchase_stock', 'stock', 'account'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
