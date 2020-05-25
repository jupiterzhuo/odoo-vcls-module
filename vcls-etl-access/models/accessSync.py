from . import ETL_ACCESS
from . import generalSync

import pytz
from tzlocal import get_localzone
from datetime import datetime
from datetime import timedelta
import time
import logging
import psycopg2
_logger = logging.getLogger(__name__)

from odoo import models, fields, api

class accessSync(models.Model):
    _name = 'etl.sync.access'
    _inherit = 'etl.sync.mixin'

    def getAccessInstance(self):
        return ETL_ACCESS.ETL_ACCESS.getInstance()
    
    @api.model
    def access_process_keys(self,batch_size=False,loop=True,duration=9):

        priorities = self.env['etl.sync.access.keys'].search([('state','not in',['upToDate','postponed'])]).mapped('priority')
        if priorities:
            top_priority = max(priorities)
        else:
            top_priority = False

        if top_priority:
            self.env.user.context_data_integration = True

            loop_cron = loop

            accessInstance = self.getAccessInstance().getConnection()

            if batch_size:
                to_process = self.env['etl.sync.access.keys'].search([('state','not in',['upToDate','postponed']),('priority','=',top_priority)],limit=batch_size)
            else:
                to_process = self.env['etl.sync.access.keys'].search([('state','not in',['upToDate','postponed']),('priority','=',top_priority)])

            
            if to_process:
                template = to_process[0]
                _logger.info("ETL | Found {} {} keys {}".format(len(to_process),template.externalObjName,template.state))
                #we initiate a sync object
                sync = self.env['etl.access.{}'.format(template.externalObjName.lower())]
                translator = sync.getAccessTranslator(accessInstance)
                counter = 0

                #get SF records
                query_id = "vcls-etl-access.etl_access_{}_query".format(template.externalObjName.lower())
                sql = self.env.ref(query_id).value
                records = accessInstance.execute(sql).fetchall()
                if records:
                    _logger.info("ETL |  {} returned {} records from ACCESS".format(sql,len(records)))
                    #we start the processing loop
                    for access_rec in records:
                        #grab the related key if in to_process
                        key = to_process.filtered(lambda p: p.externalId == str(access_rec[0]))
                        if key:
                            counter += 1
                            if template.externalObjName == 'timesheet':
                                if key[0].state == 'needCreateOdoo':
                                    translator.createTimesheet(sync, access_rec[0], accessInstance,counter, len(to_process))
                                    key[0].write({'state':'upToDate','priority':0})
                                    _logger.info("ETL | Record Created {}/{} | {} |".format(counter,len(to_process),key[0].externalObjName))
                            else:
                                attributes = translator.translateToOdoo(access_rec, sync, accessInstance)
                                if not attributes:
                                    key[0].write({'state':'postponed','priority':0})
                                    _logger.info("ETL | Missing Mandatory info to process key {} - {}".format(key[0].externalObjName,key[0].externalId))
                                    continue

                                #UPDATE Case
                                if key[0].state == 'needUpdateOdoo':
                                    #we catch the existing record
                                    o_rec = self.env[key[0].odooModelName].with_context(active_test=False).search([('id','=',key[0].odooId)],limit=1)
                                    if o_rec:
                                        o_rec.with_context(tracking_disable=1).write(attributes)
                                        key[0].write({'state':'upToDate','priority':0})
                                        _logger.info("ETL | Record Updated {}/{} | {} | {}".format(counter,len(to_process),key[0].externalObjName,attributes.get('log_info')))
                                    else:
                                        key[0].write({'state':'upToDate','priority':0})
                                        _logger.info("ETL | Missed Update - Odoo record not found {}/{} | {} | {}".format(counter,len(to_process),key[0].odooModelName,key[0].odooId))
                                 
                                #CREATE Case
                                elif key[0].state == 'needCreateOdoo':
                                    odoo_id = self.env[key[0].odooModelName].with_context(tracking_disable=1).create(attributes)
                                    key[0].write({'state':'upToDate','odooId':odoo_id.id,'priority':0})
                                    #key[0].write({'state':'upToDate','priority':0})
                                    _logger.info("ETL | Record Created {}/{} | {} | {}".format(counter,len(to_process),key[0].externalObjName,attributes.get('log_info')))
                                    if key[0].odooModelName == "sale.order":
                                        translator.setOrderLine(sync,access_rec, accessInstance, odoo_id.id)
                                        odoo_id.action_sync()
                                        odoo_id.action_confirm()
                                        task_stage = self.env['project.task.type'].search([('name','=','0% Progress')],limit = 1)
                                        project_id = self.env['project.project'].search([('sale_order_id','=',odoo_id.id)],limit = 1)
                                        task_id = self.env['project.task'].search([('sale_order_id','=',odoo_id.id)],limit = 1)
                                        if project_id:
                                            project_id.write({
                                                'user_id': odoo_id.user_id.id,
                                            })                                  
                                        if task_id:
                                            task_id.stage_id = task_stage
                                        
                                else:
                                    _logger.info("ETL | Non-managed key state {} | {}".format(key[0].id,key[0].state))
                                
                if loop_cron:
                    cron = self.env.ref('vcls-etl.cron_relaunch_access')
                    cron.write({
                        'active': True,
                        'nextcall': datetime.now() + timedelta(seconds=30),
                        'numbercall': 1,
                    })
                    _logger.info("ETL | CRON renewed")
                self.env.user.context_data_integration = False
    
    
