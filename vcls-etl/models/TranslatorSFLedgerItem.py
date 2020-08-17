from . import TranslatorSFGeneral
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class KeyNotFoundError(Exception):
    pass

class TranslatorSFLedgerItem(TranslatorSFGeneral.TranslatorSFGeneral):
    def __init__(self,SF):
        super().__init__(SF)
    
    @staticmethod
    def translateToOdoo(SF_LedgerItem, odoo, SF):
        mapOdoo = odoo.env['map.odoo']
        result = {}
        if SF_LedgerItem['s2cor__Ledger_Entry__c']:
            move_id = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_LedgerItem['s2cor__Ledger_Entry__c'],"account.move","LedgerEntry",odoo)
            result['move_id'] = move_id
            move_name = odoo.env['account.move'].search([('id','=',move_id)]).name
            if move_name and SF_LedgerItem['s2cor__Description__c']:
                result['name'] = move_name + " | " + SF_LedgerItem['s2cor__Description__c']
            elif move_name:
                result['name'] = move_name
            elif SF_LedgerItem['s2cor__Description__c']:
                result['name'] = SF_LedgerItem['s2cor__Description__c']

        if SF_LedgerItem['s2cor__Supplier_Tag__c']:
            result['partner_id'] = TranslatorSFLedgerItem.convertSupplierTag(SF,SF_LedgerItem['s2cor__Supplier_Tag__c'],odoo)

        if SF_LedgerItem['s2cor__Ledger_Account__c']:
            result['account_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_LedgerItem['s2cor__Ledger_Account__c'],"account.account","LedgerAccount",odoo)
        result['debit'] = SF_LedgerItem['s2cor__Base_Debit__c']
        result['credit'] = SF_LedgerItem['s2cor__Base_Credit__c']   
        

        result['date'] = SF_LedgerItem['s2cor__Date__c']
        #result['date_maturity'] = SF_LedgerItem['']


        result['convertion_rate'] = SF_LedgerItem['s2cor__Exchange_Rate__c']
        result['currency_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertCurrency(SF_LedgerItem['CurrencyIsoCode'],odoo)
        result['quantity'] = 1.0
        result['ref'] = SF_LedgerItem['Name']

        #result['full_reconcile_id'] / SF_LedgerItem['s2cor__Document_Number_Tag__c']
        if result['account_id']:
            return result
        result['account_id'] = odoo.env['account.account'].search([('code','=','512000-1000')],limit=1).id
        
        return result

    @staticmethod
    def generateLog(SF_LedgerItem):
        result = {
            'model': 'account.move.line',
            'message_type': 'comment',
            'body': '<p>Updated.</p>'
        }

        return result
    @staticmethod
    def translateToSF(Odoo_Item):
        pass

    @staticmethod
    def convertSupplierTag(SF, SfTag, odoo):
        queryType = "SELECT s2cor__Account__c FROM s2cor__Sage_ACC_Tag__c WHERE Id='{}'".format(str(SfTag))
        account = SF.getConnection().query(queryType)['records'][0]['s2cor__Account__c']
        accountId = odoo.env['etl.sync.keys'].search([('externalId','=',str(account))],limit=1)
        if accountId:
            odooAccount = odooAccount = odoo.env['res.partner'].search([('id','=',accountId.odooId)],limit=1)
            if odooAccount:
                return odooAccount.id
        return False

