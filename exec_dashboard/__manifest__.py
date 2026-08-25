{
    'name': 'Exective Dashboard',
    'version': '19.0.1.0.0',
    'summary': 'Executive dashboards inside CRM, Sales, Invoicing and Project apps',
    'description': """
Adds a "Dashboard" menu inside CRM, Sales, Invoicing and Project apps showing
clickable KPI tiles (counts + amounts) as requested by management.
""",
    'category': 'Sales/CRM',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'license': 'LGPL-3',
    'depends': ['crm', 'sale', 'account', 'project', 'purchase'],
    'data': [
        'views/menu_root.xml',
        'views/crm_dashboard_views.xml',
        'views/sale_dashboard_views.xml',
        'views/invoice_dashboard_views.xml',
        'views/project_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'exec_dashboard/static/src/css/dashboard.css',
            'exec_dashboard/static/src/js/crm_dashboard.js',
            'exec_dashboard/static/src/js/sale_dashboard.js',
            'exec_dashboard/static/src/js/invoice_dashboard.js',
            'exec_dashboard/static/src/js/project_dashboard.js',
            'exec_dashboard/static/src/xml/crm_dashboard.xml',
            'exec_dashboard/static/src/xml/sale_dashboard.xml',
            'exec_dashboard/static/src/xml/invoice_dashboard.xml',
            'exec_dashboard/static/src/xml/project_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
