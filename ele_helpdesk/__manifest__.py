# -*- coding: utf-8 -*-
{
    'name': ' Ele Helpdesk',
    'version': '19.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Standalone Helpdesk system: Tickets, Teams, Dashboard and Custom Report',
    'description': """
Helpdesk Custom Module (Community Edition compatible)
========================================================
A complete, standalone Help Desk system that does NOT require the
Enterprise Helpdesk app. Includes:

* Ticket management (Team, Stage, Type, Priority, Department, Source)
* Kanban board with drag & drop stages
* Custom Dashboard (Kanban / Pivot / Graph / List)
* Custom Report wizard -> filterable PDF report
""",
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'depends': ['base', 'mail', 'portal'],
    'data': [
        'security/helpdesk_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/helpdesk_stage_data.xml',
        'data/ticket_type_data.xml',
        'data/helpdesk_sla_data.xml',
        'data/helpdesk_ticket_tag_data.xml',
        'views/helpdesk_stage_views.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_sla_views.xml',
        'views/helpdesk_ticket_tag_views.xml',
        'views/res_partner_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_dashboard_views.xml',
        'wizard/helpdesk_report_wizard_view.xml',  # <-- Wizard pehle load hoga
        'report/helpdesk_report_actions.xml',      # <-- Reports pehle load hongi
        'report/helpdesk_report_template.xml',
        'views/website_client_form_templates.xml',  # <-- Client Form page
        'views/portal_templates.xml',                # <-- "Helpdesk Tickets" card on /my/home
        'views/menu_views.xml',                     # <-- Menus sab se aakhir mein
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_frontend': [
            'ele_helpdesk/static/src/css/helpdesk_contact_form.css',
            'ele_helpdesk/static/src/js/helpdesk_contact_form.js',
        ],
        'web.assets_backend': [
            'ele_helpdesk/static/src/js/helpdesk_dashboard/helpdesk_dashboard.js',
            'ele_helpdesk/static/src/js/helpdesk_dashboard/helpdesk_dashboard.xml',
            'ele_helpdesk/static/src/js/helpdesk_dashboard/helpdesk_dashboard.css',
            'ele_helpdesk/static/src/js/helpdesk_analytics/helpdesk_analytics.js',
            'ele_helpdesk/static/src/js/helpdesk_analytics/helpdesk_analytics.xml',
            'ele_helpdesk/static/src/js/helpdesk_analytics/helpdesk_analytics.css',
        ],
    },
}