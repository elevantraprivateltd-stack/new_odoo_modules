# -*- coding: utf-8 -*-
from odoo import models, fields


class HelpdeskTeam(models.Model):
    _name = 'helpdesk.team'
    _description = 'Helpdesk Team'

    name = fields.Char(string='Team Name', required=True)
    member_ids = fields.Many2many('res.users', string='Team Members')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    ticket_count = fields.Integer(string='Ticket Count', compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        for team in self:
            team.ticket_count = self.env['helpdesk.ticket'].search_count(
                [('team_id', '=', team.id)]
            )
