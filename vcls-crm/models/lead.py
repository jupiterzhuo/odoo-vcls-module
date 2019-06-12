# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError, Warning

import logging
_logger = logging.getLogger(__name__)

class Leads(models.Model):

    _inherit = 'crm.lead'

    ###################
    # DEFAULT METHODS #
    ###################

    def _default_am(self):
        return self.guess_am()
    
    ### CUSTOM FIELDS RELATED TO MARKETING PURPOSES ###
    user_id = fields.Many2one(
        'res.users', 
        string='Account Manager', 
        track_visibility='onchange', 
        #default='_default_am',
        )

    country_group_id = fields.Many2one(
        'res.country.group',
        string = "Geographic Area",
        compute = '_compute_country_group',
    )

    referent_id = fields.Many2one(
        'res.partner',
        string = 'Referent',
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

    product_category_id = fields.Many2one(
        'product.category',
        string = 'Business Line',
        domain = "[('parent_id','=',False)]"
    )

    #date fields
    expected_start_date = fields.Date(
        string="Expected Project Start Date",
    )

    won_reason = fields.Many2one('crm.won.reason', string='Won Reason', index=True, track_visibility='onchange')

    internal_ref = fields.Char(
        string="Ref",
        #readonly = True,
        store = True,
        compute = '_compute_internal_ref',
        inverse = '_set_internal_ref',
    )

    ###################
    # COMPUTE METHODS #
    ###################

    @api.depends('country_id')
    def _compute_country_group(self):
        for lead in self:
            groups = lead.country_id.country_group_ids
            if groups:
                lead.country_group_id = groups[0]
    
    """@api.onchange('partner_id','country_id')
    def _change_am(self):
        for lead in self:
            lead.user_id = lead.guess_am()"""
    
    @api.depends('partner_id','partner_id.altname','type')
    def _compute_internal_ref(self):
        for lead in self:
            if lead.partner_id and lead.type=='opportunity': #we compute a ref only for opportunities, not lead
                if not lead.partner_id.altname:
                    _logger.warning("Please document ALTNAME for the client {}".format(lead.partner_id.name))
                else:
                    next_index = lead.partner_id.core_process_index+1 or 1
                    lead.partner_id.core_process_index = next_index
                    lead.internal_ref = "{}-{:03}".format(lead.partner_id.altname,next_index)
    
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
                    lead.partner_id.core_process_index = ref_index

            except:
                _logger.warning("Bad Lead Reference syntax: {}".format(lead.internal_ref))
                #lead.internal_ref = False



    ################
    # TOOL METHODS #
    ################

    def guess_am(self):
        if self.partner_id.user_id:
            return self.partner_id.user_id
        elif self.country_group_id.default_am:
            return self.country_group_id.default_am
        #elif self.team_id.
        else:
            return False

    def name_to_internal_ref(self):
        for lead in self:
            #we verify if the format is matching expectations
            try:
                offset = lead.name.upper().find(lead.partner_id.altname.upper())
                if offset != -1:
                    index = int(lead.name[offset+len(lead.partner_id.altname)+1:offset+len(lead.partner_id.altname)+4])
                    lead.name = "{}-{:03}{}".format(lead.partner_id.altname.upper(),index,lead.name[offset+len(lead.partner_id.altname)+4:])
                    lead.internal_ref = "{}-{:03}".format(lead.partner_id.altname.upper(),index)

            except:
                _logger.info("Unable to extract ref from opp name {}".format(lead.name))


    @api.multi
    def _create_lead_partner_data(self, name, is_company, parent_id=False):
        """ extract data from lead to create a partner
            :param name : furtur name of the partner
            :param is_company : True if the partner is a company
            :param parent_id : id of the parent partner (False if no parent)
            :returns res.partner record
        """
        data = super()._create_lead_partner_data(name,is_company,parent_id)
        data['country_group_id'] = self.country_group_id
        data['referent_id'] = self.referent_id
        data['functional_focus_id'] = self.functional_focus_id
        data['partner_seniority_id'] = self.partner_seniority_id
        data['industry_id'] = self.industry_id
        data['client_activity_ids'] = self.client_activity_ids
        data['client_product_ids'] = self.client_product_ids

        return data

    @api.multi
    def _convert_opportunity_data(self, customer, team_id=False):
        """ Extract the data from a lead to create the opportunity
            :param customer : res.partner record
            :param team_id : identifier of the Sales Team to determine the stage
        """
        data = super()._convert_opportunity_data(customer, team_id)
        data['country_group_id'] = self.country_group_id
        data['referent_id'] = self.referent_id
        data['functional_focus_id'] = self.functional_focus_id
        data['partner_seniority_id'] = self.partner_seniority_id
        data['industry_id'] = self.industry_id
        data['client_activity_ids'] = self.client_activity_ids
        data['client_product_ids'] = self.client_product_ids
        data['product_category_id'] = self.product_category_id
        
        return data