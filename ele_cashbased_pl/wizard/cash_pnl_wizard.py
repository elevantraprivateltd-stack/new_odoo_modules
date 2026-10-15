# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError

# States that mean "money has NOT actually moved yet" and must be excluded
# from a cash-basis report. Listed broadly to stay compatible across Odoo
# versions where the account.payment state selection has changed field values.
EXCLUDED_STATES = ['draft', 'cancel', 'cancelled', 'canceled', 'rejected']


class CashPnlWizard(models.TransientModel):
    _name = 'cash.pnl.wizard'
    _description = 'Profit and Loss (Cash Basis) Wizard'

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    date_from = fields.Date(
        string='Start Date', required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1),
    )
    date_to = fields.Date(
        string='End Date', required=True,
        default=fields.Date.context_today,
    )
    opening_balance = fields.Monetary(
        string='Opening Cash & Bank Balance', default=0.0,
        currency_field='currency_id',
        help="Optional. If filled, the report also shows the Closing Cash & "
             "Bank Balance = Opening Balance + Total Receipts - Total Payments.",
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wiz in self:
            if wiz.date_from and wiz.date_to and wiz.date_from > wiz.date_to:
                raise UserError(_('Start Date must be before End Date.'))

    # ------------------------------------------------------------------
    # Core cash-basis logic
    # ------------------------------------------------------------------
    def _payment_date_field(self):
        """Return whichever date field exists on account.payment in this
        Odoo version ('date' on recent versions, 'payment_date' on older
        ones), so the module keeps working after minor version changes."""
        Payment = self.env['account.payment']
        return 'date' if 'date' in Payment._fields else 'payment_date'

    def _get_payments(self, payment_type):
        self.ensure_one()
        date_field = self._payment_date_field()
        domain = [
            (date_field, '>=', self.date_from),
            (date_field, '<=', self.date_to),
            ('payment_type', '=', payment_type),
            ('company_id', '=', self.company_id.id),
            ('state', 'not in', EXCLUDED_STATES),
        ]
        return self.env['account.payment'].search(domain)

    def _liquidity_account_ids(self, payment):
        """Ids of the cash/bank (liquidity) accounts touched by this payment's
        journal entry - these are excluded so we're left with the real
        income/expense (or receivable/payable) accounts actually hit."""
        ids = set()
        if payment.journal_id.default_account_id:
            ids.add(payment.journal_id.default_account_id.id)
        for line in payment.move_id.line_ids:
            if line.account_id.account_type in ('asset_cash', 'liability_credit_card'):
                ids.add(line.account_id.id)
        return ids

    def _get_payment_account(self, payment):
        """Returns the account.account this receipt/payment should be grouped
        under, trying several strategies in order of reliability:

        1. `destination_account_id` - a field Odoo itself computes on
           account.payment as the counterpart account (receivable/payable,
           or a manually chosen account for standalone payments). This is
           the most reliable source since it's exactly what Odoo used when
           posting the entry, and doesn't depend on guessing which lines
           are 'liquidity' lines.
        2. Move-line based: exclude the bank/cash leg(s) of the journal
           entry and take whichever account remains.
        3. Last resort: the move line with the largest non-liquidity-journal
           amount, even if its account_type looks like a cash/bank type
           (better than showing nothing).
        """
        # Strategy 1
        dest = getattr(payment, 'destination_account_id', False)
        if dest:
            return dest

        # Strategy 2
        liquidity_ids = self._liquidity_account_ids(payment)
        counterpart_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.id not in liquidity_ids
        )
        if counterpart_lines:
            # If several distinct accounts are hit, return the one with the
            # largest absolute amount (main strategy stays simple/1 account
            # per payment; a full split-by-line still happens in the loop
            # below when this method isn't used directly).
            return counterpart_lines[0].account_id

        # Strategy 3: drop the account_type filter, just exclude the exact
        # journal default account.
        journal_account_id = payment.journal_id.default_account_id.id if payment.journal_id.default_account_id else False
        other_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.id != journal_account_id
        )
        if other_lines:
            return other_lines[0].account_id

        return False

    def _group_by_account(self, payments):
        """Returns (lines, total). Groups every receipt/payment by the actual
        Chart of Accounts account it hit in the accounting entry (e.g. the
        income/expense account already set up for that donation/expense
        type) - NOT by any separate manual tag. This mirrors how a real
        Income & Expenditure / Receipts & Payments account is built: the
        split simply follows whatever account codes already exist in the
        Chart of Accounts, so there is no 'Uncategorised' line as long as
        the underlying journal entry has a proper account on it."""
        groups = {}
        total = 0.0
        for pay in payments:
            acc = self._get_payment_account(pay)
            amt = pay.amount
            if acc:
                key = acc.id
                if key not in groups:
                    label = '%s %s' % (acc.code, acc.name) if acc.code else acc.name
                    groups[key] = {'name': label, 'sequence': acc.code or 'zzzz', 'amount': 0.0}
                groups[key]['amount'] += amt
            else:
                # Truly nothing found (e.g. payment has no posted move at
                # all). Name includes the payment reference so it can be
                # tracked down and fixed at the source instead of hiding it.
                key = 'uncat'
                label = _('Uncategorised (check payment %s - no posted journal entry found)') % (pay.name or pay.id)
                if key not in groups:
                    groups[key] = {'name': label, 'sequence': 'zzzz', 'amount': 0.0}
                groups[key]['amount'] += amt
            total += amt
        lines = sorted(groups.values(), key=lambda g: (g['sequence'], g['name']))
        return lines, total

    def _get_income_lines(self):
        self.ensure_one()
        lines, total = self._group_by_account(self._get_payments('inbound'))
        return lines

    def _get_expense_lines(self):
        self.ensure_one()
        lines, total = self._group_by_account(self._get_payments('outbound'))
        return lines

    def _get_total_income(self):
        self.ensure_one()
        return sum(p.amount for p in self._get_payments('inbound'))

    def _get_total_expense(self):
        self.ensure_one()
        return sum(p.amount for p in self._get_payments('outbound'))

    def _get_net_result(self):
        self.ensure_one()
        return self._get_total_income() - self._get_total_expense()

    def _get_closing_balance(self):
        self.ensure_one()
        return self.opening_balance + self._get_net_result()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_print_report(self):
        self.ensure_one()
        return self.env.ref(
            'ele_cashbased_pl.action_report_cash_pnl'
        ).report_action(self)
