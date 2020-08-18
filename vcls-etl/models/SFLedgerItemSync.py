from . import TranslatorSFLedgerItem
from . import TranslatorSFGeneral
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

class SFLedgerItemSync(models.Model):
    _name = 'etl.salesforce.ledgeritem'
    _inherit = 'etl.sync.salesforce'

    def getSFTranslator(self, sfInstance):
        return TranslatorSFLedgerItem.TranslatorSFLedgerItem(sfInstance.getConnection())

    def reconciledEntries(self, duration=10):
        userSF = self.env.ref('vcls-etl.SF_mail').value
        passwordSF = self.env.ref('vcls-etl.SF_password').value
        token = self.env.ref('vcls-etl.SF_token').value
        sfInstance = ETL_SF.ETL_SF.getInstance(userSF, passwordSF, token)

        timestamp_end = datetime.now() + timedelta(minutes=duration) - timedelta(seconds=10)

        sql = "Select Id, Name, s2cor__Document_Number_Tag__c, s2cor__Ledger_Account__c, s2cor__Date__c From s2cor__Sage_ACC_Ledger_Item__c"
        records = sfInstance.getConnection().query_all(sql)['records']
        inc_id = self.env.ref('vcls-hr.company_VCINC').id
        keys = self.env['account.move.line'].search([('company_id','=',inc_id), ('full_reconcile_id','=',False)])
        if records and keys:
            counter = 0
            for sf_rec in records:
                if datetime.now()>timestamp_end:
                    break
                else:
                    counter += 1
                    key = keys.filtered(lambda p: p.ref == sf_rec['Name'])
                    if key:
                        if sf_rec['s2cor__Document_Number_Tag__c']:
                            reconciled = self.env['account.move.line'].browse(int(key[0].id)).full_reconcile_id
                            if not reconciled:
                                sql = "Select Id, Name, s2cor__Is_Reconciled__c From s2cor__Sage_ACC_Tag__c WHERE Id ='{}'".format(sf_rec['s2cor__Document_Number_Tag__c'])
                                tags = sfInstance.getConnection().query_all(sql)['records']
                                
                                if tags[0]['s2cor__Is_Reconciled__c']:
                                    sql = "SELECT Id, Name FROM s2cor__Sage_ACC_Ledger_Item__c WHERE s2cor__Document_Number_Tag__c = '{}'".format(sf_rec['s2cor__Document_Number_Tag__c'])
                                    items = sfInstance.getConnection().query_all(sql)['records']
                                    if items:
                                        line_ids = []
                                        for item in items:
                                            line_id = keys = self.env['account.move.line'].search([('ref','=',item['Name'])],limit=1)
                                            if line_id:
                                                line_ids.append(line_id.id)
                                        if line_ids:
                                            reconcile = self.env['account.full.reconcile'].create({
                                                'name': tags[0]['Name'],
                                                'reconciled_line_ids': [(6, 0, line_ids)]
                                            }).id
                                            _logger.info("New reconciliation ID : {}".format(str(reconcile)))
                        reconciled = self.env['account.move.line'].browse(int(key[0].id)).full_reconcile_id
                        if not reconciled:
                            queryAccountNumber = "SELECT s2cor__Account_Number__c FROM s2cor__Sage_ACC_Ledger_Account__c WHERE Id ='{}'".format(str(sf_rec['s2cor__Ledger_Account__c']))
                            accountNumber = sfInstance.getConnection().query(queryAccountNumber)['records']
                            Date = sf_rec['s2cor__Date__c']
                            if len(accountNumber)>0:
                                if accountNumber[0]['s2cor__Account_Number__c']:
                                    if accountNumber[0]['s2cor__Account_Number__c'].startswith('401') and Date < "2020-01-01":
                                        reconcile = self.env['account.full.reconcile'].search([('name','=','OK')],limit=1)
                                        if reconcile:
                                            reconcile.write({
                                                'reconciled_line_ids': [(4, int(key[0].id))]
                                            })
                                        else:
                                            reconcile = self.env['account.full.reconcile'].create({
                                                'name': "OK",
                                                'reconciled_line_ids': [(4, int(key[0].id), 0)]
                                            })
                                        _logger.info("New reconciliation ID : {}".format(str(reconcile.id)))
                                    
                _logger.info("Reconciliation | Item {}/{} ".format(counter,len(records)))




