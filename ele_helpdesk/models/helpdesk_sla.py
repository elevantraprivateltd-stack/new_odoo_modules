# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HelpdeskSLA(models.Model):
    _name = 'helpdesk.sla'
    _description = 'Helpdesk SLA Policy'
    _order = 'sequence'
    _rec_name = 'ticket_rating'

    name = fields.Char(string='Policy Name', compute='_compute_name', store=True)
    sequence = fields.Integer(string='Sequence', default=10)
    ticket_rating = fields.Selection(
        [('P1', 'P1 - Critical'), ('P2', 'P2 - High'), ('P3', 'P3 - Normal')],
        string='Priority', required=True,
    )
    # Resolution time expressed in days + hours so it is easy to configure
    # (e.g. P2 = 2 days -> days=2, hours=0 -> 48 hours total).
    days = fields.Integer(string='Days', default=0)
    hours = fields.Integer(string='Hours', default=0)
    resolution_hours = fields.Integer(
        string='Resolution Time (Hours)', compute='_compute_resolution_hours',
        store=True, help='Total SLA resolution time in hours (days converted + hours).',
    )
    description = fields.Char(string='Description')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('ticket_rating_uniq', 'unique(ticket_rating)',
         'An SLA policy already exists for this priority. Edit the existing one instead.'),
    ]

    @api.depends('ticket_rating')
    def _compute_name(self):
        labels = dict(self._fields['ticket_rating'].selection)
        for sla in self:
            sla.name = labels.get(sla.ticket_rating, sla.ticket_rating or 'New SLA')

    @api.depends('days', 'hours')
    def _compute_resolution_hours(self):
        for sla in self:
            sla.resolution_hours = (sla.days or 0) * 24 + (sla.hours or 0)

    @api.model
    def get_sla_hours_map(self):
        """Returns {'P1': hours, 'P2': hours, 'P3': hours}, used by
        helpdesk.ticket to compute the deadline. Falls back to the
        documented defaults (P1=4h, P2=2 days, P3=7 days) for any
        priority that has no SLA policy configured yet."""
        defaults = {'P1': 4, 'P2': 48, 'P3': 168}
        rows = self.sudo().search_read([], ['ticket_rating', 'resolution_hours'])
        for row in rows:
            if row['ticket_rating']:
                defaults[row['ticket_rating']] = row['resolution_hours']
        return defaults
