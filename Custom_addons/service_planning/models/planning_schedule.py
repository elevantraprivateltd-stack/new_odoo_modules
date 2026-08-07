from odoo import models, fields, api, http
from odoo.exceptions import ValidationError
from odoo.addons.base.models.res_partner import _tz_get
from datetime import timedelta
import logging
from datetime import datetime, time
from dateutil import rrule

_logger = logging.getLogger(__name__)

from dateutil.relativedelta import relativedelta
import calendar


class SaleOrder(models.Model):
    _inherit = "sale.order"

    planning_start_date = fields.Datetime(string="Planning Start Date")
    planning_end_date = fields.Datetime(string="Planning End Date")

    def action_sync_service_planning(self):
        Planning = self.env['planning.schedule']

        for order in self:
            if order.state not in ['draft', 'sent', 'sale', 'cancel']:
                continue

            # Sirf wo lines jinme product hai
            valid_lines = order.order_line.filtered(lambda l: l.product_id)
            if not valid_lines:
                continue

            # 🔑 Saare products ek combined string mein
            combined_products = ", ".join(valid_lines.mapped('product_id.name')) or "No Product"

            start_date = order.planning_start_date or fields.Datetime.now()
            end_date = order.planning_end_date or fields.Datetime.now()

            duration = end_date - start_date
            days = duration.days if duration.days > 0 else 1
            allocated_hours = days * 8.0

            assignment_name = f"{order.partner_id.name or 'No Customer'} / {combined_products}"

            # 🔑 Ab search sirf sale_order_id se hoga (per line nahi)
            existing = Planning.search([
                ('sale_order_id', '=', order.id),
            ], limit=1)

            vals = {
                'sale_order_id': order.id,
                'sale_order_line_id': valid_lines[0].id,  # reference ke liye first line
                'name': assignment_name,
                'start_date': start_date,
                'end_date': end_date,
                'allocated_time_pct': allocated_hours,
                'schedule_status': 'cancelled' if order.state == 'cancel' else 'open',
            }

            if existing:
                existing.write(vals)
            else:
                Planning.create(vals)

    def action_confirm(self):
        res = super().action_confirm()
        self.action_sync_service_planning()
        return res

    def action_cancel(self):
        res = super(SaleOrder,
                    self.with_context(skip_planning_validation=True)).action_cancel()
        plans = self.env['planning.schedule'].search([
            ('sale_order_id', 'in', self.ids)
        ])
        plans.write({
            'schedule_status': 'cancelled'
        })
        return res

    def action_draft(self):
        return super(
            SaleOrder,
            self.with_context(skip_planning_validation=True)
        ).action_draft()

    def unlink(self):
        plans = self.env['planning.schedule'].search([
            ('sale_order_id', 'in', self.ids)
        ])
        plans.write({
            'schedule_status': 'deleted',
            'sale_order_id': False,
        })
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.action_sync_service_planning()
        return orders

    def write(self, vals):
        res = super().write(vals)
        self.action_sync_service_planning()
        return res

    def name_get(self):
        if self.env.context.get('planning_line_display'):
            result = []
            for line in self:
                customer = line.order_id.partner_id.name or "No Customer"
                product = line.product_id.name or "No Product"
                result.append((line.id, f"{customer} / {product}"))
            return result
        return super().name_get()


