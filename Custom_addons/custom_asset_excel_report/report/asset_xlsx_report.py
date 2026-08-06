"""Builds the Asset Register / Asset Disposal Excel workbooks directly with
xlsxwriter, reading straight from base_accounting_kit's `account.asset.asset`
and `account.asset.depreciation.line` models (no report_xlsx dependency).
"""
import io
import logging

import xlsxwriter

_logger = logging.getLogger(__name__)

DEP_METHOD_LABELS = {
    "linear": "Linear",
    "degressive": "Degressive",
}

STATE_LABELS = {
    "draft": "Draft",
    "open": "Running",
    "paused": "Paused",
    "close": "Disposed",
    "cancelled": "Cancelled",
}

BASE_HEADERS = [
    "Sr. No.",
    "Asset ID",
    "Asset Description",
    "Asset Class",
    "Department / Cost Centre",
    "Location",
    "Custodian",
    "Supplier",
    "PO No.",
    "Invoice No.",
    "Date of Acquisition",
    "Depreciation Method",
    "Useful Life (Periods)",
    "Depreciation Rate (%)",
    "Residual Value",
    "Opening Cost",
    "Additions",
    "Disposals",
    "Closing Cost",
    "Opening Accumulated Depreciation",
    "Depreciation Charge for the Year",
    "Depreciation on Disposal",
    "Closing Accumulated Depreciation",
    "Net Book Value",
    "Revaluation Date",
    "Revaluation Adjustment",
    "Revalued Amount",
    "Impairment Loss / Reversal",
    "Asset Status",
    "Remarks",  # Index 29
]

DISPOSAL_EXTRA_HEADERS = [
    "Sale Proceeds",
    "Date of Disposal",
    "Name of Buyer",
]


def _write_date(sheet, row, col, value, date_fmt, normal_fmt):
    if value:
        sheet.write_datetime(row, col, value, date_fmt)
    else:
        sheet.write(row, col, "", normal_fmt)


