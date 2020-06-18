# -*- coding: utf-8 -*-

from odoo import models, fields, api, http, _


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

    @api.onchange('marketing_task_id')
    def _onchange_marketing_task_id(self):
        if self.marketing_task_id:
            self.marketing_project_id=self.marketing_task_id.project_id
            
    @api.onchange('partner_id')
    def _get_marketing_info(self):
        for lead in self:
            lead.marketing_project_id = lead.partner_id.marketing_project_id
            lead.marketing_task_id = lead.partner_id.marketing_task_id
            lead.marketing_task_ids = lead.partner_id.marketing_task_ids
            lead.marketing_task_out_id = lead.partner_id.marketing_task_out_id
            lead.opted_in_date = lead.partner_id.opted_in_date
            lead.opted_out_date = lead.partner_id.opted_out_date
    
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

