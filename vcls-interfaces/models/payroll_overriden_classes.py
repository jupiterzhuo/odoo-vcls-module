# -*- coding: utf-8 -*-
#Python Imports
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
#Odoo Imports
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class VclsEntity(models.Model):
    _inherit = 'res.company'

    """ We just add a short name to the company object in order to use it in files naming conventions """
    short_name = fields.Char(
        string = 'Short Name',)

    """ We override the field to allow a translation of the string"""
    phone = fields.Char(related='partner_id.phone', string=_("Phone"), store=True, readonly=False)
    vat = fields.Char(related='partner_id.vat', string=_("VAT"), readonly=False)
    siret = fields.Char(related='partner_id.siret', string=_("Siret"), readonly=False)
    capital = fields.Text(string=_("Capital"), readonly=False, translate=True)

    @api.multi
    def _get_vcls_template_report_data(self):
        return {
            '_t': _,
        }

class LeaveType(models.Model):
    _inherit = 'hr.leave.type'
    
    """ We add a field to capture in which payroll export column a specific type is related to."""
    
    payroll_type = fields.Selection([
        ('rtt', 'RTT'),
        ('cp_paid', 'CP Paid'),
        ('cp_unpaid', 'CP Unpaid'),
        ('sick', 'Sick'),
        ('other_paid','Other Paid'),
        ])
    
class Leave(models.Model):
    _inherit = 'hr.leave'
    
    """ We add fields to support the payroll export and have a comfortable splitting of leave if required"""
    
    trunc_start = fields.Date(
        string = 'Truncated Start',
        readonly = True,
        )
    
    trunc_end = fields.Date(
        string = 'Truncated End',
        readonly = True,
        )
    
    trunc_duration = fields.Float(
        string = 'Truncated Duration',
        readonly = True,
        )
    
    export_string = fields.Char(
        readonly = True,
        )
    

class Employee(models.Model):
    _inherit = 'hr.employee'
    
    @api.multi
    def get_leaves_distribution(self,date_start,date_end):
        """ Returns a dictionary summarizing how days in leave are distributed over the given period. 
            total: the number of days in the given period,
            off: according to the resource calendar, the number of days off
            bank: number of bank holidays (i.e global leaves)
            leave: days part of user-related leaves
            weekend : saturday or sunday
            
            Called from the payroll line calculation with 
        """
        for employee in self:
            #init constants
            total = 0
            off = 0
            bank = 0
            leave = 0
            weekend = 0
        
            wt = employee.resource_calendar_id
        
            start_ord = date_start.toordinal()
            end_ord = date_end.toordinal()
             
            for d_ord in range(start_ord,end_ord+1): #1 is added to ensure the last day of the range to be taken in account
                
                d = date.fromordinal(d_ord)
                wd = d.weekday()
                
                if wd > 4 : #if saturday or sunday
                    weekend += 1
                    continue
                
                # we look at global leaves
                noon = datetime.combine(d, time(12, 0, 0))
                if wt.global_leave_ids.filtered(lambda r: r.date_from<noon and r.date_to>noon):
                    bank += 1
                    continue
                
                #the remaining days are considered as leave if the day is present in the working time.
                #if not (i.e. attendances is empty), then the employee is considered off
                attendances = len(wt.attendance_ids.filtered(lambda r: r.dayofweek == str(wd)))
                
                leave += attendances*0.5 #half a day per attendance
                off += 1-(attendances*0.5)
                
                
                
        
            return {
                'total': (date_end-date_start).days + 1,
                'weekend': weekend,
                'bank': bank,
                'off': off,
                'leave': leave,
            }
        