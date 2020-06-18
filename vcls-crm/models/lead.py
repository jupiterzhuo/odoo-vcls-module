# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import date
import datetime
import requests
import json

import logging
_logger = logging.getLogger(__name__)

URL_POWER_AUTOMATE = "https://prod-29.westeurope.logic.azure.com:443/workflows/9f6737616b7047498a61a053cd883fc2/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=W5bnOEb4gMnP_E9_VnzK7c8AuYb2zGovg5BHwIoi-U8"

class ResoucesLeads(models.Model):

    _name = 'crm.resource.lead'
    _description = 'resource for lead'
    
    project_role_id = fields.Many2one(
        'hr.project_role', string='Seniority')
    number = fields.Float('Number')


class LeadStage(models.Model):
    _name = 'crm.lead.stage'
    _description = 'stage for lead'

    name = fields.Char(
        required = True,
        string = 'Name'
    )
    
    active = fields.Boolean(default = True)


class Leads(models.Model):

    _inherit = 'crm.lead'
    altname = fields.Char('Altname')
    hide_altname = fields.Boolean()

    @api.onchange('email_from')
    def _onchange_email_from(self):
        lead_id = self.id if not isinstance(self.id, models.NewId) else 0
        if self.email_from and self.sudo().search([
            ('type', '=', 'lead'), ('id', '!=', lead_id),
            ('email_from', '=', self.email_from)], limit=1
        ):
        
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('A lead with this email already exists.'),
                }
            }

    @api.onchange('partner_id', 'partner_name')
    def onchange_info(self):
        hide_altname = False
        if not self.partner_name:
            hide_altname = True
        self.hide_altname = hide_altname

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id.is_company:
            self.altname = self.partner_id.altname
        else:
            self.altname = self.partner_id.parent_id.altname

    @api.onchange('opted_in')
    def onchange_opted_in(self):
        if self.opted_in:
            self.opted_out = False
            self.gdpr_status = 'in'
            self.opted_in_date = datetime.datetime.now()
        else:
            self.opted_out = True
            self.gdpr_status = 'out'
            self.opted_out_date = datetime.datetime.now()

    ###################
    # DEFAULT METHODS #
    ###################


    def _default_am(self):
        return self.guess_am()

    @api.model
    def _default_lead_stage(self):
        try:
            return self.env.ref('vcls-crm.lead_open')
        except:
            return self.env['crm.lead.stage']


    ####################
    # OVERRIDEN FIELDS #
    ####################

    company_id = fields.Many2one(string = 'Trading Entity', default = lambda self: self.env.ref('vcls-hr.company_VCFR'))

    source_id = fields.Many2one('utm.source', "Initial Lead Source")

    user_id = fields.Many2one(
        'res.users', 
        string='Account Manager', 
        track_visibility='onchange', 
        domain=lambda self: [("groups_id", "=", self.env['res.groups'].search([('name','=', 'Account Manager')]).id)],
        default='default_am',
        )

    date_closed = fields.Datetime('Closed Date', readonly=False, copy=False)
    date_deadline = fields.Date(string='Proposal Sending Deadline')

    #################
    # CUSTOM FIELDS #
    #################

    manual_probability = fields.Boolean()

    child_ids = fields.Many2many(
        'res.partner',
        compute='_compute_child_ids',
    )

    # Related fields in order to avoid mismatch & errors
    opted_in = fields.Boolean(
        default= False,
        string = 'Opted In'
    )

    opted_out = fields.Boolean(
        default = True,
        string = 'Opted Out'
    )
 
    lead_stage_id = fields.Many2one(
        'crm.lead.stage',
        string = 'Lead Stage',
        default = _default_lead_stage,
        )
    
    sig_opp = fields.Boolean(
        store = True,
        default = 'False',
        compute = '_compute_sig_opp',
    )

    ### CUSTOM FIELDS RELATED TO MARKETING PURPOSES ###
    
    company_id = fields.Many2one(default = '')

    country_group_id = fields.Many2one(
        'res.country.group',
        string = "Geographic Area",
        compute = '_compute_country_group',
    )

    referent_id = fields.Many2one(
        'res.partner',
        string = 'Referee',
    )

    stakeholder_ids = fields.Many2many(
        'res.partner',
        string = 'Stakeholders',
    )

    functional_focus_id = fields.Many2one(
        'partner.functional.focus',
        string = 'Functional  Focus',
    )

    partner_seniority_id = fields.Many2one(
        'partner.seniority',
        string = 'Seniority',
    )

    client_activity_ids = fields.Many2many(
        'client.activity',
        string = 'Client Activity',
    )

    client_product_ids = fields.Many2many(
        'client.product',
        string = 'Client Product',
    )

    industry_id = fields.Many2one(
        'res.partner.industry',
        string = "Industry",
    )

    scope_of_work = fields.Html(
        placeholder = 'Summary in bullet points'
    )

    product_category_id = fields.Many2one(
        'product.category',
        string = 'Business Line',
        domain = "[('is_business_line','=',True)]"
    )

    
    #date fields
    expected_start_date = fields.Date(
        string="Expected Project Start Date",
    )


    won_reason = fields.Many2one(
        'crm.won.reason'
    )

    won_reasons = fields.Many2many(
        'crm.won.reason',
        string='Won Reasons',
        index=True,
        track_visibility='onchange'
    )

    lost_reasons = fields.Many2many(
        'crm.lost.reason',
        string='Lost Reasons',
        index=True,
        track_visibility='onchange'
    )

    internal_ref = fields.Char(
        string="Ref",
        #store = True,
        #compute = '_compute_internal_ref',
        #inverse = '_set_internal_ref',
    )
    
    technical_adv_id = fields.Many2one(
        'hr.employee', 
        string='PIC', 
        track_visibility='onchange', 
        )
    
    proposal_writer_id = fields.Many2one(
        'hr.employee', 
        string='Proposal Writer', 
        track_visibility='onchange', 
        )
    
    support_team = fields.Many2many(
        'hr.employee', 
        string='Other Technical Experts', 
        )
    
    resources_ids = fields.Many2many(
        'crm.resource.lead', 
        string='Resources', 
        )
    
    CDA = fields.Boolean('CDA signed')
    MSA = fields.Boolean('MSA valid')
    sp_folder = fields.Char('Sharepoint Folder')
    
    contract_type = fields.Selection([('saleorder', 'Sale Order'),
                                      ('workorder', 'Work Order'),
                                      ('termandcondition', 'Terms and conditions'),])

    risk_ids = fields.Many2many(
        'risk',
        string='Risk',
        store=True,
        compute='_compute_risk_ids'
    )

    #is_support_user = fields.Boolean(compute='_compute_is_support_user', store=False)

    app_country_group_id = fields.Many2one(
        'res.country.group',
        string = "Application Geographic Area",
    )

    therapeutic_area_ids = fields.Many2many(
        'therapeutic.area',
        string ='Therapeutic Area',
    )
    
    targeted_indication_ids = fields.Many2many(
        'targeted.indication',
        string ='Targeted Indication',
    )
    
    stage_development_id = fields.Many2one(
        'stage.development',
        string ='Stage of Development',
    )

    meet_story = fields.Char(
    )

    initial_vcls_contact = fields.Many2one(
        'res.users', 
        default=lambda self: self.env.user.id,
        string='VCLS Sponsor'
    )

    age = fields.Char(
        compute = '_compute_lead_age'
    )

    conversion_date = fields.Date(string = 'Lead to Opp date')

    proposal_type = fields.Selection([('email', 'Email Proposal'),
                                      ('simple', 'Simple Proposal'),
                                      ('complex', 'Complex Proposal'),])

    #name = fields.Char() We don't compute, it breaks too much usecases

    lead_history = fields.Many2many(comodel_name="crm.lead", relation="crm_lead_rel", column1="crm_lead_id1")

    ### MIDDLE NAME ###

    contact_middlename = fields.Char("Middle name")

    ### WON / LOST DESCRIPTION ###
    won_lost_description = fields.Char(string = 'Won/Lost details')

    linkedIn_url = fields.Char(string = 'LinkedIn profile')

    
    """opted_in_date = fields.Datetime(
        string = 'Opted In Date',
        default = lambda self: self.create_date,
    )
    opted_out_date = fields.Datetime(
        string = 'Opted Out Date', 
        related = 'unsubscribed_campaign_id.create_date'



    
    unsubscribed_campaign_id = fields.Many2one('utm.campaign', string = 'Opted Out Campaign')

    
    )

    gdpr_status = fields.Selection(
        [
            ('undefined', 'Undefined'),
            ('in', 'In'),
            ('out', 'Out'),
        ],
        string = 'GDPR Status',
        compute = '_compute_gdpr'
    )"""

    contact_us_message = fields.Char()

    @api.model
    def create(self, vals):
       
        if vals.get('type', '') == 'lead':
            temp = self.build_lead_name(vals)
            if temp:
                vals['name'] = temp
        
        lead = super(Leads, self).create(vals)
        # VCLS MODS
        if lead.type == 'lead':
            lead.message_ids[0].subtype_id = self.env.ref('vcls-crm.lead_creation')
        elif lead.type == 'opportunity' and lead.partner_id:
            vals.update({'type':'opportunity'})
            lead.write(vals)
           
        # END OF MODS
        return lead
    
    @api.multi
    def write(self, vals):
        #_logger.info("OPP VALS {} ".format(vals))

        for lead in self:
            lead_vals = {**vals} #we make a copy of the vals to avoid iterative updates

            if self._context.get('clear_ref'):
                _logger.info("Clearing Opp Ref {}".format(lead.internal_ref))
                cleared = super(Leads, lead).write(lead_vals)
                continue
            
            #Lead naming convention
            if (lead_vals.get('type',lead.type) == 'lead'):
                temp = lead.build_lead_name(lead_vals)
                if temp:
                    lead_vals['name'] = temp

            #we manage the reference of the opportunity, if we change the type or update an opportunity not having a ref defined
            if lead_vals.get('internal_ref',False):
                lead_vals['internal_ref'] = lead.force_reference(lead_vals)[0] #we force the index

            #_logger.info("INTERNAL REF {}".format(vals.get('internal_ref',self.internal_ref)))
            if (lead_vals.get('type',lead.type) == 'opportunity') and not lead_vals.get('internal_ref',lead.internal_ref):
                client = self.env['res.partner'].browse(lead_vals.get('partner_id',lead.partner_id.id)) #if a new client defined or was already existing
                if client:
                    lead_vals['internal_ref']=client._get_new_ref()[0]
                else:
                    lead_vals['internal_ref']=False
            
            lead_vals['name']=lead.build_opp_name(lead_vals.get('internal_ref',lead.internal_ref),lead_vals.get('name',lead.name))

            #we manage the case of manual_probability, we re-use the manually set value, except if new one is 0 or 100
            if lead_vals.get('stage_id') and lead.manual_probability:
                stage = self.env['crm.stage'].browse(lead_vals.get('stage_id'))
                if stage.probability not in [0.0,100.00]:
                    lead_vals['probability']=lead.probability

            #_logger.info("{} Manual={}".format(lead_vals,lead.manual_probability))
            if self.env.user.context_data_integration:
                if not super(models.Model, lead).write(lead_vals):
                    return False
            else:
                if not super(Leads, lead).write(lead_vals):
                    return False

        return True

    ###################
    # COMPUTE METHODS #
    ###################

    def _compute_child_ids(self):
           for partner in self.partner_id:
               self.child_ids = partner.child_ids if partner.child_ids else False

    @api.depends('tag_ids')
    def _compute_sig_opp(self):
        for opp in self:
            if ('Value>300K' in opp.tag_ids.mapped('name')) or ('Atypical Opportunity' in opp.tag_ids.mapped('name')) or ('Go_or_No_Go_Decision_Required' in opp.tag_ids.mapped('name')):
                opp.sig_opp = True
            else:
                opp.sig_opp = False

    def build_lead_name(self,vals):
        # self.ensure_one()
        if vals.get('contact_name', self.contact_name) and vals.get('contact_lastname', self.contact_lastname):
                if vals.get('contact_middlename', self.contact_middlename):
                    return vals.get('contact_name', self.contact_name) + " " + vals.get('contact_middlename', self.contact_middlename) + " " + vals.get('contact_lastname', self.contact_lastname)
                else:
                    return vals.get('contact_name', self.contact_name) + " " + vals.get('contact_lastname', self.contact_lastname)
        else:
            return False


    @api.onchange('industry_id')
    def _onchange_industry_id(self):
        if self.partner_id:
            self.partner_id.industry_id = self.industry_id
    
    @api.onchange('client_activity_ids')
    def _onchange_client_activity_ids(self):
        if self.partner_id:
            self.partner_id.client_activity_ids |= self.client_activity_ids
    
    @api.onchange('client_product_ids')
    def _onchange_client_product_ids(self):
        if self.partner_id:
            self.partner_id.client_product_ids |= self.client_product_ids

    @api.onchange('probability')
    def _onchange_probability(self):
        self.manual_probability=True

    #we override this one to exclude the case when manual_probability is True
    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        _logger.info("NEW STAGE PROB {}".format(self.stage_id.probability))
        if not self.manual_probability or self.stage_id.probability == 100 or self.stage_id.probability == 0:
            _logger.info("NEW STAGE PROB {}".format(self.stage_id.probability))
            values = self._onchange_stage_id_values(self.stage_id.id)
            self.update(values)
        else:
            pass


    @api.depends('country_id')
    def _compute_country_group(self):
        for lead in self:
            groups = lead.country_id.country_group_ids
            if groups:
                lead.country_group_id = groups[0]
    
    @api.depends('create_date', 'type', 'conversion_date')
    def _compute_lead_age(self):
        for lead in self:
            if lead.conversion_date != False:
                reference = lead.conversion_date
            elif lead.create_date != False:
                reference = lead.create_date.date()
            else:
                reference = date.today()
            today = date.today()
            delta = today - reference
            if delta.days == 1:
                lead.age = "{} day old".format(delta.days)
            elif delta.days == 0:
                lead.age = "{} day old (created/converted today)".format(delta.days)
            else:
                lead.age = "{} days old".format(delta.days)
    

    """@api.depends('campaign_id', 'unsubscribed_campaign_id')
    def _compute_gdpr(self):
        for record in self:
            if record.campaign_id and not record.unsubscribed_campaign_id:
                record.gdpr_status = 'in'
            elif record.unsubscribed_campaign_id:
                record.gdpr_status = 'out'
            else:
                record.gdpr_status = 'undefined'"""

    #if we change the partner_id, then we clean the ref to trigger a new creation at save
    @api.onchange('partner_id')
    def _clear_ref(self):
        for lead in self:
            lead.internal_ref = False
            
    
    @api.onchange('name')
    def _onchange_name(self):
        for lead in self:
            if lead.type == 'opportunity' and lead.internal_ref:
                lead.name = lead.build_opp_name(lead.internal_ref,lead.name)

    
    @api.onchange('partner_id')
    def _change_am(self):
        for lead in self:
            lead.user_id = lead.guess_am()
    
    @api.one
    def force_reference(self,vals):
        ref = vals['internal_ref']
        client_id = vals.get('partner_id',self.partner_id.id)

        if client_id:
            client = self.env['res.partner'].browse(client_id)
            items = ref.split('-')
            if len(items)==2:
                index = int(items[1])
                if client.altname and (items[0].lower() == client.altname.lower()) and index:
                    if index > client.core_process_index:
                        client.write({
                            'altname':items[0].upper(),
                            'core_process_index':index,
                        })
                    ref = "{}-{:03}".format(items[0].upper(),index)
                    _logger.info("OPP REF FORCED | {}".format(ref))
                    return ref

                else:
                    _logger.info("Opp ref format error | {}".format(ref))
                    return False 
            else:
                _logger.info("Split Error opp ref | {}".format(ref))
                return False
        else:
            _logger.info("No Client found to force opp ref {}".format(ref))
            return False
    
    """@api.depends('partner_id','type')
    def _compute_internal_ref(self):
        for lead in self:
            if lead.partner_id and lead.type=='opportunity': #we compute a ref only for opportunities, not lead
                if not lead.partner_id.altname:
                    _logger.warning("Please document ALTNAME for the client {}".format(lead.partner_id.name))
                else:
                    next_index = lead.partner_id.core_process_index+1 or 1
                    _logger.info("_compute_internal_ref: Core Process increment for {} from {} to {}".format(lead.partner_id.name,lead.partner_id.core_process_index,next_index))
                    #lead.partner_id.write({'core_process_index': next_index})
                    lead.internal_ref = "{}-{:03}".format(lead.partner_id.altname,next_index)
                    lead.name_to_internal_ref(False)"""
                    
    """ @api.onchange('internal_ref')
    def _set_internal_ref(self):
        for lead in self:
            #format checking
            try:
                ref_alt = lead.internal_ref[:-4]
                ref_index = int(lead.internal_ref[-3:])
                if ref_alt.upper() != lead.partner_id.altname.upper():
                    _logger.warning("ALTNAME MISMATCH:{} in company and {} in opportunity {}".format(lead.partner_id.altname.upper(),ref_alt.upper(),lead.name))
                    return
                    #lead.internal_ref = False
                
                if ref_index > lead.partner_id.core_process_index:
                    lead.partner_id.write({'core_process_index': ref_index})
                    _logger.info("_set_internal_ref: Core Process update for {} to {}".format(lead.partner_id.name,ref_index))

            except:
                _logger.warning("Bad Lead Reference syntax: {}".format(lead.internal_ref))
                #lead.internal_ref = False"""


    ################
    # TOOL METHODS #
    ################

    def guess_am(self):
        if self.partner_id.user_id:
            return self.partner_id.user_id
        else:
            return False
    
    def build_opp_name(self,reference=False,name=False):
        _logger.info("Build opp name {} {}".format(reference,name))
        
        #we assume the pipe '|' to be the separator of ref and name
        parts = name.split('| ')
        parts.reverse()
        name_without_ref = parts[0]

        if reference and name_without_ref:
            return "{} | {}".format(reference,name_without_ref)
        elif reference and not name_without_ref:
            return reference
        else:
            return name_without_ref


    @api.multi
    def _create_lead_partner_data(self, name, is_company, parent_id=False):
        """ extract data from lead to create a partner
            :param name : furtur name of the partner
            :param is_company : True if the partner is a company
            :param parent_id : id of the parent partner (False if no parent)
            :returns res.partner record
        """
        data = super()._create_lead_partner_data(name, is_company, parent_id)
        data['country_group_id'] = self.country_group_id.id
        data['referent_id'] = self.referent_id.id
        data['vcls_contact_id'] = self.initial_vcls_contact.id
        data['functional_focus_id'] = self.functional_focus_id.id
        data['partner_seniority_id'] = self.partner_seniority_id.id
        data['industry_id'] = self.industry_id.id
        data['client_activity_ids'] = [(6, 0, self.client_activity_ids.ids)]
        data['client_product_ids'] = [(6, 0, self.client_product_ids.ids)]
        data['linkedin'] = self.linkedIn_url
        data['category_id'] = [(4, self.env.ref('vcls-contact.category_account').id, 0)]
        data['contact_us_message'] = self.contact_us_message
        if is_company:
            data['altname'] = self.altname
        else:
            if self.contact_middlename:
                data.update({
                    "lastname2": self.contact_middlename,
                })
                if 'name' in data:
                    del data['name']
        return data

    @api.multi
    def _convert_opportunity_data(self, customer, team_id=False):
        """ Extract the data from a lead to create the opportunity
            :param customer : res.partner record
            :param team_id : identifier of the Sales Team to determine the stage
        """
        data = super()._convert_opportunity_data(customer, team_id)
        
        """#program integration
        if customer:
            isFirstOpportunity = True if len(self.env['crm.lead'].search([('partner_id','=',customer.id)])) < 0 else False
            if isFirstOpportunity :
                values = {'name': "Opportunity's program for client : {}".format(customer.altName),'client_id':customer.id}
                if customer.expert_id:
                    values = values.update({'leader_id':customer.expert_id}) 
                elif customer.user_id:
                    values = values.update({'leader_id':customer.user_id})
                    
                new_program = self.env['project.program'].create(values)
                data['program_id'] = new_program.id"""
        
        data['country_group_id'] = self.country_group_id.id
        data['referent_id'] = self.referent_id.id
        data['functional_focus_id'] = self.functional_focus_id.id
        data['partner_seniority_id'] = self.partner_seniority_id.id
        data['industry_id'] = self.industry_id.id
        data['client_activity_ids'] = [(6, 0, self.client_activity_ids.ids)]
        data['client_product_ids'] = [(6, 0, self.client_product_ids.ids)]
        data['product_category_id'] = self.product_category_id.id
        data['converted_date'] = datetime.datetime.now()
        data['linkedIn_url'] = self.linkedIn_url
        
        return data

    def _onchange_partner_id_values(self, partner_id):
        #_logger.info("Partner Id Values {}".format(partner_id))
        result = super(Leads, self)._onchange_partner_id_values(partner_id)
        #_logger.info("Partner Id Values RAW {}".format(result))
        if partner_id:
            partner = self.env["res.partner"].browse(partner_id)
            result.update({
                "industry_id": partner.industry_id.id,
                "client_activity_ids": [(6, 0, partner.client_activity_ids.ids)],
                "client_product_ids": [(6, 0, partner.client_product_ids.ids)]
            })
            if not partner.is_company:
                result.update({
                    "contact_middlename": partner.lastname2,
                })
        _logger.info("Partner Id Values END {} - {}".format(self.internal_ref, self.name))
        return result
    
    @api.onchange('contact_name', 'contact_lastname', 'contact_middlename')
    def _compute_partner_name(self):
        for lead in self:
            if lead.type == 'lead':
                if lead.contact_name and lead.contact_lastname:
                    if lead.contact_middlename:
                        lead.name = lead.contact_name + " " + lead.contact_middlename + " " + lead.contact_lastname
                    else:
                        lead.name = lead.contact_name + " " + lead.contact_lastname

    """def all_campaigns_pop_up(self):
        model_id = self.env['ir.model'].search([('model','=','crm.lead')], limit = 1)
        return {
            'name': 'All participated campaigns',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'marketing.participant',
            'type': 'ir.actions.act_window',
            'domain': "[('model_id','=', {}),('res_id','=',{})]".format(model_id.id, self.id)
        }"""
    
    def create_contact_pop_up(self):
        result = self.env['crm.lead'].browse(self.id).handle_partner_assignation('create', False)
        self.partner_id = result.get(self.id)
        partner_object = self.env['res.partner'].browse(self.partner_id.id)
        partner_object.gdpr_status = self.gdpr_status
        partner_object.opted_in = self.opted_in
        partner_object.opted_out = self.opted_out
        return result.get(self.id)
    
    # Copy/Paste in order to redirect to right view (overriden)
    @api.multi
    def redirect_opportunity_view(self):
        self.ensure_one()
        # Get opportunity views
        form_view = self.env.ref('crm.crm_case_form_view_oppor')
        tree_view = self.env.ref('crm.crm_case_tree_view_oppor')
        return {
            'name': _('Opportunity'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'opportunity')],
            'res_id': self.id,
            'view_id': False,
            'views': [
                (form_view.id, 'form'),
                (tree_view.id, 'tree'),
                (False, 'kanban'),
                (False, 'calendar'),
                (False, 'graph')
            ],
            'type': 'ir.actions.act_window',
            'context': {'default_type': 'opportunity'}
        }
    

    @api.onchange('stage_id')
    def _check_won_lost(self):
        if self.stage_id.probability == 100:
            if len(self.won_reasons) == 0:
                raise ValidationError(_("Please use the \"MARK WON\" button or select at least 1 reason."))
    
    risk_raised = fields.Boolean(default = False)

    def raise_go_nogo(self):
        for record in self:
            self.env['risk']._raise_risk(self.env.ref('vcls-crm.risk_go_nogo'), '{},{}'.format(record._name, record.id))
            record.risk_raised = True

    def _compute_risk_ids(self):
        for record in self:
            record.risk_ids = self.env['risk'].search([
                ('resource', '=', 'crm.lead,{}'.format(record.id)),
            ])
            
    def open_related_risks(self):
        return {
            'name': 'All related risk(s)',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'risk',
            'type': 'ir.actions.act_window',
            'domain': "[('resource','=', '{},{}')]".format(self._name, self.id)
        }

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        if self.type == 'opportunity':
            raise ValidationError(_('You cannot duplicate opportunities'))
        return super(Leads, self).copy(default)

    @api.multi
    def create_sp_folder(self):
        self.ensure_one()
        """
        As long as the migration in the new Sharepoint Online is not complete, 
        the client Name should start with AAA (to not interfer in the other folders)
        """
        client_name = "AAA-TEST-" + self.partner_id.altname
        project_name = str(self.internal_ref.split('-', 1)[1].split('|', 1)[0])
        header_to_send = {
            "Content-Type": "application/json",
            "Referrer": "https://vcls.odoo.com/create-sp-folder"
        }
        data_to_send = {
            "client": client_name,
            "project": project_name,
        }
        response = requests.post(URL_POWER_AUTOMATE, data=json.dumps(data_to_send), headers=header_to_send)

        if response.status_code in [200, 202]:
            message = "Success"
            data_back = response.json()
            self.sp_folder = data_back['clientSiteUrl']
            message_log = ("The Sharepoint Folder has been created, here is the link: {}".format(self.sp_folder))
            self.message_post(body=message_log)
            _logger.info("Call API: Power Automate message: {}, whith the client: {} and for the project: {}".format(message, client_name, project_name))
            return

        if response.status_code in [400, 403]:
            _logger.warning("Call API: Power Automate message: {}, whith the client: {} and for the project: {}".format(response.status_code, client_name, project_name))
            raise Warning(_("Sharepoint didn't respond, Please try again"))

        if response.status_code in [500, 501, 503]:
            message = "Server error"
        else:
            message = response.status_code

        _logger.warning("Call API: Power Automate message: {}, whith the client: {} and for the project: {}".format(message, client_name, project_name))
        raise Warning(_("Sharepoint didn't respond, Please try again"))
