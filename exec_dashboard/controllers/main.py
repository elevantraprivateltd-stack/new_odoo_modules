# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime, timedelta, date
import calendar
import logging

_logger = logging.getLogger(__name__)


def _month_bounds(base_date, offset=0):
    """Return (first_day, last_day) of the month `offset` months from base_date."""
    y, m = base_date.year, base_date.month + offset
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    first = date(y, m, 1)
    last = date(y, m, calendar.monthrange(y, m)[1])
    return first, last


def build_date_domain(date_field, preset=None, date_from=None, date_to=None):
    """Build an Odoo domain list for a date/datetime field based on a quick
    preset (today / this_week / this_month / last_month / this_quarter /
    this_year) or an explicit custom range (date_from / date_to)."""
    today = datetime.now().date()
    start = end = None

    if preset in (None, '', 'all'):
        pass
    elif preset == 'today':
        start = end = today
    elif preset == 'this_week':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif preset == 'this_month':
        start, end = _month_bounds(today, 0)
    elif preset == 'last_month':
        start, end = _month_bounds(today, -1)
    elif preset == 'this_quarter':
        q = (today.month - 1) // 3
        start = date(today.year, q * 3 + 1, 1)
        end_month = q * 3 + 3
        end = date(today.year, end_month, calendar.monthrange(today.year, end_month)[1])
    elif preset == 'this_year':
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
    elif preset == 'custom':
        start = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else None
        end = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else None

    domain = []
    if start:
        domain.append((date_field, '>=', start.strftime('%Y-%m-%d 00:00:00')))
    if end:
        domain.append((date_field, '<=', end.strftime('%Y-%m-%d 23:59:59')))
    return domain


def opt(rec_id, name):
    return {'id': rec_id, 'name': name}


