from . import TranslatorSFGeneral
import logging
_logger = logging.getLogger(__name__)

class KeyNotFoundError(Exception):
    pass

class TranslatorSFOpportunity(TranslatorSFGeneral.TranslatorSFGeneral):
    def __init__(self,SF):
        super().__init__(SF)
    
    @staticmethod
    def translateToOdoo(SF_Opportunity, odoo, SF):
        mapOdoo = odoo.env['map.odoo']
        result = {}

        context = odoo.env.context

        #_logger.info("{}".format(SF_Opportunity))
        if SF_Opportunity['LeadSource']:
            result['marketing_project_id'] = mapOdoo.convertRef(SF_Opportunity['LeadSource'],odoo,'project.project',False)
        
        if context.get('custom_context')=='small_update':
            result['log_info'] = 'small_update {}'.format(SF_Opportunity['LeadSource'])
            return result

        ### DEFAULT VALUES
        result['type'] = 'opportunity'
        
        ### IDENTIFICATION
        result['name'] = SF_Opportunity['Name']
        if SF_Opportunity['StageName']:
            result = TranslatorSFOpportunity.convertStageName(SF_Opportunity['StageName'],odoo,mapOdoo,result)

        description = ''
        if SF_Opportunity['Description']:
            description +='Description :\n' + str(SF_Opportunity['Description']) + '\n'
        if SF_Opportunity['Client_Product_Description__c']:
            description +='Client Product Description :\n' +  str(SF_Opportunity['Client_Product_Description__c'])
        if SF_Opportunity['Reasons_lost__c']:
            result['lost_reasons']=[(6, 0, mapOdoo.convertRef(SF_Opportunity['Reasons_lost__c'],odoo,'crm.lost.reason',True))]
        if SF_Opportunity['Reasons_Lost_Comments__c']:
            description +='Lost Reason:\n' +  str(SF_Opportunity['Reasons_Lost_Comments__c'])
        result['scope_of_work'] = description
        result['description'] = SF_Opportunity['Significant_Opportunity_Notes__c']  

        result['probability'] = SF_Opportunity['Probability']	

        if SF_Opportunity['Proposal_Type__c']:
            result['proposal_type'] = TranslatorSFOpportunity.convert_opp_type(SF_Opportunity['Proposal_Type__c'])
        
        if SF_Opportunity['Significant_Opportunity__c']:
            tag = TranslatorSFOpportunity.get_tag_id(odoo,SF_Opportunity['Significant_Opportunity__c'])
            _logger.info("SIG OPP {} TAG {}".format(SF_Opportunity['Significant_Opportunity__c'],tag))
            if tag:
                result['tag_ids'] =  [(4, tag, 0)]
        
        ### RELATIONS
        result['partner_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Opportunity['AccountId'],"res.partner","Account",odoo)
        # we manage the case of non, exisitng account > will be created later
        if not result['partner_id']:
            return False

        result['user_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertSfIdToOdooId(SF_Opportunity['OwnerId'],odoo,SF)
        if SF_Opportunity['Technical_Advisor__c']:
            user_id = TranslatorSFGeneral.TranslatorSFGeneral.convertSfIdToOdooId(SF_Opportunity['Technical_Advisor__c'],odoo,SF)
            if user_id:
                employee = odoo.env['hr.employee'].with_context(active_test=False).search([('user_id','=',user_id)],limit=1)
                if employee:
                    result['technical_adv_id'] = employee.id
        if SF_Opportunity['Proposal_Writer__c']:
            result['proposal_writer_id'] = mapOdoo.convertRef(SF_Opportunity['Proposal_Writer__c'], odoo, 'hr.employee', False)

        ### FINANCIAL
        result['customer_currency_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertCurrency(SF_Opportunity['CurrencyIsoCode'],odoo)
        result['amount_customer_currency'] = SF_Opportunity['Amount']  

        ### DATES
        result['expected_start_date'] = SF_Opportunity['Project_start_date__c']
        result['date_deadline'] = SF_Opportunity['Deadline_for_Sending_Proposal__c']
        result['date_closed'] = SF_Opportunity['CloseDate']

        if SF_Opportunity['CampaignId']:
            result['marketing_task_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Opportunity['CampaignId'],"project.task","Campaign",odoo)
        ### OTHER
        #result.update(odoo.env['crm.lead']._onchange_partner_id_values(int(result['partner_id']) if result['partner_id'] else False)) 
        result['message_ids'] = [(0, 0, TranslatorSFOpportunity.generateLog(SF_Opportunity))]
        result['log_info'] = SF_Opportunity['Name']
        
        if SF_Opportunity['ContractId']:
            result['agreement_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Opportunity['ContractId'],"agreement","Contract",odoo)

        return result

    @staticmethod
    def generateLog(SF_Opportunity):
        result = {
            'model': 'crm.lead',
            'message_type': 'comment',
            'body': '<p>Salesforce Synchronization</p>'
        }

        return result
    @staticmethod
    def translateToSF(Odoo_Account):
        pass
    
    @staticmethod
    def convertStageName(StageName,odoo,mapOdoo,result):
        if StageName == 'Closed Won':
            result['won_status'] = 'won'
            result['probability'] = 100
            stage_id = odoo.env['crm.stage'].search([('name','=','Closed Won')]).id
            if stage_id:
                result['stage_id'] = stage_id
        elif StageName == 'Closed Lost':
            result['won_status'] = 'lost'
            result['probability'] = 0
            result['active'] = False
        else:
            result['won_status'] = 'pending'
            result['stage_id'] = mapOdoo.convertRef(StageName,odoo,'crm.stage',False)
            _logger.info("STAGE CRM {}".format(result['stage_id']))

        return result
    
    @staticmethod
    def convert_opp_type(opp_type):
        if opp_type == 'Email Proposal':
            result = 'email'
        elif opp_type == 'Simple Proposal':
            result = 'simple'
        elif opp_type == 'Complex Proposal':
            result = 'complex'
        else:
            result = False
        return result

    @staticmethod
    def get_tag_id(odoo,tag_name="NoTag"):
        tag = odoo.env['crm.lead.tag'].search([('name','=',tag_name)],limit=1)
        if tag:
            return tag.id
        else:
            return False



    