def build_asset_workbook(assets, date_from=False, date_to=False, disposal=False):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    sheet = workbook.add_worksheet("Disposal Report" if disposal else "Assets")

    header_fmt = workbook.add_format(
        {
            "bold": True,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#D9D9D9",
            "text_wrap": True,
        }
    )
    normal_fmt = workbook.add_format(
        {"border": 1, "align": "center", "valign": "vcenter", "text_wrap": True}
    )
    money_fmt = workbook.add_format(
        {"border": 1, "align": "center", "num_format": "#,##0.00"}
    )
    date_fmt = workbook.add_format(
        {"border": 1, "align": "center", "num_format": "yyyy-mm-dd"}
    )

    headers = BASE_HEADERS + (DISPOSAL_EXTRA_HEADERS if disposal else [])
    for col, title in enumerate(headers):
        sheet.write(0, col, title, header_fmt)
    sheet.freeze_panes(1, 0)

    row = 1
    counter = 1

    for asset in assets:
        dep_method = (
            DEP_METHOD_LABELS.get(asset.method, asset.method)
            if 'DEP_METHOD_LABELS' in globals() and hasattr(asset, 'method')
            else getattr(asset, 'method', '')
        )
        useful_life = getattr(asset, 'method_number', 0) or 0

        if getattr(asset, 'method', False) == "linear" and useful_life:
            dep_rate = round(100.0 / float(useful_life), 2)
        else:
            dep_rate = round((getattr(asset, 'method_progress_factor', 0.0) or 0.0) * 100, 2)

        cost = asset.value or 0.0
        residual_value = asset.salvage_value or 0.0

        lines = asset.depreciation_line_ids

        # Safe date filter handling
        # Filter lines to consider only posted/posted-journal depreciation lines
        posted_lines = lines.filtered(
            lambda l: l.move_check or (l.move_id and l.move_id.state == 'posted')
        ) if lines else lines

        # 1. Opening Accumulated Depreciation Calculation
        if date_from:
            opening_accum = sum(
                posted_lines.filtered(
                    lambda l: l.depreciation_date and l.depreciation_date < date_from
                ).mapped("amount")
            ) if posted_lines else 0.0
        else:
            # Agar wizard mein start date blank ho, toh default import / initial depreciation lein
            opening_accum = getattr(asset, 'already_depreciated_amount_import', 0.0) or 0.0

        # 2. Closing Accumulated Depreciation Calculation
        if date_to:
            closing_accum = sum(
                posted_lines.filtered(
                    lambda l: l.depreciation_date and l.depreciation_date <= date_to
                ).mapped("amount")
            ) if posted_lines else 0.0
        else:
            closing_accum = sum(posted_lines.mapped("amount")) if posted_lines else 0.0

        # 3. Depreciation Charge for the Year
        dep_for_year = sum(
            posted_lines.filtered(
                lambda l: l.depreciation_date
                          and (not date_from or date_from <= l.depreciation_date)
                          and (not date_to or l.depreciation_date <= date_to)
            ).mapped("amount")
        ) if posted_lines else 0.0

        # Disposal calculations
        dep_on_disposal = 0.0
        disposals_value = 0.0

        is_disposed = asset.state == "close" or bool(getattr(asset, 'disposal_date', False))
        in_date_from = not date_from or (getattr(asset, 'disposal_date', False) and date_from <= asset.disposal_date)
        in_date_to = not date_to or (getattr(asset, 'disposal_date', False) and asset.disposal_date <= date_to)

        if is_disposed and in_date_from and in_date_to:
            if posted_lines and getattr(asset, 'disposal_date', False):
                dep_on_disposal = sum(
                    posted_lines.filtered(
                        lambda l: l.depreciation_date and l.depreciation_date <= asset.disposal_date
                    ).mapped("amount")
                )
            else:
                dep_on_disposal = closing_accum
            disposals_value = dep_on_disposal

        net_book_value = cost - closing_accum

        opening_cost = cost
        closing_cost = cost
        additions_value = (
            cost
            if (
                    asset.date
                    and date_from
                    and date_to
                    and date_from <= asset.date <= date_to
            )
            else 0.0
        )

        # PO No logic check
        po_number = getattr(asset, 'po_no', '') or ''
        if not po_number and getattr(asset, 'invoice_id', False):
            po_number = asset.invoice_id.invoice_origin or ''

        row_values = [
            counter,
            getattr(asset, 'sequence_no', '') or "",
            asset.name or "",
            asset.category_id.name if getattr(asset, 'category_id', False) else "",
            asset.department_cost_centre_id.display_name
            if getattr(asset, 'department_cost_centre_id', False)
            else "",
            getattr(asset, 'location_id', '') or "",
            getattr(asset, 'custodian', '') or "",
            asset.partner_id.name if getattr(asset, 'partner_id', False) else "",
            po_number,
            asset._get_invoice_no() if hasattr(asset, '_get_invoice_no') else "",
        ]
        for col, val in enumerate(row_values):
            sheet.write(row, col, val, normal_fmt)

        col = len(row_values)  # 10
        _write_date(sheet, row, col, asset.date, date_fmt, normal_fmt)
        col += 1  # 11
        sheet.write(row, col, dep_method, normal_fmt)
        col += 1  # 12
        sheet.write(row, col, useful_life, normal_fmt)
        col += 1  # 13
        sheet.write(row, col, dep_rate, normal_fmt)
        col += 1  # 14
        sheet.write(row, col, residual_value, money_fmt)
        col += 1  # 15
        sheet.write(row, col, opening_cost, money_fmt)
        col += 1  # 16
        sheet.write(row, col, additions_value, money_fmt)
        col += 1  # 17
        sheet.write(row, col, disposals_value, money_fmt)
        col += 1  # 18
        sheet.write(row, col, closing_cost, money_fmt)
        col += 1  # 19
        sheet.write(row, col, opening_accum, money_fmt)
        col += 1  # 20
        sheet.write(row, col, dep_for_year, money_fmt)
        col += 1  # 21
        sheet.write(row, col, dep_on_disposal, money_fmt)
        col += 1  # 22
        sheet.write(row, col, closing_accum, money_fmt)
        col += 1  # 23
        sheet.write(row, col, net_book_value, money_fmt)
        col += 1  # 24
        _write_date(sheet, row, col, getattr(asset, 'revaluation_date', False), date_fmt, normal_fmt)
        col += 1  # 25
        sheet.write(row, col, getattr(asset, 'revaluation_adjustment', 0.0) or 0.0, money_fmt)
        col += 1  # 26
        sheet.write(row, col, getattr(asset, 'revalued_amount', 0.0) or 0.0, money_fmt)
        col += 1  # 27
        sheet.write(row, col, getattr(asset, 'impairment_amount', 0.0) or 0.0, money_fmt)
        col += 1  # 28
        state_val = STATE_LABELS.get(asset.state, asset.state) if 'STATE_LABELS' in globals() else asset.state
        sheet.write(row, col, state_val or "", normal_fmt)
        col += 1  # 29

        # FIXED: Added Remark custom field here
        remarks_val = getattr(asset, 'remark', False) or getattr(asset, 'note', '') or ""
        sheet.write(row, col, remarks_val, normal_fmt)
        col += 1  # 30

        if disposal:
            sheet.write(row, col, getattr(asset, 'sale_proceeds', 0.0) or 0.0, money_fmt)
            col += 1
            _write_date(sheet, row, col, getattr(asset, 'disposal_date', False), date_fmt, normal_fmt)
            col += 1
            sheet.write(row, col, getattr(asset, 'buyer_name', '') or "", normal_fmt)
            col += 1

        row += 1
        counter += 1

    sheet.set_column("A:A", 8)
    sheet.set_column("B:B", 15)
    sheet.set_column("C:C", 35)
    sheet.set_column("D:D", 25)
    sheet.set_column("E:E", 35)
    sheet.set_column("F:F", 20)
    sheet.set_column("G:G", 20)
    sheet.set_column("H:H", 25)
    sheet.set_column("I:I", 18)
    sheet.set_column("J:J", 18)
    sheet.set_column("K:AD", 20)
    if disposal:
        sheet.set_column("AE:AG", 18)

    workbook.close()
    output.seek(0)
    return output.getvalue()


def _write_date(sheet, row, col, date_val, date_fmt, normal_fmt):
    if not date_val:
        sheet.write(row, col, "", normal_fmt)
        return
    # Agar Odoo string date bhej raha hai to safely string hi write kar dein
    if isinstance(date_val, str):
        sheet.write(row, col, date_val, normal_fmt)
    else:
        try:
            sheet.write_datetime(row, col, date_val, date_fmt)
        except Exception:
            sheet.write(row, col, str(date_val), normal_fmt)
