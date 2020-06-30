# -*- coding: utf-8 -*-
#Python Imports
from datetime import date, datetime, time, timedelta
import xlsxwriter
import base64

#Odoo Imports
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

import logging
_logger = logging.getLogger(__name__)

class BillabilityExport(models.Model):
    _name = 'export.billability'
    _inherit = 'export.excel.mixin'
        
    """ This model represents an export of employees containing information required to compute capacity of the resource over a particular period. """

    name = fields.Char(readonly = True)
    active = fields.Boolean(default=True)
    
    attachment_id = fields.Many2one(
        string = 'Excel File',
        readonly = True,
        )
    
    ################
    # CRUD METHODS #
    ################
    
    #At export creation, we generate the uid, and call the line create methods
    @api.model
    def create(self,vals):
        
        #export is created
        export=super().create(vals)
        
        #Build name
        count = len(self.env['export.billability'].search([('start_date','=',export.start_date),('end_date','=',export.end_date)]))
        export.name = "{:{dfmt}}_{:{dfmt}}_BillabilityExport_{:02}".format(export.start_date,export.end_date,count,dfmt='%Y%m%d')
        
        export.generate_excel(export.sudo().build_data())
        
        return export
    
    ################
    # TOOL METHODS #
    ################
    
    def build_data(self, start_date=False, end_date=False):
        """ This methods computes a list of dictionnaries for the excel billability export.
        Each row will be related to one active contract for the employee over the defined period.
        Each roww will contain related capacity information, including raw capacity and leaves.
        To make comptation easier, we will iterate over Companies in order to compute a default capacity."""
        start_date = start_date or self.start_date
        end_date = end_date or self.end_date
        
        _logger.info("|||End Date line 55|||:{}".format(end_date))
        if self.end_date:
            _logger.info("|||self.end_date 56|||:{}".format(self.end_date))
        data= []
        distribution = {
            'Days [d]': 0,
            'Weekends [d]': 0,
            'Bank Holiday [d]': 0,
            'Out of Contract [d]': 0, 
            'Day Duration [h]': 8,
            'Offs [d]': 0,
            'Leaves [d]': 0,
            'Worked [d]': 0,
            'Effective Capacity [h]': 0,
            # 'Control [d]': -1,
        }
        
        all_days = set(start_date + timedelta(days=x) for x in range((end_date-start_date).days + 1))
        distribution['Days [d]'] = len(all_days)
        
        #we remove the weekend
        gen_worked_days = set(filter(lambda d: d.weekday()<5,all_days))
        distribution['Weekends [d]'] = distribution['Days [d]']-len(gen_worked_days)
        
        #loop companies to access bank holidays
        companies = self.env['res.company'].search([('short_name','!=','BH')])
        for company in companies:
            bank_days = set(self.env['hr.bank.holiday'].search([('company_id.id','=',company.id),('date','>=',start_date),('date','<=',end_date)]).mapped('date'))
            distribution['Bank Holiday [d]'] = len(bank_days)
            comp_worked_days = gen_worked_days - bank_days
            
            #we now look into contracts valid over the defined period (i.e. starterd before the export end, end after export start, no end planned)
            contracts = self.env['hr.contract'].search([('employee_id.employee_type','=','internal'),('company_id.id','=',company.id),('date_start','<=',end_date),
                                                        '|',('date_end','>=',start_date),('date_end','=',False),
                                                        '|',('employee_id.employee_end_date','>=',start_date),('employee_id.employee_end_date','=',False)])
            
            #TODO: check if contract started during this week, and if so, add last contract
            
            name_dict = {}
            #makes a dict with names as keys and contracts as values
            for contract in contracts:
                name = contract.employee_id.name
                if name not in name_dict:    
                    name_dict[name] = []
                name_dict[name].append(contract)
            #keeps names with more than 1 contract
            extra_contracts = {k:v for (k,v) in name_dict.items() if len(v) > 1}
            #finds most recent contract and removes 
            for name, values in extra_contracts.items():
                difference = {}
                for contract in values:
                    difference[contract] =  date.today() - contract.date_start
                
                correct_contract = min(difference, key=difference.get)
                values.remove(correct_contract)
            extra_contracts_list = [v for k,v in extra_contracts.items()]
            extra_contracts_list_flat = [item for sublist in extra_contracts_list for item in sublist]
            # end_date = datetime.datetime.date(2020,6,28)
            # end_date = datetime.strptime('2020-06-28', '%Y-%m-%d').date()
            for contract in contracts:
                #if the contract is in extra_contracts, its a duplicate then dont add them to the data
                if contract in extra_contracts_list_flat:
                    continue
                if not (contract.resource_calendar_id):
                    raise ValidationError('The contract {} has no working schedule configured.'.format(contract.name))
                    
                start_date = max(contract.date_start,start_date)

                # end_date = min(contract.date_end if contract.date_end else end_date, contract.employee_id.employee_end_date if contract.employee_id.employee_end_date else end_date)
                
                # end_date = end_date if contract.date_end > end_date else contract.date_end
                # end_date = end_date if contract.employee_id.employee_end_date > end_date else contract.employee_id.employee_end_date
                
                # if contract.date_end and contract.date_end < end_date:
                #     end_date = contract.date_end
                #     if 'Aurore' in contract.name:
                #         _logger.info("end_date change cont:{}".format(end_date))
                # if contract.employee_id.employee_end_date and contract.employee_id.employee_end_date < end_date:
                #     end_date =  contract.employee_id.employee_end_date
                #     if 'Aurore' in contract.name:
                #         _logger.info("end_date change term:{}".format(end_date))
                # if contract.date_end and 'Aurore' in contract.name:
                #     _logger.info("|||cont-end|||:{}".format(contract.date_end))
                # if contract.employee_id.employee_end_date and 'Aurore' in contract.name:
                #     _logger.info("|||employee end date|||:{}".format(contract.employee_id.employee_end_date))
                # if 'Aurore' in contract.name:
                #     _logger.info("|||end_date 128!!!|||:{}".format(end_date))
                if 'Aurore' in contract.name:
                    _logger.info("|||end_date 128!!!|||:{}".format(end_date))
                contr_worked_days = set(filter(lambda d: d >= contract.date_start and d <= end_date,comp_worked_days))

                distribution['Out of Contract [d]'] = len(comp_worked_days)-len(contr_worked_days)
                if 'Aurore' in contract.name:
                    _logger.info("Billability:BILL startdate: {},BILL enddate:{}, Gen WD: {},compWD:{},contractWD:{},cont-Start:{},cont-end:{}".format(start_date,end_date,gen_worked_days,comp_worked_days,contr_worked_days,contract.date_start,contract.date_end))
                
                #we get leaves of the employee over the contract period
                leaves = self.env['hr.leave'].search([('employee_id.id','=',contract.employee_id.id),('state','=','validate'),('date_from','<=',end_date),('date_to','>=',start_date)])
                attendances = contract.resource_calendar_id.attendance_ids
                distribution['Day Duration [h]'] = (contract.resource_calendar_id.effective_hours/len(attendances))*2
                
                #we finally loop through the days to know if it is a days off/leave/or worked
                distribution['Offs [d]'] = 0
                distribution['Leaves [d]'] = 0
                distribution['Worked [d]'] = 0
                for d in contr_worked_days:
                    #compute off time
                    budget = 1.0
                    if len(attendances)<10: #if employee not working every day
                        #days are off if we don't find attendances in the working time for this particular day of the week
                        off = 1.0-len(contract.resource_calendar_id.attendance_ids.filtered(lambda a: a.dayofweek == str(d.weekday())))*0.5
                        distribution['Offs [d]'] += off
                        budget -= off #we decrement budget accordingly
                    
                    #compute leave time
                    if budget>0 and leaves: #if leaves are overlapping the period
                        leave = leaves.filtered(lambda l: l.date_from.date()<=d and l.date_to.date()>=d) #if this specific date is included in one of the leaves
                        if leave:
                            if leave[0].request_unit_half: #if this is a half a day leave request
                                distribution['Leaves [d]'] += 0.5
                                budget -= 0.5
                            else:
                                distribution['Leaves [d]'] += budget
                                budget -= budget
                    
                    #worked time is the remaining one
                    distribution['Worked [d]'] += max(budget,0)

                    if 'Aurore' in contract.name:
                        _logger.info("Billability: DAY: ,employee: {}, offs: {}, leaves: {}".format(d,contract.name,distribution['Offs [d]'],distribution['Leaves [d]']))

                    #KPI's
                distribution['Effective Capacity [h]'] = distribution['Worked [d]']*distribution['Day Duration [h]']
                if 'Aurore' in contract.name:
                    _logger.info("||||Billability|||| week start date :{} employee: {}, offs: {}, leaves: {}, day duration: {}, worked: {}".format(start_date,contract.name,distribution['Offs [d]'],distribution['Leaves [d]'],distribution['Day Duration [h]'],distribution['Worked [d]']))
                # distribution['Control [d]'] = distribution['Days [d]'] - (distribution['Weekends [d]'] + distribution['Bank Holiday [d]'] + distribution['Out of Contract [d]'] + distribution['Offs [d]'] + distribution['Leaves [d]'] + distribution['Worked [d]']

                         
                data.append(self.build_row(contract,distribution))   
        
        return sorted(data, key=lambda k: k['Employee Name'])
    
    """ Complete the distribution dictionnary with employee/contract related info"""
    def build_row(self,contract,distribution):
        
        line = {
            #employee related
            'Employee ID': contract.employee_id.employee_external_id,
            'Employee Name': contract.employee_id.name,
            'Email': contract.employee_id.work_email,
            'Company': contract.company_id.name,
            'Office': contract.employee_id.office_id.name,
            'Employee Start Date': str(contract.employee_id.employee_start_date),
            'Employee End Date': str(contract.employee_id.employee_end_date),
            'Line Manager': contract.employee_id.parent_id.name,
            'Line Manager ID': contract.employee_id.parent_id.employee_external_id,
            #contract related
            'Contract Name': contract.name,
            'Contract Start': str(contract.date_start),
            'Contract End': str(contract.date_end),
            'Contract Type': contract.type_id.name,
            'Department':  contract.job_id.department_id.name,
            'Job Title': contract.job_id.project_role_id.name,
            'Working Percentage': contract.resource_calendar_id.effective_percentage,
            'Raw Weekly Capacity [h]': contract.resource_calendar_id.effective_hours,
            'Employee Internal ID': contract.employee_id.id,
            'Consult %' : contract.consultancy_percentage
        }
        line = {**line, **distribution}
 
        #raise ValidationError("{}".format(line))
        return line
        
        
        
    
    