# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ScanDocBatch(models.Model):
    """One working session of scanning.

    * IN  batch  -> one Receipt (stock.picking). Every scan adds quantity to it.
                    On finish the Receipt is validated: stock + accounting update.
    * OUT batch  -> one Sales Order. Every scan adds quantity to it.
                    On finish the order is confirmed, the Delivery is validated
                    (stock updates) and, if enabled, the invoice is posted.
    """
    _name = 'scan.doc.batch'
    _description = 'Doc Scan Batch'
    _order = 'id desc'

    name = fields.Char(readonly=True, default='New', copy=False)
    mode = fields.Selection([('in', 'Stock IN (Receipt)'), ('out', 'Stock OUT (Sale)')],
                            required=True, readonly=True)
    state = fields.Selection([('open', 'Open'), ('done', 'Finished')], default='open',
                             readonly=True)
    user_id = fields.Many2one('res.users', string='Scanned By', default=lambda s: s.env.user,
                              readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company, readonly=True)
    last_scan = fields.Datetime(readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Receipt', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    log_ids = fields.One2many('scan.doc.log', 'batch_id', string='Scans')
    total_qty = fields.Float(compute='_compute_total_qty', string='Total Quantity')
    reference = fields.Char(compute='_compute_total_qty', string='Document')

    @api.depends('picking_id', 'sale_order_id', 'picking_id.move_ids.product_uom_qty',
                 'sale_order_id.order_line.product_uom_qty')
    def _compute_total_qty(self):
        for b in self:
            if b.mode == 'in':
                b.total_qty = sum(b.picking_id.move_ids.mapped('product_uom_qty'))
                b.reference = b.picking_id.name or ''
            else:
                b.total_qty = sum(b.sale_order_id.order_line.mapped('product_uom_qty'))
                b.reference = b.sale_order_id.name or ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code('scan.doc.batch') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_open_batch(self, mode):
        batch = self.search([
            ('state', '=', 'open'), ('mode', '=', mode),
            ('user_id', '=', self.env.uid), ('company_id', '=', self.env.company.id),
        ], limit=1)
        return batch or self.create({'mode': mode})

    def _warehouse(self):
        wh = self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', self.company_id.id)], limit=1)
        if not wh:
            raise UserError(_('No warehouse found. Please create a warehouse first.'))
        return wh

    def _pending_qty(self, product):
        """Quantity of this product already waiting in the open batch."""
        self.ensure_one()
        if self.mode == 'in':
            moves = self.picking_id.move_ids.filtered(lambda m: m.product_id == product)
            return sum(moves.mapped('product_uom_qty'))
        lines = self.sale_order_id.order_line.filtered(lambda l: l.product_id == product)
        return sum(lines.mapped('product_uom_qty'))

    # ------------------------------------------------------------------
    # add / remove quantity (called by every scan / undo)
    # ------------------------------------------------------------------
    def _add_product(self, product, qty):
        self.ensure_one()
        if self.mode == 'in':
            self._add_to_receipt(product, qty)
        else:
            self._add_to_sale(product, qty)
        self.last_scan = fields.Datetime.now()

    def _add_to_receipt(self, product, qty):
        if not self.picking_id:
            picking_type = self._warehouse().in_type_id
            self.picking_id = self.env['stock.picking'].sudo().create({
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'origin': self.name,
                'company_id': self.company_id.id,
            })
        picking = self.picking_id.sudo()
        move = picking.move_ids.filtered(lambda m: m.product_id == product)[:1]
        if move:
            move.product_uom_qty += qty
        else:
            vals = {
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'company_id': self.company_id.id,
            }
            if 'name' in self.env['stock.move']._fields:
                vals['name'] = product.display_name
            self.env['stock.move'].sudo().create(vals)

    def _add_to_sale(self, product, qty):
        if not self.sale_order_id:
            cfg = self.env['scan.doc.config'].get_config()
            self.sale_order_id = self.env['sale.order'].sudo().create({
                'partner_id': cfg.customer_id.id,
                'origin': self.name,
                'company_id': self.company_id.id,
                'warehouse_id': self._warehouse().id,
            })
        order = self.sale_order_id.sudo()
        line = order.order_line.filtered(lambda l: l.product_id == product)[:1]
        if line:
            line.product_uom_qty += qty
        else:
            self.env['sale.order.line'].sudo().create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_qty': qty,
            })

    def _remove_product(self, product, qty):
        """Undo a scan while the batch is still open."""
        self.ensure_one()
        if self.mode == 'in':
            move = self.picking_id.sudo().move_ids.filtered(lambda m: m.product_id == product)[:1]
            if move:
                if move.product_uom_qty - qty > 0:
                    move.product_uom_qty -= qty
                else:
                    move.unlink()
        else:
            line = self.sale_order_id.sudo().order_line.filtered(lambda l: l.product_id == product)[:1]
            if line:
                if line.product_uom_qty - qty > 0:
                    line.product_uom_qty -= qty
                else:
                    line.unlink()

    # ------------------------------------------------------------------
    # finish: this is where Receipt / Delivery / accounting get updated
    # ------------------------------------------------------------------
    def action_finish(self):
        for batch in self.filtered(lambda b: b.state == 'open'):
            batch = batch.with_company(batch.company_id)
            if batch.mode == 'in':
                batch._finish_receipt()
            else:
                batch._finish_sale()
            batch.state = 'done'
        return True

    def _validate_picking(self, picking):
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.with_context(skip_backorder=True).button_validate()
        if picking.state != 'done':
            raise UserError(_('%s could not be validated automatically (state: %s). '
                              'Please open it and check the stock.') % (picking.name, picking.state))

    def _finish_receipt(self):
        picking = self.picking_id.sudo()
        if not picking or not picking.move_ids:
            picking.unlink()
            return
        self._validate_picking(picking)

    def _finish_sale(self):
        order = self.sale_order_id.sudo()
        if not order or not order.order_line:
            order.unlink()
            return
        order.action_confirm()
        for picking in order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
            self._validate_picking(picking)
        cfg = self.env['scan.doc.config'].get_config()
        if cfg.auto_invoice:
            invoices = order._create_invoices()
            if cfg.sale_account_id:
                invoices.invoice_line_ids.filtered(
                    lambda l: l.display_type == 'product').write({'account_id': cfg.sale_account_id.id})
            invoices.action_post()
            self.invoice_id = invoices[:1]

    @api.model
    def _cron_finish_idle(self):
        batches = self.sudo().search([('state', '=', 'open')])
        now = fields.Datetime.now()
        for batch in batches:
            cfg = self.env['scan.doc.config'].sudo().search(
                [('company_id', '=', batch.company_id.id)], limit=1)
            minutes = cfg.idle_minutes if cfg else 10
            if batch.last_scan and batch.last_scan > now - timedelta(minutes=minutes):
                continue
            try:
                with self.env.cr.savepoint():
                    batch.action_finish()
            except Exception:
                _logger.exception('Doc Scan: could not finish batch %s', batch.name)

    def action_open_document(self):
        self.ensure_one()
        doc = self.picking_id if self.mode == 'in' else self.sale_order_id
        if not doc:
            raise UserError(_('Nothing to open yet.'))
        return doc.get_formview_action()
