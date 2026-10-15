from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def action_duplicate_company_setup(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Company Master Data Clone",
            "res_model": "company.duplicate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_source_company_id": self.id,
            },
        }
