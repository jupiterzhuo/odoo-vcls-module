# -*- coding: utf-8 -*-

from odoo import models, fields, api, http, _


class Contacts(models.Model):

    _inherit = 'res.partner'

    origin_lead_id = fields.Many2one(
        comodel_name="crm.lead",
    )

    marketing_project_id = fields.Many2one(
        comodel_name = 'project.project',
        string = "Lead Source",
        domain = [('project_type','=','marketing')]
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
        related = 'marketing_task_out_id.create_date',
    )

    gdpr_status = fields.Selection(
        [
            ('undefined', 'Undefined'),
            ('in', 'In'),
            ('out', 'Out'),
        ],
        string = 'GDPR Status',
        compute = '_compute_gdpr_status',
    )

    @api.onchange('marketing_task_id')
    def _onchange_marketing_task_id(self):
        if self.marketing_task_id:
            self.marketing_project_id=self.marketing_task_id.project_id

    @api.depends('marketing_task_id', 'marketing_task_out_id')
    def _compute_gdpr_status(self):
        for record in self:
            if record.marketing_task_out_id or record.opted_out:
                record.gdpr_status = 'out'
            elif record.gdpr_status != 'out' and (record.opted_in or record.marketing_task_id):
                record.gdpr_status = 'in'
            else:
                record.gdpr_status = 'undefined'

    def all_campaigns_pop_up(self):
        #we gather the participants related to the source lead and the current contact
        partner_model = self.env['ir.model'].search([('model','=','res.partner')], limit = 1)
        lead_model = self.env['ir.model'].search([('model','=','crm.lead')], limit = 1)
        domain = "['|','&',('model_id','=', {}),('res_id','=',{}),'&',('model_id','=', {}),('res_id','=',{})]".format(partner_model.id,self.id,lead_model.id,self.origin_lead_id.id)
        
        return {
            'name': 'All participated events',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'marketing.participant',
            'type': 'ir.actions.act_window',
            'domain': domain,
        }

