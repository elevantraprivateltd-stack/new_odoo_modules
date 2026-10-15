import base64
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..report.asset_xlsx_report import build_asset_workbook

_logger = logging.getLogger(__name__)


class AssetDisposalReportWizard(models.TransientModel):
    _name = "asset.disposal.report.wizard"
    _description = "Asset Disposal Excel Report Wizard"

    date_from = fields.Date(
        string="Start Date",
        required=False,
        default=lambda self: fields.Date.context_today(self),
    )

    date_to = fields.Date(
        string="End Date",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    def action_print_report(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_("Start Date must be before End Date."))

        domain = [
            ("active", "in", [True, False]),
            ("state", "=", "close"),
        ]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))

        assets = self.env["account.asset.asset"].search(domain)
        if not assets:
            raise UserError(_("No disposed assets found in the selected date range."))

        xlsx_bytes = build_asset_workbook(
            assets,
            self.date_from,
            self.date_to,
            disposal=True,
        )

        attachment = self.env["ir.attachment"].create(
            {
                "name": "Asset_Disposal_Report.xlsx",
                "type": "binary",
                "datas": base64.b64encode(xlsx_bytes),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": (
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet"
                ),
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }
