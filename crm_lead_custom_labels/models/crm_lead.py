from odoo import models, fields


class CrmLead(models.Model):
    _inherit = "crm.lead"


    date_deadline = fields.Date(
        string="Lead End Date",
        help="Estimate of the date on which the opportunity will be won.",
    )

    salesperson = fields.Many2one(
        "res.users",
        string="Salesperson"
    )

    lead_nature_of_assignment = fields.Many2one(
        "product.product",
        string="Nature of Assignment",
    )

    lead_scope_reference = fields.Char(
        string="Scope Reference",
        help="Tender/Proposal ka link yahan paste karein",
    )

    lead_assignment_expected_execution = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
        ('one_time', 'One Time'),
    ], string="Assignment Expected Execution")

    lead_comments = fields.Text(
        string="Comments",
    )

    lead_proposal_submitted = fields.Boolean(
        string="Proposal Submitted",
    )
