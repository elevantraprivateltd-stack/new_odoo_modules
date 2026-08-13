# -*- coding: utf-8 -*-
from odoo import models, fields
from datetime import timedelta


class HelpdeskReportWizard(models.TransientModel):
    _name = 'helpdesk.report.wizard'
    _description = 'Helpdesk Custom Report Wizard'

    date_from = fields.Date(
        string='From Date',
        default=lambda self: fields.Date.today() - timedelta(days=30),
        required=True,
    )
    date_to = fields.Date(
        string='To Date',
        default=lambda self: fields.Date.today(),
        required=True,
    )
    team_id = fields.Many2one('helpdesk.team', string='Team')
    stage_id = fields.Many2many('helpdesk.stage', string='Stage')
    priority = fields.Selection(
        [('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Urgent')],
        string='Priority',
    )
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string='Ticket Type')
    department = fields.Selection(
        [
            ('sales', 'Sales'),
            ('technical', 'Technical'),
            ('billing', 'Billing'),
            ('general', 'General'),
        ],
        string='Department',
    )
    user_id = fields.Many2one('res.users', string='Assigned Agent')
    partner_id = fields.Many2one('res.partner', string='Customer')
    only_overdue = fields.Boolean(string='Only Overdue Tickets')

    def _get_domain(self):
        self.ensure_one()
        domain = [
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to),
        ]
        if self.team_id:
            domain.append(('team_id', '=', self.team_id.id))
        if self.stage_id:
            domain.append(('stage_id', 'in', self.stage_id.ids))
        if self.priority:
            domain.append(('priority', '=', self.priority))
        if self.ticket_type_id:
            domain.append(('ticket_type_id', '=', self.ticket_type_id.id))
        if self.department:
            domain.append(('department', '=', self.department))
        if self.user_id:
            domain.append(('user_id', '=', self.user_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        if self.only_overdue:
            domain.append(('is_overdue', '=', True))
        return domain

    def action_generate_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'ele_helpdesk.action_report_helpdesk_custom'
        ).report_action(self)

    def action_view_pivot(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Custom Report - Pivot',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'pivot,graph,list',
            'domain': self._get_domain(),
            'target': 'current',
        }

    def action_view_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Custom Report - Tickets',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'list,form',
            'domain': self._get_domain(),
            'target': 'current',
        }

    def get_kpis(self):
        self.ensure_one()
        tickets = self.env['helpdesk.ticket'].search(self._get_domain())
        total = len(tickets)
        closed = tickets.filtered(lambda t: t.stage_id.is_close)
        open_tickets = tickets - closed
        overdue = tickets.filtered(lambda t: t.is_overdue)
        durations = []
        for t in closed:
            if t.close_date and t.create_date:
                delta = t.close_date - t.create_date
                durations.append(delta.total_seconds() / 3600.0)
        avg_resolution = round(sum(durations) / len(durations), 1) if durations else 0.0

        return {
            'total': total,
            'open': len(open_tickets),
            'closed': len(closed),
            'overdue': len(overdue),
            'avg_resolution_hours': avg_resolution,
        }

    def get_tickets(self):
        self.ensure_one()
        return self.env['helpdesk.ticket'].search(self._get_domain())
