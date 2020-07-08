# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError

class ProjectProgram(models.Model):

    _name = 'project.program'
    _description = 'Client Program'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        required = True,
    )

    active = fields.Boolean(
        default = True,
    )

    client_id = fields.Many2one(
        comodel_name = 'res.partner',
        domain = "[('customer','=',True)]",
        string = 'Related Client',
        required = True,
    )

    leader_id = fields.Many2one(
        comodel_name = 'res.users',
        string = 'Program Leader',
    )

    product_name = fields.Char(
        string = "Product Name",
        help = 'The client product name',
    )

    client_product_ids = fields.Many2many(
        comodel_name = 'client.product',
        string = 'Client Product',
    )

   
    app_country_group_id = fields.Many2one(
        'res.country.group',
        string = "Application Geographic Area",
    )

    prim_therapeutic_area_id = fields.Many2one(
        'therapeutic.area',
    )

    prim_indication_id = fields.Many2one(
       'targeted.indication', 
    )

    prim_detailed_indication = fields.Text()

    sec_therapeutic_area_id = fields.Many2one(
        'therapeutic.area',
    )

    sec_indication_id = fields.Many2one(
       'targeted.indication', 
    )

    sec_detailed_indication = fields.Text()

    program_info = fields.Text(
        compute = '_compute_program_info',
        store = True,
    )

    """therapeutic_area_ids = fields.Many2many(
        'therapeutic.area',
        string ='Therapeutic Area',
    )
    
    targeted_indication_ids = fields.Many2many(
        'targeted.indication',
        string ='Targeted Indication',
    )"""

     # Only 4 input so no need to create new object
    stage_id =  fields.Selection([('pre', 'Preclinical'),('exploratory', 'Exploratory Clinical'),
    ('confirmatory', 'Confirmatory Clinical'), ('post', 'Post Marketing')], 'Stage', default='pre')
    
    product_description = fields.Text()
    
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='Sale Order Count')
    quotation_count = fields.Integer(compute='_compute_quotation_count', string='Quotation Count')
    opportunity_count = fields.Integer(compute='_compute_opportunity_count', string='Opportunity Count')
    project_count = fields.Integer(compute='_compute_project_count', string='Main Project Count')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count')

    @api.depends('name','product_name','client_id','leader_id','app_country_group_id',
                   'prim_therapeutic_area_id','prim_indication_id','prim_detailed_indication',
                   'sec_therapeutic_area_id','sec_indication_id','sec_detailed_indication', )
    def _compute_program_info(self):
        for program in self:
            info = "{} Program | {} for {} in {} \nled by {}:\n\n".format(program.client_id.name,program.name,program.product_name,', '.join(program.app_country_group_id.mapped('name')),program.leader_id.name)
            if program.prim_therapeutic_area_id:
                info += "Primary Therapeutic Info:\nArea | {}\nIndication | {}\nDetails | {}\n\n".format(program.prim_therapeutic_area_id.name,program.prim_indication_id.name,program.prim_detailed_indication)
            if program.sec_therapeutic_area_id:
                info += "Secondary Therapeutic Info:\nArea | {}\nIndication | {}\nDetails | {}\n\n".format(program.sec_therapeutic_area_id.name,program.sec_indication_id.name,program.sec_detailed_indication)
            program.program_info = info

    def _compute_sale_order_count(self):
        for program in self:
            orders = self.env['sale.order'].search([('program_id','=',program.id),('state','in',['sale','done'])])
            if orders:
                program.sale_order_count = len(orders)
    
    def _compute_quotation_count(self):
        for program in self:
            quotations = self.env['sale.order'].search([('program_id','=',program.id),('state','in',['draft','sent'])])
            if quotations:
                program.quotation_count = len(quotations)
    
            
    def _compute_opportunity_count(self):
        for program in self:
            opps = self.env['crm.lead'].search([('program_id','=',program.id)])
            if opps:
                program.opportunity_count = len(opps)
            
    def _compute_project_count(self):
        for program in self:
            projects = self.env['project.project'].search([('program_id','=',program.id),('parent_id','=',False)])
            if projects:
                program.project_count = len(projects)
    
    def _compute_invoice_count(self):
        for program in self:
            program.invoice_count = sum(self.env['project.project'].search([('program_id','=',program.id)]).mapped('invoices_count'))
    
    @api.multi
    def action_projects_followup(self):
        self.ensure_one()
        action = self.env.ref('vcls-timesheet.project_timesheet_forecast_report_action').read()[0]
        project_ids = self.env['project.project'].search([('program_id','=',self.id)]).mapped('id')
        action['domain'] = [('project_id','in',project_ids)]
        action['context'] = {}
        return action
    
    @api.multi
    def action_open_invoices(self):
        self.ensure_one()
        action = self.env.ref('vcls-invoicing.action_ia_invoices').read()[0]
        invoice_ids = self.env['project.project'].search([('program_id','=',self.id)]).mapped('out_invoice_ids.id')
        action['domain'] = [('id', '=', invoice_ids)]
        action['context'] = {}
        return action


### ADD PROGRAM TO OTHER MODELS ###
class Client(models.Model):

    _inherit = 'res.partner'

    program_ids = fields.One2many(
        'project.program',
        'client_id',
        string = 'Client Programs',
        readonly = True,
    )

    program_count = fields.Integer(
        compute = '_compute_program_count',
    )

    ### METHODS ###
    @api.depends('program_ids')
    def _compute_program_count(self):
        for client in self:
            client.program_count = len(client.program_ids)


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    program_id = fields.Many2one(
        comodel_name = 'project.program',
        string = 'Related Program',
    )    

class Project(models.Model):

    _inherit = 'project.project'

    program_id = fields.Many2one(
        comodel_name = 'project.program',
        string = 'Related Program',
        related="sale_order_id.program_id",
    )
