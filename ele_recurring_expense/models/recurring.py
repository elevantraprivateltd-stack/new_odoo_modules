# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountRecurringPayments(models.Model):
    """Add an expense breakdown to recurring payment templates."""

    _inherit = 'account.recurring.payments'

    payment_line_ids = fields.One2many(
        comodel_name='account.recurring.payment.custom.line',
        inverse_name='payment_id',
        string='Expense Items Breakdown',
        copy=True,
    )


class AccountRecurringPaymentCustomLine(models.Model):
    """Individual expense/account lines attached to a recurring template."""

    _name = 'account.recurring.payment.custom.line'
    _description = 'Recurring Payment Breakdown Item'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    payment_id = fields.Many2one(
        comodel_name='account.recurring.payments',
        string='Recurring Template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Item / Expense Description',
        required=True,
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        check_company=True,
    )
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='payment_id.company_id.currency_id',
        string='Currency',
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='payment_id.company_id',
        string='Company',
        store=True,
        readonly=True,
    )
