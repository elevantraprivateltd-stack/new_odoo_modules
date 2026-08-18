# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    helpdesk_ticket_ids = fields.One2many(
        'helpdesk.ticket', 'partner_id', string='Helpdesk Tickets',
    )
    helpdesk_ticket_count = fields.Integer(
        string='Ticket Count', compute='_compute_helpdesk_ticket_count',
    )

    def _compute_helpdesk_ticket_count(self):
        Ticket = self.env['helpdesk.ticket']
        for partner in self:
            partner.helpdesk_ticket_count = Ticket.search_count(
                [('partner_id', '=', partner.id)]
            )

    def action_view_helpdesk_tickets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tickets - %s' % (self.name or ''),
            'res_model': 'helpdesk.ticket',
            'view_mode': 'list,form,kanban',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
