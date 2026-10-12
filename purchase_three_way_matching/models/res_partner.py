from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_po_line_ids = fields.One2many(
        'purchase.order.line', 'partner_id', string='Vendor PO Lines', readonly=True)
    vendor_po_total_count = fields.Integer(
        string='Total POs', compute='_compute_vendor_po_stats')
    vendor_po_total_amount = fields.Float(
        string='Total PO Amount', compute='_compute_vendor_po_stats')

    def _compute_vendor_po_stats(self):
        stats = {}
        ids = [i for i in self.ids if i]
        if ids:
            groups = self.env['purchase.order']._read_group(
                [('partner_id', 'in', ids), ('state', 'in', ('purchase', 'done'))],
                ['partner_id'], ['__count', 'amount_total:sum'])
            stats = {partner.id: (count, total) for partner, count, total in groups}
        for partner in self:
            count, total = stats.get(partner.id, (0, 0.0))
            partner.vendor_po_total_count = count
            partner.vendor_po_total_amount = total
