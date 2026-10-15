from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    zone = fields.Char(related="partner_id.zone", store=True)
    area = fields.Char(related="partner_id.area", store=True)
    board_type = fields.Char(related="partner_id.board_type", store=True)
    institute = fields.Char(related="partner_id.institute", store=True)
    size = fields.Char(related="partner_id.size", store=True)

    customer_status = fields.Selection(related="partner_id.customer_status", store=True)
    confirm_date = fields.Date(related="partner_id.confirm_date", store=True)