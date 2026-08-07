{
    'name': 'Service Planning',
    'version': '19.0.1.0.0',  # Odoo 19 compatible version
    'summary': 'Advanced Project Scheduling and Resource Management for Community',
    'description': """
Service Planning & Resource Management
=======================================
This module brings advanced project scheduling, resource allocation, and interactive planning views to Odoo Community Edition.

Key Features:
-------------
* **Gantt & Timeline Views**: Visualize employee schedules, project timelines, and task allocations efficiently.
* **Resource Management**: Seamless integration with HR and Project modules to assign tasks based on employee availability.
* **Custom Reporting**: Generate and export planning reports via interactive wizards.
* **Seamless Integration**: Fully integrated with Sales, HR, Calendar, and Project modules.
""",
    'category': 'Services/Project',
    'author': 'Elevantra Private Limited',
    'website': 'https://Eleventra.cloud',
    'images': ['static/description/icon.png'],
    'depends': [
        'base',
        'web',
        'mail',
        'hr',
        'project',
        'sale',
        'calendar'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/planning_schedule_views.xml',
        'views/planning_gantt_views.xml',
        'views/planning_report_wizard_views.xml',
        'reports/planning_reports.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'service_planning/static/src/js/gantt_view.js',
            'service_planning/static/src/xml/gantt_templates.xml',
            'service_planning/static/src/css/gantt.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
