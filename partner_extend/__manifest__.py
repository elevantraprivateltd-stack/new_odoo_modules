# -*- coding: utf-8 -*-
{
    'name': 'School Management Contact Fields',
    'version': '19.0.1.0.0',
    'summary': 'Adds custom fields (Zone, Area, Board Type, etc.) to Contacts and CRM Forms',
    'sequence': 10,
    'description': """
School Management Contact Fields (Odoo 19 Community)
===================================================
This module extends the res.partner and crm.lead models:
- Adds custom school fields (Zone, Area, Board Type)
- Positions fields directly below the address block in Contacts
- Integrates custom fields into CRM Lead views
    """,
    'category': 'Tools',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'depends': [
        'base',
        'contacts',
        'crm',
    ],
    'data': [
        'views/res_partner.xml',
        'views/crm_lead.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}