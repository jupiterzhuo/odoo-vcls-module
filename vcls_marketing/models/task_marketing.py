# -*- coding: utf-8 -*-

from odoo import models, fields, api, http, _

class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    project_type_default = fields.Selection(
        selection_add = [('marketing', 'Marketing')],
        string='Project Type for Default',
    )

class Task(models.Model):
    
    _inherit = 'project.task'

    task_type = fields.Selection(
        selection_add = [('marketing','Marketing Campaign')],
        default='gen',
        string='Task Type',
        compute='_compute_task_type',
        store=True,)

    type_of_activity = fields.Many2many(
        comodel_name='res.partner.type.activity',
        string="Type of Activity",
    )

    @api.depends('parent_id', 'project_id.project_type')
    def _compute_task_type(self):
        for task in self:
            if task.project_id.project_type == 'dev':
                if task.parent_id:
                    task.task_type = 'dev.task'
                else:
                    task.task_type = 'dev.vers'

            if task.project_id.project_type == 'marketing':
                task.task_type = 'marketing'
   
    organizer_id = fields.Many2one(
        'res.partner',
        string='Organizer'
    )
    business_line_id = fields.Many2many(
        'product.category',
        string='Business line',
        domain='[("is_business_line", "=", True)]'
    )
    country_group_id = fields.Many2one(
        'res.country.group',
        string='Country group',
    )

    related_events_ids = fields.One2many(
        comodel_name = 'marketing.campaign',
        inverse_name = 'marketing_task_id',
    )

    related_mailing_campaigns_ids = fields.One2many(
        comodel_name = 'mail.mass_mailing.campaign',
        inverse_name = 'marketing_task_id',
    )

    attendee_ids = fields.Many2many(
        comodel_name = 'hr.employee',
        string="Attendees",
    )

    ### COSTS related fields
    currency_id = fields.Many2one(
        comodel_name = 'res.currency',
        related = 'project_id.currency_id',
    )

    travel_cost = fields.Monetary(
        default=0.0,
        group_operator="sum",
        )
    sponsorship_cost = fields.Monetary(
        default=0.0,
        group_operator="sum",
        )
    registration_cost = fields.Monetary(
        default=0.0,
        group_operator="sum",
        )
    saved_cost = fields.Monetary(
        string = 'Savings Negociated',
        default=0.0,
        group_operator="sum",
        )
    total_cost = fields.Monetary(
        compute='_compute_total_cost',
        store = True,
        group_operator="sum",
    )
    
    @api.depends('travel_cost','sponsorship_cost','registration_cost','saved_cost')
    def _compute_total_cost(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            task.total_cost = (task.travel_cost + task.sponsorship_cost + task.registration_cost)


    lead_count = fields.Integer(
        compute="_compute_lead_count",
        group_operator="sum",
        )
    lead_participated = fields.Integer(
        compute="_compute_lead_participated",
        group_operator="sum",
        )
    opp_count = fields.Integer(
        compute="_compute_opp_count",
        group_operator="sum",
        )
    contact_count = fields.Integer(
        compute="_compute_contact_count",
        group_operator="sum",
        )
    contact_participated = fields.Integer(
        compute="_compute_contact_participated",
        group_operator="sum",
        )
    convertion_ratio = fields.Float(
        compute="_compute_convertion_ratio",
        group_operator="avg",
        )
    lead_lost = fields.Integer(
        compute="_compute_lead_lost",
        group_operator="sum",
        )
    contact_lost = fields.Integer(
        compute="_compute_contact_lost",
        group_operator="sum",
        )

    def _compute_lead_count(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            leads = self.env['crm.lead'].search([('marketing_task_id.id','=',task.id),('type','=','lead')])
            if leads:
                task.lead_count = len(leads)
            else:
                task.lead_count = 0

    def _compute_lead_participated(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            leads = self.env['crm.lead'].search(['|',('marketing_task_id.id','=',task.id),('marketing_task_ids','in',task.id),('type','=','lead')])
            task.lead_participated = len(leads) if leads else 0


    def _compute_opp_count(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            opps = self.env['crm.lead'].search([('marketing_task_id.id','=',task.id),('type','=','opportunity')])
            if opps:
                task.opp_count = len(opps)
            else:
                task.opp_count = 0
        
    def _compute_contact_count(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            partners = self.env['res.partner'].search([('marketing_task_id.id','=',task.id)])
            if partners:
                task.contact_count = len(partners)
            else:
                task.contact_count = 0
    
    def _compute_contact_participated(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            contacts = self.env['res.partner'].search(['|',('marketing_task_id.id','=',task.id),('marketing_task_ids','in',task.id)])
            task.contact_participated = len(contacts) if contacts else 0

    def _compute_convertion_ratio(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            if task.opp_count > 0 or task.lead_count > 0:
                task.convertion_ratio = (task.opp_count/(task.opp_count+task.lead_count))
            else:
                task.convertion_ratio = 0.0
    
    def _compute_lead_lost(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            leads = self.env['crm.lead'].search([('marketing_task_out_id.id','=',task.id),('type','=','lead')])
            if leads:
                task.lead_lost = len(leads)
            else:
                task.lead_lost = 0
        
    def _compute_contact_lost(self):
        for task in self.filtered(lambda t: t.task_type == 'marketing'):
            partners = self.env['res.partner'].search([('marketing_task_out_id.id','=',task.id)])
            if partners:
                task.contact_lost = len(partners)
            else:
                task.contact_lost = 0

    @api.multi
    def action_open_leads(self):
        self.ensure_one()
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        lead_ids = self.env['crm.lead'].search([('type','=','lead'),'|',('marketing_task_ids','in',self.id),('marketing_task_id.id','=',self.id)]).ids
        action['domain'] = [('id', '=', lead_ids)]
        #action['context'] = {}
        return action

    @api.multi
    def action_open_opps(self):
        self.ensure_one()
        action = self.env.ref('crm.crm_lead_opportunities_tree_view').read()[0]
        opp_ids = self.env['crm.lead'].search([('type','=','opportunity'),('marketing_task_id.id','=',self.id)]).ids
        action['domain'] = [('id', '=', opp_ids)]
        #action['context'] = {}
        return action
    
    @api.multi
    def action_open_contacts(self):
        self.ensure_one()
        action = self.env.ref('vcls-contact.action_contact_all_externals').read()[0]
        contact_ids = self.env['res.partner'].search(['|',('marketing_task_ids','in',self.id),('marketing_task_id.id','=',self.id)]).ids
        action['domain'] = [('id', '=', contact_ids)]
        #action['context'] = {}
        return action


class ResPartnerTypeActivity(models.Model):
    _description = 'Marketing Task Type of Activity'
    _name = "res.partner.type.activity"
    _order = "name"

    name = fields.Char('Name', translate=True)
    full_name = fields.Char('Full Name', translate=True)
    active = fields.Boolean('Active', default=True)
