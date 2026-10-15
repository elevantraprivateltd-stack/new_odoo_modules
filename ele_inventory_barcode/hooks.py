# -*- coding: utf-8 -*-


def post_init_hook(env):
    """On install: give a barcode to every existing product that has none."""
    templates = env['product.template'].search([('barcode', '=', False)])
    templates._scandoc_assign_barcodes()
