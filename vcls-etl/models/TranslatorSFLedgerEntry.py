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

        if SF_LedgerEntry['s2cor__Layer__c'] == 'Actual Deleted':
            result['state'] = 'draft'
        else:
            result['state'] = 'posted'

        result['journal_id'] = TranslatorSFLedgerEntry.getJournalId(SF,SF_LedgerEntry['Id'],odoo,SF_LedgerEntry['s2cor__Source_Document__c'],SF_LedgerEntry['s2cor__Date__c'])
        result['currency_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertCurrency(SF_LedgerEntry['CurrencyIsoCode'],odoo)
        result['company_id'] = odoo.env.ref('vcls-hr.company_VCINC').id

        if SF_LedgerEntry['s2cor__Supplier_Tag__c']:
            accountId = TranslatorSFLedgerEntry.convertSupplierTag(SF,SF_LedgerEntry['s2cor__Supplier_Tag__c'],odoo)
            partnerId = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(accountId, 'res.partner', 'Account', odoo)
            if partnerId:
                result['partner_id'] = partnerId
            else:
                contactId = TranslatorSFLedgerEntry.createContact(odoo, SF, accountId)
                result['partner_id'] = contactId
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
        if account:
            return account
        return False
    
    @staticmethod
    def getJournalId(SF, SfId, odoo, SourceDocument, Date):
        sale = False
        queryAccount = "SELECT s2cor__Ledger_Account__c FROM s2cor__Sage_ACC_Ledger_Item__c WHERE s2cor__Ledger_Entry__c ='{}'".format(str(SfId))
        ledgerItem = SF.getConnection().query(queryAccount)['records']
        mapOdoo = odoo.env['map.odoo']
        if len(ledgerItem)>0:
            for item in ledgerItem:
                if item['s2cor__Ledger_Account__c']:
                    queryAccountNumber = "SELECT s2cor__Account_Number__c FROM s2cor__Sage_ACC_Ledger_Account__c WHERE Id ='{}'".format(str(item['s2cor__Ledger_Account__c']))
                    accountNumber = SF.getConnection().query(queryAccountNumber)['records']
                    if len(accountNumber)>0:
                        if accountNumber[0]['s2cor__Account_Number__c']:
                            if accountNumber[0]['s2cor__Account_Number__c'].startswith('512000'):
                                return mapOdoo.convertRef('Voisin Consulting INC BOA ($)',odoo,'account.journal',False)
                            elif accountNumber[0]['s2cor__Account_Number__c'].startswith('7'):
                                sale = mapOdoo.convertRef('Customer Invoices',odoo,'account.journal',False)
        if sale:
            return sale
        elif SourceDocument == 'Manual Adjustment':
            return mapOdoo.convertRef('Miscellaneous Operations',odoo,'account.journal',False)
        else:
            return mapOdoo.convertRef('Vendor Bills',odoo,'account.journal',False)

    @staticmethod
    def createContact(odoo, SF, accountId):
        translator = odoo.env['etl.salesforce.account'].getSFTranslator(SF)
        queryAccount = odoo.env.ref('vcls-etl.etl_sf_account_query').value + " WHERE Id = '{}'".format(accountId)
        records = SF.getConnection().query_all(queryAccount)['records'][0]
        attributes = translator.translateToOdoo(records, odoo, SF)
        if attributes:
            odoo_id = odoo.env['res.partner'].with_context(tracking_disable=1).create(attributes).id
            key = odoo.env['etl.sync.keys'].create({
                'state' : 'upToDate',
                'externalId' : accountId,
                'odooId': odoo_id,
                'externalObjName': 'Account',
                'odooModelName': 'res.partner',
                'search_value': 'ledger',
            })
            _logger.info("ETL | Record Created {} | {}".format(key.externalObjName,attributes.get('log_info')))
            return odoo_id
        else:
            _logger.info("ETL | Missing Mandatory info to process key {} - {}".format('Account',accountId))
            return False

    @staticmethod
    def createItems(entryId, sync, sfInstance):
        dictCreate = []
        counter = 0
        translator = sync.env['etl.salesforce.ledgeritem'].getSFTranslator(sfInstance)
        queryItems = sync.env.ref('vcls-etl.etl_sf_ledgeritem_query').value + " WHERE s2cor__Ledger_Entry__c = '{}'".format(entryId)
        records = sfInstance.getConnection().query_all(queryItems)['records']
        for sf_rec in records:
            attributes = translator.translateToOdoo(sf_rec, sync, sfInstance)
            if attributes:
                dictCreate.append(dict(attributes))
            counter += 1
        
        if dictCreate:
            sync.env['account.move.line'].create(dictCreate)
            _logger.info("ETL | Records Created  {} | {}".format('LedgerItem',attributes.get('log_info')))


