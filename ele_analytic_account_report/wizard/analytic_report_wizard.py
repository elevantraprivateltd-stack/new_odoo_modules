# -*- coding: utf-8 -*-
import base64
import io
from datetime import datetime, time

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AnalyticReportWizard(models.TransientModel):
    _name = 'analytic.report.wizard'
    _description = 'Analytic Account Report Wizard'

    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today.replace(month=1, day=1)

    date_from = fields.Date(string='Date From', required=True, default=_default_date_from)
    date_to = fields.Date(string='Date To', required=True, default=fields.Date.context_today)

    def _default_analytic_account_ids(self):
        if self._context.get('active_model') == 'account.analytic.account' and self._context.get('active_ids'):
            return [(6, 0, self._context.get('active_ids'))]
        return False

    plan_ids = fields.Many2many(
        comodel_name='account.analytic.plan',
        string='Analytic Plans / Segments',
        help='Select plans to filter analytic accounts.',
    )
    analytic_account_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Analytic Accounts',
        default=_default_analytic_account_ids,
        help='Leave empty to include all analytic accounts.',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    target_move = fields.Selection(
        selection=[
            ('posted', 'All Posted Entries'),
            ('all', 'All Entries'),
        ],
        string='Target Moves',
        default='posted',
        required=True,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise UserError(_('The "Date From" must be before the "Date To".'))

    def _get_domain(self):
        self.ensure_one()
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        if self.analytic_account_ids:
            domain.append(('account_id', 'in', self.analytic_account_ids.ids))
        elif self.plan_ids:
            domain.append(('account_id.plan_id', 'in', self.plan_ids.ids))
        if self.target_move == 'posted':
            domain.append(('move_line_id.parent_state', '=', 'posted'))
        return domain

    def _get_selected_accounts(self):
        self.ensure_one()
        if self.analytic_account_ids:
            return self.analytic_account_ids
        domain = [('company_id', '=', self.company_id.id)]
        if self.plan_ids:
            domain.append(('plan_id', 'in', self.plan_ids.ids))
        return self.env['account.analytic.account'].search(domain, order='plan_id, name')

    def _get_segment_pl_matrix(self):
        """Return one P&L column per selected analytic account."""
        self.ensure_one()
        accounts = self._get_selected_accounts()
        return accounts._get_segment_pl_matrix(
            date_from=self.date_from,
            date_to=self.date_to,
            target_move=self.target_move,
            company=self.company_id,
        )

    def _get_report_data(self):
        self.ensure_one()
        analytic_line_obj = self.env['account.analytic.line']
        lines = analytic_line_obj.search(self._get_domain(), order='account_id, date, id')

        grouped = {}
        for line in lines:
            account = line.account_id
            grouped.setdefault(account, {
                'lines': [],
                'total_debit': 0.0,
                'total_credit': 0.0,
                'total_amount': 0.0,
            })
            debit = line.amount if line.amount > 0 else 0.0
            credit = -line.amount if line.amount < 0 else 0.0
            grouped[account]['lines'].append({
                'date': line.date,
                'name': line.name or '',
                'partner': line.partner_id.display_name or '',
                'general_account': line.general_account_id.display_name or '',
                'debit': debit,
                'credit': credit,
                'amount': line.amount,
            })
            grouped[account]['total_debit'] += debit
            grouped[account]['total_credit'] += credit
            grouped[account]['total_amount'] += line.amount

        report_data = []
        for account, vals in grouped.items():
            report_data.append({
                'account': account,
                'plan': account.plan_id.display_name or _('Unassigned Segment'),
                'lines': vals['lines'],
                'total_debit': vals['total_debit'],
                'total_credit': vals['total_credit'],
                'total_amount': vals['total_amount'],
            })
        report_data.sort(key=lambda r: (r['plan'], r['account'].display_name or ''))
        return report_data

    def action_print_pdf(self):
        self.ensure_one()
        if not self._get_report_data():
            raise UserError(_('There is no analytic data for the selected filters.'))
        return self.env.ref('ele_analytic_account_report.action_report_analytic_account_pdf').report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_(
                'The "xlsxwriter" python library is required to export XLSX files. '
                'Please install it on the server with: pip install xlsxwriter'
            ))

        report_data = self._get_report_data()
        if not report_data:
            raise UserError(_('There is no analytic data for the selected filters.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Analytic Report')

        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1F4E78'})
        bold_fmt = workbook.add_format({'bold': True})
        account_fmt = workbook.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center'})
        money_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        money_bold_fmt = workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'border': 1, 'bg_color': '#F2F2F2'})
        date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        text_fmt = workbook.add_format({'border': 1})
        label_bold_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#F2F2F2'})
        pl_label_fmt = workbook.add_format({'border': 1})
        pl_bold_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#EDF2F7', 'font_color': '#1F4E78'})
        pl_money_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        pl_money_bold_fmt = workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'border': 1, 'bg_color': '#EDF2F7', 'font_color': '#1F4E78'})

        sheet.merge_range(0, 0, 0, 8, 'Analytic Account Report', title_fmt)
        sheet.write(1, 0, 'Period:', bold_fmt)
        sheet.write(1, 1, '%s  to  %s' % (self.date_from, self.date_to))
        sheet.write(2, 0, 'Company:', bold_fmt)
        sheet.write(2, 1, self.company_id.name)

        # ================================================================
        # SEGMENT-WISE P&L MATRIX — requested side-by-side layout
        # ================================================================
        matrix = self._get_segment_pl_matrix()
        row = 4
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

        headers = ['Date', 'Reference', 'Partner', 'General Account', 'Debit', 'Credit', 'Balance']
        for group in report_data:
            sheet.merge_range(row, 0, row, 6, group['account'].display_name or '', account_fmt)
            row += 1
            for col, header in enumerate(headers):
                sheet.write(row, col, header, header_fmt)
            row += 1
            for line in group['lines']:
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
                sheet.write_number(row, 6, line['debit'] - line['credit'], money_fmt)
                row += 1
            sheet.write(row, 3, 'Total', label_bold_fmt)
            sheet.write_number(row, 4, group['total_debit'], money_bold_fmt)
            sheet.write_number(row, 5, group['total_credit'], money_bold_fmt)
            sheet.write_number(row, 6, group['total_amount'], money_bold_fmt)
            row += 2

        widths = [28, 30, 22, 26, 14, 14, 14, 15, 15]
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)
        sheet.freeze_panes(6, 1)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'Analytic_Account_Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
