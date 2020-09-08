# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, http

from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class MailActivityType(models.Model):
    
    _inherit = 'mail.activity.type'

    default_delay = fields.Integer(
        default = 0,
    )

class MailActivity(models.Model):
    
    _inherit = 'mail.activity'

    lm_ids = fields.Many2many(
        'res.users',
        compute='_get_lm_ids',
        compute_sudo=True,
        store = True,
        )
    
    """default_delay = fields.Integer(
        default = 0,
    )"""


    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        TYPES = {
            'out_invoice': 'Invoice',
            'in_invoice': 'Vendor Bill',
            'out_refund': 'Credit Note',
            'in_refund': 'Vendor Credit note',
        }
        for activity in self:
            rec = self.env[activity.res_model].browse(activity.res_id)
            if activity.res_model == 'account.invoice':
                activity.res_name = "%s | %s" % (TYPES[rec.type], rec.temp_name or '')
            elif activity.res_model == 'project.task':
                activity.res_name = "%s - %s" % (rec.name, rec.project_id.display_name or '')
            else:
                activity.res_name = rec.name_get()[0][1]

    @api.depends('user_id')  
    def _get_lm_ids(self):
        #Populate a list of authorized user for domain filtering 
        for rec in self:
            if rec.user_id:
                empl = self.env['hr.employee'].search([('user_id','=',rec.user_id.id)],limit=1)
                if empl:
                    rec.lm_ids = empl.lm_ids
                else:
                    rec.lm_ids = False
            else:
                rec.lm_ids = False

    @api.multi
    def open_record(self):
        for rec in self:
            actions = {}
            rec.ensure_one()
            obj = self.env[rec.res_model].browse(rec.res_id)
            url = http.request.env['ir.config_parameter'].get_param('web.base.url')
            actions['lead'] = self.env.ref('crm.crm_lead_all_leads')
            actions['opportunity'] = self.env.ref('crm.crm_lead_opportunities_tree_view')
            actions['in_invoice'] = self.env.ref('purchase.action_invoice_pending')
            link = "{}/web#id={}&model={}".format(url, rec.res_id, rec.res_model)

            if rec.res_model == 'account.invoice' and obj.type == "in_invoice":
                link = f"{url}/web#id={rec.res_id}&action={actions['in_invoice'].id}&model={rec.res_model}&view_type=form"
            if rec.res_model == 'crm.lead':
                if obj.type == 'opportunity':
                    link = f"{url}/web#id={rec.res_id}&action={actions['opportunity'].id}&model={rec.res_model}&view_type=form"
                else:
                    link = f"{url}/web#id={rec.res_id}&action={actions['lead'].id}&model={rec.res_model}&view_type=form"
            return {
                'type': 'ir.actions.act_url',
                'url': link,
                'target': 'current',
            }
    
    def action_feedback(self, feedback=False):
        # We override to set a safe context and block other tentative of deletion
        self = self.with_context(safe_unlink=True)
        return super(MailActivity, self).action_feedback(feedback)


    @api.multi
    def unlink(self):
        user = self.env['res.users'].browse(self._uid)
        for act in self:
            if not self.env.context.get('safe_unlink', False) and not user.has_group('base.group_system'):
                _logger.info("SAFE UNLINK {} - {}".format(act.res_name,act.user_id.name))
                raise ValidationError("You are not authorized to cancel this activity.")
        return super(MailActivity, self).unlink()
    
    @api.model
    def create(self, values):
        if values.get('activity_type_id'):
            activity_type = self.env['mail.activity.type'].browse(values.get('activity_type_id'))

            if activity_type.default_delay>0 and values.get('date_deadline') == fields.Date.context_today(self):
                #we compute a default deadline value, based on type configuration
                if activity_type.delay_unit == 'days':
                    values['date_deadline'] = fields.Date.context_today(self) + relativedelta(days=activity_type.default_delay)
                elif activity_type.delay_unit == 'weeks':
                    values['date_deadline'] = fields.Date.context_today(self) + relativedelta(weeks=activity_type.default_delay)
                elif activity_type.delay_unit == 'months':
                    values['date_deadline'] = fields.Date.context_today(self) + relativedelta(months=activity_type.default_delay)
                else:
                    pass
            else:
                pass

        return super(MailActivity, self).create(values)
    
    @api.model
    def clean_obsolete(self):
        models_to_clean = [
            {'name':'project.project','id':'project_project'},
            {'name':'project.task','id':'project_task'},
            {'name':'crm.lead','id':'crm_lead'},
            {'name':'sale.order','id':'sale_order'},
            {'name':'purchase.order','id':'purchase_order'},
            ]
        
        for model in models_to_clean:
            query = "DELETE FROM mail_activity WHERE res_model='{}' AND res_id not in (SELECT id FROM {})".format(model['name'],model['id'])
            _logger.info("Clearing Obsolete Activities\n{}".format(query))
            self.env.cr.execute(query)
            self.env.cr.commit()

