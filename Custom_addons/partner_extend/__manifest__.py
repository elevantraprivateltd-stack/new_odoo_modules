# -*- coding: utf-8 -*-
{
    'name': 'School Management Contact Fields',
    'summary': 'Adds custom fields (Zone, Area, Board Type, etc.) to Contacts Form',
    'sequence': 10,
    'description': """
        This module adds custom fields to the res.partner model 
        and positions them exactly below the address fields as required.
    """,
    'category': 'Tools',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'contacts',
        'crm'
    ],
    'data': [
        'views/res_partner.xml',
        'views/crm_lead.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}