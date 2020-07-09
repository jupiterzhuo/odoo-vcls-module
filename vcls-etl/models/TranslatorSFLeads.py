from . import TranslatorSFGeneral
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class KeyNotFoundError(Exception):
    pass

class TranslatorSFLeads(TranslatorSFGeneral.TranslatorSFGeneral):
    def __init__(self,SF):
        super().__init__(SF)
    
    @staticmethod
    def translateToOdoo(SF_Leads, odoo, SF):
        mapOdoo = odoo.env['map.odoo']
        result = {}

        context = odoo.env.context

        # We process the key updates required by Marketing
        
        if SF_Leads['Inactive_Lead__c']:
            result['active'] = False
        else:
            result['active'] = True

        if SF_Leads['Opted_In__c']:
            result['opted_in'] = True
            result['gdpr_status'] = 'in'
        if SF_Leads['Unsubscribed_from_Marketing_Comms__c']:
            if SF_Leads['Unsubscribed_from_Marketing_Comms__c'] == 'Unsubscribed':
                result['opted_in'] = False
                result['gdpr_status'] = 'out'
        if SF_Leads['Content_Name__c']:
            result['content_name'] = SF_Leads['Content_Name__c']
                	
        if context.get('custom_context')=='small_update':
            result['log_info'] = 'small_update {}'.format(result['active'])
            return result

        ### IDENTIFICATION
        result['type'] = 'lead'
        if SF_Leads['Salutation']:
            result['title'] = mapOdoo.convertRef(SF_Leads['Salutation'], odoo,'res.partner.title',False)
        if SF_Leads['FirstName']:
            result['contact_name'] = SF_Leads['FirstName']
        if SF_Leads['MiddleName']:
            if SF_Leads['MiddleName'] != 'None':
                result['contact_middlename'] = SF_Leads['MiddleName']
        if SF_Leads['LastName']:
            result['contact_lastname'] = SF_Leads['LastName']

        temp = "{} {} {}".format(result.get('contact_name',''),result.get('contact_middlename',''),result.get('contact_lastname',''))
        result['name'] = temp.replace('  ',' ')

        if SF_Leads['OwnerId']:
            result['user_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertSfIdToOdooId(SF_Leads['OwnerId'],odoo,SF)

        result['description'] = ''
        if SF_Leads['Description']:
            result['description'] += 'Description : \n' + str(SF_Leads['Description']) + '\n'
        if SF_Leads['Initial_Product_Interest__c']:
            result['description'] += 'Initial Interest : \n' + str(SF_Leads['Initial_Product_Interest__c']) + '\n'

        if SF_Leads['LeadSource']:
            result['marketing_project_id'] = mapOdoo.convertRef(SF_Leads['LeadSource'],odoo,'project.project',False)

        result = TranslatorSFLeads.partner_finder(result,SF_Leads,odoo)
        

        if SF_Leads['Activity__c']:
            result['client_activity_ids'] =  [(6, 0, mapOdoo.convertRef(SF_Leads['Activity__c'],odoo,'client.activity',True))]
        if SF_Leads['Product_Type__c']:
            result['client_product_ids'] = [(6, 0, mapOdoo.convertRef(SF_Leads['Product_Type__c'],odoo,'client.product',True))]
        
        result['phone'] = SF_Leads['Phone']
        result['website'] =  SF_Leads['Website']
        result['city'] = SF_Leads['City']
        result['zip'] = SF_Leads['PostalCode']
        result['street'] = SF_Leads['Street']
        if SF_Leads['Country']:
            result['country_id'] = mapOdoo.convertRef(SF_Leads['Country'],odoo,'res.country',False)
        if SF_Leads['State']:
            result['state_id'] = mapOdoo.convertRef(SF_Leads['State'],odoo,'res.country.state',False)
        if SF_Leads['Status']:
            result['lead_stage_id'] = mapOdoo.convertRef(SF_Leads['Status'],odoo,'crm.lead.stage',False)

        if SF_Leads['Rating']:
            result['priority'] = TranslatorSFLeads.convertRating(SF_Leads)

        result['customer_currency_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertCurrency(SF_Leads['CurrencyIsoCode'],odoo)
        if SF_Leads['First_VCLS_Contact_Point__c']:
            result['initial_vcls_contact'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Leads['First_VCLS_Contact_Point__c'],"res.partner","Contact", odoo)
        if SF_Leads['External_Referee__c']:
            result['referent_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Leads['External_Referee__c'], "res.partner", "Contact", odoo)
        #fax
        if SF_Leads['Functional_Focus__c']:
            result['functional_focus_id'] = mapOdoo.convertRef(SF_Leads['Functional_Focus__c'],odoo,'partner.functional.focus',False)
        
        if SF_Leads['Industry']:
            result['industry_id'] = mapOdoo.convertRef(SF_Leads['Industry'],odoo,'res.partner.industry',False)
        result['contact_us_message'] = SF_Leads['Contact_us_Message__c']
        result['function'] = SF_Leads['Title']
        if SF_Leads['Seniority__c']:
            result['partner_seniority_id'] = mapOdoo.convertRef(SF_Leads['Seniority__c'], odoo,'partner.seniority',False)
        result['message_ids'] = [(0, 0, TranslatorSFLeads.generateLog(SF_Leads))]

        #_logger.info("TRANSLATOR LEAD {}".format(result))
        if SF_Leads['Opt_in_Campaign__c']:
            result['marketing_task_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Leads['Opt_in_Campaign__c'],"project.task","Campaign",odoo)
        if SF_Leads['Unsubscribe_Campaign__c']:
            result['marketing_task_out_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Leads['Unsubscribe_Campaign__c'],"project.task","Campaign",odoo)
        result['conversion_date'] = SF_Leads['ConvertedDate']
        if SF_Leads['LinkedIn_Profile__c']:
            result['linkedin_url'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUrl(SF_Leads['LinkedIn_Profile__c'])
        
        
        result['log_info'] = result['name']

        return result
    
    @staticmethod
    def partner_finder(result,SF,odoo):
        if SF['Email']:
            #we look for an existing partner
            result['email_from'] = SF['Email']
            existing = odoo.env['res.partner'].search([('email','=ilike',SF['Email'])],limit=1)
            if existing:
                _logger.info("Found existing Lead Partner {}".format(existing.email))
                result['partner_id'] = existing.id
            else:
                #we try to find if the company exists
                company = odoo.env['res.partner'].search([('is_company','=',True),('name','=ilike',SF['Company'])],limit=1)
                if company:
                    _logger.info("Found existing Company {}".format(company.name))
                    result['partner_id'] = company.id
                else:
                    result['partner_name'] = SF['Company']

        return result
    
    @staticmethod
    def convertRating(SF):
        if SF['Rating'] == 'Hot':
            return '3'
        elif SF['Rating'] == 'Warm':
            return '2'
        elif SF['Rating'] == 'Cold': 
            return '1'
        else:
            return '0'
    
    @staticmethod
    def generateLog(SF_Leads):
        result = {
            'model': 'crm.lead',
            'message_type': 'comment',
            'body': '<p>Updated.</p>'
        }

        return result
    @staticmethod
    def translateToSF(Odoo_Account):
        pass
    