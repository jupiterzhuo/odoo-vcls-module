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

        sql = "Select Id, Name, s2cor__Document_Number_Tag__c, s2cor__Ledger_Account__c, s2cor__Date__c, s2cor__Ledger_Entry__c From s2cor__Sage_ACC_Ledger_Item__c"
        to_process = sfInstance.getConnection().query_all(sql)['records']

        inc_id = self.env.ref('vcls-hr.company_VCINC').id
        records = self.env['account.move.line'].search([('company_id','=',inc_id), ('processed','=',False), ('full_reconcile_id','=',False), ('account_id','=',5437)])

        if not records:
            records = self.env['account.move.line'].search([('company_id','=',inc_id), ('processed','=', True), ('full_reconcile_id','=',False), ('account_id','=',5437)])
            for record in records:
                record.processed = False
        if records:
            counter = 0
            #LOOP IN ODOO RECORDS
            for od_rec in records:
                if datetime.now()>timestamp_end:
                    break
                else:
                    counter += 1
                    item = False
                    reconcile = False
                    #LOOP TO GET SF RECORD
                    for proc in to_process:
                        if proc['Name'] == od_rec.ref:
                            item = proc
                            break
                    #IF RECORD SF FOUND
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
                            reconcile = False
                            queryAccountNumber = "SELECT s2cor__Account_Number__c FROM s2cor__Sage_ACC_Ledger_Account__c WHERE Id ='{}'".format(str(item['s2cor__Ledger_Account__c']))
                            accountNumber = sfInstance.getConnection().query(queryAccountNumber)['records']
                            Date = item['s2cor__Date__c']
                            if len(accountNumber)>0:
                                if accountNumber[0]['s2cor__Account_Number__c']:
                                    queryMove = "SELECT s2cor__Source_Document__c FROM s2cor__Sage_ACC_Ledger_Entry__c WHERE Id ='{}'".format(item['s2cor__Ledger_Entry__c'])
                                    moveDocument = sfInstance.getConnection().query(queryMove)['records']
                                    if accountNumber[0]['s2cor__Account_Number__c'].startswith('401'):
                                        if Date < "2020-01-01" or moveDocument[0]['s2cor__Source_Document__c'] == 'Adjustment' or moveDocument[0]['s2cor__Source_Document__c'] == 'Manual Adjustment' or moveDocument[0]['s2cor__Source_Document__c'] == 'Payments to Vendors US':
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
                                    if not reconcile and accountNumber[0]['s2cor__Account_Number__c'].startswith('401000'):
                                        line_ids = []
                                        somme = 0
                                        if od_rec.credit > 0 or od_rec.debit > 0:
                                            if od_rec.credit > 0:
                                                lines = self.env['account.move.line'].search([('move_id','=',od_rec.move_id.id), ('account_id','=', od_rec.account_id.id), ('debit','>', 0), ('full_reconcile_id','=',False)])
                                            else:
                                                lines = self.env['account.move.line'].search([('move_id','=',od_rec.move_id.id), ('account_id','=', od_rec.account_id.id), ('credit','>', 0), ('full_reconcile_id','=',False)])
                                            if lines:
                                                for line in lines:
                                                    for proc in to_process:
                                                        if proc['Name'] == line.ref:
                                                            lineToReconcile = proc
                                                            break
                                                    if lineToReconcile:
                                                        if lineToReconcile['s2cor__Document_Number_Tag__c']:
                                                            if item['s2cor__Document_Number_Tag__c']:
                                                                if lineToReconcile['s2cor__Document_Number_Tag__c'] == item['s2cor__Document_Number_Tag__c']:
                                                                    sqlTag = "Select Id, Name, s2cor__Is_Reconciled__c From s2cor__Sage_ACC_Tag__c WHERE Id ='{}'".format(lineToReconcile['s2cor__Document_Number_Tag__c'])
                                                                    tags = sfInstance.getConnection().query_all(sqlTag)['records']
                                                                    if not tags[0]['s2cor__Is_Reconciled__c']:
                                                                        line_ids.append(line.id)
                                                                        if od_rec.credit > 0:
                                                                            somme += line.debit
                                                                        else:
                                                                            somme += line.credit
                                                                        if somme > 0:
                                                                            if somme == od_rec.credit or somme == od_rec.debit:
                                                                                line_ids.append(od_rec.id)
                                                                                reconcile = self.env['account.full.reconcile'].create({
                                                                                    'name': od_rec.move_id.name,
                                                                                    'reconciled_line_ids': [(6, 0, line_ids)]
                                                                                })
                                                                                _logger.info("New reconciliation ID : {}".format(str(reconcile.id)))
                                            if not reconcile:
                                                if od_rec.credit > 0:
                                                    line = self.env['account.move.line'].search([('account_id','=', od_rec.account_id.id), ('debit','=', od_rec.credit), ('date','>=','01/01/2020'), ('full_reconcile_id','=',False)], limit = 1)
                                                else:
                                                    line = self.env['account.move.line'].search([('account_id','=', od_rec.account_id.id), ('credit','=', od_rec.debit), ('date','>=','01/01/2020'), ('full_reconcile_id','=',False)], limit = 1)
                                                if line:
                                                    for proc in to_process:
                                                        if proc['Name'] == line.ref:
                                                            lineToReconcile = proc
                                                            break
                                                    if lineToReconcile:
                                                        if lineToReconcile['s2cor__Document_Number_Tag__c']:
                                                            if item['s2cor__Document_Number_Tag__c']:
                                                                if lineToReconcile['s2cor__Document_Number_Tag__c'] == item['s2cor__Document_Number_Tag__c']:
                                                                    sqlTag = "Select Id, Name, s2cor__Is_Reconciled__c From s2cor__Sage_ACC_Tag__c WHERE Id ='{}'".format(lineToReconcile['s2cor__Document_Number_Tag__c'])
                                                                    tags = sfInstance.getConnection().query_all(sqlTag)['records']
                                                                    if not tags[0]['s2cor__Is_Reconciled__c']:
                                                                        reconcile = self.env['account.full.reconcile'].create({
                                                                                'name': "{} / {}".format(od_rec.move_id.name, line.move_id.name),
                                                                                'reconciled_line_ids': [(6, 0, [line.id, od_rec.id])]
                                                                        })
                                                                        _logger.info("New reconciliation ID : {}".format(str(reconcile.id)))
                    od_rec.processed = True
                _logger.info("Reconciliation | Item {}/{} ".format(counter,len(records)))




