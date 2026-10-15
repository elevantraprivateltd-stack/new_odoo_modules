# -*- coding: utf-8 -*-
from odoo import fields, models


class CashPnlCategory(models.Model):
    _name = 'cash.pnl.category'
    _description = 'Cash Basis P&L Category'
    _order = 'type, sequence, name'

    name = fields.Char(required=True)
    type = fields.Selection(
        [('income', 'Income'), ('expense', 'Expense')],
        required=True,
        default='income',
        help="Income categories are offered on Receipts (inbound payments). "
             "Expense categories are offered on Payments (outbound payments).",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True,
    )
