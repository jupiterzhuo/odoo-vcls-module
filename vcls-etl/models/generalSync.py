# -*- coding: utf-8 -*-

from odoo import models, fields, api

import datetime, pytz
from datetime import datetime,timedelta

from abc import ABC,abstractmethod

from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceMalformedRequest

from . import ETL_SF

import logging
_logger = logging.getLogger(__name__)

class KeyNotFoundError(Exception):
    pass

class ETLMap(models.Model):
    _name = 'etl.sync.keys'
    _description = 'Odoo ID with external ID'

    odooId = fields.Char(readonly = True,index=True)
    externalId = fields.Char(readonly = True,index=True)
    odooModelName = fields.Char(readonly = True)
    externalObjName = fields.Char(readonly = True)
    lastModifiedExternal = fields.Datetime(readonly = True)
    lastModifiedOdoo = fields.Datetime(readonly = True)
    priority = fields.Integer(default=0)
    
    state = fields.Selection([
        ('upToDate', 'Up To Date'),
        ('needUpdateOdoo', 'Need Update In Odoo'),
        ('needUpdateExternal', 'Need Update In External'),
        ('needCreateOdoo', 'Need To Be Created In Odoo'),
        ('needCreateExternal', 'Need To Be Created In External'),
        ('postponed','Missing Key Info to Process'),
        ],
        string='State',
        default='upToDate' # For existing keys
    )
    migration_running = fields.Boolean()

    @api.one
    def setState(self, state):
        self.state = state
    
    def open_con(self):
        userSF = self.env.ref('vcls-etl.SF_mail').value
        passwordSF = self.env.ref('vcls-etl.SF_password').value
        token = self.env.ref('vcls-etl.SF_token').value
        return ETL_SF.ETL_SF.getInstance(userSF, passwordSF, token)
    
    def update_keys(self,params={}):
        _logger.info("ETL | UPDATE KEYS {}".format(params))
        rec_ext = params['sfInstance'].getConnection().query_all(params['sql'])['records']
        keys_exist = self.search([('externalObjName','=',params['externalObjName']),('odooModelName','=',params['odooModelName'])])
        #we default the state of all keys not already to be updated
        keys_exist.filtered(lambda k: k.state != 'needUpdateOdoo').write({'state':'upToDate','priority':0})
        keys_exist_sfid = keys_exist.mapped('externalId')
        keys_create = keys_exist.filtered(lambda k: k.externalId and not k.odooId)

        keys_update = self.env['etl.sync.keys']
        keys_to_test=keys_exist.filtered(lambda k: k.externalId and k.odooId)

        #We look for non exisitng keys
        for rec in rec_ext:
            if rec['Id'] not in keys_exist_sfid: #if the rec does not exists

                vals = {
                    'externalObjName':params['externalObjName'],
                    'externalId': rec['Id'],
                    'lastModifiedExternal': datetime.strptime(rec['LastModifiedDate'], "%Y-%m-%dT%H:%M:%S.000+0000"),
                    'odooModelName': params['odooModelName'],
                    'state':'needCreateOdoo',
                }

                if rec.get('Email',False) and params['externalObjName']=="Contact": #we need to check if a contact already exists with this email
                    existing = self.env[params['odooModelName']].with_context(active_test=False).search([('email','=ilike',rec['Email']),('is_company','=',False)],limit=1)
                    if existing and not '@vcls.com' in rec['Email']:
                        vals['odooId']=existing.id
                        keys_update |= self.create(vals)
                        _logger.info("KEYS | Contact duplicate found {}".format(rec['Email']))
                    else:
                        keys_create |= self.create(vals)
                        _logger.info("KEYS | {} New Creation {}".format(params['externalObjName'],vals))
                else:        
                    keys_create |= self.create(vals)
                    _logger.info("KEYS | {} New Creation {}".format(params['externalObjName'],vals))

            else: #we ensure not to try to update records we don't have in the rec
                key = keys_to_test.filtered(lambda k: k.externalId==rec['Id'])
                if key:
                    keys_update |= key
                    _logger.info("KEYS | {} To Update {}".format(params['externalObjName'],key.odooId))         
                        
    
        if rec_ext:
            _logger.info("QUERY |\n{}\nreturned {} {} records".format(params['sql'],len(rec_ext),params['externalObjName']))
        if keys_exist:
            _logger.info("KEYS | Found {} existing keys of {}".format(len(keys_exist),params['externalObjName']))

        if keys_create:
            keys_create.write({'state':'needCreateOdoo','priority':params['priority']+1})
            _logger.info("KEYS | {} Keys to create".format(len(keys_create)))
        if keys_update:
            keys_update.write({'state':'needUpdateOdoo','priority':params['priority']})
            _logger.info("KEYS | {} Keys to update".format(len(keys_update)))   

    @api.model
    def sf_update_keys(self,obj_dict,is_full_update=True):
        """
        We 1st process the keys and priorities, starting from contacts.
        But then the queue must be executed in revert order of priorities to ensure parent accounts to be created 1st, etc.
        """
        ### PREPARATION
        #Update the context to execute vcls-rdd override
        self.env.user.context_data_integration = True
        #Clean the keys table of corrupted entries
        to_clean = self.search([('odooModelName','=',False),('state','!=','map')])
        #we also clean the ones to create in externals because we don't manage anymore this usecase
        to_clean |= self.search([('externalId','=',False),('state','!=','map')])
        #we also clean the keys not created yet, in order to cover the change in source filtering
        to_clean |= self.search([('odooId','=',False),('state','!=','map')])
        for key in to_clean:
            key.unlink()
        
        #get instance
        sfInstance = self.open_con()

        #make time filter if required
        new_run = datetime.now(pytz.timezone("GMT"))
        if not is_full_update:
            last_run = self.env.ref('vcls-etl.ETL_LastRun').value
            formated_last_run = fields.Datetime.from_string(last_run).astimezone(pytz.timezone("GMT")).strftime("%Y-%m-%dT%H:%M:%S.00+0000")
            time_sql = " LastModifiedDate > {}".format(formated_last_run)
        else:
            time_sql = ""

        self.env.ref('vcls-etl.etl_sf_time_filter').value = time_sql

        ### CAMPAIGN KEYS PROCESSING
        if obj_dict.get('do_campaign',False):
            """
            Campaigns have the highest priority, because contacts and leads are related to campaigns
            """
            # 1st without parents (because they might be parents) 
            sql = """
                SELECT Id, LastModifiedDate FROM Campaign 
                """
            params = {
                'sfInstance':sfInstance,
                'priority':950,
                'externalObjName':'Campaign',
                'sql': self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_campaign_filter').value,time_sql,'ParentId = null']),
                'odooModelName':'project.task',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)
            
            # Then Campaigns Without Parents 
            sql = """
                SELECT Id, LastModifiedDate FROM Campaign 
                    """
            params = {
                'sfInstance':sfInstance,
                'priority':900,
                'externalObjName':'Campaign',
                'sql': self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_campaign_filter').value,time_sql,'ParentId != null']),
                'odooModelName':'project.task',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)

        ### ACCOUNT KEYS PROCESSING
        if obj_dict.get('do_account',False):
            """
            Account have the second priority, because they are used for opportunities creation
            """
            # accounts without parents 
            sql = """
                SELECT Id, LastModifiedDate FROM Account 
                """
            params = {
                'sfInstance':sfInstance,
                'priority':850,
                'externalObjName':'Account',
                'sql': self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_account_filter').value,time_sql,'ParentId = null']),
                'odooModelName':'res.partner',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)

            # accounts with parents 
            sql = """
                SELECT Id, LastModifiedDate FROM Account 
                    """
            params = {
                'sfInstance':sfInstance,
                'priority':800,
                'externalObjName':'Account',
                'sql': self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_account_filter').value,time_sql,'ParentId != null']),
                'odooModelName':'res.partner',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)

            
        ### CONTACT KEYS PROCESSING (we get emails to manage potential duplicates)
        if obj_dict.get('do_contact',False):
            sql = """
                SELECT Id, LastModifiedDate, Email FROM Contact
                """
            params = {
                'sfInstance':sfInstance,
                'priority':700,
                'externalObjName':'Contact',
                'sql':self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_contact_filter').value,time_sql]),
                'odooModelName':'res.partner',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)

        ### CONTRACT KEYS PROCESSING
        if obj_dict.get('do_contract',False):
            #The one without parent contracts
            sql = """
                SELECT Id, LastModifiedDate FROM Contract
                    """
            params = {
                'sfInstance':sfInstance,
                'priority':650,
                'externalObjName':'Contract',
                'sql': self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_contract_filter').value,time_sql,' Link_to_Parent_Contract__c = null']),
                'odooModelName':'agreement',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)
            #The one with parent contracts
            sql = """
                SELECT Id, LastModifiedDate FROM Contract
                    """
            params = {
                'sfInstance':sfInstance,
                'priority':600,
                'externalObjName':'Contract',
                'sql': self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_contract_filter').value,time_sql,' Link_to_Parent_Contract__c != null']),
                'odooModelName':'agreement',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)
        
        ### LEAD KEYS PROCESSING
        if obj_dict.get('do_lead',False):
            sql = """
                SELECT Id, LastModifiedDate FROM Lead 
                """
            params = {
                'sfInstance':sfInstance,
                'priority':500,
                'externalObjName':'Lead',
                'sql': self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_lead_filter').value,time_sql]),
                'odooModelName':'crm.lead',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)

        ### OPPORTUNITY KEYS PROCESSING
        if obj_dict.get('do_opportunity',False):
            sql = """
                SELECT Id, LastModifiedDate FROM Opportunity 
                    """
            params = {
                'sfInstance':sfInstance,
                'priority':400,
                'externalObjName':'Opportunity',
                'sql': self.build_sql(sql,[self.env.ref('vcls-etl.etl_sf_opportunity_filter').value,time_sql]),
                'odooModelName':'crm.lead',
                'is_full_update':is_full_update,
            }
            self.update_keys(params)

        ###CLOSING
        #we trigger the processing job
        """cron = self.env.ref('vcls-etl.cron_process')
        cron.write({
            'active': True,
            'nextcall': datetime.now() + timedelta(seconds=30),
            'numbercall': 2,
        })""" 


        self.env.ref('vcls-etl.ETL_LastRun').value = new_run.strftime("%Y-%m-%d %H:%M:%S.00+0000")
        self.env.user.context_data_integration = False
    
    def build_sql(self,core,filters=None,post=None):
        sql = core
        if filters:
            for fil in filters:
                if fil != "":
                    if 'WHERE' not in sql:
                        sql += " WHERE " + fil
                    else:
                        sql += " AND " + fil
        if post:
            sql += ' ' + post
            
        return sql

    
    
    @api.model
    def relaunch_cron(self,external_id=None,numbercall=0):
        if external_id:
            cron = self.env.ref(external_id)
            if cron:
                cron.write({
                    'active': True,
                    'nextcall': datetime.now() + timedelta(seconds=10),
                    'numbercall': numbercall,
                })
                _logger.info("ETL | CRON relaunched")



        
    """def updateAccountKey(self, externalInstance):
        sql = 'Select Id From Account'
        modifiedRecordsExt = externalInstance.getConnection().query_all(sql)['records']

        for item in modifiedRecordsExt:
            odooAccount = self.env['etl.sync.keys'].search([('externalId','=',item['Id'])], limit=1)
            if odooAccount:
                odooAccount.write({'odooModelName':'res.partner','externalObjName':'Account'})
                #print("Update Key Account externalId :{}".format(item['Id']))
                #_logger.info("Update Key Account externalId :{}".format(item['Id']))


    def updateContactKey(self, externalInstance):
        sql =  'SELECT Id FROM Contact'
        modifiedRecordsExt = externalInstance.getConnection().query_all(sql)['records']
        _logger.info("ETL | updateContactKey | \n {} \n  Found {} records".format(sql,len(modifiedRecordsExt)))

        for item in modifiedRecordsExt:
            odooContact = self.env['etl.sync.keys'].search([('externalId','=',item['Id'])], limit=1)
            if odooContact:
                odooContact.write({'odooModelName':'res.partner','externalObjName':'Contact'})
                #print("Update Key Contact externalId :{}".format(item['Id']))
                #_logger.info("Update Key Contact externalId :{}".format(item['Id']))

    def updateOpportunityKey(self, externalInstance):
        sql =  'SELECT Id '
        sql += 'FROM Opportunity'
        modifiedRecordsExt = externalInstance.getConnection().query_all(sql)['records']

        for item in modifiedRecordsExt:
            odooOpportunity = self.env['etl.sync.keys'].search([('externalId','=',item['Id'])], limit=1)
            if odooOpportunity:
                odooOpportunity.write({'odooModelName':'crm.lead','externalObjName':'Opportunity'})
                #print("Update Key Opportunity externalId :{}".format(item['Id']))
                #_logger.info("Update Key Opportunity externalId :{}".format(item['Id']))"""

class GeneralSync(models.AbstractModel):
    _name = 'etl.sync.mixin'
    _description = 'This model represents an abstract parent class used to manage ETL'
    
    lastRun = fields.Datetime(readonly = True)

    def setNextRun(self):
        self.lastRun = fields.Datetime.from_string(datetime.now(pytz.timezone("GMT")).strftime("%Y-%m-%d %H:%M:%S.00+0000"))
        print(self.lastRun)
    
    def getStrLastRun(self):
        if not self.lastRun:
            return fields.Datetime.from_string('2000-01-01 00:00:00.000000+00:0')
        return self.lastRun
    
    @api.model
    def getLastUpdate(self, OD_id):
        partner = self.env['res.partner']
        odid = int(OD_id[0])
        record = partner.browse([odid])
        return str(record.write_date)

    @staticmethod
    def isDateOdooAfterExternal(dateOdoo,dateExternal):
        return dateOdoo >= dateExternal

    """ abstractmethods that need not be implemented in inherited Models
    def updateKeyTables(self):
    def updateOdooInstance(self):
    def needUpdateExternal(self):
    def updateKeyTable(self, externalInstance): """



