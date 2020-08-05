from . import TranslatorSFGeneral
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class KeyNotFoundError(Exception):
    pass

class TranslatorSFLedgerAccount(TranslatorSFGeneral.TranslatorSFGeneral):
    def __init__(self,SF):
        super().__init__(SF)
    
    @staticmethod
    def translateToOdoo(SF_LedgerAccount, odoo, SF):
        mapOdoo = odoo.env['map.odoo']
        result = {}

        
        key = odoo.env['etl.sync.keys'].search([('externalId','=',str(SF_LedgerAccount['Id']))],limit=1)
        if key.state == "needCreateOdoo":
            account = odoo.env['account.account'].search([('code','=',str(SF_LedgerAccount['s2cor__Account_Number__c']))],limit=1)
            if account:
                key = odoo.env['etl.sync.keys'].search([('externalId','=',str(SF_LedgerAccount['Id']))],limit=1)
                key.write({'state':'upToDate','odooId':str(account.id)})
                return False


        code = SF_LedgerAccount['s2cor__Account_Number__c']

        if code:
            result['code'] = SF_LedgerAccount['s2cor__Account_Number__c']
            result['name'] = SF_LedgerAccount['s2cor__Description__c']
            result['display_name'] = SF_LedgerAccount['Name']
            type_id = TranslatorSFLedgerAccount.convertType(SF, SF_LedgerAccount['s2cor__Parent__c'], odoo)
            print(type_id)
            result['user_type_id'] = type_id
            result['company_id'] = odoo.env.ref('vcls-hr.company_VCINC').id

            #Allow Reconciliation
            result['reconcile'] = True
            return result
        return False
    @staticmethod
    def convertType(SF, SfParent, odoo):
        queryType = "Select Name FROM s2cor__Sage_ACC_Ledger_Account__c WHERE id='{}'".format(str(SfParent))
        typeName = SF.getConnection().query(queryType)['records'][0]['Name']
        print(typeName)
        accountType = odoo.env['account.account.type'].search([('name','=ilike',typeName)],limit=1)
        if accountType:
            return accountType.id
        type_list = typeName.split()
        accountType = odoo.env['account.account.type'].search([('name','=ilike',type_list[-1])],limit=1)
        if accountType:
            return accountType.id
        return False

    @staticmethod
    def generateLog(SF_LedgerAccount):
        result = {
            'model': 'account.account',
            'message_type': 'comment',
            'body': '<p>Updated.</p>'
        }

        return result
    @staticmethod
    def translateToSF(Odoo_Account):
        pass
    