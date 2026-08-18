# models/sale_order.py
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    print_engagement_header_footer = fields.Boolean(
        string="Print with Header/Footer",
        default=True,
        help="Agar ye checked hai to Engagement Letter report company ka "
             "existing (default) header/footer use karega. Agar uncheck "
             "hai to sirf plain content print hoga, bina header/footer ke."
    )






# models/res_config_settings.py


# class ResConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'
#
#     engagement_letter_header_image = fields.Binary(
#         related='company_id.engagement_letter_header_image', readonly=False)
#     engagement_letter_footer_image = fields.Binary(
#         related='company_id.engagement_letter_footer_image', readonly=False)