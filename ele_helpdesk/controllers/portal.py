# -*- coding: utf-8 -*-
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route


class HelpdeskCustomerPortal(CustomerPortal):
    """Adds a 'Support Tickets' card to /my/home (same look as Your Invoices,
    Tasks, etc.) and a /my/tickets page listing the logged-in customer's own
    tickets, with a button that opens the Client Form to raise a new one."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'ticket_count' in counters:
            partner = request.env.user.partner_id
            Ticket = request.env['helpdesk.ticket']
            values['ticket_count'] = Ticket.search_count(
                [('partner_id', '=', partner.id)]
            ) if Ticket.check_access_rights('read', raise_exception=False) else 0
        return values

    @route(['/my/tickets', '/my/tickets/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_tickets(self, page=1, **kw):
        partner = request.env.user.partner_id
        Ticket = request.env['helpdesk.ticket']
        domain = [('partner_id', '=', partner.id)]

        ticket_count = Ticket.search_count(domain)
        pager = portal_pager(url='/my/tickets', total=ticket_count, page=page, step=20)
        tickets = Ticket.search(domain, limit=20, offset=pager['offset'], order='create_date desc')

        return request.render('ele_helpdesk.portal_my_tickets', {
            'tickets': tickets,
            'pager': pager,
            'page_name': 'ticket',
            'default_url': '/my/tickets',
        })

    @route('/my/tickets/new', type='http', auth='user', website=True)
    def portal_new_ticket(self, **kw):
        # Re-uses the same Client Form used on elevantra.cloud and inside Odoo.
        return request.redirect('/helpdesk/client-form')

    # -----------------------------------------------------------------
    # Customer ticket detail page - "the customer page" for a single
    # ticket. Access control: a portal user may only ever open a ticket
    # that belongs to their own partner_id; anything else raises a 403
    # via the standard portal _document_check_access helper (same
    # mechanism used by /my/orders/<id>, /my/invoices/<id>, etc.), which
    # relies on the ir.rule "Portal: own tickets only" already defined
    # in security/helpdesk_security.xml.
    # -----------------------------------------------------------------
    @route(['/my/tickets/<int:ticket_id>'], type='http', auth='user', website=True)
    def portal_ticket_detail(self, ticket_id, **kw):
        try:
            ticket_sudo = self._document_check_access('helpdesk.ticket', ticket_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        return request.render('ele_helpdesk.portal_ticket_detail', {
            'ticket': ticket_sudo,
            'page_name': 'ticket',
        })
