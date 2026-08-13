# -*- coding: utf-8 -*-
from odoo import models, fields


class HelpdeskTicketType(models.Model):
    _name = 'helpdesk.ticket.type'
    _description = 'Helpdesk Ticket Type'
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)
