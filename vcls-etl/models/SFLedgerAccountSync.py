from . import TranslatorSFLedgerAccount
from . import ETL_SF
from . import generalSync

import pytz
from simple_salesforce import Salesforce
from tzlocal import get_localzone
from datetime import datetime
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


from odoo import models, fields, api

class SFLedgerAccountSync(models.Model):
    _name = 'etl.salesforce.ledgeraccount'
    _inherit = 'etl.sync.salesforce'

    def getSFTranslator(self, sfInstance):
        return TranslatorSFLedgerAccount.TranslatorSFLedgerAccount(sfInstance.getConnection())


    def getSQLForKeys(self):
        sql =  'SELECT Id, LastModifiedDate '
        sql += 'FROM s2cor__Sage_ACC_Ledger_Account__c'
        return sql
    
    def getSQLForRecord(self):
        sql = self.env.ref('vcls-etl.etl_sf_ledger_account_query').value
        _logger.info(sql)
        return sql

    def getModifiedRecordsOdoo(self):
        return self.env['account.account'].search([('write_date','>', self.getStrLastRun())])
    
    def getAllRecordsOdoo(self):
        return self.env['account.account'].search([])

    def getKeysFromOdoo(self):                
        return self.env['etl.sync.keys'].search([('odooModelName','=','account.account'),('externalObjName','=','Ledger_Account')])
    
    def getKeysToUpdateOdoo(self):
        return self.env['etl.sync.keys'].search([('odooModelName','=','account.account'),('externalObjName','=','Ledger_Account'),'|',('state','=','needCreateOdoo'),('state','=','needUpdateOdoo')])
    
    def getKeysToUpdateExternal(self):
        return self.env['etl.sync.keys'].search([('odooModelName','=','account.account'),('externalObjName','=','Ledger_Account'),'|',('state','=','needCreateExternal'),('state','=','needUpdateExternal')])

    
    def createKey(self, odooId, externalId):
        values = {'odooModelName':'account.account','externalObjName':'Ledger_Account'}
        if odooId:
            values.update({'odooId': odooId, 'state':'needCreateExternal'})
        elif externalId:
            values.update({'externalId':externalId, 'state':'needCreateOdoo'})
        self.env['etl.sync.keys'].create(values)

    def getExtModelName(self):
        return "Ledger_Account"
