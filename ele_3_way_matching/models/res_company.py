from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    po_three_way_match = fields.Boolean(string='3-Way Matching', default=False)
