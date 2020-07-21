# -*- coding: utf-8 -*-

from odoo import models, fields, api, http, _

import logging
_logger = logging.getLogger(__name__)


class Project(models.Model):

    _inherit = 'project.project'
    
    event_type = fields.Selection([
        ('conference', 'conference'),
        ('webinar', 'webinar'),
        ('other', 'other'),
    ], string='Event Type')


    project_type = fields.Selection(
        selection_add = [('marketing', 'Marketing')],
        string = 'Project Type',
    )

    is_marketing_related = fields.Boolean(
        default = False,
        help= "Wen True, the related Source will be consolidated as 'Marketing' source in leads/opps analysis."
    )

    ###############
    # ORM METHODS #
    ###############
    @api.model
    def create(self, vals):

        project = super(Project, self).create(vals)

        if project.project_type == 'marketing':
            project.company_id = self.env.ref('base.main_company')
            wt = self.env['resource.calendar'].search([('company_id','=',self.env.ref('base.main_company').id),('effective_hours','=',40.0)],limit=1)
            if wt:
                project.resource_calendar_id = wt
            else:
                project.resource_calendar_id = False
        
        return project

    @api.multi
    def tasks_tree_view(self):
        action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]
        #_logger.info("TASK: {}".format(action))
        for project in self:
            if project.project_type == 'marketing':
                action = self.env.ref('vcls_marketing.act_marketing_project_2_marketing_task_all').read()[0]
                #_logger.info("TASKM: {}".format(action))
            else:
                pass
        return action

    @api.model
    def _source_from_campaign(self):
        #we 1st consolidate contacts
        to_update = self.env['res.partner'].search([('marketing_task_id','!=',False),('marketing_project_id','=',False)])
        for contact in to_update:
            task = contact.marketing_task_id
            contact.marketing_project_id = task.marketing_project_id
            _logger.info("Contact {} updated with source {} from {}".format(contact.name,contact.marketing_project_id.name,contact.marketing_task_id.name))

        #we do the same with leads
        to_update = self.env['crm.lead'].search([('marketing_task_id','!=',False),('marketing_project_id','=',False)])
        for lead in to_update:
            task = lead.marketing_task_id
            lead.marketing_project_id = task.marketing_project_id
            _logger.info("lead {} updated with source {} from {}".format(lead.name,lead.marketing_project_id.name,lead.marketing_task_id.name))
        



