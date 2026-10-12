from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_three_way_match = fields.Boolean(
        string='3-Way Matching',
        related='company_id.po_three_way_match', readonly=False)
