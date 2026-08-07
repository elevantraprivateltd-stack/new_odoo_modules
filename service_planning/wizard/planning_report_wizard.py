
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# ======================================================================
# 1. EMPLOYEE REPORT
# ======================================================================
class PlanningEmployeeReportWizard(models.TransientModel):
    _name = "planning.employee.report.wizard"
    _description = "Employee Report"

    # --- selection criteria ---
    sale_order_id = fields.Many2one(
        "sale.order", string="SO",
        help="Filter by a particular Sale Order."
    )
    date_from = fields.Datetime(string="From Date")
    date_to = fields.Datetime(string="To Date")
    employee_ids = fields.Many2many(
        "resource.resource", string="Employee(s)",
        help="Filter by one or more particular employees/resources."
    )
    include_deleted = fields.Boolean(string="Include Deleted", default=False)

    # holds the computed result set so the PDF template can read it
    result_ids = fields.Many2many(
        "planning.schedule", string="Results", readonly=True
    )

    @api.onchange("sale_order_id")
    def _onchange_sale_order_id(self):
        """When an SO is picked, auto-fill the Employee(s) field with the
        resources already assigned to that SO's planning schedule(s)."""
        if self.sale_order_id:
            schedules = self.env["planning.schedule"].search([
                ("sale_order_id", "=", self.sale_order_id.id),
                ("schedule_status", "!=", "deleted"),
            ])
            resources = schedules.mapped("employee_ids")
            if resources:
                self.employee_ids = [(6, 0, resources.ids)]
        else:
            self.employee_ids = [(5, 0, 0)]

    def _build_domain(self):
        self.ensure_one()
        domain = [("recurrency", "=", False)]

        if not self.include_deleted:
            domain.append(("schedule_status", "!=", "deleted"))

        if self.sale_order_id:
            domain.append(("sale_order_id", "=", self.sale_order_id.id))

        if self.date_from:
            domain.append(("end_date", ">=", self.date_from))
        if self.date_to:
            domain.append(("start_date", "<=", self.date_to))

        if self.employee_ids:
            domain.append(("employee_ids", "in", self.employee_ids.ids))

        return domain

    def action_generate_report(self):
        domain = self._build_domain()
        return {
            "type": "ir.actions.act_window",
            "name": "Employee Report",
            "res_model": "planning.schedule",
            "view_mode": "list,form,pivot",
            "domain": domain,
            "context": {"search_default_group_by_employee": 1},
            "target": "current",
        }

    def action_print_pdf(self):
        self.ensure_one()
        domain = self._build_domain()
        records = self.env["planning.schedule"].search(domain, order="start_date asc")
        self.result_ids = [(6, 0, records.ids)]
        return self.env.ref(
            "service_planning.action_report_employee_report"
        ).report_action(self)


# ======================================================================
# 2. SO EXECUTION REPORT
# ======================================================================
class PlanningSoExecutionReportWizard(models.TransientModel):
    _name = "planning.so.execution.report.wizard"
    _description = "SO Execution Report"

    criteria_type = fields.Selection([
        ("date", "Ongoing on a particular date"),
        ("so", "Particular SO"),
        ("period", "Custom Period (start to end date)"),
    ], string="Selection Criteria", required=True, default="date")

    ongoing_date = fields.Datetime(string="Date")
    sale_order_id = fields.Many2one("sale.order", string="SO")
    period_start = fields.Datetime(string="Period Start")
    period_end = fields.Datetime(string="Period End")

    include_deleted = fields.Boolean(string="Include Deleted", default=False)

    result_ids = fields.Many2many(
        "planning.schedule", string="Results", readonly=True
    )

    def _build_domain(self):
        self.ensure_one()
        domain = [("recurrency", "=", False)]

        if not self.include_deleted:
            domain.append(("schedule_status", "!=", "deleted"))

        if self.criteria_type == "date":
            if not self.ongoing_date:
                raise ValidationError("Please select a date.")
            domain += [
                ("start_date", "<=", self.ongoing_date),
                ("end_date", ">=", self.ongoing_date),
            ]

        elif self.criteria_type == "so":
            if self.sale_order_id:
                domain.append(("sale_order_id", "=", self.sale_order_id.id))

        elif self.criteria_type == "period":
            if self.period_start:
                domain.append(("end_date", ">=", self.period_start))
            if self.period_end:
                domain.append(("start_date", "<=", self.period_end))

        return domain

    def action_generate_report(self):
        domain = self._build_domain()
        return {
            "type": "ir.actions.act_window",
            "name": "SO Execution Report",
            "res_model": "planning.schedule",
            "view_mode": "list,form,pivot",
            "domain": domain,
            "context": {"search_default_group_by_so": 1},
            "target": "current",
        }

    def action_print_pdf(self):
        self.ensure_one()
        domain = self._build_domain()
        records = self.env["planning.schedule"].search(domain, order="start_date asc")
        self.result_ids = [(6, 0, records.ids)]
        return self.env.ref(
            "service_planning.action_report_so_execution_report"
        ).report_action(self)