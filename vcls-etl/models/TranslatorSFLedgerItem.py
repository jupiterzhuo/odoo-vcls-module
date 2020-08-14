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
    def translateToOdoo(SF_LedgerItem, odoo, SF, ID):
        mapOdoo = odoo.env['map.odoo']
        result = {}
        if ID:
            SF_LedgerItem['id'] = ID
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
        print(result)
        if result['account_id']:
            return result
        result['account_id'] = odoo.env['account.account'].search([('code','=','512000-1000')],limit=1).id
        
        return result

    @staticmethod
    def createItem(SF, odoo):
        to_process = odoo.env['etl.sync.keys'].search([('state','not in',['upToDate','postponed']),('odooModelName','=','account.move.line')])
        dictCreate = []
        if to_process:
            template = to_process[0]
            _logger.info("ETL | Found {} {} keys {} ".format(len(to_process),template.externalObjName,template.state))
            counter = 0
            query_id = "vcls-etl.etl_sf_{}_query".format(template.externalObjName.lower())
            filter_id = "vcls-etl.etl_sf_{}_filter".format(template.externalObjName.lower())
            postfilter_id = "vcls-etl.etl_sf_{}_post".format(template.externalObjName.lower())
            sql = odoo.env['etl.sync.keys'].build_sql(odoo.env.ref(query_id).value,[odoo.env.ref(filter_id).value,odoo.env.ref("vcls-etl.etl_sf_time_filter").value],odoo.env.ref(postfilter_id).value)

            records = SF.getConnection().query_all(sql)['records']
            if records:
                _logger.info("ETL |  {} returned {} records from SF".format(sql,len(records)))
                #we start the processing loop
                for sf_rec in records:
                    key = to_process.filtered(lambda p: p.externalId == sf_rec['Id'])
                    if key:
                        counter += 1
                        attributes = TranslatorSFLedgerItem.translateToOdoo(sf_rec, odoo, SF, key[0].odooId)

                        if not attributes:
                            if key[0].state != 'upToDate':
                                key[0].write({'state':'postponed','priority':0})
                                _logger.info("ETL | Missing Mandatory info to process key {} - {}".format(key[0].externalObjName,key[0].externalId))
                            else:
                                _logger.info("ETL | Record already exist {} - {}".format(key[0].externalObjName,key[0].externalId))
                            continue
                        #UPDATE Case
                        if key[0].state == 'needUpdateOdoo':
                            #we catch the existing record
                            o_rec = odoo.env[key[0].odooModelName].with_context(active_test=False).search([('id','=',key[0].odooId)],limit=1)
                            if o_rec:
                                #if attributes.get('active',False):
                                    #rem = attributes.pop('active')
                                entry = odoo.env['account.move'].browse(attributes['move_id'])
                                if entry:
                                    entry.state = 'draft'
                                    o_rec.with_context(tracking_disable=1).write(attributes)
                                    key[0].write({'state':'upToDate','priority':0})
                                    entry.state = 'posted'
                                    _logger.info("ETL | Record Updated {}/{} | {} | {}".format(counter,len(to_process),key[0].externalObjName,attributes.get('log_info')))
                            else:
                                key[0].write({'state':'upToDate','priority':0})
                                _logger.info("ETL | Missed Update - Odoo record not found {}/{} | {} | {}".format(counter,len(to_process),key[0].odooModelName,key[0].odooId))
                        
                        #CREATE Case
                        elif key[0].state == 'needCreateOdoo':
                            #odoo_id = odoo.env[key[0].odooModelName].with_context(tracking_disable=1).create(attributes).id
                            dictCreate.append(dict(attributes))
                            #key[0].write({'state':'upToDate','priority':0})
                            _logger.info("ETL | Record Created {}/{} | {} | {}".format(counter,len(to_process),key[0].externalObjName,attributes.get('log_info')))

                        else:
                            _logger.info("ETL | Non-managed key state {} | {}".format(key[0].id,key[0].state))
        if dictCreate:
            odoo.env['account.move.line'].create(dictCreate)
        TranslatorSFLedgerItem.updateKeysItem(SF, odoo)

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

    @staticmethod
    def updateKeysItem(SF, odoo):
        to_process = odoo.env['etl.sync.keys'].search([('state','not in',['upToDate','postponed']),('odooModelName','=','account.move.line')])
        if to_process:
            sql = "SELECT Id, Name FROM s2cor__Sage_ACC_Ledger_Item__c"
            records = SF.getConnection().query_all(sql)['records']
            for sf_rec in records:
                key = to_process.filtered(lambda p: p.externalId == sf_rec['Id'])
                if key:
                    if key[0].state == 'needCreateOdoo':
                        odoo_id = odoo.env['account.move.line'].search([('ref','=',sf_rec['Name'])]).id
                        if odoo_id:
                            key[0].write({'state':'upToDate','odooId':odoo_id,'priority':0})

