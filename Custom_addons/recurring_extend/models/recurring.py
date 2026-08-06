from odoo import models, fields, api

# Server Model: account.recurring.template (Normal Model)
class AccountRecurringTemplate(models.Model):
    _inherit = 'account.recurring.template'

    custom_line_ids = fields.One2many(
        'account.recurring.template.custom.line',
        'template_id',
        string='Template Breakdown Items'
    )


class AccountRecurringTemplateCustomLine(models.Model):
    _name = 'account.recurring.template.custom.line'
    _description = 'Recurring Template Breakdown Item'

    template_id = fields.Many2one('account.recurring.template', string='Template Ref', ondelete='cascade')
    name = fields.Char(string='Item / Expense Description', required=True)
    account_id = fields.Many2one('account.account', string='Account')
    amount = fields.Float(string='Amount')


# Payment Model Extension
class AccountRecurringPayments(models.Model):
    _inherit = 'account.recurring.payments'

    payment_line_ids = fields.One2many(
        'account.recurring.payment.custom.line',
        'payment_id',
        string='Payment Expense Breakdown'
    )

    @api.onchange('recurring_template_id', 'template_id')
    def _onchange_recurring_template_id_load_lines(self):
        template = getattr(self, 'recurring_template_id', False) or getattr(self, 'template_id', False)
        if template and hasattr(template, 'custom_line_ids'):
            lines = []
            for item in template.custom_line_ids:
                lines.append((0, 0, {
                    'name': item.name,
                    'account_id': item.account_id.id if item.account_id else False,
                    'amount': item.amount,
                }))
            self.payment_line_ids = [(5, 0, 0)] + lines


class AccountRecurringPaymentCustomLine(models.Model):
    _name = 'account.recurring.payment.custom.line'
    _description = 'Recurring Payment Breakdown Item'

    payment_id = fields.Many2one('account.recurring.payments', string='Payment Ref', ondelete='cascade')
    name = fields.Char(string='Item / Expense Description', required=True)
    account_id = fields.Many2one('account.account', string='Account')
    amount = fields.Float(string='Amount')