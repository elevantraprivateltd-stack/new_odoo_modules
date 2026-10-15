{
    'name': 'Ele Lead Sales & Assigned',
    'version': '19.0.1.0.0',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'category': 'Extra Tools',
    'summary': 'Custom Labels, Field Renaming & Tab Modifications for CRM and Partners',
    'description': """
Lead Custom Labels
==================
This module customizes Odoo CRM & Partner forms:
- Renames 'Expected Closing' to 'Lead End Date'
- Replaces/Updates tabs with 'Lead' and 'Client Info'
- Adds 'Task Assigned to Resource' field in CRM
- Changes 'Company' to 'Institute' in Partner/School view
    """,
    'depends': ['base', 'crm'],
    'data': [
        'views/crm_lead.xml',
    ],
    'images': ['static/description/crm_lead_custom_labels_banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}