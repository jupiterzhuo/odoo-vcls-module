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
        to_process = sfInstance.getConnection().query_all(sql)['records']

        inc_id = self.env.ref('vcls-hr.company_VCINC').id
        records = self.env['account.move.line'].search([('company_id','=',inc_id), ('processed','=',False), ('full_reconcile_id','=',False)])

        if not records:
            records = self.env['account.move.line'].search([('company_id','=',inc_id), ('processed','=', True), ('full_reconcile_id','=',False)])
            for record in records:
                record.processed = False
        if records:
            counter = 0
            for od_rec in records:
                if datetime.now()>timestamp_end:
                    break
                else:
                    counter += 1
                    item = False
                    for proc in to_process:
                        if proc['Name'] == od_rec.ref:
                            item = proc
                            break
                    if item:
                        if item['s2cor__Document_Number_Tag__c']:
                            reconciled = od_rec.full_reconcile_id
                            if not reconciled:
                                sqlTag = "Select Id, Name, s2cor__Is_Reconciled__c From s2cor__Sage_ACC_Tag__c WHERE Id ='{}'".format(item['s2cor__Document_Number_Tag__c'])
                                tags = sfInstance.getConnection().query_all(sqlTag)['records']
                                if tags[0]['s2cor__Is_Reconciled__c']:
                                    sqlDocument = "SELECT Id, Name FROM s2cor__Sage_ACC_Ledger_Item__c WHERE s2cor__Document_Number_Tag__c = '{}'".format(item['s2cor__Document_Number_Tag__c'])
                                    items = sfInstance.getConnection().query_all(sqlDocument)['records']
                                    if items:
                                        line_ids = []
                                        for item in items:
                                            line_id = self.env['account.move.line'].search([('ref','=',item['Name'])],limit=1)
                                            if line_id:
                                                line_ids.append(line_id.id)
                                                line_id.processed = True
                                        if line_ids:
                                            reconcile = self.env['account.full.reconcile'].create({
                                                'name': tags[0]['Name'],
                                                'reconciled_line_ids': [(6, 0, line_ids)]
                                            }).id
                                            _logger.info("New reconciliation ID : {} For IDS : {}".format(str(reconcile),line_ids))

                        reconciled = od_rec.full_reconcile_id
                        if not reconciled:
                            queryAccountNumber = "SELECT s2cor__Account_Number__c FROM s2cor__Sage_ACC_Ledger_Account__c WHERE Id ='{}'".format(str(item['s2cor__Ledger_Account__c']))
                            accountNumber = sfInstance.getConnection().query(queryAccountNumber)['records']
                            Date = item['s2cor__Date__c']
                            if len(accountNumber)>0:
                                if accountNumber[0]['s2cor__Account_Number__c']:
                                    if accountNumber[0]['s2cor__Account_Number__c'].startswith('401') and Date < "2020-01-01":
                                        reconcile = self.env['account.full.reconcile'].search([('name','=','OK')],limit=1)
                                        if reconcile:
                                            reconcile.write({
                                                'reconciled_line_ids': [(4, od_rec.id)]
                                            })
                                        else:
                                            reconcile = self.env['account.full.reconcile'].create({
                                                'name': "OK",
                                                'reconciled_line_ids': [(4, od_rec.id, 0)]
                                            })
                                        _logger.info("New reconciliation ID : {}".format(str(reconcile.id)))
                                    elif accountNumber[0]['s2cor__Account_Number__c'].startswith('401000'):
                                        line_ids = []
                                        somme = 0
                                        if od_rec.credit > 0:
                                            lines = self.env['account.move.line'].search([('move_id','=',od_rec.move_id.id), ('account_id','=', od_rec.account_id.id), ('debit','>', 0)])
                                            if lines:
                                                for line in lines:
                                                    line_ids.append(line.id)
                                                    somme += line.debit
                                                if somme == od_rec.credit:
                                                        line_ids.append(od_rec.id)
                                                        reconcile = self.env['account.full.reconcile'].create({
                                                            'name': od_rec.move_id.name,
                                                            'reconciled_line_ids': [(6, 0, line_ids)]
                                                        })
                                                        _logger.info("New reconciliation ID : {}".format(str(reconcile.id)))
                                                else:
                                                    line = self.env['account.move.line'].search([('account_id','=', od_rec.account_id.id), ('debit','=', od_rec.credit)], limit = 1)
                                                    if line:
                                                        reconcile = self.env['account.full.reconcile'].create({
                                                                'name': "{} / {}".format(od_rec.move_id.name, line.move_id.name),
                                                                'reconciled_line_ids': [(6, 0, [line.id, od_rec.id])]
                                                        })
                                                        _logger.info("New reconciliation ID : {}".format(str(reconcile.id)))
                                        elif od_rec.debit > 0:
                                            lines = self.env['account.move.line'].search([('move_id','=',od_rec.move_id.id), ('account_id','=', od_rec.account_id.id), ('credit','>', 0)])
                                            if lines:
                                                for line in lines:
                                                    line_ids.append(line.id)
                                                    somme += line.debit
                                                if somme == od_rec.debit:
                                                        line_ids.append(od_rec.id)
                                                        reconcile = self.env['account.full.reconcile'].create({
                                                            'name': od_rec.move_id.name,
                                                            'reconciled_line_ids': [(6, 0, line_ids)]
                                                        })
                                                        _logger.info("New reconciliation ID : {}".format(str(reconcile.id)))
                                                else:
                                                    line = self.env['account.move.line'].search([('account_id','=', od_rec.account_id.id), ('credit','=', od_rec.debit)], limit = 1)
                                                    if line:
                                                        reconcile = self.env['account.full.reconcile'].create({
                                                                'name': "{} / {}".format(od_rec.move_id.name, line.move_id.name),
                                                                'reconciled_line_ids': [(6, 0, [line.id, od_rec.id])]
                                                        })
                                                        _logger.info("New reconciliation ID : {}".format(str(reconcile.id)))
                    od_rec.processed = True
                _logger.info("Reconciliation | Item {}/{} ".format(counter,len(records)))




