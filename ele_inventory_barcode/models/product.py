# -*- coding: utf-8 -*-
from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        for product in products.filtered(lambda p: not p.barcode):
            product.barcode = product._scandoc_new_barcode()
        return products

    def _scandoc_new_barcode(self):
        """Return a new unique EAN-13 barcode (internal range, starts with 20)."""
        seq = self.env['ir.sequence'].sudo()
        while True:
            base = '20' + seq.next_by_code('scan.doc.barcode')  # 2 + 10 = 12 digits
            total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base))
            code = base + str((10 - total % 10) % 10)
            if not self.sudo().with_context(active_test=False).search_count([('barcode', '=', code)]):
                return code


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._scandoc_assign_barcodes()
        return templates

    def _scandoc_assign_barcodes(self):
        for variant in self.product_variant_ids.filtered(lambda p: not p.barcode):
            variant.barcode = variant._scandoc_new_barcode()

    def action_generate_barcode(self):
        """Server action: Action menu > Generate Barcodes."""
        self._scandoc_assign_barcodes()
        return True
