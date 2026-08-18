# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, api


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Helpdesk Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    # SLA hours per ticket rating -> used to auto compute Expected Time.
    # Actual values now live on helpdesk.sla (Helpdesk > Configuration > SLA
    # Policies) so they can be changed without touching code. These are only
    # the fallback defaults per the agreed SLA:
    # P1 = 4 hours, P2 = 2 days (48h), P3 = 7 days (168h).
    _SLA_HOURS = {'P1': 4, 'P2': 48, 'P3': 168}

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

    # ---------------------------------------------------------
    # Customer satisfaction rating (1-5 stars) - filled in by the
    # customer/agent once the ticket is closed. Feeds the "Average
    # Rating" stat shown on the Live Dashboard.
    # ---------------------------------------------------------
    rating = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        string='Customer Rating', tracking=True,
        help='Customer satisfaction rating for this ticket (1 to 5 stars).',
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

    tag_ids = fields.Many2many('helpdesk.ticket.tag', string='Tags')

    # ---------------------------------------------------------
    # SLA timing milestones - used by the Analytics Dashboard to
    # compute Time to Assign / Time to Respond / Time to Close.
    # ---------------------------------------------------------
    assigned_date = fields.Datetime(
        string='Assigned On', readonly=True, copy=False,
        help='First time an agent was assigned to this ticket.',
    )
    first_response_date = fields.Datetime(
        string='First Response On', readonly=True, copy=False,
        help='First time the ticket moved out of its initial stage '
             '(used as a proxy for the first agent response).',
    )

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
        sla_hours = self.env['helpdesk.sla'].get_sla_hours_map()
        for ticket in self:
            hours = sla_hours.get(ticket.ticket_rating, self._SLA_HOURS.get(ticket.ticket_rating, 168))
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
        sla_hours = self.env['helpdesk.sla'].get_sla_hours_map()
        for vals in vals_list:
            if vals.get('ticket_ref', 'New') == 'New':
                vals['ticket_ref'] = self.env['ir.sequence'].next_by_code(
                    'helpdesk.ticket.ref'
                ) or 'New'
            # Auto compute the deadline (Expected Time) as per the ticket
            # rating (SLA policy), counted from the auto Date of Reporting (now).
            if not vals.get('deadline'):
                rating = vals.get('ticket_rating') or 'P3'
                hours = sla_hours.get(rating, self._SLA_HOURS.get(rating, 168))
                vals['deadline'] = fields.Datetime.now() + timedelta(hours=hours)
            # If a ticket is created already assigned to an agent, stamp it
            # straight away so "Time to Assign" is measured correctly.
            if vals.get('user_id') and not vals.get('assigned_date'):
                vals['assigned_date'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        now = fields.Datetime.now()

        # Stamp "first response" the first time a ticket leaves its
        # original stage (only for tickets that don't have it yet).
        if vals.get('stage_id'):
            stage = self.env['helpdesk.stage'].browse(vals['stage_id'])
            if stage.is_close:
                vals['close_date'] = now
            movers = self.filtered(
                lambda t: not t.first_response_date and t.stage_id.id != vals['stage_id']
            )
            if movers:
                super(HelpdeskTicket, movers).write({'first_response_date': now})

        # Stamp "assigned" the first time an agent is set on a ticket
        # that doesn't have an assignment timestamp yet.
        if vals.get('user_id'):
            newly_assigned = self.filtered(lambda t: not t.assigned_date)
            if newly_assigned:
                super(HelpdeskTicket, newly_assigned).write({'assigned_date': now})

        return super().write(vals)

    def action_open_customer(self):
        """Smart-button style helper: opens the linked Customer's own
        record page (the 'customer page') straight from the ticket."""
        self.ensure_one()
        if not self.partner_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
            'target': 'current',
        }

    def name_get(self):
        result = []
        for ticket in self:
            label = f"[{ticket.ticket_ref}] {ticket.name}"
            result.append((ticket.id, label))
        return result

    # ---------------------------------------------------------
    # Live Dashboard (read-only stats, called from the OWL widget)
    # ---------------------------------------------------------
    @api.model
    def get_dashboard_customers(self):
        """List of customers that have at least one ticket -> used to
        populate the dashboard's customer filter dropdown."""
        rows = self.sudo().search_read(
            [('partner_id', '!=', False)], ['partner_id'],
        )
        seen = {}
        for row in rows:
            partner = row['partner_id']
            if partner:
                seen[partner[0]] = partner[1]
        return [
            {'id': pid, 'name': name}
            for pid, name in sorted(seen.items(), key=lambda item: item[1] or '')
        ]

    @api.model
    def _sla_success_rate(self, closed_domain):
        """% of closed tickets that were closed on/before their deadline.
        Computed from the real 'deadline' vs 'close_date' fields - no
        fabricated numbers."""
        rows = self.sudo().search_read(closed_domain, ['deadline', 'close_date'])
        rows = [r for r in rows if r['deadline'] and r['close_date']]
        if not rows:
            return 0.0
        met = sum(1 for r in rows if r['close_date'] <= r['deadline'])
        return round(100.0 * met / len(rows), 2)

    @api.model
    def _avg_rating(self, domain):
        """Average customer satisfaction rating (out of 5) for tickets
        matching domain that actually have a rating set."""
        rows = self.sudo().search_read(domain + [('rating', '!=', False)], ['rating'])
        if not rows:
            return 0.0
        total = sum(int(r['rating']) for r in rows)
        return round(total / len(rows), 1)

    @api.model
    def _avg_open_hours(self, open_ids):
        if not open_ids:
            return 0.0
        now = fields.Datetime.now()
        total = sum((now - t.create_date).total_seconds() / 3600.0 for t in open_ids)
        return round(total / len(open_ids), 1)

    @api.model
    def get_dashboard_data(self, partner_id=False):
        """Aggregated, always-fresh stats for the Live Dashboard.
        Pass a partner_id to restrict every number to that customer only."""
        Ticket = self.sudo()
        base_domain = [('partner_id', '=', partner_id)] if partner_id else []

        open_domain = base_domain + [('stage_id.is_close', '=', False)]
        closed_domain = base_domain + [('stage_id.is_close', '=', True)]

        open_ids = Ticket.search(open_domain)

        teams = self.env['helpdesk.team'].sudo().search([])
        team_data = []
        for team in teams:
            t_domain = base_domain + [('team_id', '=', team.id)]
            t_open_domain = t_domain + [('stage_id.is_close', '=', False)]
            t_closed_domain = t_domain + [('stage_id.is_close', '=', True)]
            team_data.append({
                'id': team.id,
                'name': team.name,
                'open': Ticket.search_count(t_open_domain),
                'unassigned': Ticket.search_count(t_open_domain + [('user_id', '=', False)]),
                'urgent': Ticket.search_count(t_open_domain + [('priority', '=', '3')]),
                'closed': Ticket.search_count(t_closed_domain),
                'failed': Ticket.search_count(t_domain + [('is_overdue', '=', True)]),
                'sla_success_rate': self._sla_success_rate(t_closed_domain),
                'avg_rating': self._avg_rating(t_domain),
            })

        # ---------------- "My Tickets" / "My Performance" (current user) --
        uid = self.env.uid
        my_domain = base_domain + [('user_id', '=', uid)]
        my_open_domain = my_domain + [('stage_id.is_close', '=', False)]
        my_open_ids = Ticket.search(my_open_domain)

        today_start = fields.Datetime.to_string(
            fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        my_closed_today_domain = my_domain + [
            ('stage_id.is_close', '=', True), ('close_date', '>=', today_start),
        ]
        last7_start = fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=7))
        my_closed_last7_domain = my_domain + [
            ('stage_id.is_close', '=', True), ('close_date', '>=', last7_start),
        ]
        my_closed_all_domain = my_domain + [('stage_id.is_close', '=', True)]

        my = {
            'open': len(my_open_ids),
            'high_priority': Ticket.search_count(my_open_domain + [('priority', '=', '2')]),
            'urgent': Ticket.search_count(my_open_domain + [('priority', '=', '3')]),
            'avg_open_hours': self._avg_open_hours(my_open_ids),
            'failed': Ticket.search_count(my_domain + [('is_overdue', '=', True)]),
            'closed_today': Ticket.search_count(my_closed_today_domain),
            'sla_success_rate': self._sla_success_rate(my_closed_all_domain),
            'avg_rating': self._avg_rating(my_closed_today_domain),
            'closed_last7': Ticket.search_count(my_closed_last7_domain),
            'sla_success_rate_last7': self._sla_success_rate(my_closed_last7_domain),
            'avg_rating_last7': self._avg_rating(my_closed_last7_domain),
            'daily_target': 5,  # adjust here, or move to a config parameter later
        }

        return {
            'total': Ticket.search_count(base_domain),
            'open': len(open_ids),
            'closed': Ticket.search_count(closed_domain),
            'urgent': Ticket.search_count(open_domain + [('priority', '=', '3')]),
            'high_priority': Ticket.search_count(open_domain + [('priority', '=', '2')]),
            'unassigned': Ticket.search_count(open_domain + [('user_id', '=', False)]),
            'overdue': Ticket.search_count(base_domain + [('is_overdue', '=', True)]),
            'avg_open_hours': self._avg_open_hours(open_ids),
            'sla_success_rate': self._sla_success_rate(closed_domain),
            'teams': team_data,
            'my': my,
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
        }

    # ---------------------------------------------------------
    # Analytics Dashboard (KPI cards + pie/stacked-bar charts +
    # Top Customers / Top Assignees / Tickets by Tags tables)
    # ---------------------------------------------------------
    @staticmethod
    def _avg_hours(rows, start_key, end_key):
        deltas = []
        for r in rows:
            start, end = r.get(start_key), r.get(end_key)
            if start and end:
                deltas.append((end - start).total_seconds() / 3600.0)
        return round(sum(deltas) / len(deltas), 1) if deltas else 0.0

    @api.model
    def get_analytics_dashboard_data(self, partner_id=False):
        Ticket = self.sudo()
        domain = [('partner_id', '=', partner_id)] if partner_id else []
        tickets = Ticket.search(domain)

        # ---- KPI cards -------------------------------------------------
        timing_rows = tickets.read(['create_date', 'assigned_date', 'first_response_date', 'close_date'])
        kpis = {
            'tickets': len(tickets),
            'rating': self._avg_rating(domain),
            'time_to_assign': self._avg_hours(timing_rows, 'create_date', 'assigned_date'),
            'time_to_respond': self._avg_hours(timing_rows, 'create_date', 'first_response_date'),
            'time_to_close': self._avg_hours(timing_rows, 'create_date', 'close_date'),
        }

        # ---- Pie chart: tickets by stage --------------------------------
        stages = self.env['helpdesk.stage'].sudo().search([], order='sequence')
        stage_breakdown = []
        for stage in stages:
            count = Ticket.search_count(domain + [('stage_id', '=', stage.id)])
            if count:
                stage_breakdown.append({'id': stage.id, 'name': stage.name, 'count': count})

        # ---- Stacked bar: tickets by stage, split by team ----------------
        teams = self.env['helpdesk.team'].sudo().search([])
        team_stage_breakdown = []
        for team in teams:
            per_stage = {}
            total = 0
            for stage in stages:
                count = Ticket.search_count(
                    domain + [('team_id', '=', team.id), ('stage_id', '=', stage.id)]
                )
                per_stage[str(stage.id)] = count
                total += count
            if total:
                team_stage_breakdown.append({'id': team.id, 'name': team.name, 'stages': per_stage})

        # ---- Top Customers ------------------------------------------------
        cust_rows = self.env['helpdesk.ticket'].sudo().read_group(
            domain + [('partner_id', '!=', False)], ['partner_id'], ['partner_id'],
        )
        top_customers = sorted(
            [{'name': r['partner_id'][1], 'count': r['partner_id_count']} for r in cust_rows],
            key=lambda r: r['count'], reverse=True,
        )[:10]

        # ---- Top Assignees --------------------------------------------------
        agent_rows = self.env['helpdesk.ticket'].sudo().read_group(
            domain + [('user_id', '!=', False)], ['user_id'], ['user_id'],
        )
        top_assignees = sorted(
            [{'name': r['user_id'][1], 'count': r['user_id_count']} for r in agent_rows],
            key=lambda r: r['count'], reverse=True,
        )[:10]

        # ---- Tickets by Tags -------------------------------------------------
        tag_counts = {}
        for ticket in tickets:
            for tag in ticket.tag_ids:
                tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1
        tickets_by_tags = sorted(
            [{'name': name, 'count': count} for name, count in tag_counts.items()],
            key=lambda r: r['count'], reverse=True,
        )

        return {
            'kpis': kpis,
            'stage_breakdown': stage_breakdown,
            'team_stage_breakdown': team_stage_breakdown,
            'stages': [{'id': s.id, 'name': s.name} for s in stages],
            'top_customers': top_customers,
            'top_assignees': top_assignees,
            'tickets_by_tags': tickets_by_tags,
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
        }
