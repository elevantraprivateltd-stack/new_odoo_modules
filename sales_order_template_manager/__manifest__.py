# -*- coding: utf-8 -*-
{
    'name': 'Sales Order Template Manager',
    'version': '1.0',
    'category': 'Sales',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],

    'summary': 'Custom Sale Order Templates and Engagement Letter Reports for Sales order.',
    'description': """
Sale Order Template & Engagement Letter Module
==============================================
This module enhances the standard Odoo Sales management system by adding custom templates and reporting features.

Key Features:
-------------
* **Custom Sale Order Views & Reports**: we can to print the proposal text in the report from the term and condition field .
* **Engagement Letter Generation**: we add a custom page to notebook and add a custom print button to print the engagement letter .
* **Streamlined UI**: Optimized sales view interface for easier management of templates and customer proposals.
""",
    'depends': ['base', 'sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'report/sale_order_template.xml',
        'report/engagement_letter_report.xml',
        'views/sale_order_proposal_template_views.xml',
        'views/sale_order_views.xml',
        'views/engagement_letter.xml',
    ],
    'images': ['static/description/sale_order_template_banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}