# -*- coding: utf-8 -*-
import base64
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

CORS_HEADERS = [
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', 'POST, GET, OPTIONS'),
    ('Access-Control-Allow-Headers', 'Content-Type'),
]

# Selection values must match models/helpdesk_ticket.py exactly.
STATE_VALUES = {'new', 'existing'}
DOMAIN_VALUES = {
    'odoo_issue', 'odoo_development', 'record_to_report',
    'order_to_cash', 'source_to_pay',
}
LEVEL_VALUES = {'low', 'medium', 'high'}
RATING_VALUES = {'P1', 'P2', 'P3'}


class HelpdeskPublicController(http.Controller):
    """
    Public endpoints used by the EXTERNAL website (e.g. elevantra.cloud)
    - and by the internal 'Client Form' menu inside Odoo itself - to push a
    Client Form submission straight into the Helpdesk backlog (Help Hesk form).

    Every field on the Client Form is mapped DIRECTLY onto the matching
    field of helpdesk.ticket, so an agent opening the ticket sees Company,
    Reported By, Designation, State, Domain, Impact, Urgency and Ticket
    Rating already filled in - nothing has to be re-typed.
    """

    # -----------------------------------------------------------------
    # GET - serves the Client Form itself (used by the new "Client Form"
    # menu inside Odoo, and can also be iframed from elevantra.cloud).
    # -----------------------------------------------------------------
    @http.route(
        '/helpdesk/client-form',
        type='http', auth='public', methods=['GET'], website=False, csrf=False,
    )
    def client_form_page(self, **kw):
        return request.render('ele_helpdesk.client_form_page_template', {})

    # -----------------------------------------------------------------
    # POST - receives the Client Form submission (from elevantra.cloud or
    # from the Odoo-hosted copy) and creates the ticket.
    # -----------------------------------------------------------------
    @http.route(
        '/helpdesk/ticket/submit',
        type='http', auth='public', methods=['POST', 'OPTIONS'],
        csrf=False, save_session=False,
    )
    def submit_ticket(self, **post):
        # Preflight request from the browser (cross-domain fetch)
        if request.httprequest.method == 'OPTIONS':
            return request.make_response('', headers=CORS_HEADERS)

        company = (post.get('company') or '').strip()
        reported_by = (post.get('reported_by') or '').strip()
        designation = (post.get('designation') or '').strip()
        email = (post.get('email') or '').strip()
        phone = (post.get('phone') or '').strip()

        client_state = (post.get('state') or '').strip().lower()
        issue_domain = (post.get('domain') or '').strip().lower()
        impact = (post.get('impact') or '').strip().lower()
        urgency = (post.get('urgency') or '').strip().lower()
        ticket_rating = (post.get('ticket_rating') or '').strip().upper()
        message = (post.get('description') or post.get('message') or '').strip()

        if not company or not reported_by:
            return self._json({'success': False, 'error': 'Company and Reported By are required.'}, 400)

        # Guard against unexpected values so a bad/tampered request never 500s.
        client_state = client_state if client_state in STATE_VALUES else False
        issue_domain = issue_domain if issue_domain in DOMAIN_VALUES else False
        impact = impact if impact in LEVEL_VALUES else False
        urgency = urgency if urgency in LEVEL_VALUES else False
        ticket_rating = ticket_rating if ticket_rating in RATING_VALUES else 'P3'

        Partner = request.env['res.partner'].sudo()
        partner = False
        # If a logged-in portal customer fills the form, tie the ticket to
        # their own account so it shows up straight away under "My Tickets".
        if request.env.user and not request.env.user._is_public():
            partner = request.env.user.partner_id
        elif email:
            partner = Partner.search([('email', '=', email)], limit=1)
        if not partner and (email or reported_by):
            partner_vals = {'name': reported_by or company, 'email': email}
            if phone:
                partner_vals['phone'] = phone
            if company:
                partner_vals['company_name'] = company
            partner = Partner.create(partner_vals)

        subject = f"{reported_by or 'Website Enquiry'} - {company}" if company else (reported_by or 'Website Enquiry')

        ticket_vals = {
            'name': subject,
            'description': f"<p>{message}</p>" if message else '',
            'partner_id': partner.id if partner else False,
            'partner_name': reported_by,
            'partner_email': email,
            'partner_phone': phone,
            # --- values coming straight from the Client Form ---
            'company': company,
            'reported_by': reported_by,
            'designation': designation,
            'client_state': client_state,
            'issue_domain': issue_domain,
            'impact': impact,
            'urgency': urgency,
            'ticket_rating': ticket_rating,
            'source': 'web_form',
        }

        try:
            ticket = request.env['helpdesk.ticket'].sudo().create(ticket_vals)
        except Exception:
            _logger.exception('Helpdesk website ticket creation failed')
            return self._json({'success': False, 'error': 'Could not create ticket.'}, 500)

        self._attach_files(ticket)

        return self._json({'success': True, 'ticket_ref': ticket.ticket_ref})

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _attach_files(self, ticket):
        """Store any uploaded file(s) from the Client Form as ir.attachment,
        linked to the newly created ticket (shows up in the ticket chatter)."""
        files = request.httprequest.files.getlist('attachment')
        Attachment = request.env['ir.attachment'].sudo()
        for f in files:
            if not f or not f.filename:
                continue
            Attachment.create({
                'name': f.filename,
                'datas': base64.b64encode(f.read()),
                'res_model': 'helpdesk.ticket',
                'res_id': ticket.id,
            })

    def _json(self, data, status=200):
        headers = CORS_HEADERS + [('Content-Type', 'application/json')]
        return request.make_response(json.dumps(data), headers=headers, status=status)
