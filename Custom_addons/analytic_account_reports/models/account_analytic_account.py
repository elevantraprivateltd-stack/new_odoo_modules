# -*- coding: utf-8 -*-
import base64
import io

from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # -------------------------------------------------------------------
    # Data computation
    # -------------------------------------------------------------------
    def _get_analytic_report_data(self):
        """Return a dict with the detail lines, the totals and the actual
        date range covered by the data, for this single analytic account.
        No date filter is applied on purpose: the report always shows the
        complete, up to date picture for the account, and the period
        shown in the header is simply the earliest/latest transaction
        date found."""
        self.ensure_one()
        analytic_line_obj = self.env['account.analytic.line']
        lines = analytic_line_obj.search(
            [('account_id', '=', self.id)],
            order='date, id',
        )

        data_lines = []
        total_debit = 0.0
        total_credit = 0.0
        total_amount = 0.0
        dates = []

        for line in lines:
            debit = line.amount if line.amount > 0 else 0.0
            credit = -line.amount if line.amount < 0 else 0.0
            data_lines.append({
                'date': line.date,
                'name': line.name or '',
                'partner': line.partner_id.display_name or '',
                'general_account': line.general_account_id.display_name or '',
                'debit': debit,
                'credit': credit,
                'balance': debit - credit,
            })
            total_debit += debit
            total_credit += credit
            total_amount += line.amount
            if line.date:
                dates.append(line.date)

        return {
            'lines': data_lines,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_amount': total_amount,
            'date_from': min(dates) if dates else False,
            'date_to': max(dates) if dates else False,
            'count': len(data_lines),
            'segment': self.plan_id.display_name or '-',
            'pl_summary': self._get_segment_pl_data(),
            'budget_items': self._get_budget_items_data(),
            'generated_on': fields.Date.context_today(self),
        }

    def _get_budget_items_data(self):
        """Return the Budget Items (Budgetary Position, Start/End Date,
        Paid Date, Planned/Practical/Theoretical amounts, Achievement %)
        linked to this analytic account.

        This relies on the optional Budget Management feature
        (crossovered.budget.lines / the 'crossovered_budget_line' field on
        account.analytic.account). If that feature is not installed on
        this database, this simply returns an empty list instead of
        raising an error, so the report always works either way."""
        self.ensure_one()
        if 'crossovered_budget_line' not in self._fields:
            return []

        try:
            budget_lines = self.crossovered_budget_line
        except Exception:
            return []

        data = []
        for bline in budget_lines:
            data.append({
                'budget': bline.crossovered_budget_id.name or '',
                'budgetary_position': bline.general_budget_id.name or '',
                'date_from': getattr(bline, 'date_from', False),
                'date_to': getattr(bline, 'date_to', False),
                'paid_date': getattr(bline, 'paid_date', False),
                'planned_amount': getattr(bline, 'planned_amount', 0.0) or 0.0,
                'practical_amount': getattr(bline, 'practical_amount', 0.0) or 0.0,
                'theoretical_amount': getattr(bline, 'theoritical_amount', 0.0) or 0.0,
                'percentage': getattr(bline, 'percentage', 0.0) or 0.0,
            })
        return data

    # -------------------------------------------------------------------      <<< NEW METHOD BLOCK STARTS HERE
    # Profit & Loss flow for this analytic account (segment)
    # -------------------------------------------------------------------
    def _get_segment_pl_data(self):
        """Return the full Profit & Loss flow (Revenue -> Cost of Revenue
        -> Gross Profit -> Operating Expenses -> Operating Income ->
        Other Income -> Other Expenses -> Net Profit) for this single
        analytic account, based on posted journal items whose analytic
        distribution includes this account. No date filter, same as the
        rest of this report: always the complete up-to-date picture."""
        self.ensure_one()
        # Adjust this mapping if your Chart of Accounts uses different
        # account_type values.
        TYPE_CATEGORY_MAP = {
            'income': 'revenue',
            'income_other': 'other_income',
            'expense_direct_cost': 'cost_of_revenue',
            'expense': 'operating_expenses',
            'expense_depreciation': 'other_expenses',
        }
        INCOME_CATEGORIES = ('revenue', 'other_income')
        domain = [
            ('parent_state', '=', 'posted'),
            ('analytic_distribution', '!=', False),
            ('account_id.account_type', 'in', list(TYPE_CATEGORY_MAP.keys())),
        ]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        move_lines = self.env['account.move.line'].search(domain)
        values = {
            'revenue': 0.0, 'cost_of_revenue': 0.0, 'operating_expenses': 0.0,
            'other_income': 0.0, 'other_expenses': 0.0,
        }
        for line in move_lines:
            category = TYPE_CATEGORY_MAP.get(line.account_id.account_type)
            if not category:
                continue
            distribution = line.analytic_distribution or {}
            percentage = None
            for key, pct in distribution.items():
                try:
                    ids_in_key = [int(x) for x in str(key).split(',')]
                except ValueError:
                    continue
                if self.id in ids_in_key:
                    percentage = pct
                    break
            if percentage is None:
                continue
            line_amount = (line.credit - line.debit) if category in INCOME_CATEGORIES \
                else (line.debit - line.credit)
            values[category] += line_amount * (percentage / 100.0)
        gross_profit = values['revenue'] - values['cost_of_revenue']
        operating_income = gross_profit - values['operating_expenses']
        net_profit = operating_income + values['other_income'] - values['other_expenses']
        return [
            {'label': _('Revenue'), 'value': values['revenue'], 'bold': False},
            {'label': _('Less Cost of Revenue'), 'value': values['cost_of_revenue'], 'bold': False},
            {'label': _('Gross Profit'), 'value': gross_profit, 'bold': True},
            {'label': _('Less Operating Expenses'), 'value': values['operating_expenses'], 'bold': False},
            {'label': _('Operating Income (or Loss)'), 'value': operating_income, 'bold': True},
            {'label': _('Plus Other Income'), 'value': values['other_income'], 'bold': False},
            {'label': _('Less Other Expenses'), 'value': values['other_expenses'], 'bold': False},
            {'label': _('Net Profit'), 'value': net_profit, 'bold': True},
        ]

    # -------------------------------------------------------------------      <<< NEW METHOD BLOCK ENDS HERE

    # -------------------------------------------------------------------
    # Actions (bound directly on the record, shown under "Print")
    # -------------------------------------------------------------------
    def action_print_analytic_pdf_report(self):
        if not self:
            raise UserError(_('Please select at least one Analytic Account.'))
        return self.env.ref(
            'analytic_account_reports.action_report_analytic_account_direct_pdf'
        ).report_action(self)

    def action_export_analytic_excel_report(self):
        if not self:
            raise UserError(_('Please select at least one Analytic Account.'))
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_(
                'The "xlsxwriter" python library is required to export XLSX '
                'files. Please install it on the server with: '
                'pip install xlsxwriter'
            ))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Analytic Report')

        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 14, 'font_color': '#1F4E78',
        })
        sub_fmt = workbook.add_format({'italic': True, 'font_color': '#666666'})
        account_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white',
            'font_size': 11, 'border': 1,
        })
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center',
        })
        money_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        money_bold_fmt = workbook.add_format({
            'num_format': '#,##0.00', 'bold': True, 'border': 1, 'bg_color': '#F2F2F2',
        })
        date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        text_fmt = workbook.add_format({'border': 1})
        label_bold_fmt = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#F2F2F2',
        })
        pct_fmt = workbook.add_format({'num_format': '0.00"%"', 'border': 1})
        pl_label_fmt = workbook.add_format({'border': 1})
        pl_bold_fmt = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#EDF2F7', 'font_color': '#1F4E78',
        })
        pl_money_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        pl_money_bold_fmt = workbook.add_format({
            'num_format': '#,##0.00', 'bold': True, 'border': 1,
            'bg_color': '#EDF2F7', 'font_color': '#1F4E78',
        })

        sheet.merge_range(0, 0, 0, 8, 'Analytic Account Report', title_fmt)
        row = 2
        headers = ['Date', 'Reference', 'Partner', 'General Account', 'Debit', 'Credit', 'Balance']
        budget_headers = [
            'Budget', 'Budgetary Position', 'Start Date', 'End Date', 'Paid Date',
            'Planned Amount', 'Practical Amount', 'Theoretical Amount', 'Achievement (%)',
        ]

        for account in self:
            data = account._get_analytic_report_data()

            sheet.merge_range(row, 0, row, 8, account.display_name or '', account_fmt)
            row += 1

            period_text = 'Period: %s  to  %s' % (
                data['date_from'] or '-', data['date_to'] or '-',
            )
            sheet.merge_range(row, 0, row, 2, period_text, sub_fmt)
            sheet.write(row, 3, 'Segment:', label_bold_fmt)
            sheet.write(row, 4, data['segment'], text_fmt)
            row += 1
            sheet.write(row, 3, 'Total Entries:', label_bold_fmt)
            sheet.write(row, 4, data['count'])
            row += 2

            if not data['lines']:
                sheet.merge_range(
                    row, 0, row, 6,
                    'No analytic transactions found for this account.',
                    sub_fmt,
                )
                row += 1
            else:
                for line in data['lines']:
                    if line['date']:
                        sheet.write_datetime(row, 0, line['date'], date_fmt)
                    else:
                        sheet.write(row, 0, '', text_fmt)
                    sheet.write(row, 1, line['name'], text_fmt)
                    sheet.write(row, 2, line['partner'], text_fmt)
                    sheet.write(row, 3, line['general_account'], text_fmt)
                    sheet.write_number(row, 4, line['debit'], money_fmt)
                    sheet.write_number(row, 5, line['credit'], money_fmt)
                    sheet.write_number(row, 6, line['balance'], money_fmt)
                    row += 1
            sheet.write(row, 3, 'Total', label_bold_fmt)
            sheet.write_number(row, 4, data['total_debit'], money_bold_fmt)
            sheet.write_number(row, 5, data['total_credit'], money_bold_fmt)
            sheet.write_number(row, 6, data['total_amount'], money_bold_fmt)
            row += 2

            # ---- Profit & Loss Summary (segment flow) ----
            # ---- Profit & Loss Summary (segment flow) ----
            sheet.merge_range(
                row, 0, row, 8,
                'Profit & Loss Summary - %s' % (data['segment'],), account_fmt,
            )
            row += 1
            for pl_row in data['pl_summary']:
                fmt_label = pl_bold_fmt if pl_row['bold'] else pl_label_fmt
                fmt_money = pl_money_bold_fmt if pl_row['bold'] else pl_money_fmt
                sheet.merge_range(row, 0, row, 6, pl_row['label'], fmt_label)
                sheet.write_number(row, 7, pl_row['value'], fmt_money)
                row += 1
            row += 1

            # ---- Budget Items (only shown when Budget Management data exists) ----

            # ---- Budget Items (only shown when Budget Management data exists) ----
            if data['budget_items']:
                sheet.merge_range(
                    row, 0, row, 8, 'Budget Items', account_fmt,
                )
                row += 1
                for col, header in enumerate(budget_headers):
                    sheet.write(row, col, header, header_fmt)
                row += 1
                for bitem in data['budget_items']:
                    sheet.write(row, 0, bitem['budget'], text_fmt)
                    sheet.write(row, 1, bitem['budgetary_position'], text_fmt)
                    if bitem['date_from']:
                        sheet.write_datetime(row, 2, bitem['date_from'], date_fmt)
                    else:
                        sheet.write(row, 2, '', text_fmt)
                    if bitem['date_to']:
                        sheet.write_datetime(row, 3, bitem['date_to'], date_fmt)
                    else:
                        sheet.write(row, 3, '', text_fmt)
                    if bitem['paid_date']:
                        sheet.write_datetime(row, 4, bitem['paid_date'], date_fmt)
                    else:
                        sheet.write(row, 4, '', text_fmt)
                    sheet.write_number(row, 5, bitem['planned_amount'], money_fmt)
                    sheet.write_number(row, 6, bitem['practical_amount'], money_fmt)
                    sheet.write_number(row, 7, bitem['theoretical_amount'], money_fmt)
                    sheet.write_number(row, 8, bitem['percentage'], pct_fmt)
                    row += 1
                row += 1

            row += 1

        widths = [14, 30, 20, 24, 13, 13, 13, 15, 15]
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        filename = (
            'Analytic_Account_Report_%s.xlsx' % (self[0].name or self[0].id)
            if len(self) == 1 else 'Analytic_Account_Report.xlsx'
        )

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.ids[0],
            'mimetype': (
                'application/vnd.openxmlformats-officedocument'
                '.spreadsheetml.sheet'
            ),
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
