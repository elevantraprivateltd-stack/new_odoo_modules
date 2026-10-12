# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import file_open


class ScanDocController(http.Controller):

    @http.route('/scan_doc', type='http', auth='user')
    def scan_page(self, **kw):
        if not request.env.user.has_group('stock.group_stock_user'):
            return request.make_response('Not allowed.', status=403)
        with file_open('barcode_inventory_accounting/static/src/scan_page.html', 'r') as f:
            html = f.read()
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    def _safe(self, func):
        try:
            with request.env.cr.savepoint():
                return func()
        except UserError as e:
            return {'ok': False, 'message': e.args[0]}

    @http.route('/scan_doc/scan', type='jsonrpc', auth='user')
    def scan(self, barcode, mode, qty=1):
        return self._safe(lambda: request.env['scan.doc.log'].process_scan(barcode, mode, qty))

    @http.route('/scan_doc/undo', type='jsonrpc', auth='user')
    def undo(self, log_id):
        return self._safe(lambda: request.env['scan.doc.log'].browse(int(log_id)).undo_scan())

    @http.route('/scan_doc/finish', type='jsonrpc', auth='user')
    def finish(self):
        return self._safe(lambda: request.env['scan.doc.log'].finish_my_batches())

    @http.route('/scan_doc/recent', type='jsonrpc', auth='user')
    def recent(self):
        return request.env['scan.doc.log'].status()
