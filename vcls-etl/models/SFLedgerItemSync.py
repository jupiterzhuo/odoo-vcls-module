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

    def reconciledEntries(self):
        userSF = self.env.ref('vcls-etl.SF_mail').value
        passwordSF = self.env.ref('vcls-etl.SF_password').value
        token = self.env.ref('vcls-etl.SF_token').value
        sfInstance = ETL_SF.ETL_SF.getInstance(userSF, passwordSF, token)

        sql = "Select Id, Name, s2cor__Document_Number_Tag__c From s2cor__Sage_ACC_Ledger_Item__c"
        records = sfInstance.getConnection().query_all(sql)['records']
        keys = self.env['etl.sync.keys'].search([('odooModelName','=','account.move.line')])
        if records:
            counter = 0
            for sf_rec in records:
                counter += 1
                if sf_rec['s2cor__Document_Number_Tag__c']:
                    key = keys.filtered(lambda p: p.externalId == sf_rec['Id'])
                    reconciled = self.env['account.move.line'].browse(int(key[0].odooId)).full_reconcile_id
                    if not reconciled:
                        sql = "Select Id, Name, s2cor__Is_Reconciled__c From s2cor__Sage_ACC_Tag__c WHERE Id ='{}'".format(sf_rec['s2cor__Document_Number_Tag__c'])
                        tags = sfInstance.getConnection().query_all(sql)['records']
                        if tags[0]['s2cor__Is_Reconciled__c']:
                            sql = "SELECT Id, Name FROM s2cor__Sage_ACC_Ledger_Item__c WHERE s2cor__Document_Number_Tag__c = '{}'".format(sf_rec['s2cor__Document_Number_Tag__c'])
                            items = sfInstance.getConnection().query_all(sql)['records']
                            if items:
                                line_ids = []
                                for item in items:
                                    line_ids.append(TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(item['Id'],"account.move.line","LedgerItem",self))
                                if line_ids:
                                    reconcile = self.env['account.full.reconcile'].create({
                                        'name': tags[0]['Name'],
                                        'reconciled_line_ids': [(6, 0, line_ids)]
                                    }).id
                                    _logger.info("New reconciliation ID : {}".format(str(reconcile)))
                _logger.info("Reconciliation | Item {}/{} ".format(counter,len(records)))





