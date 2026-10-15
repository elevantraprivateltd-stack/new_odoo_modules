# -*- coding: utf-8 -*-
{
    'name': 'Ele Executive summary',
    'version': '19.0.4.0.0',
    'summary': 'Ultra professional colorful dashboards with real Chart.js graphs and full working filters for CRM, Sales, Projects, Invoices and Resources.',
    'description': """
        Ultra Advanced Executive Dashboards – Odoo 19 Community
        =======================================================
        - Real Chart.js colorful graphs (Doughnut, Bar, Line, Pie)
        - Full server-side filter bar on every dashboard (team, stage,
          source, salesperson/user, customer, department, status, and
          quick date-range presets: Today / This Week / This Month /
          Last Month / This Quarter / This Year / Custom Range)
        - Every KPI card, chart, and drill-down list respects the active
          filters at all times
        - CRM, Sales, Project, Invoice, Resource (HR)
        - Clickable KPI cards open filtered records
        - Premium modern dark UI with icon-badged KPI cards
    """,
    'category': 'Technical/Dashboards',
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'depends': [
        'base',
        'web',
        'crm',
        'sale_management',
        'project',
        'account',
        'hr',
        'hr_holidays',
    ],
    'data': [
        'views/menu_root.xml',
        'views/crm_dashboard_views.xml',
        'views/sale_dashboard_views.xml',
        'views/project_dashboard_views.xml',
        'views/invoice_dashboard_views.xml',
        'views/resource_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'exec_dashboard/static/lib/chart.umd.min.js',
            'exec_dashboard/static/src/css/dashboard.css',
            'exec_dashboard/static/src/js/crm_dashboard.js',
            'exec_dashboard/static/src/js/sale_dashboard.js',
            'exec_dashboard/static/src/js/project_dashboard.js',
            'exec_dashboard/static/src/js/invoice_dashboard.js',
            'exec_dashboard/static/src/js/resource_dashboard.js',
            'exec_dashboard/static/src/xml/crm_dashboard.xml',
            'exec_dashboard/static/src/xml/sale_dashboard.xml',
            'exec_dashboard/static/src/xml/project_dashboard.xml',
            'exec_dashboard/static/src/xml/invoice_dashboard.xml',
            'exec_dashboard/static/src/xml/resource_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
