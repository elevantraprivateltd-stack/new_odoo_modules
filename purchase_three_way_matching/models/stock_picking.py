from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_order_ids = fields.Many2many(
        'purchase.order', 'stock_picking_vendor_po_rel', 'picking_id', 'purchase_order_id',
        string='Purchase Orders', copy=False,
        help="Select the vendor's Purchase Orders. Their pending products are added "
             "to this receipt automatically.")
    vendor_total_po_count = fields.Integer(
        string='Vendor Total POs', compute='_compute_vendor_po_counts')
    vendor_open_po_count = fields.Integer(
        string='Vendor Open POs', compute='_compute_vendor_po_counts',
        help="Confirmed Purchase Orders of this vendor that are not fully received.")

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------
    @api.depends('partner_id', 'picking_type_code')
    def _compute_vendor_po_counts(self):
        PurchaseOrder = self.env['purchase.order']
        for picking in self:
            total = open_count = 0
            if picking.partner_id and picking.picking_type_code == 'incoming':
                domain = [('partner_id', '=', picking.partner_id.id),
                          ('state', 'in', ('purchase', 'done'))]
                total = PurchaseOrder.search_count(domain)
                open_count = PurchaseOrder.search_count(
                    domain + [('receipt_status', '!=', 'full')])
            picking.vendor_total_po_count = total
            picking.vendor_open_po_count = open_count

    # ------------------------------------------------------------------
    # Auto-fill products from the selected POs
    # ------------------------------------------------------------------
    def _prepare_po_move_vals(self, pol):
        """Receipt line values for the quantity of a PO line still to be received."""
        self.ensure_one()
        product = pol.product_id
        if not product or pol.display_type or product.type != 'consu':
            return False
        remaining = pol.product_qty - pol.qty_received
        if pol.product_uom_id.compare(remaining, 0.0) <= 0:
            return False
        location = self.location_id or self.partner_id.property_stock_supplier
        vals = {
            'product_id': product.id,
            'product_uom_qty': remaining,
            'product_uom': pol.product_uom_id.id,
            'purchase_line_id': pol.id,
            'partner_id': self.partner_id.id,
            'origin': pol.order_id.name,
            'location_id': location.id,
            'location_dest_id': self.location_dest_id.id,
            'picking_type_id': self.picking_type_id.id,
            'price_unit': pol._get_stock_move_price_unit(),
        }
        return {k: v for k, v in vals.items() if v not in (False, None)}

    def _sync_vendor_po_moves(self):
        """Add the lines of newly selected POs, remove the lines of un-selected POs."""
        self.ensure_one()
        wanted = self.purchase_order_ids
        moves = self.move_ids
        removed = moves.filtered(
            lambda m: m.purchase_line_id
            and m.purchase_line_id.order_id not in wanted
            and (not m.state or m.state == 'draft'))
        present_lines = (moves - removed).mapped('purchase_line_id')
        StockMove = self.env['stock.move']
        new_moves = StockMove
        for pol in wanted.order_line:
            if pol in present_lines:
                continue
            vals = self._prepare_po_move_vals(pol)
            if vals:
                new_moves |= StockMove.new(vals)
        if removed or new_moves:
            self.move_ids = (moves - removed) | new_moves
        if wanted:
            self.origin = ', '.join(wanted.mapped('name'))
        elif removed:
            self.origin = False

    @api.onchange('partner_id')
    def _onchange_partner_vendor_pos(self):
        """Vendor selected: load ALL its open POs and their pending products automatically."""
        if self.picking_type_code != 'incoming' or self.state not in ('draft', False):
            return
        orders = self.env['purchase.order']
        if self.partner_id:
            orders = orders.search([
                ('partner_id', '=', self.partner_id.id),
                ('state', 'in', ('purchase', 'done')),
                ('receipt_status', '!=', 'full'),
            ], order='date_order, id')
        self.purchase_order_ids = orders
        self._sync_vendor_po_moves()

    @api.onchange('purchase_order_ids')
    def _onchange_purchase_order_ids(self):
        self._sync_vendor_po_moves()
