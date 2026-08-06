from odoo import fields, models


class AssetDispose(models.TransientModel):
    _inherit = "asset.dispose"

    buyer_name = fields.Char(
        string="Name of Buyer",
        help="Only relevant when Disposal Type is 'Sale'.",
    )

    def action_dispose(self):
        self.ensure_one()
        sale_value = self.sale_value if self.disposal_type == "sale" else 0.0
        sale_account = self.sale_account_id if self.disposal_type == "sale" else False
        move = self.asset_id._dispose(
            self.date,
            sale_value=sale_value,
            sale_account=sale_account,
            buyer_name=self.buyer_name if self.disposal_type == "sale" else "",
        )
        return {
            "name": "Disposal Entry",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
            "target": "current",
        }
