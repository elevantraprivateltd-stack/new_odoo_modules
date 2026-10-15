from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    three_way_status = fields.Selection([
        ('non_po', 'Non-PO Bill (No Matching)'),
        ('ready', 'Ready to Pay'),
        ('waiting', 'Waiting for Receipt'),
        ('exception', 'Exception: Billed More Than Ordered'),
    ], string='3-Way Matching', compute='_compute_three_way_status')
    three_way_message = fields.Text(compute='_compute_three_way_status')

    # ------------------------------------------------------------------
    # 3-way matching
    # ------------------------------------------------------------------
    def _three_way_to_po_uom(self, line, pol):
        if line.product_uom_id and pol.product_uom_id:
            return line.product_uom_id._compute_quantity(line.quantity, pol.product_uom_id)
        return line.quantity

    def _three_way_other_billed(self, pol):
        """Qty billed on OTHER posted bills of this PO line (this bill excluded)."""
        me = self._origin or self
        total = 0.0
        for line in pol.invoice_lines:
            move = line.move_id
            if move == me or move.state != 'posted' \
                    or move.move_type not in ('in_invoice', 'in_refund'):
                continue
            qty = self._three_way_to_po_uom(line, pol)
            total += qty if move.move_type == 'in_invoice' else -qty
        return total

    def _three_way_evaluate(self):
        """Return (status, message) computed from fresh data."""
        self.ensure_one()
        if self.move_type != 'in_invoice' or not self.company_id.po_three_way_match:
            return False, False
        po_lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product' and l.purchase_line_id)
        if not po_lines:
            return 'non_po', False

        this_bill = {}
        for line in po_lines:
            pol = line.purchase_line_id
            if pol.product_id.type == 'service':
                continue
            this_bill[pol] = this_bill.get(pol, 0.0) + self._three_way_to_po_uom(line, pol)

        status = 'ready'
        messages = []
        for pol, qty in this_bill.items():
            total_billed = self._three_way_other_billed(pol) + qty
            info = _("%(po)s - %(product)s: Ordered %(ordered)s, Received %(received)s, "
                     "Billed (with this bill) %(billed)s.",
                     po=pol.order_id.name, product=pol.product_id.display_name,
                     ordered=pol.product_qty, received=pol.qty_received, billed=total_billed)
            if pol.product_uom_id.compare(total_billed, pol.product_qty) > 0:
                status = 'exception'
                messages.append(info + ' ' + _("Billed more than ordered."))
            elif pol.product_uom_id.compare(total_billed, pol.qty_received) > 0:
                if status != 'exception':
                    status = 'waiting'
                messages.append(info + ' ' + _("Goods not fully received yet."))
        return status, '\n'.join(messages) or False

    @api.depends('company_id.po_three_way_match', 'move_type', 'state',
                 'invoice_line_ids.quantity', 'invoice_line_ids.purchase_line_id',
                 'invoice_line_ids.purchase_line_id.qty_received',
                 'invoice_line_ids.purchase_line_id.product_qty')
    def _compute_three_way_status(self):
        for move in self:
            move.three_way_status, move.three_way_message = move._three_way_evaluate()

    def action_register_payment(self, *args, **kwargs):
        if not self.env.context.get('skip_three_way_match'):
            for move in self.filtered(lambda m: m.move_type == 'in_invoice'):
                status, message = move._three_way_evaluate()
                if status in ('waiting', 'exception'):
                    raise UserError(_(
                        "You cannot pay bill %(name)s yet (3-Way Matching).\n\n%(msg)s",
                        name=move.name or move.display_name, msg=message))
        return super().action_register_payment(*args, **kwargs)
