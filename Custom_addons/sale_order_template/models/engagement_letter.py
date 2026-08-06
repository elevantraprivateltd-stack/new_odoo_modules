# models/res_company.py
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    engagement_letter_header_image = fields.Binary(
        string="Engagement Letter Header Image",
        help="Full-width letterhead header image (recommended width ~1000px)."
    )
    engagement_letter_footer_image = fields.Binary(
        string="Engagement Letter Footer Image",
        help="Full-width letterhead footer image (recommended width ~1000px)."
    )






# models/res_config_settings.py


# class ResConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'
#
#     engagement_letter_header_image = fields.Binary(
#         related='company_id.engagement_letter_header_image', readonly=False)
#     engagement_letter_footer_image = fields.Binary(
#         related='company_id.engagement_letter_footer_image', readonly=False)