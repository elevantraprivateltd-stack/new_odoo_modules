{
    'name': 'Purchase 3-Way Matching',
    'version': '19.0.1.0.0',
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
* Vendor form and vendor bill show the vendor's POs and products.
    """,
    'author': 'Elevantra Private Ltd',
    'depends': ['purchase', 'purchase_stock', 'account'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
