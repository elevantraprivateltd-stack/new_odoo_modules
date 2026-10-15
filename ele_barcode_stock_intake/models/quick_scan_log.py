# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QuickScanLog(models.Model):
    _name = 'quick.scan.log'
    _description = 'Quick Barcode Scan Log'
    _order = 'id desc'

    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    barcode = fields.Char(readonly=True)
    mode = fields.Selection([('in', 'Stock IN'), ('out', 'Stock OUT')], required=True, readonly=True)
    qty = fields.Float(string='Quantity', readonly=True)
    user_id = fields.Many2one('res.users', string='Scanned By', default=lambda s: s.env.user, readonly=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True)
    state = fields.Selection([('done', 'Done'), ('reverted', 'Undone')], default='done', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company, readonly=True)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_stock_location(self):
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        if not wh:
            raise UserError(_('No warehouse found. Please create a warehouse first.'))
        return wh.lot_stock_id

    @api.model
    def _on_hand(self, product, location):
        product.invalidate_recordset()
        return product.with_context(location=location.id).qty_available

    @api.model
    def _do_move(self, product, qty, src, dest, reference):
        vals = {
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'location_id': src.id,
            'location_dest_id': dest.id,
            'origin': reference,
        }
        if 'name' in self.env['stock.move']._fields:
            vals['name'] = reference
        move = self.env['stock.move'].create(vals)
        move._action_confirm()
        move._action_assign()
        move.quantity = qty
        move.picked = True
        move._action_done()
        return move

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

        notes = []
        if 'is_storable' in product._fields and not product.is_storable:
            product.sudo().is_storable = True
            notes.append(_('"Track Inventory" was switched on for this product.'))

        stock_loc = self._get_stock_location()
        reference = _('Quick Scan %s') % ('IN' if mode == 'in' else 'OUT')

        if mode == 'in':
            src = product.property_stock_production
            dest = stock_loc
        else:
            available = self._on_hand(product, stock_loc)
            if available < qty:
                raise UserError(_('Not enough stock for %(p)s. In stock: %(a)s, you want to take out: %(q)s.')
                                % {'p': product.display_name, 'a': available, 'q': qty})
            src = stock_loc
            dest = self.env.ref('stock.stock_location_customers')

        move = self._do_move(product, qty, src, dest, reference)
        log = self.create({
            'product_id': product.id,
            'barcode': barcode,
            'mode': mode,
            'qty': qty,
            'move_id': move.id,
        })
        return {
            'ok': True,
            'log_id': log.id,
            'product': product.display_name,
            'mode': mode,
            'qty': qty,
            'on_hand': self._on_hand(product, stock_loc),
            'notes': notes,
        }

    def undo_scan(self):
        """Reverse a wrong scan with an opposite stock move."""
        self.ensure_one()
        if self.state == 'reverted':
            raise UserError(_('This scan is already undone.'))
        stock_loc = self._get_stock_location()
        move = self.move_id
        if self.mode == 'in' and self._on_hand(self.product_id, stock_loc) < self.qty:
            raise UserError(_('Cannot undo: that stock has already been taken out.'))
        self._do_move(self.product_id, self.qty, move.location_dest_id, move.location_id,
                      _('Quick Scan UNDO'))
        self.state = 'reverted'
        return {
            'ok': True,
            'product': self.product_id.display_name,
            'on_hand': self._on_hand(self.product_id, stock_loc),
        }

    @api.model
    def recent(self, limit=15):
        logs = self.search([('user_id', '=', self.env.uid)], limit=limit)
        return [{
            'id': l.id,
            'product': l.product_id.display_name,
            'mode': l.mode,
            'qty': l.qty,
            'state': l.state,
            'time': fields.Datetime.context_timestamp(self, l.create_date).strftime('%H:%M:%S'),
        } for l in logs]
