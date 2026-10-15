# -*- coding: utf-8 -*-
import base64
import io
from collections import OrderedDict
from datetime import datetime, time

from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    TYPE_CATEGORY_MAP = {
        'income': 'revenue',
        'income_other': 'other_income',
        'expense_direct_cost': 'cost_of_revenue',
        'expense': 'operating_expenses',
        'expense_depreciation': 'other_expenses',
    }
    INCOME_CATEGORIES = ('revenue', 'other_income')

    # -------------------------------------------------------------------
    # Shared Profit & Loss / Segment matrix
    # -------------------------------------------------------------------
    def _get_segment_pl_matrix(self, date_from=False, date_to=False,
                               target_move='posted', company=False):
        """Build the requested side-by-side P&L matrix.

        Each analytic account is one report column.  The analytic plan is
        shown as the account's segment/plan context, but accounts are never
        collapsed into a single plan column.

        Example:
            Particulars | Segment 1 | Segment 2 | Segment 3
            Revenue     | ...        | ...        | ...
            Expense     | ...        | ...        | ...
            Profit/Loss | ...        | ...        | ...

        ``self`` may contain one or many analytic accounts.
        """
        accounts = self.exists()
        if not accounts:
            return {'segments': [], 'rows': []}

        company = company or accounts[:1].company_id or self.env.company
        account_ids = set(accounts.ids)

        # One column per analytic account, stable by plan then account name.
        ordered_accounts = accounts.sorted(
            key=lambda a: (
                a.plan_id.display_name if a.plan_id else _('Unassigned Segment'),
                a.display_name or '',
                a.id,
            )
        )
        segments = [
            {
                'id': account.id,
                'name': account.display_name or _('Unnamed Segment'),
                'plan': account.plan_id.display_name if account.plan_id else _('Unassigned Segment'),
            }
            for account in ordered_accounts
        ]

        domain = [
            ('analytic_distribution', '!=', False),
            ('account_id.account_type', 'in', list(self.TYPE_CATEGORY_MAP.keys())),
            ('company_id', '=', company.id),
        ]
        if target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        move_lines = self.env['account.move.line'].search(domain)

        values = {
            account.id: {'revenue': 0.0, 'expense': 0.0}
            for account in ordered_accounts
        }

        for line in move_lines:
            category = self.TYPE_CATEGORY_MAP.get(line.account_id.account_type)
            if not category:
                continue

            distribution = line.analytic_distribution or {}
            matched_percentages = {}

            # Odoo analytic_distribution keys can contain comma-separated
            # analytic account IDs.  Keep each selected account independent.
            for key, pct in distribution.items():
                try:
                    ids_in_key = [
                        int(x.strip()) for x in str(key).split(',')
                        if x.strip()
                    ]
                except (TypeError, ValueError):
                    continue

                percentage = float(pct or 0.0)
                for account_id in ids_in_key:
                    if account_id in account_ids:
                        # If the same account appears in more than one key,
                        # add the allocations rather than dropping them.
                        matched_percentages[account_id] = (
                            matched_percentages.get(account_id, 0.0) + percentage
                        )

            for account_id, percentage in matched_percentages.items():
                amount = (
                    (line.credit - line.debit)
                    if category in self.INCOME_CATEGORIES
                    else (line.debit - line.credit)
                ) * (percentage / 100.0)

                if category in self.INCOME_CATEGORIES:
                    values[account_id]['revenue'] += amount
                else:
                    values[account_id]['expense'] += amount

        rows = [
            {
                'label': _('Revenue'),
                'values': [values[a.id]['revenue'] for a in ordered_accounts],
                'bold': False,
            },
            {
                'label': _('Expense'),
                'values': [values[a.id]['expense'] for a in ordered_accounts],
                'bold': False,
            },
            {
                'label': _('Profit/Loss'),
                'values': [
                    values[a.id]['revenue'] - values[a.id]['expense']
                    for a in ordered_accounts
                ],
                'bold': True,
            },
        ]
        return {'segments': segments, 'rows': rows}

    # -------------------------------------------------------------------
    # Data computation for a single analytic account
    # -------------------------------------------------------------------
    def _get_analytic_report_data(self):
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

        segment_matrix = self._get_segment_pl_matrix(
            target_move='posted',
            company=self.company_id,
        )

        return {
            'lines': data_lines,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_amount': total_amount,
            'date_from': min(dates) if dates else False,
            'date_to': max(dates) if dates else False,
            'count': len(data_lines),
            'segment': self.plan_id.display_name or '-',
            'segment_matrix': segment_matrix,
            'pl_summary': self._get_segment_pl_data(),
            'budget_items': self._get_budget_items_data(),
            'generated_on': fields.Date.context_today(self),
        }

    def _get_budget_items_data(self):
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

    # -------------------------------------------------------------------
    # Legacy detailed P&L for the single-account section
    # -------------------------------------------------------------------
    def _get_segment_pl_data(self):
        self.ensure_one()
        domain = [
            ('parent_state', '=', 'posted'),
            ('analytic_distribution', '!=', False),
            ('account_id.account_type', 'in', list(self.TYPE_CATEGORY_MAP.keys())),
        ]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        move_lines = self.env['account.move.line'].search(domain)
        values = {
            'revenue': 0.0,
            'cost_of_revenue': 0.0,
            'operating_expenses': 0.0,
            'other_income': 0.0,
            'other_expenses': 0.0,
        }
        for line in move_lines:
            category = self.TYPE_CATEGORY_MAP.get(line.account_id.account_type)
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
            line_amount = ((line.credit - line.debit)
                           if category in self.INCOME_CATEGORIES
                           else (line.debit - line.credit))
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

    # -------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------
    def action_print_analytic_pdf_report(self):
        if not self:
            raise UserError(_('Please select at least one Analytic Account.'))
        return self.env.ref(
            'ele_analytic_account_report.action_report_analytic_account_direct_pdf'
        ).report_action(self)

    def action_export_analytic_excel_report(self):
        if not self:
            raise UserError(_('Please select at least one Analytic Account.'))
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_(
                'The "xlsxwriter" python library is required to export XLSX '
                'files. Please install it on the server with: pip install xlsxwriter'
            ))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Analytic Report')

        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1F4E78'})
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
        label_bold_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#F2F2F2'})
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

        # ================================================================
        # SEGMENT-WISE P&L MATRIX — the requested layout
        # ================================================================
        matrix = self._get_segment_pl_matrix(
            target_move='posted',
            company=self[:1].company_id if self else self.env.company,
        )
        segment_count = len(matrix['segments'])
        last_col = max(segment_count, 1)
        sheet.merge_range(row, 0, row, last_col, 'Segment-wise Profit & Loss', account_fmt)
        row += 1
        sheet.write(row, 0, 'Particulars', header_fmt)
        for idx, segment in enumerate(matrix['segments'], start=1):
            sheet.write(row, idx, segment['name'], header_fmt)
        row += 1
        for pl_row in matrix['rows']:
            fmt_label = pl_bold_fmt if pl_row['bold'] else pl_label_fmt
            fmt_money = pl_money_bold_fmt if pl_row['bold'] else pl_money_fmt
            sheet.write(row, 0, pl_row['label'], fmt_label)
            for idx, value in enumerate(pl_row['values'], start=1):
                sheet.write_number(row, idx, value, fmt_money)
            row += 1
        row += 2

        # ================================================================
        # ACCOUNT DETAIL
        # ================================================================
        headers = ['Date', 'Reference', 'Partner', 'General Account', 'Debit', 'Credit', 'Balance']
        budget_headers = [
            'Budget', 'Budgetary Position', 'Start Date', 'End Date', 'Paid Date',
            'Planned Amount', 'Practical Amount', 'Theoretical Amount', 'Achievement (%)',
        ]

        for account in self:
            data = account._get_analytic_report_data()
            sheet.merge_range(row, 0, row, 8, account.display_name or '', account_fmt)
            row += 1
            period_text = 'Period: %s  to  %s' % (data['date_from'] or '-', data['date_to'] or '-')
            sheet.merge_range(row, 0, row, 2, period_text, sub_fmt)
            sheet.write(row, 3, 'Segment:', label_bold_fmt)
            sheet.write(row, 4, data['segment'], text_fmt)
            row += 1
            sheet.write(row, 3, 'Total Entries:', label_bold_fmt)
            sheet.write(row, 4, data['count'])
            row += 2

            if not data['lines']:
                sheet.merge_range(row, 0, row, 6,
                                  'No analytic transactions found for this account.', sub_fmt)
                row += 1
            else:
                for line in data['lines']:
                    if line['date']:
                        dt = datetime.combine(line['date'], time.min) if not isinstance(line['date'], datetime) else line['date']
                        sheet.write_datetime(row, 0, dt, date_fmt)
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

            # Keep the detailed single-account P&L as additional information.
            sheet.merge_range(row, 0, row, 8,
                              'Detailed P&L - %s' % data['segment'], account_fmt)
            row += 1
            for pl_row in data['pl_summary']:
                fmt_label = pl_bold_fmt if pl_row['bold'] else pl_label_fmt
                fmt_money = pl_money_bold_fmt if pl_row['bold'] else pl_money_fmt
                sheet.merge_range(row, 0, row, 6, pl_row['label'], fmt_label)
                sheet.write_number(row, 7, pl_row['value'], fmt_money)
                row += 1
            row += 1

            if data['budget_items']:
                sheet.merge_range(row, 0, row, 8, 'Budget Items', account_fmt)
                row += 1
                for col, header in enumerate(budget_headers):
                    sheet.write(row, col, header, header_fmt)
                row += 1
                for bitem in data['budget_items']:
                    sheet.write(row, 0, bitem['budget'], text_fmt)
                    sheet.write(row, 1, bitem['budgetary_position'], text_fmt)
                    for col, key in ((2, 'date_from'), (3, 'date_to'), (4, 'paid_date')):
                        value = bitem[key]
                        if value:
                            dt = datetime.combine(value, time.min) if not isinstance(value, datetime) else value
                            sheet.write_datetime(row, col, dt, date_fmt)
                        else:
                            sheet.write(row, col, '', text_fmt)
                    sheet.write_number(row, 5, bitem['planned_amount'], money_fmt)
                    sheet.write_number(row, 6, bitem['practical_amount'], money_fmt)
                    sheet.write_number(row, 7, bitem['theoretical_amount'], money_fmt)
                    sheet.write_number(row, 8, bitem['percentage'], pct_fmt)
                    row += 1
                row += 1
            row += 1

        widths = [26, 30, 22, 26, 14, 14, 14, 15, 15]
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)
        sheet.freeze_panes(3, 1)

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
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