class PlanningSchedule(models.Model):
    _name = "planning.schedule"
    # Task 1: Title me se agar description change karni ho
    _description = "Planning Allocation"
    _order = "start_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    schedule_status = fields.Selection([
        ('open', 'Open'),
        ('cancelled', 'Cancelled'),
        ('deleted', 'Deleted'),
    ], string="Schedule Status", default="open", tracking=True)

    so_status = fields.Selection(
        related='sale_order_id.state',
        string="SO Status",
        readonly=True,
        store=True
    )
    name = fields.Char(
        string="Assignment Name",
        tracking=True,
    )

    project_id = fields.Many2one('project.project', string="Project")
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        required=False,
        tracking=True,
    )

    sale_order_line_id = fields.Many2one(
        "sale.order.line",
        string="Sale Order Line",
        domain="[('order_id', '=', sale_order_id)]",
    )

    # Purani line ko badal kar yeh likhein:
    employee_ids = fields.Many2many(
        "resource.resource",
        "planning_schedule_resource_rel",  # Relation table name
        "schedule_id",  # Current model id
        "resource_id",  # Target model id
        string="Resources",
        tracking=True,
    )

    # Recurrency Flow Of calendar
    _RRULE_FREQ_MAP = {
        'daily': rrule.DAILY, 'weekly': rrule.WEEKLY,
        'monthly': rrule.MONTHLY, 'yearly': rrule.YEARLY,
    }
    _RRULE_WEEKDAY_SELECTION_MAP = {
        'MON': rrule.MO, 'TUE': rrule.TU, 'WED': rrule.WE, 'THU': rrule.TH,
        'FRI': rrule.FR, 'SAT': rrule.SA, 'SUN': rrule.SU,
    }
    _RRULE_WEEKDAY_FIELD_MAP = {
        'mon': rrule.MO, 'tue': rrule.TU, 'wed': rrule.WE, 'thu': rrule.TH,
        'fri': rrule.FR, 'sat': rrule.SA, 'sun': rrule.SU,
    }

    recurrency = fields.Boolean(string="Recurrent")
    rrule_type_ui = fields.Selection([
        ('daily', 'Daily'), ('weekly', 'Weekly'),
        ('monthly', 'Monthly'), ('yearly', 'Yearly'), ('custom', 'Custom'),
    ], default='weekly')
    rrule_type = fields.Selection([
        ('daily', 'Days'), ('weekly', 'Weeks'),
        ('monthly', 'Months'), ('yearly', 'Years'),
    ], default='weekly')
    interval = fields.Integer(default=1)
    end_type = fields.Selection([
        ('count', 'Number of repetitions'), ('end_date', 'End date'), ('forever', 'Forever'),
    ], default='count')
    count = fields.Integer(default=1)
    until = fields.Date(string="Repeat Until")
    month_by = fields.Selection([('date', 'Date of month'), ('day', 'Day of month')], default='date')
    day = fields.Integer(default=1)
    weekday = fields.Selection([
        ('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'),
        ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday'),
    ])
    byday = fields.Selection([
        ('1', 'First'), ('2', 'Second'), ('3', 'Third'), ('4', 'Fourth'), ('-1', 'Last'),
    ])
    no_of_days = fields.Integer(
        string="No of Days",
        default=1
    )
    mon = fields.Boolean("Mon")
    tue = fields.Boolean("Tue")
    wed = fields.Boolean("Wed")
    thu = fields.Boolean("Thu")
    fri = fields.Boolean("Fri")
    sat = fields.Boolean("Sat")
    sun = fields.Boolean("Sun")
    event_tz = fields.Selection(
        _tz_get, string="Timezone",
        default=lambda self: self.env.context.get('tz') or self.env.user.tz)

    parent_schedule_id = fields.Many2one('planning.schedule', string="Parent Schedule",
                                         ondelete='cascade', copy=False)
    recurrence_child_ids = fields.One2many('planning.schedule', 'parent_schedule_id',
                                           string="Recurring Occurrences")
    recurrence_group_id = fields.Many2one(
        'planning.schedule', string="Recurrence Group",
        compute='_compute_recurrence_group_id', store=True,
    )

    @api.depends('parent_schedule_id')
    def _compute_recurrence_group_id(self):
        for rec in self:
            rec.recurrence_group_id = rec.parent_schedule_id.id or rec.id

    def _align_start_date_with_recurrence(self, vals):
        if not vals.get('recurrency') or not vals.get('start_date'):
            return vals
        try:
            start_dt = fields.Datetime.from_string(vals['start_date']) if isinstance(vals['start_date'], str) else vals[
                'start_date']
        except Exception:
            return vals

        original_start_dt = start_dt

        repeat_type = vals.get('rrule_type_ui') or vals.get('rrule_type')
        if vals.get('rrule_type_ui') == 'custom':
            repeat_type = vals.get('rrule_type')

        if repeat_type == 'monthly':
            month_by = vals.get('month_by', 'date')
            if month_by == 'date':
                target_day = int(vals.get('day') or start_dt.day)
                try:
                    start_dt = start_dt.replace(day=target_day)
                except ValueError:
                    pass
        elif repeat_type == 'weekly':
            weekdays = []
            if vals.get('mon'): weekdays.append(0)
            if vals.get('tue'): weekdays.append(1)
            if vals.get('wed'): weekdays.append(2)
            if vals.get('thu'): weekdays.append(3)
            if vals.get('fri'): weekdays.append(4)
            if vals.get('sat'): weekdays.append(5)
            if vals.get('sun'): weekdays.append(6)
            if weekdays:
                current_weekday = start_dt.weekday()
                days_ahead = min((wd - current_weekday) % 7 for wd in weekdays)
                if days_ahead > 0:
                    start_dt += timedelta(days=days_ahead)


        shift = start_dt - original_start_dt
        if shift.total_seconds() != 0 and vals.get('end_date'):
            try:
                end_dt = fields.Datetime.from_string(vals['end_date']) if isinstance(vals['end_date'], str) else vals[
                    'end_date']
                end_dt += shift
                vals['end_date'] = fields.Datetime.to_string(end_dt)
            except Exception:
                pass

        vals['start_date'] = fields.Datetime.to_string(start_dt)
        return vals

    def _get_week_days(self):
        self.ensure_one()
        selected = [wd for field, wd in self._RRULE_WEEKDAY_FIELD_MAP.items() if self[field]]
        if selected:
            return selected
        fallback_field = list(self._RRULE_WEEKDAY_FIELD_MAP.keys())[self.start_date.weekday()]
        return [self._RRULE_WEEKDAY_FIELD_MAP[fallback_field]]

    def _build_rrule(self):
        self.ensure_one()
        repeat_type = self.rrule_type_ui if self.rrule_type_ui != 'custom' else self.rrule_type
        freq = self._RRULE_FREQ_MAP.get(repeat_type)
        _logger.info(">>> _build_rrule: repeat_type=%s freq=%s start_date=%s", repeat_type, freq, self.start_date)
        if not freq:
            return None

        rrule_params = dict(
            dtstart=self.start_date,
            interval=self.interval or 1,
        )

        if repeat_type == 'weekly':
            rrule_params['byweekday'] = self._get_week_days()

        elif repeat_type == 'monthly':
            if self.month_by == 'day':
                weekday_obj = self._RRULE_WEEKDAY_SELECTION_MAP.get(self.weekday or 'MON')
                rrule_params['byweekday'] = weekday_obj(int(self.byday or '1'))
            else:
                rrule_params['bymonthday'] = self.day or self.start_date.day

        elif repeat_type == 'yearly':
            rrule_params['bymonth'] = self.start_date.month
            rrule_params['bymonthday'] = self.start_date.day

        if self.end_type == 'count':
            rrule_params['count'] = min(self.count or 1, 720)
        elif self.end_type == 'end_date' and self.until:
            rrule_params['until'] = datetime.combine(self.until, time.max)
        else:
            rrule_params['count'] = 720

        _logger.info(">>> rrule_params = %s", rrule_params)
        return rrule.rrule(freq, **rrule_params)

    def _generate_recurrence_records(self, vals_list=None):
        for rec in self:
            _logger.info("=== _generate_recurrence_records CALLED for id=%s recurrency=%s parent=%s ===",
                         rec.id, rec.recurrency, rec.parent_schedule_id.id)

            if not rec.recurrency or rec.parent_schedule_id:
                _logger.info(">>> SKIPPED (recurrency=%s parent=%s)", rec.recurrency, rec.parent_schedule_id.id)
                continue

            rec.recurrence_child_ids.unlink()


            if not rec.start_date or (not rec.recurrency and not rec.end_date):
                _logger.warning(
                    ">>> SKIPPED: missing required date(s) on id=%s (recurrency=%s)",
                    rec.id, rec.recurrency
                )
                continue

            duration = timedelta(hours=1)

            # ✅ ADD THIS
            if rec.recurrency and rec.end_date != rec.start_date + duration:
                rec.with_context(skip_recurrence=True).write({
                    'end_date': rec.start_date + duration
                })

            try:
                rule = rec._build_rrule()
            except Exception as e:
                _logger.exception("CRITICAL error building rrule for id=%s: %s", rec.id, e)
                continue

            if not rule:
                _logger.warning(">>> rule is None for id=%s (rrule_type_ui=%s)", rec.id, rec.rrule_type_ui)
                continue

            occurrences = list(rule)
            _logger.info(">>> OCCURRENCES for id=%s: %s", rec.id, occurrences)

            vals_list = []

            extra_days = 1
            repeat_type = rec.rrule_type_ui if rec.rrule_type_ui != 'custom' else rec.rrule_type

            if repeat_type == 'monthly' and rec.month_by == 'day':
                extra_days = max(rec.no_of_days or 1, 1)

            skip_first_occurrence = len(occurrences) > 1

            for index, new_start in enumerate(occurrences):
                if index == 0 and skip_first_occurrence:
                    continue

                for day_index in range(extra_days):
                    final_start = new_start + timedelta(days=day_index)

                    vals = rec.copy_data()[0]
                    vals.update({
                        'start_date': final_start,
                        'end_date': final_start + duration,
                        'recurrency': False,
                        'parent_schedule_id': rec.id,
                    })
                    vals.pop('recurrence_child_ids', None)
                    vals_list.append(vals)

            _logger.info(">>> vals_list length for id=%s: %s", rec.id, len(vals_list))

            if vals_list:
                try:
                    self.env['planning.schedule'].with_context(skip_recurrence=True).create(vals_list)
                    _logger.info(">>> CHILDREN CREATED SUCCESSFULLY for id=%s", rec.id)
                except Exception as e:
                    _logger.exception("Error creating children for id=%s: %s", rec.id, e)

    # ==========================================================
    # THESE HOOKS ARE MANDATORY — WITHOUT THEM NOTHING RUNS
    # ==========================================================
    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("### planning.schedule CREATE called with %s vals", len(vals_list))
        vals_list = [self._align_start_date_with_recurrence(dict(v)) for v in vals_list]
        records = super().create(vals_list)

        if not self.env.context.get('skip_recurrence'):
            to_generate = records.filtered(lambda r: r.recurrency and not r.parent_schedule_id)
            _logger.info("### CREATE: %s records need recurrence generation", len(to_generate))
            to_generate._generate_recurrence_records()

        return records

    def write(self, vals):
        _logger.info("### planning.schedule WRITE called with vals=%s", vals)

        recurrence_trigger_fields = {
            'recurrency', 'rrule_type', 'rrule_type_ui', 'interval', 'count',
            'end_type', 'until', 'month_by', 'day', 'weekday', 'byday',
            'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
            'start_date', 'end_date', 'no_of_days',
        }
        need_regen = bool(recurrence_trigger_fields & set(vals.keys()))

        # ===========================
        # Recurrent ON
        # Original End Date save karo
        # ===========================
        if vals.get('recurrency') is True:
            for rec in self.filtered(lambda r: not r.parent_schedule_id):
                if rec.end_date and not rec.original_end_date:
                    vals['original_end_date'] = rec.end_date

        res = super().write(vals)

        # ===========================
        # Recurrent OFF
        # Child delete + End Date restore
        # ===========================
        if vals.get('recurrency') is False:
            for rec in self.filtered(lambda r: not r.parent_schedule_id):
                rec.recurrence_child_ids.unlink()

                restore_end_date = rec.original_end_date

                if not restore_end_date and rec.sale_order_id and rec.sale_order_id.planning_end_date:
                    restore_end_date = rec.sale_order_id.planning_end_date

                if restore_end_date:
                    rec.with_context(skip_recurrence=True).write({
                        'end_date': restore_end_date,
                        'original_end_date': False,
                    })

            return res

        # ===========================
        # Generate recurrence
        # ===========================
        if not self.env.context.get('skip_recurrence') and need_regen:
            to_generate = self.filtered(
                lambda r: r.recurrency and not r.parent_schedule_id
            )
            _logger.info(
                "### WRITE: %s records need recurrence generation",
                len(to_generate)
            )
            to_generate._generate_recurrence_records()

        return res

    def action_check_planning_validation(self):
        self.filtered(lambda r: r.recurrency and not r.parent_schedule_id)._generate_recurrence_records()
        return True


    start_date = fields.Datetime(string="Start Date", tracking=True)
    end_date = fields.Datetime(string="End Date", tracking=True)

    original_end_date = fields.Datetime(copy=False)

    allocated_time_pct = fields.Float(
        string="Allocated Hours",
        tracking=True,
    )

    description = fields.Text(string="Employee Note", tracking=True)

    # this method use for validation error script 3 number 4 req
    def action_check_planning_validation(self):
        Planning = self.env['planning.schedule']
        SaleOrder = self.env['sale.order']

        open_orders = SaleOrder.search([
            ('state', 'in', ['draft', 'sent', 'sale'])
        ])

        missing_count = 0
        duplicate_count = 0

        for order in open_orders:
            for line in order.order_line:
                if not line.product_id:
                    continue

                plans = Planning.search([
                    ('sale_order_id', '=', order.id),
                    ('sale_order_line_id', '=', line.id),
                ])

                if not plans:
                    missing_count += 1

                if len(plans) > 1:
                    duplicate_count += len(plans) - 1

        message = f"Validation Completed: Missing Entries: {missing_count}, Duplicate Entries: {duplicate_count}"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Planning Validation',
                'message': message,
                'type': 'success' if missing_count == 0 and duplicate_count == 0 else 'warning',
                'sticky': False,
            }
        }

    @api.onchange("sale_order_id")
    def _onchange_sale_order_id(self):
        for rec in self:
            if rec.sale_order_id:
                if rec.sale_order_line_id and rec.sale_order_line_id.order_id != rec.sale_order_id:
                    rec.sale_order_line_id = False

                rec.start_date = rec.sale_order_id.planning_start_date
                rec.end_date = rec.sale_order_id.planning_end_date

                if rec.start_date and rec.end_date:
                    duration = rec.end_date - rec.start_date
                    days = duration.days if duration.days > 0 else 1
                    rec.allocated_time_pct = days * 8.0
                else:
                    rec.allocated_time_pct = 0.0

            else:
                rec.name = False
                rec.sale_order_line_id = False
                rec.start_date = False
                rec.end_date = False
                rec.allocated_time_pct = 0.0

    @api.onchange("sale_order_line_id")
    def _onchange_sale_order_line_id(self):
        for rec in self:
            if rec.sale_order_line_id and rec.sale_order_id:
                customer_name = rec.sale_order_id.partner_id.name if rec.sale_order_id.partner_id else "No Customer"
                product_name = rec.sale_order_line_id.product_id.name or "No Product"
                rec.name = f"{customer_name} / {product_name}"

                # 🔑 YA MISSING TA — is wajah se total nahi aata ta
                rec.start_date = rec.sale_order_id.planning_start_date
                rec.end_date = rec.sale_order_id.planning_end_date

                if rec.start_date and rec.end_date:
                    duration = rec.end_date - rec.start_date
                    days = duration.days if duration.days > 0 else 1
                    rec.allocated_time_pct = days * 8.0
                else:
                    rec.allocated_time_pct = 0.0

    @api.constrains('sale_order_id', 'sale_order_line_id', 'start_date', 'end_date')
    def _check_duplicate_assignment(self):
        for record in self:
            if not record.sale_order_id:
                continue

            if self.env.context.get('skip_planning_validation'):
                continue
            if not record.start_date and record.sale_order_id.planning_start_date:
                record.start_date = record.sale_order_id.planning_start_date
            if not record.start_date:
                raise ValidationError("Missing Entry Alert! Start Date is required.")
            if record.end_date and record.end_date < record.start_date:
                raise ValidationError("End Date cannot be before Start Date.")

            request = http.request
            is_from_sale_order_form = False
            if request and request.httprequest:
                referrer = request.httprequest.referrer or ''
                if '/odoo/sales/' in referrer:
                    is_from_sale_order_form = True

            if is_from_sale_order_form:
                continue

            duplicate = self.search([
                ('id', '!=', record.id),
                ('sale_order_id', '=', record.sale_order_id.id),
                ('schedule_status', '!=', 'deleted'),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    "Duplicate Entry Alert! This Sale Order is already planned. Duplicate planning record is not allowed."
                )
