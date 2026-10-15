from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    report_header_icon = fields.Binary(string="Report Header Icon", attachment=True)

    engagement_letter_html = fields.Html(
        string='Engagement Letter Content',
        translate=True,
        default="""
                <p><strong>To,</strong></p>
                <p>The Management,</p>
                <br/>
                <p>We are pleased to confirm our acceptance of this engagement...</p>
            """
    )

    # Header button click hone par report trigger karne ka function
    def action_print_engagement_letter(self):
        return self.env.ref('sales_order_template_manager.action_report_engagement_letter').report_action(self)
