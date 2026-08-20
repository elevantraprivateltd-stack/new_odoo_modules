# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderProposalTemplate(models.Model):
    _name = 'sale.order.proposal.template'
    _description = 'Sale Order Proposal Template'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    text = fields.Html(string='Text')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    proposal_template_id = fields.Many2one(
        'sale.order.proposal.template',
        string='Proposal Template',
        help="Select a Proposal Template. Its 'Text' content will "
             "automatically be loaded into the Terms & Conditions (note) "
             "field and printed on the quotation report."
    )

    @api.onchange('proposal_template_id')
    def _onchange_proposal_template_id(self):
        for order in self:
            if order.proposal_template_id:
                order.note = order.proposal_template_id.text
