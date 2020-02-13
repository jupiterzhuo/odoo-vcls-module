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

        _logger.info("{}".format(SF_Opportunity))

        ### DEFAULT VALUES
        result['type'] = 'opportunity'
        
        ### IDENTIFICATION
        result['name'] = SF_Opportunity['Name'] + ' #debug'
        if SF_Opportunity['StageName']:
            result = TranslatorSFOpportunity.convertStageName(SF_Opportunity['StageName'],odoo,mapOdoo,result)

        description = ''
        if SF_Opportunity['Description']:
            description +='Description :\n' + str(SF_Opportunity['Description']) + '\n'
        if SF_Opportunity['Client_Product_Description__c']:
            description +='Client Product Description :\n' +  str(SF_Opportunity['Client_Product_Description__c'])
        if SF_Opportunity['Reasons_Lost_Comments__c']:
            description +='Lost Reason:\n' +  str(SF_Opportunity['Reasons_Lost_Comments__c'])
        result['scope_of_work'] = description
        result['description'] = SF_Opportunity['Significant_Opportunity_Notes__c']  

        result['probability'] = SF_Opportunity['Probability']	
        
        ### RELATIONS
        result['partner_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Opportunity['AccountId'],"res.partner","Account",odoo)
        result['user_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertSfIdToOdooId(SF_Opportunity['OwnerId'],odoo,SF)
        if SF_Opportunity['Technical_Advisor__c']:
            user_id = TranslatorSFGeneral.TranslatorSFGeneral.convertSfIdToOdooId(SF_Opportunity['Technical_Advisor__c'],odoo,SF)
            if user_id:
                employee = odoo.env['hr.employee'].with_context(active_test=False).search([('user_id','=',user_id)],limit=1)
                if employee:
                    result['technical_adv_id'] = employee.id

        ### FINANCIAL
        result['customer_currency_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertCurrency(SF_Opportunity['CurrencyIsoCode'],odoo)
        result['amount_customer_currency'] = SF_Opportunity['Amount']  

        ### DATES
        result['expected_start_date'] = SF_Opportunity['Project_start_date__c']
        result['date_deadline'] = SF_Opportunity['Deadline_for_Sending_Proposal__c']
        result['date_closed'] = SF_Opportunity['CloseDate']
        
        ### OTHER
        result.update(odoo.env['crm.lead']._onchange_partner_id_values(int(result['partner_id']) if result['partner_id'] else False)) 
        result['message_ids'] = [(0, 0, TranslatorSFOpportunity.generateLog(SF_Opportunity))]
        result['log_info'] = SF_Opportunity['Name']

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

        return result



    