from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    zone = fields.Char(string="Zone")
    area = fields.Char(string="Area")
    board_type = fields.Char(string="Board Type")
    institute = fields.Char(string="Institute")
    size = fields.Char(string="Size")
    customer_status = fields.Selection([
        ('new', 'New'),
        ('old', 'Old')
    ], string="Customer Status")

    confirm_date = fields.Date(string="Confirm Date")

    decision_maker = fields.Char(string="Decision Maker")
    school_fee_structure = fields.Selection([('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], string="School Fee Structure")
    academic_year_starting = fields.Selection([('aug_sept', 'August - September'), ('april', 'April')], string="Academic Year Starting", default='aug_sept')
    sample_drop_time = fields.Selection([('morning', 'Morning'), ('afternoon', 'Afternoon')], string="Sample Drop Time")
    decision_time = fields.Selection([('immediate', 'Immediate'), ('later', 'Later')], string="Decision Time")
    primary_contact = fields.Char(string="Primary Contact")
    designation = fields.Selection([('principal', 'Principal'), ('vice_principal', 'Vice Principal'), ('coordinator', 'Coordinator')], string="Designation")
    secondary_contact = fields.Char(string="Secondary Contact")
    designation_2nd = fields.Selection([('owner', 'School Owner'), ('director', 'Director'), ('manager', 'Manager')], string="Designation (2nd)")
    # section_ids = fields.Many2many('school.section', string="Section")

    section_details = fields.Text(string="Section Details")



