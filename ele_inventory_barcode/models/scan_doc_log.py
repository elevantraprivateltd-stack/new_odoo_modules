# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ScanDocLog(models.Model):
    _name = 'scan.doc.log'
    _description = 'Barcode Scan (Receipt & Sale) Log'
    _order = 'id desc'

    batch_id = fields.Many2one('scan.doc.batch', string='Batch', readonly=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    barcode = fields.Char(readonly=True)
    mode = fields.Selection([('in', 'Stock IN'), ('out', 'Stock OUT')], required=True, readonly=True)
    qty = fields.Float(string='Quantity', readonly=True)
    user_id = fields.Many2one('res.users', string='Scanned By', default=lambda s: s.env.user, readonly=True)
    state = fields.Selection([('done', 'Done'), ('reverted', 'Undone')], default='done', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company, readonly=True)

    # ------------------------------------------------------------------
    @api.model
    def _stock_location(self):
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        if not wh:
            raise UserError(_('No warehouse found. Please create a warehouse first.'))
        return wh.lot_stock_id

    @api.model
    def _on_hand(self, product, location):
        product.invalidate_recordset()
        return product.with_context(location=location.id).qty_available

    # ------------------------------------------------------------------
    # main entry point: called for every scan
    # ------------------------------------------------------------------
    @api.model
    def process_scan(self, barcode, mode, qty=1):
        barcode = (barcode or '').strip()
        if not barcode:
            raise UserError(_('Empty barcode.'))
        if mode not in ('in', 'out'):
            raise UserError(_('Choose IN or OUT first.'))
        try:
            qty = float(qty or 1)
        except (TypeError, ValueError):
            raise UserError(_('Quantity must be a number.'))
        if qty <= 0:
            raise UserError(_('Quantity must be greater than zero.'))

        Product = self.env['product.product']
        product = Product.search([('barcode', '=', barcode)], limit=1) \
            or Product.search([('default_code', '=', barcode)], limit=1)
        if not product:
            raise UserError(_('Barcode %s: no product found.') % barcode)
        if product.type != 'consu':
            raise UserError(_('%s is not a stockable product.') % product.display_name)
        if product.tracking != 'none':
            raise UserError(_('%s is tracked by lot/serial number. Please use the normal '
                              'Receipt / Delivery screens for it.') % product.display_name)

        notes = []
        if not product.is_storable:
            product.sudo().is_storable = True
            notes.append(_('"Track Inventory" was switched on for this product.'))

        stock_loc = self._stock_location()
        batch = self.env['scan.doc.batch']._get_open_batch(mode)
        pending = batch._pending_qty(product)

        if mode == 'out':
            available = self._on_hand(product, stock_loc)
            if available < pending + qty:
                raise UserError(_('Not enough stock for %(p)s. In stock: %(a)s, already in this '
                                  'sale: %(w)s, you want: %(q)s.')
                                % {'p': product.display_name, 'a': available, 'w': pending, 'q': qty})

        batch._add_product(product, qty)
        log = self.create({
            'batch_id': batch.id,
            'product_id': product.id,
            'barcode': barcode,
            'mode': mode,
            'qty': qty,
        })
        batch.invalidate_recordset(['total_qty', 'reference'])
        return {
            'ok': True,
            'log_id': log.id,
            'product': product.display_name,
            'mode': mode,
            'qty': qty,
            'on_hand': self._on_hand(product, stock_loc),
            'in_document': pending + qty,
            'document': batch.reference,
            'notes': notes,
        }

    def undo_scan(self):
        """Take a wrong scan back (only while its batch is still open)."""
        self.ensure_one()
        if self.state == 'reverted':
            raise UserError(_('This scan is already undone.'))
        if self.batch_id.state != 'open':
            raise UserError(_('This batch is already finished (Receipt / Sale is confirmed). '
                              'Use a Return or Credit Note in Odoo to correct it.'))
        self.batch_id._remove_product(self.product_id, self.qty)
        self.state = 'reverted'
        return {
            'ok': True,
            'product': self.product_id.display_name,
            'on_hand': self._on_hand(self.product_id, self._stock_location()),
        }

    @api.model
    def finish_my_batches(self):
        """'Finish & Update Stock' button: validate everything this user has open."""
        batches = self.env['scan.doc.batch'].search([
            ('state', '=', 'open'), ('user_id', '=', self.env.uid),
            ('company_id', '=', self.env.company.id)])
        if not batches:
            raise UserError(_('Nothing to finish. Scan something first.'))
        done = []
        for b in batches:
            ref, had_items = b.reference, b.total_qty > 0
            b.action_finish()
            if had_items:
                done.append({'mode': b.mode, 'document': ref, 'invoice': b.invoice_id.name or ''})
        if not done:
            raise UserError(_('Nothing to finish. Scan something first.'))
        return {'ok': True, 'done': done}

    @api.model
    def status(self, limit=15):
        logs = self.search([('user_id', '=', self.env.uid)], limit=limit)
        open_batches = self.env['scan.doc.batch'].search([
            ('state', '=', 'open'), ('user_id', '=', self.env.uid),
            ('company_id', '=', self.env.company.id)])
        return {
            'logs': [{
                'id': l.id,
                'product': l.product_id.display_name,
                'mode': l.mode,
                'qty': l.qty,
                'state': l.state,
                'open': l.batch_id.state == 'open',
                'time': fields.Datetime.context_timestamp(self, l.create_date).strftime('%H:%M:%S'),
            } for l in logs],
            'open': [{
                'mode': b.mode,
                'document': b.reference,
                'qty': b.total_qty,
            } for b in open_batches],
        }
