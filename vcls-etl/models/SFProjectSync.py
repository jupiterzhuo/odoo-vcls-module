from . import ETL_SF
from . import generalSync
from . import SFProjectSync_constants
from . import SFProjectSync_mapping

from odoo.exceptions import ValidationError

import pytz
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceMalformedRequest
from tzlocal import get_localzone
from datetime import date
from datetime import datetime
from datetime import timedelta
import time
import logging
_logger = logging.getLogger(__name__)

from odoo import models, fields, api


class SFProjectSync(models.Model):
    #_name = 'etl.salesforce.project'
    _inherit = 'etl.sync.salesforce'

    project_sfid = fields.Char()
    project_sfname = fields.Char()
    project_sfref = fields.Char()
    sf_invoiced_amount = fields.Float()
    so_ids = fields.Many2many(
        'sale.order',
        readonly = True,
    )
    """project_ids = fields.Many2many(
        'project.project',
        readonly = True,
    )"""
    migration_status = fields.Selection(
        [
            ('todo', 'ToDo'),
            ('so', 'Sale Order'),
            ('structure', 'Structure'),
            ('ts', 'Timesheets'),
            ('complete', 'Complete'),
        ],
        default = 'todo', 
    )

    ####################
    ## MIGRATION METHODS
    ####################
    @api.model
    def initiate(self):
        instance = self.getSFInstance()

        query = """
        SELECT Id, Name, KimbleOne__Reference__c, Activity__c  
        FROM KimbleOne__DeliveryGroup__c 
        WHERE Automated_Migration__c = TRUE
        """
        records = instance.getConnection().query_all(query)['records']
        for rec in records:
            existing = self.search([('project_sfid','=',rec['Id'])],limit=1)
            if not existing:
                self.create({
                    'project_sfid': rec['Id'],
                    'project_sfname': rec['Name'],
                    'project_sfref': rec['KimbleOne__Reference__c'],
                })

        migrations = self.search([])
        for project in migrations:
            _logger.info("PROJECT MIGRATION STATUS | {} | {} | {}".format(project.project_sfref,project.project_sfname,project.migration_status))

        #we update the reference data
        self._build_invoice_item_status(instance)
        self._build_milestone_type(instance)
        self._build_time_periods(instance)
        #as well as the mapping with odoo objects
        self._build_company_map(instance)
        self._build_product_map(instance)
        self._build_rate_map(instance)
        self._build_user_map(instance)
        self._build_activity_map(instance)
        self._build_resources_map(instance)
        self._test_maps(instance)

    """
    POST PROCESS: Move COmpleted tasks
    compute KPIs
    """
    
    @api.multi
    def project_migrate_struc(self):
        instance = self.getSFInstance()
        if not instance:
            return False
        for project in self:
            project.sudo().build_quotations(instance)

    @api.multi
    def project_migrate_ts(self):
        instance = self.getSFInstance()
        if not instance:
            return False
        for project in self:
            project.sudo().process_timesheets(instance)
    
    @api.multi
    def finalize(self):
        for project in self:
            if project.migration_status != 'ts':
                continue
            _logger.info("Historical Finalization for project {}".format(project.project_sfref))
            lines = project.so_ids.mapped('order_line')
            #trigger the computation of the  invoiced qty
            
            lines._get_invoice_qty()
            invoiced=0
            for line in lines:
                if (line.product_id.vcls_type in ['vcls_service']) and (line.order_id.invoicing_mode == 'fixed_price' or line.product_id.service_tracking == 'no'):
                    invoiced += line.qty_invoiced*line.price_unit
                elif (line.order_id.invoicing_mode == 'tm' and line.product_id.vcls_type=='rate'):
                    timesheets = line.order_id.timesheet_ids.filtered(lambda ts: ts.stage_id=='historical' and ts.so_line == line)
                    if timesheets:
                        invoiced += sum(timesheets.mapped(lambda t: t.unit_amount_rounded*t.so_line_unit_price))

            if invoiced<project.sf_invoiced_amount and lines:
                _logger.info("Historical line to add with {}".format(project.sf_invoiced_amount-invoiced))
                vals = {
                    'product_id': self.env.ref('vcls-etl.product_historical_balance').id,
                    'order_id':project.so_ids.filtered(lambda o: not o.parent_id)[0].id,
                    'name':'Historical Balance',
                    'product_uom_qty':1,
                    'qty_delivered_manual':1,
                    'price_unit':project.sf_invoiced_amount-invoiced,
                    'historical_invoiced_amount':project.sf_invoiced_amount-invoiced,
                }
                historical = self.env['sale.order.line'].create(vals)
                historical._get_invoice_qty()
            
            lines._compute_qty_delivered()
            lines._compute_untaxed_amount_invoiced()
            lines._compute_untaxed_amount_to_invoice()
                

    
    @api.model
    def migrate_structure(self,active=True):
        #we promote timesheet migrations of ongoing projects
        #If timesheets to migrate, we launch the CRON
        launch_ts = False

        if self.search([('migration_status','in',['so','structure'])]):
            launch_ts = True 
        #we look for other projects to migrate
        else:
            instance = self.getSFInstance()
            projects = self.search([('migration_status','=','todo')]).sorted(key=lambda r: r.create_date)
            if projects:
                #we migrate the structure then trigger the timesheet migration
                _logger.info("PROJECT MIGRATION | Structure of {}".format(projects[0].project_sfname))
                projects[0].build_quotations(instance)
                launch_ts = True

        if launch_ts:
            #we call the timesheet migration job
            _logger.info("Timesheet Migration Callback!")
            cron = self.env.ref('vcls-etl.cron_project_timesheets_ping')
            cron.write({
                'active': active,
                'nextcall': datetime.now() + timedelta(seconds=3),
                'numbercall': 1,
            })
        
        return launch_ts
        
        
    
    @api.model
    def migrate_timesheets_ping(self,active=True):
        instance = self.getSFInstance()
        projects = self.search([('migration_status','in',['structure','ts'])]).sorted(key=lambda r: r.create_date)
        if projects:
            _logger.info("PROJECT MIGRATION | Timesheets for {}".format(projects[0].project_sfname))
            projects[0].process_timesheets(instance)
            projects = self.search([('migration_status','in',['structure','ts'])]).sorted(key=lambda r: r.create_date)
        
        if projects: #still timesheets to migrate, launch the pong version
            cron = self.env.ref('vcls-etl.cron_project_timesheets_pong')
            cron.write({
                'active': active,
                'nextcall': datetime.now() + timedelta(seconds=3),
                'numbercall': 1,
            })
            return True
        
        else:
            #we call back the structure migration job to process remaining projects
            cron = self.env.ref('vcls-etl.cron_project_structure')
            cron.write({
                'active': active,
                'nextcall': datetime.now() + timedelta(seconds=3),
                'numbercall': 1,
            })
            return False
    
    @api.model
    def migrate_timesheets_pong(self,active=True):
        instance = self.getSFInstance()
        projects = self.search([('migration_status','in',['structure','ts'])]).sorted(key=lambda r: r.create_date)
        if projects:
            _logger.info("PROJECT MIGRATION | Timesheets for {}".format(projects[0].project_sfname))
            projects[0].process_timesheets(instance)
            projects = self.search([('migration_status','in',['structure','ts'])]).sorted(key=lambda r: r.create_date)
        
        if projects: #still timesheets to migrate, launch the ping version
            cron = self.env.ref('vcls-etl.cron_project_timesheets_ping')
            cron.write({
                'active': active,
                'nextcall': datetime.now() + timedelta(seconds=3),
                'numbercall': 1,
            })
            return True
        
        else:
            #we call back the structure migration job to process remining projects
            cron = self.env.ref('vcls-etl.cron_project_structure')
            cron.write({
                'active': active,
                'nextcall': datetime.now() + timedelta(seconds=3),
                'numbercall': 1,
            })
            return False
    
    
    
    @api.multi
    def process_timesheets(self,instance):
        if not instance:
            return False
        
        for project in self.filtered(lambda p: p.migration_status=='structure'):
            #get the related keys of elements
            line_ids = project.so_ids.mapped('order_line.id')
            so_lines = self.env['sale.order.line'].browse(line_ids)
            _logger.info("FOUND Order Lines {} {}".format(so_lines.mapped('name'),so_lines.mapped('ts_migrated')))
            
            lines_to_migrate = so_lines.filtered(lambda l: l.ts_migrated==False and l.task_id and l.product_id.vcls_type!='subscription')
            _logger.info("Lines to migrate {}".format(lines_to_migrate.mapped('name')))
            
            if lines_to_migrate:
                migrating_line = lines_to_migrate[0]
                #get required source data
                keys = self.env['etl.sync.keys'].search([('odooId','=',str(migrating_line.id)),('odooModelName','=','sale.order.line'),('externalObjName','=','KimbleOne__DeliveryElement__c'),('search_value','=',False)])
                _logger.info("KEYS to migrate {} for line {}".format(keys.mapped('name'),migrating_line.id))
                if keys:
                    #get timesheets
                    element_string = project.list_to_filter_string(keys.mapped('externalId'))
                    timesheet_data = project._get_timesheet_data(instance,element_string,migrating_line.ts_max_id)
                    if timesheet_data:
                        migrating_line.ts_max_id = max(self.values_from_key(timesheet_data,'Migration_Index__c'))
                        _logger.info("TS MAX ID {} on {} entries.".format(migrating_line.ts_max_id,len(timesheet_data)))
                        #we get assignements 
                        assignment_string = project.list_to_filter_string(timesheet_data,'KimbleOne__ActivityAssignment__c')
                        assignment_data = project._get_assignment_data(instance,assignment_string,'Id')

                        #we loop per elements
                        for element_key in keys:
                            project.process_element_ts(element_key,assignment_data,timesheet_data)
                        
                        if len(timesheet_data)<200: #we got all the TS of the element
                            migrating_line.ts_migrated = True

                    else:
                        migrating_line.ts_migrated = True
                else:
                    migrating_line.ts_migrated = True

                #we recheck if remaining lines
                lines_to_migrate = so_lines.filtered(lambda l: l.ts_migrated==False and l.task_id) 

            #when all lines have been migrated 
            if not lines_to_migrate:
                project.migration_status = 'ts'
                continue     
        
        for project in self.filtered(lambda p: p.migration_status=='ts'):
            project.finalize() 
            project.migration_status = 'complete'
            

    def process_element_ts(self,element_key,assignment_data,timesheet_data):
        inv_status = self.env['etl.sync.keys'].search([('externalObjName','=','KimbleOne__ReferenceData__c'),('search_value','=','InvoiceItemStatus')])
        task_stage = self.env['project.task.type'].search([('name','=','0% Progress')],limit = 1)
        count = 0
        #element level values
        so_line = self.env['sale.order.line'].browse(int(element_key.odooId))
        parent_task_id = so_line.task_id
        project_id = so_line.project_id
        main_project_id = project_id.parent_id if project_id.parent_id else project_id
        #tool values
        so_lines = so_line.order_id.order_line
        

        #we look for a mapping key and create if not exists. This will help to resync afterwards if required
        map_key = self.env['etl.sync.keys'].search([('externalObjName','=','Timesheet_Map'),('externalId','=',element_key.externalId),('odooId','=',str(parent_task_id.id))],limit=1)
        if not map_key:
            vals = {
                'externalObjName':'Timesheet_Map',
                'externalId': element_key.externalId,
                'odooId': str(parent_task_id.id),
                'state':'map',
            }
            self.env['etl.sync.keys'].create(vals)
            #we change the stage of the task to allow timesheets
            parent_task_id.stage_id = task_stage


        #element timesheets
        e_ts = list(filter(lambda a: a['KimbleOne__DeliveryElement__c']==element_key.externalId,timesheet_data))
        _logger.info("Processing {} Timesheets for project {} task {}".format(len(e_ts),project_id.name,parent_task_id.name))

        #we build the time cat before the subtask in order to let it inherit
        self.create_time_categories(parent_task_id,e_ts)
        #we build subtasks and timecategories according to found categories
        self.create_subtasks(element_key,parent_task_id,e_ts)
        
        for assignment in assignment_data:
            a_ts = list(filter(lambda a: a['KimbleOne__ActivityAssignment__c']==assignment['Id'],e_ts))
            if not a_ts or (not assignment['KimbleOne__ActivityRole__c']) :
                _logger.info("MIGRATION WARNING: No Timesheets or No Role For {}".format(assignment['KimbleOne__ActivityRole__c']))
                continue
            #assignment level values
            product_template = self.sf_id_to_odoo_rec(assignment['KimbleOne__ActivityRole__c'])
            
            hourly_rate = assignment['KimbleOne__InvoicingCurrencyForecastRevenueRate__c']
            employee = self.sf_id_to_odoo_rec(assignment['KimbleOne__Resource__c'])
            if not employee: 
                #this means the employee doesn't exists and we need to look through role to find the forecast employee
                product = self.sf_id_to_odoo_rec(assignment['KimbleOne__ActivityRole__c'])
                if product:
                    employee = product.forecast_employee_id
                #if not we look for the price, and DESCRIPTION OF THE SO LINE TO BE THE NAME OF THE ROLE IN KIMBLE
            if not employee:
                _logger.info("MAP.ERROR | No employee found for resource {} and role {}".format(assignment['KimbleOne__Resource__c'],assignment['KimbleOne__ActivityRole__c']))

            #we check if this employee is already mapped in the project, and if the mapping as the proper seniority
            map_create = True
            if employee in project_id.sale_line_employee_ids.mapped('employee_id'):
                map_line = project_id.sale_line_employee_ids.filtered(lambda l: l.employee_id == employee)[0]
                if product_template.seniority_level_id == map_line.sale_line_id.product_id.seniority_level_id:
                    #we have found an adequate mapping, i.e. the product_template seniority and the mapping seniority are equivalent
                    _logger.info("MAP.OK | {} on {}".format(employee.name,map_line.sale_line_id.name))
                    map_create = False
                    rate_id = map_line.sale_line_id.product_id.product_tmpl_id
                else:
                    #the mapping does not have the proper seniority, we delete
                    _logger.info("MAP.BAD | {} on {}".format(employee.name,map_line.sale_line_id.name))
                    map_line.unlink()
            
            if map_create:
                rate_lines = so_lines.filtered(lambda l: l.vcls_type == 'rate' and l.product_id.product_tmpl_id == product_template)
                map_vals = {
                    'employee_id': employee.id,
                    'project_id': project_id.id,
                    'sale_line_id': rate_lines[0].id if rate_lines else False,
                }
                if map_vals['sale_line_id']:
                    self.env['project.sale.line.employee.map'].create(map_vals)
                    rate_id = rate_lines[0].product_id.product_tmpl_id
                    _logger.info("MAP.CREATED {} {}".format(employee.name, rate_id.name))
                else:
                    if not product_template:
                        _logger.error("MAP.FAILED | No template found for {} {} for role {} in so lines {}".format(employee.name,employee.default_rate_ids[0].name,assignment['KimbleOne__ActivityRole__c'],so_lines.filtered(lambda l: l.vcls_type == 'rate').mapped('name')))
                    elif employee:
                        _logger.error("MAP.FAILED {} {} Product T {} {} in so lines {}".format(employee.name,employee.default_rate_ids[0].name,product_template.name,product_template.id,so_lines.filtered(lambda l: l.vcls_type == 'rate').mapped('name')))
                    else:
                        _logger.error("MAP.FAILED No employee Found for {} in so lines {}".format(product_template.id,so_lines.filtered(lambda l: l.vcls_type == 'rate').mapped('name')))
                    rate_id = False


            """if employee not in project_id.sale_line_employee_ids.mapped('employee_id'):

                product_template = self.sf_id_to_odoo_rec(assignment['KimbleOne__ActivityRole__c'])
                rate_lines = so_lines.filtered(lambda l: l.vcls_type == 'rate' and l.product_id.product_tmpl_id == product_template)
                #_logger.info("EMPLOYEE MAP | Employee {} not mapped | Product_tmpl from role {} id {}".format(employee.name,product_template.name,product_template.id))
                #_logger.info("EMPLOYEE MAP Rate Lines Found {}".format(rate_lines.mapped('name')))
                map_vals = {
                    'employee_id': employee.id,
                    'project_id': project_id.id,
                    'sale_line_id': rate_lines[0].id if rate_lines else False,
                }
                if map_vals['sale_line_id']:
                    self.env['project.sale.line.employee.map'].create(map_vals)
                    rate_id = rate_lines[0].product_id
                    #_logger.info("EMPLOYEE MAP CREATED {} {}".format(employee.name, rate_id.name))
                else:
                    _logger.info("EMPLOYEE MAP FAILED {}".format(employee.name))

            else:
                map_line = project_id.sale_line_employee_ids.filtered(lambda l: l.employee_id == employee)
                #_logger.info("EMPLOYEE MAP {} map Lines {}".format(employee.name,project_id.sale_line_employee_ids.mapped('employee_id.name')))
                rate_id = map_line[0].sale_line_id.product_id.product_tmpl_id if map_line else False
                #_logger.info("EMPLOYEE MAP FOUND {} {}".format(employee.name,rate_id.name if rate_id else False))"""

            #we finally loop in TS
            for ts in a_ts:
                #timesheet values
                stack = []
                if ts['KimbleOne__Category3__c']:
                    stack.append(ts['KimbleOne__Category3__c'])
                if ts['KimbleOne__Notes__c']:
                    stack.append(ts['KimbleOne__Notes__c'])

                task_key = self.env['etl.sync.keys'].search([('externalObjName','=','Timesheet_Map'),('externalId','=',element_key.externalId),('search_value','=',ts['KimbleOne__Category1__c'])],limit=1)
                task_id = int(task_key.odooId) if task_key else parent_task_id.id
                time_category = self.env['project.time_category'].search([('name','=ilike',ts['KimbleOne__Category2__c'])],limit=1)
                period = self.env['etl.sync.keys'].search([('externalObjName','=','KimbleOne__TimePeriod__c'),('externalId','=',ts['KimbleOne__TimePeriod__c'])],limit=1)
                date = period.name if period else False

                vals = {
                    'is_timesheet': True,
                    'name': " | ".join(stack) if len(stack)>0 else "N/A",
                    'employee_id': employee.id if employee else False,
                    'rate_id': rate_id.id if rate_id else False,
                    'main_project_id': main_project_id.id,
                    'project_id': project_id.id,
                    'task_id': task_id,
                    'time_category_id': time_category.id if time_category else False,
                    'date': date,
                    'unit_amount': ts['KimbleOne__EntryUnits__c'],
                    'lc_comment': ts['KimbleOne__Category4__c'],
                }

                vals = self.get_status_vals(vals,ts,inv_status)
                if hourly_rate > 0 and not vals.get('so_line_unit_price',False): #if the assignment was billable with a price
                    vals.update({'so_line_unit_price':hourly_rate})
                else: #else we let the system pick the value from the sale_order_line
                    pass

                #we finally check if we have enough to create the timesheet
                if employee and date:
                    self.env['account.analytic.line'].with_context(migration_mode = True).create(vals)
                    count += 1
                    _logger.info("Timesheet Created {}/{}".format(count,len(e_ts)))
                else:
                    _logger.info("IMPOSSIBLE TO CREATE TS {}".format(vals))
    
    def get_status_vals(self,vals,timesheet,inv_status):
        temp_stage = False
        is_validated = True
        for status in inv_status:
            
            if status.externalId == timesheet['KimbleOne__InvoiceItemStatus__c']:
                # VCLS status treatment
                if 'Draft' in timesheet['VCLS_Status__c']:
                    temp_stage = 'draft'
                    is_validated = False
                elif 'ReadyForApproval' in timesheet['VCLS_Status__c']:
                    temp_stage = 'lc_review'
                elif 'Approved' in timesheet['VCLS_Status__c']:
                    temp_stage = 'invoiceable'
                else:
                    temp_stage = False

                #_logger.info("MIGRATED TS {} from VCLS status".format(temp_stage))
                vals.update({
                        'validated': is_validated,
                    })

                #invoicing Status treatment
                if status.name == 'WrittenOff' or not temp_stage:
                    vals.update({
                        'unit_amount_rounded': 0,
                        'lc_comment': 'Migration - Rejected',
                        'stage_id': 'historical',
                    })
                elif status.name == 'Invoiced':
                    vals.update({
                        'unit_amount_rounded': timesheet['KimbleOne__EntryUnits__c'],
                        'stage_id': 'historical',
                    })
                else:
                    vals.update({
                        'unit_amount_rounded': timesheet['KimbleOne__EntryUnits__c'],
                        'stage_id': temp_stage,
                    })
                break
            #else:
                #_logger.info("MIGRATED TS STATUS NOT FOUND {}".format(temp_stage))
        return vals
        
    
    def create_time_categories(self,parent_task,timesheets_data):
        cat_names = self.values_from_key(timesheets_data,'KimbleOne__Category2__c')
        cat_names = list(set(cat_names))
        tc_ids = [self.env.ref('vcls-timesheet.travel_time_category').id]#we init with the travel TC
        _logger.info("FOUND Time Cat: {}".format(cat_names))
        if cat_names:
            for item in cat_names:
                if item:
                    #we search for an existing TC
                    tc = self.env['project.time_category'].search([('name','=ilike',item)],limit=1)
                    if tc:
                        tc_ids.append(tc.id)
                    else: #we create it
                        tc = self.env['project.time_category'].create({'name':item})
                        tc_ids.append(tc.id)
        #we write the task
        parent_task.write({'time_category_ids': [(6,0,tc_ids)]})

    def create_subtasks(self,element_key,parent_task,timesheets_data):
        sub_names = self.values_from_key(timesheets_data,'KimbleOne__Category1__c')
        sub_names = list(set(sub_names))
        for item in list(filter(lambda a: a not in ['No','None'],sub_names)):
            #we check if already created
            map_key = self.env['etl.sync.keys'].search([('externalObjName','=','Timesheet_Map'),('externalId','=',element_key.externalId),('search_value','=',item)],limit=1)
            if not map_key:
                #we create the subtask
                subtask = self.env['project.task'].create({
                    'project_id':parent_task.project_id.id,
                    'name': "{}:{}".format(parent_task.name,item),
                    'parent_id':parent_task.id,
                    'stage_id':parent_task.stage_id.id,
                })
                _logger.info("Subtask Creation {} | {}".format(subtask.project_id.name,subtask.name))
                self.env['etl.sync.keys'].create({
                    'externalObjName':'Timesheet_Map',
                    'externalId': element_key.externalId,
                    'search_value': item,
                    'odooId': str(subtask.id),
                    'state':'map',
                })
    
    @api.multi
    def build_quotations(self,instance):
        if not instance:
            return False

        #get some non-project depnedent variables
        invoice_template = self.env.ref('account.account_invoices')
        if not invoice_template:
            raise ValidationError("Default Invoice Template not found.")

        #We get all the source data required for the projects in self
        project_string = self.list_to_filter_string(self.mapped('project_sfid'))
        element_data = self._get_element_data(instance,project_string)
        project_data = self._get_project_data(instance,project_string)
        assignment_data = self._get_assignment_data(instance,project_string)

        proposal_string = self.list_to_filter_string(project_data,'KimbleOne__Proposal__c')
        proposal_data = self._get_proposal_data(instance,proposal_string)
        
        element_string = self.list_to_filter_string(element_data,'Id')
        milestone_data = self._get_milestone_data(instance,element_string)
        activity_data = self._get_activity_data(instance,element_string)
        annuity_data = self._get_annuity_data(instance,element_string)

        #Then we loop to process projects separately
        for project in self:
            my_project = list(filter(lambda p: p['Id']==project.project_sfid,project_data))[0]
            #we store the total invoicde amount for future use
            my_elements = list(filter(lambda element: element['KimbleOne__DeliveryGroup__c']==my_project['Id'],element_data))
            element_filter = project.list_to_filter_string(my_elements,'Id')
            project.sf_invoiced_amount = project._get_invoiced_amount(instance,element_filter)

            if not project.so_ids: #no sale order yet
                #core_team
                core_team = self.env['core.team'].create(project.prepare_core_team_data(my_project,assignment_data))
                quote_data = project.prepare_so_data(project_data,proposal_data,element_data)
                if quote_data:
                    parent_id = False
                    for quote in sorted(quote_data,key=lambda q: q['index']):
                        vals = quote['quote_vals']
                        vals.update({'core_team_id':core_team.id,'invoice_template':invoice_template.id})
                        if not parent_id:
                            _logger.info("PARENT SO CREATION VALS:\n{}".format(vals))
                            so = project.so_create_with_changes(vals)
                            parent_id = so
                        else:
                            vals.update({'parent_id':parent_id.id})
                            _logger.info("CHILD CREATION VALS:\n{}".format(vals))
                            so = project.so_create_with_changes(vals)

                        project.write({'so_ids':[(4, so.id, 0)]})
                        so.name = "{} | {}".format(vals['internal_ref'],vals['name'])
                        #we force the fiscal position
                        so.onchange_partner_shipping_id()
                        #we prepare line content
                        services_lines = project.prepare_services(quote['elements'],so,milestone_data)
                        rates_lines = project.prepare_rates(quote['elements'],activity_data,assignment_data)
                        milestones_lines = project.prepare_milestones(quote['elements'],milestone_data)
                        subscription_lines = project.prepare_subscriptions(quote['elements'],annuity_data)

                        #create lines
                        if services_lines:
                            #we create a section
                            section = self.env['sale.order.line'].create({
                                'order_id':so.id,
                                'display_type': 'line_section',
                                'name':'Services',
                                })
                            for service in services_lines:
                                line = project.so_line_create_with_changes(service['values'])
                                #we create a key for later usage
                                existing = self.env['etl.sync.keys'].search([('externalObjName','=','KimbleOne__DeliveryElement__c'),('externalId','=',service['element']['Id'])],limit=1)
                                if existing:
                                    existing.write({'odooId':str(line.id),'name':service['element']['Name']})
                                else:
                                    self.env['etl.sync.keys'].create({
                                        'externalObjName':'KimbleOne__DeliveryElement__c',
                                        'externalId':service['element']['Id'],
                                        'state':'map',
                                        'name':service['element']['Name'],
                                        'odooModelName':'sale.order.line',
                                        'odooId':str(line.id),
                                    })
                        
                        #Milestones Lines creation
                        element_section = False
                        for milestone in milestones_lines:
                            milestone.update({'order_id':so.id})
                            if milestone.get('display_type','') == 'line_section':
                                element_section = self.env['sale.order.line'].create(milestone)
                            else:
                                milestone.update({'section_line_id':element_section.id if element_section else False})
                                project.so_line_create_with_changes(milestone)
                        
                        #Subscriptions Lines creation
                        sub_section = False
                        for sub in subscription_lines:
                            sub.update({'order_id':so.id})
                            if sub.get('display_type','') == 'line_section':
                                sub_section = self.env['sale.order.line'].create(sub)
                            else:
                                sub.update({'section_line_id':sub_section.id if sub_section else False})
                                project.so_line_create_with_changes(sub)
                                
                            
                        
                        if rates_lines:
                            #we create a section
                            section = self.env['sale.order.line'].create({
                                'order_id':so.id,
                                'display_type': 'line_section',
                                'name':'Hourly Rates',
                                })
                            for rate in rates_lines:
                                vals = {
                                    'order_id':so.id,
                                    'product_id': rate['product_id'],
                                    'product_uom_qty':0,
                                    'section_line_id':section.id,
                                    }
                                if rate['price'] > 0:
                                    vals.update({'price_unit':rate['price']})
                                project.so_line_create_with_changes(vals)
                project.migration_status = 'so'
            
            if project.migration_status == 'so':
                #we confirm the orders
                for so in project.so_ids:
                    so.action_sync()
                    so.action_confirm()
                    _logger.info("Confirming SO {}".format(so.name))

                    #we update the subscriptions date
                    subscriptions = self.env['sale.subscription'].search([('analytic_account_id','=',so.analytic_account_id.id)])
                    subscriptions.force_start_date()

                #project.process_forecasts(activity_data,assignment_data)
                #project.build_mapping()
                project.migration_status = 'structure'
    
    """def build_mapping(self,assignment_data):
        for 
        pass"""
    
    def so_line_create_with_changes(self,vals):
        line = self.env['sale.order.line'].create(vals)
        if line.display_type != 'line_section':
            line.product_id_change()
            line.product_uom_change()
            line.write(vals)
            #line._inverse_qty_delivered()
            
        return line
    
    def so_create_with_changes(self,vals):
        so = self.env['sale.order'].create(vals)
        so._compute_tax_id()
        return so
    
    def process_forecasts(self,activity_data,assignment_data):
        so_lines = self.so_ids.mapped('order_line')
        for line in so_lines:
            #we look for a key
            existing = self.env['etl.sync.keys'].search([('externalObjName','=','KimbleOne__DeliveryElement__c'),('odooModelName','=','sale.order.line'),('odooId','=',str(line.id))],limit=1)
            if existing:
                _logger.info("Processing Forecasts for {}".format(existing.name))
                activities = list(filter(lambda a: a['KimbleOne__DeliveryElement__c']==existing['externalId'],activity_data))
                if activities:
                    activity = activities[0]
                    assignments = list(filter(lambda a: a['KimbleOne__ResourcedActivity__c']==activity['Id'],assignment_data))
                    #we get all the roles
                    roles = self.values_from_key(assignments,'KimbleOne__ActivityRole__c')
                    roles = list(set(roles)) #we make it a unique list
                    for role in roles:
                        role_assignments = list(filter(lambda a: a['KimbleOne__ActivityRole__c']==role,assignments))
                        forecasted_amount = sum(self.values_from_key(role_assignments,'KimbleOne__ForecastUsage__c'))
                        #we find the existing forecast
                        rate_product = self.sf_id_to_odoo_rec(role)
                        employee = rate_product.forecast_employee_id if rate_product else False
                        if employee:
                            forecast = self.env['project.forecast'].search([('task_id','=',line.task_id.id),('employee_id','=',employee.id)],limit=1)
                            if forecast:
                                forecast.write({'resource_hours':forecasted_amount})
                                _logger.info("Forecast Updated for {} in {} with {} hours".format(employee.name,line.task_id.name,forecasted_amount))
  
            else:
                pass

    def prepare_subscriptions(self,elements,annuity_data):
        output=[]
        subscriptions = list(filter(lambda a: a['prod_info']['type']=='subscription',elements))
        for line in subscriptions:
            o_product = self.sf_id_to_odoo_rec(line['KimbleOne__Product__c'],line['Activity__c'])
            if not o_product:
                _logger.error("PRODUCT NOT FOUND FOR {} {}".format(line['KimbleOne__Product__c'],line['Activity__c']))
                #continue
            #we create one section per element, then one so line per milestone
            output.append({
                'display_type': 'line_section',
                'name':line['Name'],
                })

            annuities = list(filter(lambda a: a['KimbleOne__DeliveryElement__c']==line['Id'],annuity_data))
            for sub in annuities:
                output.append({
                        'name':sub['Name'],
                        'product_id':o_product.id,
                        'product_uom_qty':sub['KimbleOne__InitialNumberOfUnits__c'] or 1.0,
                        'price_unit':sub['KimbleOne__InvoicingCurrencyRevenueRate__c'],
                    })
        return output
        

    def prepare_milestones(self,elements,milestone_data):
        output=[]
        milestones = list(filter(lambda a: a['prod_info']['type']=='milestone',elements))
        for line in milestones:
            o_product = self.sf_id_to_odoo_rec(line['KimbleOne__Product__c'],line['Activity__c'])
            if not o_product:
                _logger.error("PRODUCT NOT FOUND FOR {} {}".format(line['KimbleOne__Product__c'],line['Activity__c']))
            #we create one section per element, then one so line per milestone
            output.append({
                'display_type': 'line_section',
                'name':line['Name'],
                })
            
            #we get the milestones corresponding to the line
            msts = list(filter(lambda a: a['KimbleOne__DeliveryElement__c']==line['Id'],milestone_data))
            for mst in msts:
                invoicing_status = self.env['etl.sync.keys'].search([('externalId','=',mst['KimbleOne__InvoiceItemStatus__c']),('externalObjName','=','KimbleOne__ReferenceData__c'),('search_value','=','InvoiceItemStatus')])
                if invoicing_status.name != 'WrittenOff':
                    output.append({
                        'name':mst['Name'],
                        'product_id':o_product.id,
                        'product_uom_qty':1,
                        'price_unit':mst['KimbleOne__InvoicingCurrencyMilestoneValue__c'],
                        'qty_delivered': 1.0 if invoicing_status.name in ['Ready','Invoiced'] else 0.0,
                        'historical_invoiced_amount':mst['KimbleOne__InvoicingCurrencyMilestoneValue__c'] if invoicing_status.name in ['Invoiced'] else 0.0,
                    })

        return output


    def prepare_services(self,elements,sale_order,milestone_data):
        output=[]
        services = list(filter(lambda a: a['prod_info']['type']=='service',elements))
        for line in services:
            o_product = self.sf_id_to_odoo_rec(line['KimbleOne__Product__c'],line['Activity__c'])
            mode = line['prod_info']['mode'] 
            if o_product and mode=='tm':
                vals = {
                    'order_id':sale_order.id,
                    'name':line['Name'],
                    'product_id':o_product.id,
                    'product_uom_qty':1,
                    'price_unit':line['Contracted_Budget__c'] or line['KimbleOne__InvoicingCurrencyContractRevenue__c'],
                }
                output.append({'element':line,'values':vals})
            elif o_product and mode=='fixed_price':
                milestones_values = self.sum_milestones(line,milestone_data)
                vals = {
                    'order_id':sale_order.id,
                    'name':line['Name'],
                    'product_id':o_product.id,
                    'product_uom_qty':1,
                    'price_unit':milestones_values['ordered'],
                    'qty_delivered':milestones_values['delivered']/milestones_values['ordered'] if milestones_values['ordered']>0 else 0,
                    'historical_invoiced_amount':milestones_values['invoiced'],
                }
                output.append({'element':line,'values':vals})
            else:
                _logger.info("No Odoo Product found for {}".format(line))
        return output

    def sum_milestones(self,element,milestone_data):
        milestones = list(filter(lambda a: a['KimbleOne__DeliveryElement__c']==element['Id'],milestone_data))
        ordered = 0
        delivered = 0
        invoiced = 0
        for milestone in milestones:
            invoicing_status = self.env['etl.sync.keys'].search([('externalId','=',milestone['KimbleOne__InvoiceItemStatus__c']),('externalObjName','=','KimbleOne__ReferenceData__c'),('search_value','=','InvoiceItemStatus')])
            if invoicing_status:
                if invoicing_status.name in ['None','WrittenOff']:
                    ordered += milestone['KimbleOne__InvoicingCurrencyMilestoneValue__c']
                elif invoicing_status.name == 'Ready':
                    delivered += milestone['KimbleOne__InvoicingCurrencyMilestoneValue__c']
                elif invoicing_status.name == 'Invoiced':
                    invoiced += milestone['KimbleOne__InvoicingCurrencyMilestoneValue__c']
                else:
                    _logger.error("Invoicing Status Mismatch for milestone in {}\n{}".format(element,milestone))
            else:
                _logger.error("Invoicing Status Mismatch for milestone in {}\n{}".format(element,milestone))
        output = {
            'ordered':ordered+delivered+invoiced,
            'delivered':delivered+invoiced,
            'invoiced':invoiced,
        }
        #_logger.info("Milestones for element {}\n{}".format(element,output))
        return output
            
        
    ###
    def prepare_rates(self,elements,activity_data,assignment_data):
        rates = []
        for element in elements:
            if not element['prod_info']:
                _logger.info("MISSING PROD INFO FOR {} {}".format(element['KimbleOne__Reference__c'],element['KimbleOne__Product__c']))
                mode = 'tm'
            else:
                mode = element['prod_info']['mode']
            if mode in ['tm','fixed_price']: #if this element has assignement
                activities = list(filter(lambda a: a['KimbleOne__DeliveryElement__c']==element['Id'],activity_data))
                if activities:
                    activity = activities[0]
                    assignments = list(filter(lambda a: a['KimbleOne__ResourcedActivity__c']==activity['Id'],assignment_data))
                    for assignment in assignments:
                        o_rate_product = self.sf_id_to_odoo_rec(assignment['KimbleOne__ActivityRole__c'])
                        if o_rate_product:
                            #we check if already found
                            existing = list(filter(lambda p: p['product_id']==o_rate_product.id,rates))
                            if existing:
                                if assignment['KimbleOne__InvoicingCurrencyForecastRevenueRate__c'] > existing[0]['price']: #if we found a cheaper one, we need to update it
                                    index = rates.index(existing[0])
                                    rates[index]['price']= assignment['KimbleOne__InvoicingCurrencyForecastRevenueRate__c']
                                else:
                                    pass
                            else:
                                #we add a rate
                                product_key = self.env['etl.sync.keys'].search([('externalId','=',assignment['KimbleOne__ActivityRole__c']),('odooId','!=',False)],limit=1)
                                rates.append({'name':product_key.name,'product_id':o_rate_product.id,'price':assignment['KimbleOne__InvoicingCurrencyRevenueRate__c']})

        return sorted(rates,key=lambda r: r['price'],reverse = True)
               


    def prepare_core_team_data(self,my_project,assignment_data=False):
        core_team = {'name':"Team {}".format(my_project['KimbleOne__Reference__c'])}
        consultants = []

        #we get the LC
        o_user = self.sf_id_to_odoo_rec(my_project['OwnerId'])
        if o_user:
            employee = self.env['hr.employee'].with_context(active_test=False).search([('user_id','=',o_user.id)],limit=1)
            if employee:
                core_team['lead_consultant'] = employee.id

        #we look all assignments to extract resource data
        if assignment_data:
            assignments = list(filter(lambda a: a['KimbleOne__DeliveryGroup__c']==my_project['Id'],assignment_data))
            resources = self.values_from_key(assignments,'KimbleOne__Resource__c')
            resources = list(set(resources)) #get unique values
            for res in resources:
                emp = self.sf_id_to_odoo_rec(res)
                if emp:
                    consultants.append(emp.id)

            core_team['consultant_ids'] = [(6, 0, consultants)]

        return core_team


    def prepare_so_data(self,project_data,proposal_data,element_data):
        """
        We use a list of dict quote_data=
        {
            index: index of the element trigerring the new quotation
            quote_vals: data to call the create
            elements: sf_id of the elements linked to this quote
        }
        """
        self.ensure_one()
        quote_data = []

        my_project = list(filter(lambda project: project['Id']==self.project_sfid,project_data))[0]
        my_proposal = list(filter(lambda proposal: proposal['Id']==my_project['KimbleOne__Proposal__c'],proposal_data))[0]
        
        #we get useful exisitng records
        o_opp = self.sf_id_to_odoo_rec(my_proposal['KimbleOne__Opportunity__c'])
        o_company = self.sf_id_to_odoo_rec(my_proposal['KimbleOne__BusinessUnit__c'])

        #get useful fields values
        o_tag = self.env['crm.lead.tag'].search([('name','=','Automated Migration')],limit=1)
        tag = o_tag.id if o_tag else False
        currency_code = my_project['KimbleOne__InvoicingCurrencyIsoCode__c'] or o_company.currency_id.name
        o_pricelist = self.env['product.pricelist'].search([('name','=',"Standard {}".format(currency_code))],limit=1)
        o_invoice_template = self.env.ref('account.account_invoices')
        o_activity_template = self.env.ref('vcls-invoicing.invoice_activity_simple_report')

        if not o_pricelist:
            _logger.error("Pricelist not found {}".format(my_project['KimbleOne__InvoicingCurrencyIsoCode__c']))
            return False
        o_business_line = self.sf_id_to_odoo_rec(my_project['Activity__c'])
        bl = o_business_line.id if o_business_line else False

        my_elements = list(filter(lambda element: element['KimbleOne__DeliveryGroup__c']==my_project['Id'],element_data))

        quotations = self.split_elements(my_elements)
        index = 0
        for item in quotations:
            start_date = my_proposal['KimbleOne__DeliveryStartDate__c'] or date.today().strftime('%Y-%m-%d')
            end_date = my_project['KimbleOne__ExpectedEndDate__c'] or date.today().strftime('%Y-%m-%d')
            _logger.info("START {} END {}".format(start_date,end_date))
            if end_date < start_date:
                _logger.info("START {} END {}".format(start_date,end_date))
                end_date = start_date
            quote_vals = {
                'company_id':o_company.id,
                'partner_id':o_opp.partner_id.id,
                'user_id': o_opp.partner_id.user_id.id,
                'opportunity_id':o_opp.id,
                'internal_ref':("{}.{}".format(my_project['KimbleOne__Reference__c'],index) if index>0 else my_project['KimbleOne__Reference__c']).upper(),
                'name': (my_project['Name'] + (' -FP' if item['mode']=='fixed_price' else ' -TM')) if index>0 else my_project['Name'],
                'unrevisioned_name':self.env['ir.sequence'].with_context(force_company=o_company.id).next_by_code('sale.order'),
                'invoicing_mode':item['mode'] if item['mode'] else False,
                'pricelist_id':o_pricelist.id,
                'scope_of_work': my_project['Scope_of_Work_Description__c'],
                'expected_start_date':start_date,
                'expected_end_date':end_date,
                'tag_ids':[(4, tag, 0)],
                'product_category_id':bl,
                'fp_delivery_mode': 'manual',
                'merge_subtask':True,
                'communication_rate': o_opp.partner_id.communication_rate,
                'invoice_template': o_invoice_template.id,
                'activity_report_template': o_activity_template.id,
            }
            quote_data.append({'index':item['min_index'],'quote_vals':quote_vals, 'elements':item['elements']})  
            index += 1

        return quote_data

    ###
    def split_elements(self,element_data):
        """
        We use a list of dict output=
        {
            min_index: used to prioritize quotation creation
            elements: elements data linked to this quote
        }
        """
        tm_group = {'min_index':100,'elements':[],'mode':'tm'}
        fp_group = {'min_index':100,'elements':[],'mode':'fixed_price'}
        others = {'min_index':100,'elements':[]}

        for element in sorted(element_data,key=lambda q: q['KimbleOne__Reference__c']):

            prod_info = list(filter(lambda info: info['sf_id']==element['KimbleOne__Product__c'][:-3],SFProjectSync_constants.ELEMENTS_INFO))
            mode = prod_info[0]['mode'] if prod_info else False
            index = int(element['KimbleOne__Reference__c'][-2:])
            element.update({'index':index,'prod_info':prod_info[0] if prod_info else False}) #we add this info for future use in SO lines creations
            
            #proposal = element['KimbleOne__OriginatingProposal__c']
            
            if mode=='tm':
                tm_group['elements'].append(element)
                if index < tm_group['min_index']:
                    tm_group['min_index'] = index
            elif mode=='fixed_price':
                fp_group['elements'].append(element)
                if index < fp_group['min_index']:
                    fp_group['min_index'] = index
            else:
                others['elements'].append(element)
                if index < others['min_index']:
                    others['min_index'] = index

        #we merge the groups
        if len(tm_group['elements'])>0:
            tm_group['elements'] = sorted(tm_group['elements'] + others['elements'],key=lambda q: q['index'])
            tm_group['min_index'] = min(tm_group['min_index'],others['min_index'])
        elif len(fp_group['elements'])>0:
            fp_group['elements'] = sorted(fp_group['elements'] + others['elements'],key=lambda q: q['index'])
            fp_group['min_index'] = min(fp_group['min_index'],others['min_index'])
        
        output = []
        if len(tm_group['elements'])>0:
            output.append(tm_group)
        if len(fp_group['elements'])>0:
            output.append(fp_group)
        return sorted(output,key=lambda q: q['min_index'])

    ###  
    def _get_invoiced_amount(self,instance,filter_string = False):
        query = SFProjectSync_constants.SELECT_GET_INVOICED_AMOUNT
        query += "WHERE KimbleOne__DeliveryElement__c IN " + filter_string
        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Invoiced from Elements".format((records[0]['expr0'])))
        return records[0]['expr0']

    def _get_timesheet_data(self,instance,filter_string = False, max_id=0):
        query = SFProjectSync_constants.SELECT_GET_TIME_ENTRIES
        query += "WHERE KimbleOne__DeliveryElement__c IN " + filter_string
        #we add a filter and order by to manage batches of 200
        query += " AND Migration_Index__c>{} ORDER BY Migration_Index__c LIMIT 200".format(max_id)
        _logger.info(query)

        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Time Entries".format(len(records)))
        
        return records

    def _get_element_data(self,instance,filter_string = False):
        query = SFProjectSync_constants.SELECT_GET_ELEMENT_DATA
        query += "WHERE Automated_Migration__c = TRUE AND KimbleOne__DeliveryGroup__c IN " + filter_string + " ORDER BY KimbleOne__Reference__c ASC"
        _logger.info(query)

        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Elements".format(len(records)))
        
        return records

    def _get_project_data(self,instance,filter_string = False):
        query = SFProjectSync_constants.SELECT_GET_PROJECT_DATA
        query += "WHERE Id IN " + filter_string
        _logger.info(query)

        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Projects".format(len(records)))
        
        return records

    def _get_proposal_data(self,instance,filter_string = False):
        query = SFProjectSync_constants.SELECT_GET_PROPOSAL_DATA
        query += "WHERE Id IN " + filter_string
        _logger.info(query)

        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Proposals".format(len(records)))
        
        return records
    
    def _get_milestone_data(self,instance,filter_string = False):
        #we get only revenue milestones
        query = SFProjectSync_constants.SELECT_GET_MILESTONE_DATA
        query += "WHERE KimbleOne__DeliveryElement__c IN " + filter_string + " AND KimbleOne__MilestoneType__c='a3d3A0000004bNb'"
        _logger.info(query)

        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Milestones".format(len(records)))
        
        return records
    
    def _get_assignment_data(self,instance,filter_string = False,mode='Project'):
        query = SFProjectSync_constants.SELECT_GET_ASSIGNMENT_DATA
        if mode == 'Project':
            query += "WHERE KimbleOne__DeliveryGroup__c IN " + filter_string
        elif mode == 'Id':
            query += "WHERE Id IN " + filter_string
        else:
            pass
        _logger.info(query)

        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Assignments".format(len(records)))
        
        return records
    
    def _get_activity_data(self,instance,filter_string = False):
        query = SFProjectSync_constants.SELECT_GET_ACTIVITY_DATA
        query += "WHERE KimbleOne__DeliveryElement__c IN " + filter_string
        _logger.info(query)

        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Resourced Activities".format(len(records)))
        
        return records
    
    def _get_annuity_data(self,instance,filter_string = False):
        query = SFProjectSync_constants.SELECT_GET_ANNUITY_DATA
        query += "WHERE KimbleOne__DeliveryElement__c IN " + filter_string
        _logger.info(query)

        records = instance.getConnection().query_all(query)['records']
        _logger.info("Found {} Annuities".format(len(records)))
        
        return records


    ######
    @api.model
    def _dev(self):
        instance = self.getSFInstance()
        self._get_time_entries(instance)
    

    def _get_time_entries(self,instance=False):
        
        query = """ 
            SELECT 
                Id,
                KimbleOne__DeliveryElement__c,
                KimbleOne__Category1__c,
                KimbleOne__Category2__c,
                KimbleOne__Category3__c,
                KimbleOne__Category4__c,
                KimbleOne__Notes__c,

                KimbleOne__InvoiceItemStatus__c,
                
                KimbleOne__TimePeriod__c,
                KimbleOne__Resource__c,
                KimbleOne__InvoicingCurrencyEntryRevenue__c,
                KimbleOne__EntryUnits__c,
                KimbleOne__ActivityAssignment__c,
                VCLS_Status__c
            FROM KimbleOne__TimeEntry__c
            WHERE KimbleOne__DeliveryElement__c IN ('a1U0Y00000BexAu','a1U0Y00000BexB4')
            AND VCLS_Status__c IN ('Billable - Draft','Billable - ReadyForApproval','Billable - Approved')
            """
            
            
        records = instance.getConnection().query_all(query)['records']
        for rec in records:
            _logger.info("{}\n{}".format(query,rec))
            break
        _logger.info("FOUND TIME ENTRIES {}".format(len(records)))



    ####################
    ## MAPPING METHODS
    ####################
    @api.model
    def build_reference_data(self):
        instance = self.getSFInstance()
        self._build_invoice_item_status(instance)
        self._build_milestone_type(instance)
        self._build_time_periods(instance)

    @api.model
    def build_maps(self):
        instance = self.getSFInstance()
        self._build_company_map(instance)
        self._build_product_map(instance)
        self._build_rate_map(instance)
        self._build_user_map(instance)
        self._build_activity_map(instance)
        self._build_resources_map(instance)
        self._test_maps(instance)


    ####################
    ## TOOL METHODS
    ####################
    def values_from_key(self,dict_list, key):
        output = []
        for item in dict_list:
            output.append(item[key])
        return output

    def sf_id_to_odoo_rec(self,sf_id,search_value = False):
        if search_value:
            key = self.env['etl.sync.keys'].search([('externalId','=',sf_id),('search_value','=',search_value),('odooId','!=',False)],limit=1)
        else:
            key = self.env['etl.sync.keys'].search([('externalId','=',sf_id),('odooId','!=',False)],limit=1)
        if key:
            return self.env[key.odooModelName].browse(int(key.odooId))
        else:
            return False
    
    def list_to_filter_string(self,list_in,key=False):
        stack = []
        for item in list_in:
            if key:
                stack.append("\'{}\'".format(item[key])) 
            else:
                stack.append("\'{}\'".format(item))
        #we remove duplicates
        stack = list(set(stack))  
        result = "({})".format(",".join(stack))
        return result
    
    def int_list_to_string_list(self,list_in,key=False):
        stack = []
        for item in list_in:
            if key:
                stack.append('{}'.format(item[key])) 
            else:
                stack.append('{}'.format(item))  
        return stack
    
        
        

    



