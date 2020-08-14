from . import TranslatorSFGeneral
from odoo.exceptions import UserError, ValidationError
import logging
import datetime
_logger = logging.getLogger(__name__)

class KeyNotFoundError(Exception):
    pass

class TranslatorSFLedgerEntry(TranslatorSFGeneral.TranslatorSFGeneral):
    def __init__(self,SF):
        super().__init__(SF)
    
    @staticmethod
    def translateToOdoo(SF_LedgerEntry, odoo, SF):
        mapOdoo = odoo.env['map.odoo']
        result = {}

        result['name'] = SF_LedgerEntry['Name']
        result['date'] = SF_LedgerEntry['s2cor__Date__c']
        result['ref'] = SF_LedgerEntry['s2cor__Sequence_Number__c']
        result['state'] = 'posted'

        result['journal_id'] = TranslatorSFLedgerEntry.getJournalId(SF,SF_LedgerEntry['Id'],odoo,SF_LedgerEntry['s2cor__Source_Document__c'],SF_LedgerEntry['s2cor__Date__c'])
        result['currency_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertCurrency(SF_LedgerEntry['CurrencyIsoCode'],odoo)
        result['company_id'] = odoo.env.ref('vcls-hr.company_VCINC').id

        if SF_LedgerEntry['s2cor__Supplier_Tag__c']:
            result['partner_id'] = TranslatorSFLedgerEntry.convertSupplierTag(SF,SF_LedgerEntry['s2cor__Supplier_Tag__c'],odoo)

        return result

    @staticmethod
    def generateLog(SF_LedgerEntry):
        result = {
            'model': 'account.move',
            'message_type': 'comment',
            'body': '<p>Updated.</p>'
        }

        return result
    @staticmethod
    def translateToSF(Odoo_Entry):
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
    
    @staticmethod
    def getJournalId(SF, SfId, odoo, SourceDocument, Date):
        sale = False
        bill = False
        queryAccount = "SELECT s2cor__Ledger_Account__c FROM s2cor__Sage_ACC_Ledger_Item__c WHERE s2cor__Ledger_Entry__c ='{}'".format(str(SfId))
        ledgerItem = SF.getConnection().query(queryAccount)['records']
        if len(ledgerItem)>0:
            for item in ledgerItem:
                if item['s2cor__Ledger_Account__c']:
                    queryAccountNumber = "SELECT s2cor__Account_Number__c FROM s2cor__Sage_ACC_Ledger_Account__c WHERE Id ='{}'".format(str(item['s2cor__Ledger_Account__c']))
                    accountNumber = SF.getConnection().query(queryAccountNumber)['records']
                    if len(accountNumber)>0:
                        if accountNumber[0]['s2cor__Account_Number__c']:
                            if accountNumber[0]['s2cor__Account_Number__c'].startswith('512000'):
                                return odoo.env.ref('vcls-etl.bank_of_america').id
                            if accountNumber[0]['s2cor__Account_Number__c'].startswith('7'):
                                sale = odoo.env.ref('vcls-etl.sales_journal').id
                            if accountNumber[0]['s2cor__Account_Number__c'].startswith('401') and Date < "2020-01-01":
                                bill = odoo.env.ref('vcls-etl.billed_journal').id
        if sale:
            return sale
        elif SourceDocument == 'Manual Adjustment':
            return odoo.env.ref('vcls-etl.manual_adjustment').id
        elif bill:
            return bill
        else:
            return odoo.env.ref('vcls-etl.purchase_journal').id

        