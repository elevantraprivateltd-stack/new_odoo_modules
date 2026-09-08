# -*- coding: utf-8 -*-
from odoo import fields, models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cash_pnl_category_id = fields.Many2one(
        'cash.pnl.category',
        string='Income/Expense Category',
        help="Used ONLY by the Cash Basis Profit and Loss report to group this "
             "receipt/payment. Has no effect on the accounting entries.",
    )

    @api.onchange('payment_type')
    def _onchange_payment_type_reset_pnl_category(self):
        for payment in self:
            if payment.cash_pnl_category_id:
                expected_type = 'income' if payment.payment_type == 'inbound' else 'expense'
                if payment.cash_pnl_category_id.type != expected_type:
                    payment.cash_pnl_category_id = False
