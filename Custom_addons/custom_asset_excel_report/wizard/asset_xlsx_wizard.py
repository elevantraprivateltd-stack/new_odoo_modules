import base64
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..report.asset_xlsx_report import build_asset_workbook

_logger = logging.getLogger(__name__)


class AssetReportWizard(models.TransientModel):
    _name = "asset.report.wizard"
    _description = "Asset Excel Report Wizard"

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

        domain = []

        if self.date_from:
            domain.append(("date", ">=", self.date_from))

        if self.date_to:
            domain.append(("date", "<=", self.date_to))

        # FIX 1: Model name corrected to account.asset.asset
        assets = self.env["account.asset.asset"].search(domain)

        if not assets:
            raise UserError(_("No asset records found in the selected date range."))

        _logger.info("Assets Found: %s", len(assets))

        xlsx_bytes = build_asset_workbook(
            assets,
            self.date_from,
            self.date_to,
            disposal=False,
        )

        _logger.info("Workbook created successfully | Size: %s", len(xlsx_bytes))

        attachment_name = (
            f"Asset_Report_{assets[0].name}.xlsx"
            if len(assets) == 1
            else "Asset_Register_Report.xlsx"
        )

        # FIX 2: res_model & res_id mapped to wizard instance (self)
        attachment = self.env["ir.attachment"].create({
            "name": attachment_name,
            "type": "binary",
            "datas": base64.b64encode(xlsx_bytes),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        _logger.info("Attachment ID: %s", attachment.id)

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
