# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import file_open


class QuickScanController(http.Controller):

    @http.route('/quick_scan', type='http', auth='user')
    def scan_page(self, **kw):
        if not request.env.user.has_group('stock.group_stock_user'):
            return request.make_response('Not allowed.', status=403)
        with file_open('ele_barcode_stock_intake/static/src/scan_page.html', 'r') as f:
            html = f.read()
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/quick_scan/scan', type='jsonrpc', auth='user')
    def scan(self, barcode, mode, qty=1):
        try:
            with request.env.cr.savepoint():
                return request.env['quick.scan.log'].process_scan(barcode, mode, qty)
        except UserError as e:
            return {'ok': False, 'message': e.args[0]}

    @http.route('/quick_scan/undo', type='jsonrpc', auth='user')
    def undo(self, log_id):
        try:
            with request.env.cr.savepoint():
                return request.env['quick.scan.log'].browse(int(log_id)).undo_scan()
        except UserError as e:
            return {'ok': False, 'message': e.args[0]}

    @http.route('/quick_scan/recent', type='jsonrpc', auth='user')
    def recent(self):
        return request.env['quick.scan.log'].recent()
