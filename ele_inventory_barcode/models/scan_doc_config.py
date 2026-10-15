# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ScanDocConfig(models.Model):
    _name = 'scan.doc.config'
    _description = 'Doc Scan Settings'

    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company,
                                 ondelete='cascade')
    customer_id = fields.Many2one(
        'res.partner', string='Customer for scanned sales',
        help='Every Stock OUT scan is sold to this customer on a Sales Order.')
    auto_invoice = fields.Boolean(
        string='Create & post the invoice automatically',
        help='When a Stock OUT batch is finished, also create and confirm the customer invoice '
             '(this updates accounting: receivable and income).')
    idle_minutes = fields.Integer(
        string='Auto-finish after (minutes)', default=10,
        help='A batch nobody scanned into for this many minutes is finished automatically '
             '(Receipt validated / Sales Order confirmed and delivered).')

    receipt_account_id = fields.Many2one(
        'account.account', string='Account credited when stock comes in',
        domain=[('account_type', 'not in', ('asset_receivable', 'liability_payable',
                                            'asset_cash', 'liability_credit_card'))],
        help='Every IN Receipt posts: Debit Stock Valuation, Credit this account. '
             'For goods you make yourself use e.g. "Stock Variation" or "Cost of Production".')

    sale_account_id = fields.Many2one(
        'account.account', string='Account credited when stock goes out (Sale)',
        domain=[('account_type', 'in', ('income', 'income_other'))],
        help='Every OUT sale invoice posts: Debit Receivable, Credit this income account. '
             'If empty, the normal income account of each product is used.')

    _company_uniq = models.Constraint('unique(company_id)', 'Only one setting record per company.')

    @api.model
    def get_config(self):
        company = self.env.company
        cfg = self.sudo().search([('company_id', '=', company.id)], limit=1)
        if not cfg:
            cfg = self.sudo().create({'company_id': company.id})
        if not cfg.customer_id:
            cfg.customer_id = self.env['res.partner'].sudo().create({
                'name': 'Walk-in Customer',
                'company_id': False,
            })
        return cfg

    def _guess_receipt_account(self):
        Account = self.env['account.account'].with_company(self.company_id)
        for name in ('Stock Variation', 'Stock Interim (Received)', 'Cost of Production'):
            account = Account.search([('name', 'ilike', name)], limit=1)
            if account:
                return account
        return Account.browse()

    def _guess_sale_account(self):
        Account = self.env['account.account'].with_company(self.company_id)
        for name in ('Product Sales', 'Sales', 'Revenue'):
            account = Account.search([('name', 'ilike', name),
                                      ('account_type', 'in', ('income', 'income_other'))], limit=1)
            if account:
                return account
        return Account.browse()

    def action_setup_accounting(self):
        """One-time button: automatic stock accounting for Receipts (and invoiced sales)."""
        self.ensure_one()
        account = self.receipt_account_id or self._guess_receipt_account()
        if not account:
            raise UserError(_('Please choose the "Account credited when stock comes in" first.'))
        self.receipt_account_id = account
        if not self.sale_account_id:
            self.sale_account_id = self._guess_sale_account()
        self.company_id.sudo().inventory_valuation = 'real_time'
        self.env.ref('stock.stock_location_suppliers').sudo().valuation_account_id = account
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Accounting is ready'),
                'message': _('Receipts now post journal entries (Debit Stock Valuation, Credit %s). '
                             'Sales post cost of goods sold when the invoice is posted.') % account.display_name,
                'type': 'success',
                'sticky': False,
            },
        }
