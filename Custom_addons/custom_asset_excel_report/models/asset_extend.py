import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Relative import (Crucial for Odoo module loading)
from ..report.asset_xlsx_report import build_asset_workbook

_logger = logging.getLogger(__name__)


class AccountAssetAsset(models.Model):
    _inherit = "account.asset.asset"

    # ---------------- CUSTOM IDENTIFICATION / TRACKING FIELDS ----------------
    sequence_no = fields.Char(
        string="Asset ID", readonly=True, copy=False, default=lambda self: _("New")
    )
    department_cost_centre_id = fields.Many2one(
        "hr.department", string="Department / Cost Centre"
    )
    location_id = fields.Char(string="Location")
    custodian = fields.Char(string="Custodian")
    remark = fields.Text(string="Remarks")
    po_no = fields.Char(
        string="PO No.",
        compute="_compute_po_no",
        store=True,
        readonly=False  # User manual override bhi kar sake agar zaroorat ho
    )

    invoice_no = fields.Char(
        string="Invoice No.",
        help="Leave blank to use the linked Invoice's number automatically.",
    )

    # ---------------- DISPOSAL TRACKING ----------------
    disposal_date = fields.Date(string="Date of Disposal", readonly=True, copy=False)
    sale_proceeds = fields.Monetary(string="Sale Proceeds", readonly=True, copy=False)
    buyer_name = fields.Char(string="Name of Buyer", readonly=True, copy=False)

    # ---------------- REVALUATION TRACKING ----------------
    revaluation_date = fields.Date(string="Revaluation Date", readonly=True, copy=False)
    revaluation_adjustment = fields.Monetary(
        string="Revaluation Adjustment", readonly=True, copy=False,
        help="Sum of all revaluation increases applied to this asset.",
    )
    revalued_amount = fields.Monetary(
        string="Revalued Amount", readonly=True, copy=False,
        help="Asset's Gross Value after the most recent revaluation.",
    )
    impairment_amount = fields.Monetary(
        string="Impairment Loss / Reversal", default=0.0,
        help="Enter manually if this asset had an impairment loss/reversal in the period.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("sequence_no", _("New")) == _("New"):
                vals["sequence_no"] = (
                        self.env["ir.sequence"].next_by_code(
                            "account.asset.custom.sequence"
                        )
                        or _("New")
                )
        return super().create(vals_list)

    def _dispose(self, disposal_date, sale_value=0.0, sale_account=None, buyer_name=None):
        """Extend base_accounting_kit's disposal to also stamp details on the asset record."""
        move = super()._dispose(
            disposal_date, sale_value=sale_value, sale_account=sale_account
        )
        self.write(
            {
                "disposal_date": disposal_date,
                "sale_proceeds": sale_value or 0.0,
                "buyer_name": buyer_name or "",
            }
        )
        return move

    def _revaluate(self, amount, date, account):
        """Extend base_accounting_kit revaluation to store revaluation details."""
        if hasattr(date, 'strftime'):
            date = date.strftime('%Y-%m-%d')

        move = super()._revaluate(amount, date, account)

        for asset in self:
            asset.write({
                'revaluation_date': date,
                'revaluation_adjustment': (asset.revaluation_adjustment or 0.0) + amount,
                'revalued_amount': asset.value + amount,
            })

        return move

    def _get_invoice_no(self):
        self.ensure_one()
        if self.invoice_no:
            return self.invoice_no
        return self.invoice_id.name or "" if self.invoice_id else ""

    @api.depends('invoice_id', 'invoice_id.invoice_origin')
    def _compute_po_no(self):
        for asset in self:
            if asset.invoice_id and asset.invoice_id.invoice_origin:
                asset.po_no = asset.invoice_id.invoice_origin
            else:
                asset.po_no = False

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id:
            # Vendor / Partner set karein
            self.partner_id = self.invoice_id.partner_id or False
            # PO Number / Origin set karein
            self.po_no = self.invoice_id.invoice_origin or False
        else:
            # Agar invoice unselect ho jaye to dono fields reset ho jayein
            self.partner_id = False
            self.po_no = False





    #invoice vendor automation in asset model
    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        if self.invoice_id and self.invoice_id.partner_id:
            # Invoice ka partner, form ki partner_id field me set hoga
            self.partner_id = self.invoice_id.partner_id
        else:
            self.partner_id = False


    # ---------------- REPORT ACTION METHODS ----------------

    def action_print_excel_report(self):
        """Fixed Asset Excel Report"""
        return self._generate_excel_report(disposal=False)

    def action_print_disposal_excel_report(self):
        """Asset Disposal Excel Report with detailed error logging"""
        try:
            return self._generate_excel_report(disposal=True)
        except Exception as e:
            _logger.error("Disposal Excel Print Failed: %s", str(e), exc_info=True)
            raise UserError(_("Disposal Report Error: %s") % str(e))

    def _generate_excel_report(self, disposal=False):
        assets = self

        if disposal:
            # Sirf disposed assets
            assets = assets.filtered(lambda a: a.state == "close")

            if not assets:
                raise UserError(_("Please select at least one disposed asset."))

        xlsx_bytes = build_asset_workbook(
            assets,
            date_from=None,
            date_to=None,
            disposal=disposal,
        )

        attachment = self.env["ir.attachment"].create({
            "name": "Asset_Disposal_Report.xlsx" if disposal else "Asset_Report.xlsx",
            "type": "binary",
            "datas": base64.b64encode(xlsx_bytes),
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }
