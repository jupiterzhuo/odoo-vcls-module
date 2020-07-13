# -*- coding: utf-8 -*-

from odoo import models, fields, api, http, _
import logging
_logger = logging.getLogger(__name__)


class Leads(models.Model):

    _inherit = 'crm.lead'

    marketing_project_id = fields.Many2one(
        comodel_name = 'project.project',
        string = "Lead Source",
        domain = [('project_type','=','marketing')],
    )

    marketing_task_id = fields.Many2one(
        comodel_name = 'project.task',
        string = "Opted-In Campaign",
        domain = [('task_type','=','marketing')]
    )

    marketing_task_out_id = fields.Many2one(
        comodel_name = 'project.task',
        string = "Opted-Out Campaign",
        domain = [('task_type','=','marketing')]
    )

    marketing_task_ids = fields.Many2many(
        comodel_name = 'project.task',
        string = "Campaigns",
        domain = [('task_type','=','marketing')]
    )

    opted_in_date = fields.Datetime(
        string = 'Opted In Date',
        #default = lambda self: self.create_date,
    )

    opted_out_date = fields.Datetime(
        string = 'Opted Out Date', 
    )

    gdpr_status = fields.Selection(
        [
            ('undefined', 'Undefined'),
            ('in', 'In'),
            ('out', 'Out'),
        ],
        string = 'GDPR Status',
        default = 'out',
    )

    content_name = fields.Char()

    is_marketing_related = fields.Boolean(
        compute = '_compute_is_marketing_related',
        store = True,
    )

    initial_marketing_project_id = fields.Many2one(
        comodel_name = 'project.project',
        string = "Initial Lead Source",
        domain = [('project_type','=','marketing')],
        compute = '_compute_initial_marketing_project',
        store = True
    )

    initial_is_marketing_related = fields.Boolean(
        compute = '_compute_initial_is_marketing_related',
        store = True,
    )

    @api.depends('marketing_project_id.is_marketing_related')
    def _compute_is_marketing_related(self):
        for lead in self.filtered(lambda l: l.marketing_project_id):
            lead.is_marketing_related = lead.marketing_project_id.is_marketing_related
    
    @api.depends('partner_id.project_marketing_id')
    def _compute_initial_marketing_project(self):
        for lead in self.filtered(lambda l: l.partner_id):
            if lead.partner_id.project_marketing_id:
                lead.initial_marketing_project_id = lead.partner_id.project_marketing_id
    
    @api.depends('initial_marketing_project_id.is_marketing_related')
    def _compute_initial_is_marketing_related(self):
        for lead in self.filtered(lambda l: l.initial_marketing_project_id):
            lead.initial_is_marketing_related = lead.initial_marketing_project_id.is_marketing_related

    @api.onchange('marketing_task_id')
    def _onchange_marketing_task_id(self):
        if self.marketing_task_id:
            self.marketing_project_id=self.marketing_task_id.project_id
    
    #we don't want anymore this info to be laoded from contact, it is now the invert, lead is pushing on contact using a cron
    """@api.onchange('partner_id')
    def _get_marketing_info(self):
        for lead in self:
            lead.marketing_project_id = lead.partner_id.marketing_project_id
            lead.marketing_task_id = lead.partner_id.marketing_task_id
            lead.marketing_task_ids = lead.partner_id.marketing_task_ids
            lead.marketing_task_out_id = lead.partner_id.marketing_task_out_id
            lead.opted_in_date = lead.partner_id.opted_in_date
            lead.opted_out_date = lead.partner_id.opted_out_date"""
    
    @api.multi
    def _create_lead_partner_data(self, name, is_company, parent_id=False):
        """ extract data from lead to create a partner
            :param name : furtur name of the partner
            :param is_company : True if the partner is a company
            :param parent_id : id of the parent partner (False if no parent)
            :returns res.partner record
        """
        data = super()._create_lead_partner_data(name, is_company, parent_id)
        data['origin_lead_id'] = self.id
        data['content_name'] = self.content_name
        data['marketing_project_id'] = self.marketing_project_id.id
        data['marketing_task_id'] = self.marketing_task_id.id
        data['marketing_task_ids'] = [(6, 0, self.marketing_task_ids.ids)]
        
        if is_company:
            pass
        else:
            data['marketing_task_out_id'] = self.marketing_task_out_id.id
            #data['opted_in_date'] = self.opted_in_date
            #data['opted_out_date'] = self.opted_out_date

        return data
    
    def all_campaigns_pop_up(self):
        model_id = self.env['ir.model'].search([('model','=','crm.lead')], limit = 1)
        return {
            'name': 'All participated events',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'marketing.participant',
            'type': 'ir.actions.act_window',
            'domain': "[('model_id','=', {}),('res_id','=',{})]".format(model_id.id, self.id)
        }

    @api.model
    def campaigns_lead_to_partner(self):
        #we search leads and opp with a partner_id, with at least one campaign documented
        leads = self.search([('partner_id','!=',False),'|','|',('marketing_task_id','!=',False),('marketing_task_ids','!=',False),('marketing_task_out_id','!=',False)])
        for lead in leads.filtered(lambda l: not l.partner_id.is_company):
            lead_campaigns = lead.marketing_task_id | lead.marketing_task_ids | lead.marketing_task_out_id
            partner_campaigns = lead.partner_id.marketing_task_id | lead.partner_id.marketing_task_ids | lead.partner_id.marketing_task_out_id
            missing = lead_campaigns - partner_campaigns
            if missing:
                _logger.info("Adding Campains to {} | {}".format(lead.partner_id.name,missing.mapped('name')))
                lead.partner_id.marketing_task_ids |= missing
    
    @api.model
    def populate_initial_marketing_info(self):
        to_update = self.env.search([('partner_id.marketing_project_id','!=',False)])
        to_update._compute_initial_marketing_project()
        to_update._compute_initial_is_marketing_related()

