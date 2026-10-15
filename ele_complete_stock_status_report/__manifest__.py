# -*- coding: utf-8 -*-
{
    'name': 'Ele Complete Stock Status Report',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Reporting',
    'summary': 'Product variant wise Stock Status Report with date range filter '
               '(Opening Balance, Received, Return to Vendor, Sold/Dispatched, '
               'Return from Customer, Closing Balance)',
    'description': """
Stock Status Report
====================
This module adds a Stock Status Report under Inventory > Reporting.

Features
--------
* Date range filter (From Date - To Date), just like the Accounting reports.
* Report is generated Product Variant wise.
* Optional filters: Warehouse, Product Category, specific Products.
* Columns:
    - Product ID (Internal Reference)
    - Product Name / Description
    - Opening Balance
    - Received (from Vendor / Purchase)
    - Return to Vendor
    - Sold / Dispatched (to Customer)
    - Return from Customer
    - Closing Balance
* Print as PDF.
* Export to Excel (XLSX).

Logic
-----
Closing Balance = Opening Balance + Received - Return to Vendor
                   - Sold/Dispatched + Return from Customer
                   (+ any other stock moves in the period, e.g. inventory
                   adjustments, manufacturing, scrap - so the closing balance
                   always matches real, actual stock on hand.)

All figures are calculated from confirmed (Done) Stock Moves (stock.move),
so the report is always accurate and does not depend on any separate
ledger table.
""",
    'author': 'Elevantra Private Limited',
    'website': 'https://www.elevantra.cloud',
    'license': 'LGPL-3',
    'depends': ['stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'report/stock_status_report_template.xml',
        'report/stock_status_report_report.xml',
        'views/stock_status_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