class UltimateDashboardController(http.Controller):

    # ------------------------------------------------------------------
    # CRM
    # ------------------------------------------------------------------
    @http.route('/exec_dashboard/get_crm_ultra_data', type='json', auth='user')
    def get_crm_ultra_data(self, domain=None, team_id=None, stage_id=None,
                            source_id=None, user_id=None, priority=None,
                            date_preset=None, date_from=None, date_to=None):
        try:
            # sudo(): this is an EXECUTIVE dashboard — it must show
            # company-wide totals, not just the records the logged-in
            # user personally owns/follows. Without sudo(), a normal
            # salesperson (or any user without "See all Leads/Opportunities")
            # only counts their OWN leads because of crm.lead's default
            # record rules, so KPI cards silently show 0 even though
            # records exist in the database (this is what was happening
            # on the server — it worked locally only because that
            # session was logged in as an Administrator/full-access user).
            Lead = request.env['crm.lead'].sudo()
            base_domain = list(domain) if domain else []

            # Scope strictly to the Pipeline (Opportunities), matching what
            # CRM > Pipeline kanban shows. crm.lead also stores raw,
            # not-yet-converted "Leads" (type='lead', visible under the
            # separate CRM > Leads menu) which never appear in the Pipeline
            # kanban. Without this filter those raw Leads were silently
            # added into every KPI (e.g. New Leads showed 12 while the
            # Pipeline's "New" column only had 3 — the extra 9 were
            # unconverted Leads, not Pipeline opportunities).
            base_domain.append(('type', '=', 'opportunity'))

            if team_id:
                base_domain.append(('team_id', '=', int(team_id)))
            if stage_id:
                base_domain.append(('stage_id', '=', int(stage_id)))
            if source_id:
                base_domain.append(('source_id', '=', int(source_id)))
            if user_id:
                base_domain.append(('user_id', '=', int(user_id)))
            if priority:
                base_domain.append(('priority', '=', priority))
            base_domain += build_date_domain('create_date', date_preset, date_from, date_to)

            # "New Leads" must mean "leads currently sitting in the stage
            # named 'New'" — exactly what the Pipeline kanban shows in its
            # "New" column. Earlier this used probability==0 (wrong: a
            # later-stage lead like Proposition can also have probability
            # 0), and before that "lowest sequence stage globally" (also
            # wrong: with multiple sales teams, each team can have its own
            # stage records, so the lowest-sequence stage across ALL teams
            # isn't necessarily the 'New' stage the user sees — e.g. it
            # picked a different team's stage and produced 13 instead of
            # the real 3). Matching by name is what actually lines up with
            # the kanban column and with by_stage_data below, which already
            # counts leads per real stage name correctly.
            new_stage_ids = request.env['crm.stage'].sudo().search(
                [('name', '=ilike', 'New')]).ids

            total_leads = Lead.search_count(base_domain)
            open_leads = Lead.search_count(base_domain + [('active', '=', True), ('probability', '<', 100)])
            if new_stage_ids:
                new_leads = Lead.search_count(base_domain + [
                    ('active', '=', True), ('stage_id', 'in', new_stage_ids),
                ])
                in_progress = Lead.search_count(base_domain + [
                    ('active', '=', True), ('probability', '<', 100),
                    ('stage_id', 'not in', new_stage_ids),
                ])
            else:
                # Fallback (no stage literally named "New") keeps old behaviour
                new_leads = Lead.search_count(base_domain + [('active', '=', True), ('probability', '=', 0)])
                in_progress = Lead.search_count(base_domain + [
                    ('active', '=', True), ('probability', '>', 0), ('probability', '<', 100),
                ])
            won_leads = Lead.search_count(base_domain + [('active', '=', True), ('probability', '=', 100)])
            lost_leads = Lead.search_count(base_domain + [('active', '=', False), ('probability', '=', 0)])

            my_activities = request.env['mail.activity'].sudo().search_count([
                ('user_id', '=', request.env.user.id),
                ('res_model', '=', 'crm.lead'),
            ])

            open_pipeline = Lead.search(base_domain + [('active', '=', True), ('probability', '<', 100)])
            total_revenue = sum(l.expected_revenue or 0.0 for l in open_pipeline)

            by_team_data = []
            for t in request.env['crm.team'].sudo().search([]):
                cnt = Lead.search_count(base_domain + [('team_id', '=', t.id)])
                if cnt:
                    by_team_data.append({'name': t.name, 'count': cnt})

            by_stage_data = []
            for s in request.env['crm.stage'].sudo().search([]):
                cnt = Lead.search_count(base_domain + [('stage_id', '=', s.id)])
                if cnt:
                    by_stage_data.append({'name': s.name, 'count': cnt})

            by_source_data = []
            for src in request.env['utm.source'].sudo().search([], limit=12):
                cnt = Lead.search_count(base_domain + [('source_id', '=', src.id)])
                if cnt:
                    by_source_data.append({'name': src.name, 'count': cnt})

            filter_options = {
                'teams': [opt(t.id, t.name) for t in request.env['crm.team'].sudo().search([])],
                'stages': [opt(s.id, s.name) for s in request.env['crm.stage'].sudo().search([])],
                'sources': [opt(s.id, s.name) for s in request.env['utm.source'].sudo().search([], limit=50)],
                'users': [opt(u.id, u.name) for u in request.env['res.users'].sudo().search([('share', '=', False)], limit=50)],
            }

            return {
                'total_leads': total_leads, 'open_leads': open_leads, 'new_leads': new_leads,
                'in_progress': in_progress, 'won_leads': won_leads, 'lost_leads': lost_leads,
                'my_activities': my_activities, 'total_revenue': round(total_revenue, 2),
                'by_team_data': by_team_data, 'by_stage_data': by_stage_data,
                'by_source_data': by_source_data, 'filter_options': filter_options,
                'new_stage_id': new_stage_ids,
            }
        except Exception as e:
            _logger.exception("exec_dashboard: get_crm_ultra_data failed")
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # SALES
    # ------------------------------------------------------------------
    @http.route('/exec_dashboard/get_sale_ultra_data', type='json', auth='user')
    def get_sale_ultra_data(self, domain=None, team_id=None, user_id=None,
                             state=None, date_preset=None, date_from=None, date_to=None):
        try:
            Order = request.env['sale.order'].sudo()
            base_domain = list(domain) if domain else []

            if team_id:
                base_domain.append(('team_id', '=', int(team_id)))
            if user_id:
                base_domain.append(('user_id', '=', int(user_id)))
            if state:
                base_domain.append(('state', '=', state))
            base_domain += build_date_domain('date_order', date_preset, date_from, date_to)

            total_orders = Order.search_count(base_domain)
            quotations = Order.search_count(base_domain + [('state', 'in', ['draft', 'sent'])])
            sale_confirmed = Order.search_count(base_domain + [('state', '=', 'sale')])
            cancelled = Order.search_count(base_domain + [('state', '=', 'cancel')])
            to_invoice = Order.search_count(base_domain + [('invoice_status', '=', 'to invoice')])
            upsell = Order.search_count(base_domain + [('invoice_status', '=', 'upselling')])
            fully_invoiced = Order.search_count(base_domain + [('invoice_status', '=', 'invoiced')])

            customers_count = request.env['res.partner'].sudo().search_count([
                ('customer_rank', '>', 0), ('active', '=', True)
            ])

            confirmed_orders = Order.search(base_domain + [('state', '=', 'sale')])
            total_sales = sum(o.amount_total or 0.0 for o in confirmed_orders)

            salesperson_data = []
            for sp in request.env['res.users'].sudo().search([('share', '=', False)], limit=20):
                cnt = Order.search_count(base_domain + [('user_id', '=', sp.id), ('state', '=', 'sale')])
                if cnt:
                    salesperson_data.append({'name': sp.name, 'count': cnt})

            filter_options = {
                'teams': [opt(t.id, t.name) for t in request.env['crm.team'].sudo().search([])],
                'users': [opt(u.id, u.name) for u in request.env['res.users'].sudo().search([('share', '=', False)], limit=50)],
                'states': [
                    {'id': 'draft', 'name': 'Quotation'}, {'id': 'sent', 'name': 'Quotation Sent'},
                    {'id': 'sale', 'name': 'Sales Order'}, {'id': 'cancel', 'name': 'Cancelled'},
                ],
            }

            return {
                'total_orders': total_orders, 'quotations': quotations, 'sale_confirmed': sale_confirmed,
                'cancelled': cancelled, 'to_invoice': to_invoice, 'upsell': upsell,
                'fully_invoiced': fully_invoiced, 'customers_count': customers_count,
                'total_sales': round(total_sales, 2), 'salesperson_data': salesperson_data,
                'filter_options': filter_options,
            }
        except Exception as e:
            _logger.exception("exec_dashboard: get_sale_ultra_data failed")
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # PROJECT
    # ------------------------------------------------------------------
    @http.route('/exec_dashboard/get_project_ultra_data', type='json', auth='user')
    def get_project_ultra_data(self, domain=None, project_id=None, stage_id=None,
                                user_id=None, date_preset=None, date_from=None, date_to=None):
        try:
            Project = request.env['project.project'].sudo()
            Task = request.env['project.task'].sudo()
            base_domain = list(domain) if domain else []

            task_domain = []
            if project_id:
                task_domain.append(('project_id', '=', int(project_id)))
            if stage_id:
                task_domain.append(('stage_id', '=', int(stage_id)))
            if user_id:
                task_domain.append(('user_ids', 'in', [int(user_id)]))
            task_domain += build_date_domain('create_date', date_preset, date_from, date_to)

            proj_domain = list(base_domain)
            if project_id:
                proj_domain.append(('id', '=', int(project_id)))

            total_projects = Project.search_count(proj_domain)
            open_projects = Project.search_count(proj_domain + [('active', '=', True)])
            total_tasks = Task.search_count(task_domain)
            my_tasks = Task.search_count(task_domain + [('user_ids', 'in', [request.env.user.id])])
            open_tasks = Task.search_count(task_domain + [('stage_id.fold', '=', False)])
            done_tasks = Task.search_count(task_domain + [('stage_id.fold', '=', True)])

            stage_data = []
            for s in request.env['project.task.type'].sudo().search([]):
                cnt = Task.search_count(task_domain + [('stage_id', '=', s.id)])
                if cnt:
                    stage_data.append({'name': s.name, 'count': cnt})

            tags_count = request.env['project.tags'].sudo().search_count([])

            filter_options = {
                'projects': [opt(p.id, p.name) for p in request.env['project.project'].sudo().search([], limit=50)],
                'stages': [opt(s.id, s.name) for s in request.env['project.task.type'].sudo().search([])],
                'users': [opt(u.id, u.name) for u in request.env['res.users'].sudo().search([('share', '=', False)], limit=50)],
            }

            return {
                'total_projects': total_projects, 'open_projects': open_projects,
                'total_tasks': total_tasks, 'open_tasks': open_tasks, 'done_tasks': done_tasks,
                'my_tasks': my_tasks, 'tags_count': tags_count, 'stage_data': stage_data,
                'filter_options': filter_options,
            }
        except Exception as e:
            _logger.exception("exec_dashboard: get_project_ultra_data failed")
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # INVOICE / ACCOUNTING
    # ------------------------------------------------------------------
    @http.route('/exec_dashboard/get_invoice_ultra_data', type='json', auth='user')
    def get_invoice_ultra_data(self, domain=None, partner_id=None, user_id=None,
                                payment_state=None, date_preset=None, date_from=None, date_to=None):
        try:
            Move = request.env['account.move'].sudo()
            base_domain = list(domain) if domain else []

            if partner_id:
                base_domain.append(('partner_id', '=', int(partner_id)))
            if user_id:
                base_domain.append(('invoice_user_id', '=', int(user_id)))
            if payment_state:
                base_domain.append(('payment_state', '=', payment_state))
            base_domain += build_date_domain('invoice_date', date_preset, date_from, date_to)

            total_invoices = Move.search_count(base_domain + [('move_type', '=', 'out_invoice')])
            draft_invoices = Move.search_count(base_domain + [('move_type', '=', 'out_invoice'), ('state', '=', 'draft')])
            posted_invoices = Move.search_count(base_domain + [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')])
            unpaid_invoices = Move.search_count(base_domain + [
                ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
            ])
            paid_invoices = Move.search_count(base_domain + [
                ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', '=', 'paid'),
            ])

            bills_count = Move.search_count(base_domain + [('move_type', '=', 'in_invoice')])
            refunds_count = Move.search_count(base_domain + [('move_type', '=', 'out_refund')])

            vendors_count = request.env['res.partner'].sudo().search_count([
                ('supplier_rank', '>', 0), ('active', '=', True)
            ])

            inv_res = Move.search_read(
                base_domain + [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
                ['amount_total', 'amount_residual']
            )
            bill_res = Move.search_read(
                base_domain + [('move_type', '=', 'in_invoice'), ('state', '=', 'posted')],
                ['amount_total']
            )

            total_sale_amount = sum(i['amount_total'] or 0.0 for i in inv_res)
            residual = sum(i['amount_residual'] or 0.0 for i in inv_res)
            payments_collected = total_sale_amount - residual
            total_purchase_amount = sum(b['amount_total'] or 0.0 for b in bill_res)

            filter_options = {
                'partners': [opt(p.id, p.name) for p in request.env['res.partner'].sudo().search(
                    [('customer_rank', '>', 0)], limit=50)],
                'users': [opt(u.id, u.name) for u in request.env['res.users'].sudo().search([('share', '=', False)], limit=50)],
                'payment_states': [
                    {'id': 'not_paid', 'name': 'Not Paid'}, {'id': 'in_payment', 'name': 'In Payment'},
                    {'id': 'paid', 'name': 'Paid'}, {'id': 'partial', 'name': 'Partially Paid'},
                    {'id': 'reversed', 'name': 'Reversed'},
                ],
            }

            return {
                'total_invoices': total_invoices, 'draft_invoices': draft_invoices,
                'posted_invoices': posted_invoices, 'unpaid_invoices': unpaid_invoices,
                'paid_invoices': paid_invoices, 'bills_count': bills_count,
                'refunds_count': refunds_count, 'vendors_count': vendors_count,
                'total_sale_amount': round(total_sale_amount, 2),
                'total_purchase_amount': round(total_purchase_amount, 2),
                'payments_collected': round(payments_collected, 2),
                'residual_amount': round(residual, 2), 'filter_options': filter_options,
            }
        except Exception as e:
            _logger.exception("exec_dashboard: get_invoice_ultra_data failed")
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # RESOURCE (HR Employee)
    # ------------------------------------------------------------------
    @http.route('/exec_dashboard/get_resource_ultra_data', type='json', auth='user')
    def get_resource_ultra_data(self, domain=None, department_id=None, job_id=None,
                                 date_preset=None, date_from=None, date_to=None):
        try:
            Employee = request.env['hr.employee'].sudo()
            base_domain = list(domain) if domain else []

            if department_id:
                base_domain.append(('department_id', '=', int(department_id)))
            if job_id:
                base_domain.append(('job_id', '=', int(job_id)))
            base_domain += build_date_domain('create_date', date_preset, date_from, date_to)

            total_employees = Employee.search_count(base_domain)
            active_employees = Employee.search_count(base_domain + [('active', '=', True)])

            departments_count = request.env['hr.department'].sudo().search_count([])

            today = datetime.now().date()
            on_leave = 0
            if 'hr.leave' in request.env:
                leave_domain = [
                    ('state', '=', 'validate'),
                    ('date_from', '<=', today),
                    ('date_to', '>=', today),
                ]
                if department_id:
                    leave_domain.append(('department_id', '=', int(department_id)))
                on_leave = request.env['hr.leave'].sudo().search_count(leave_domain)

            available = max(active_employees - on_leave, 0)

            attendance_count = 0
            if 'hr.attendance' in request.env:
                att_domain = [
                    ('check_in', '>=', datetime.combine(today, datetime.min.time())),
                    ('check_out', '=', False),
                ]
                if department_id:
                    att_domain.append(('department_id', '=', int(department_id)))
                attendance_count = request.env['hr.attendance'].sudo().search_count(att_domain)

            assigned_count = request.env['project.task'].sudo().search_count([
                ('user_ids', '!=', False), ('stage_id.fold', '=', False),
            ]) if 'project.task' in request.env else 0

            dept_data = []
            for d in request.env['hr.department'].sudo().search([]):
                cnt = Employee.search_count(base_domain + [('department_id', '=', d.id), ('active', '=', True)])
                if cnt:
                    dept_data.append({'name': d.name, 'count': cnt})

            filter_options = {
                'departments': [opt(d.id, d.name) for d in request.env['hr.department'].sudo().search([])],
                'jobs': [opt(j.id, j.name) for j in request.env['hr.job'].sudo().search([], limit=50)]
                if 'hr.job' in request.env else [],
            }

            return {
                'total_employees': total_employees, 'active_employees': active_employees,
                'departments_count': departments_count, 'attendance_count': attendance_count,
                'leave_count': on_leave, 'available_count': available,
                'assigned_count': assigned_count, 'dept_data': dept_data,
                'filter_options': filter_options,
            }
        except Exception as e:
            _logger.exception("exec_dashboard: get_resource_ultra_data failed")
            return {'error': str(e)}
