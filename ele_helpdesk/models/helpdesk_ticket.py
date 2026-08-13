# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, api


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Helpdesk Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    # SLA hours per ticket rating -> used to auto compute Expected Time.
    # (Assumption - change these numbers any time to match the real SLA)
    _SLA_HOURS = {'P1': 4, 'P2': 24, 'P3': 72}

    # ---------------------------------------------------------
    # Core fields
    # ---------------------------------------------------------
    ticket_ref = fields.Char(string='Incident Number', readonly=True, copy=False, default='New')
    name = fields.Char(string='Subject', required=True, tracking=True)
    description = fields.Html(string='Description')

    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    partner_name = fields.Char(string='Contact Name')
    partner_email = fields.Char(string='Email')
    partner_phone = fields.Char(string='Phone')

    # ---------------------------------------------------------
    # Client Form fields (Reported By section) - "from customer form"
    # ---------------------------------------------------------
    company = fields.Char(string='Company', tracking=True)
    reported_by = fields.Char(string='Reported By', tracking=True)
    designation = fields.Char(string='Designation')

    client_state = fields.Selection(
        [('new', 'New'), ('existing', 'Existing')],
        string='State', tracking=True,
    )
    issue_domain = fields.Selection(
        [
            ('odoo_issue', 'Odoo Issue'),
            ('odoo_development', 'Odoo Development'),
            ('record_to_report', 'Record to Report'),
            ('order_to_cash', 'Order to Cash'),
            ('source_to_pay', 'Source to Pay'),
        ],
        string='Domain', tracking=True,
    )

    # ---------------------------------------------------------
    # Priority block: Impact / Urgency -> Ticket rating (P1/P2/P3)
    # ---------------------------------------------------------
    impact = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        string='Impact',
    )
    urgency = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        string='Urgency',
    )
    ticket_rating = fields.Selection(
        [('P1', 'P1'), ('P2', 'P2'), ('P3', 'P3')],
        string='Ticket Rating', default='P3', tracking=True,
        help='Comes as a default from the customer form (based on Impact/Urgency) '
             'but can still be changed by the agent.',
    )

    team_id = fields.Many2one('helpdesk.team', string='Team', tracking=True)
    stage_id = fields.Many2one(
        'helpdesk.stage', string='Stage', tracking=True,
        default=lambda self: self.env['helpdesk.stage'].search([], order='sequence', limit=1),
        group_expand='_read_group_stage_ids',
    )
    priority = fields.Selection(
        [('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Urgent')],
        string='Priority', default='1', tracking=True,
    )
    user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)

    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string='Ticket Type')
    department = fields.Selection(
        [
            ('sales', 'Sales'),
            ('technical', 'Technical'),
            ('billing', 'Billing'),
            ('general', 'General'),
        ],
        string='Department', default='general',
    )
    source = fields.Selection(
        [
            ('web_form', 'Web Form'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('chat', 'Chat'),
            ('other', 'Other'),
        ],
        string='Source', default='web_form',
    )

    # ---------------------------------------------------------
    # Auto-generated fields (Help Hesk form)
    # ---------------------------------------------------------
    expected_time = fields.Char(string='Expected Time', compute='_compute_expected_time', store=True,
                                 help='Auto generated as per the Ticket Rating (SLA).')
    deadline = fields.Datetime(string='Deadline', tracking=True)
    time_remaining = fields.Char(string='Time Remaining', compute='_compute_time_remaining')

    close_date = fields.Datetime(string='Closed On', readonly=True)
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', store=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)

    rca = fields.Html(string='RCA', help='Root Cause Analysis - filled in internally by the agent.')

    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id', string='Attachments',
        domain=lambda self: [('res_model', '=', 'helpdesk.ticket')],
    )
    attachment_count = fields.Integer(string='Attachments', compute='_compute_attachment_count')

    # ---------------------------------------------------------
    # Compute / Helpers
    # ---------------------------------------------------------
    @api.depends('ticket_rating')
    def _compute_expected_time(self):
        for ticket in self:
            hours = self._SLA_HOURS.get(ticket.ticket_rating, 72)
            ticket.expected_time = '%s hours (%s)' % (hours, ticket.ticket_rating or 'P3')

    @api.depends('deadline', 'stage_id.is_close')
    def _compute_time_remaining(self):
        now = fields.Datetime.now()
        for ticket in self:
            if not ticket.deadline or ticket.stage_id.is_close:
                ticket.time_remaining = '-'
                continue
            delta = ticket.deadline - now
            hours = delta.total_seconds() / 3600.0
            if hours < 0:
                ticket.time_remaining = 'Overdue by %.1f hrs' % abs(hours)
            else:
                ticket.time_remaining = '%.1f hrs left' % hours

    @api.depends('deadline', 'stage_id.is_close')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for ticket in self:
            ticket.is_overdue = bool(
                ticket.deadline and ticket.deadline < now and not ticket.stage_id.is_close
            )

    def _compute_attachment_count(self):
        for ticket in self:
            ticket.attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'helpdesk.ticket'), ('res_id', '=', ticket.id),
            ])

    @api.onchange('impact', 'urgency')
    def _onchange_impact_urgency(self):
        """Ticket rating comes as a default from Impact/Urgency, but the
        agent/customer can still change it manually afterwards."""
        mapping = {
            ('high', 'high'): 'P1', ('high', 'medium'): 'P1', ('medium', 'high'): 'P1',
            ('high', 'low'): 'P2', ('low', 'high'): 'P2', ('medium', 'medium'): 'P2',
            ('medium', 'low'): 'P3', ('low', 'medium'): 'P3', ('low', 'low'): 'P3',
        }
        if self.impact and self.urgency:
            self.ticket_rating = mapping.get((self.impact, self.urgency), 'P3')

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['helpdesk.stage'].search([], order='sequence')

    # ---------------------------------------------------------
    # CRUD overrides
    # ---------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ticket_ref', 'New') == 'New':
                vals['ticket_ref'] = self.env['ir.sequence'].next_by_code(
                    'helpdesk.ticket.ref'
                ) or 'New'
            # Auto compute the deadline (Expected Time) as per the ticket rating,
            # counted from the auto Date of Reporting (now).
            if not vals.get('deadline'):
                rating = vals.get('ticket_rating') or 'P3'
                hours = self._SLA_HOURS.get(rating, 72)
                vals['deadline'] = fields.Datetime.now() + timedelta(hours=hours)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('stage_id'):
            stage = self.env['helpdesk.stage'].browse(vals['stage_id'])
            if stage.is_close:
                vals['close_date'] = fields.Datetime.now()
        return super().write(vals)

    def name_get(self):
        result = []
        for ticket in self:
            label = f"[{ticket.ticket_ref}] {ticket.name}"
            result.append((ticket.id, label))
        return result
