# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
import datetime


class BillabilityReport(models.Model):
    _name = "billability.report"
    _description = "Weekly Billability Report"

    # employee related fields
    name = fields.Char(compute='_get_name', store=True, readonly=True)
    active = fields.Boolean(string='Active', default=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    company = fields.Char(readonly=True)
    employee_name = fields.Char(related='employee_id.name', string="Employee Name", readonly=True, store=True)
    email = fields.Char(related='employee_id.work_email', string="Email", readonly=True)
    office = fields.Char(string="Office", readonly=True)
    employee_start_date = fields.Date(related='employee_id.employee_start_date', string="Employee Start Date", readonly=True)
    employee_end_date = fields.Date(related='employee_id.employee_end_date', string="Employee End Date", readonly=True)
    line_manager = fields.Many2one(related='employee_id.parent_id', string="Line Manager", readonly=True)
    line_manager_id = fields.Char(related='employee_id.parent_id.employee_external_id', string="Line Manager ID", readonly=True)
    

    # contract related fields
    contract_name = fields.Char(string="Contract Name", readonly=True)
    contract_start = fields.Char(string="Contract Start", readonly=True)
    contract_end = fields.Char(string="Contract End", readonly=True)
    contract_Type = fields.Char(string="Contract Type", readonly=True)
    department = fields.Char(string="Department", readonly=True)
    job_title = fields.Char(string="Job Title", readonly=True)
    working_percentage = fields.Char(string="Working Percentage", readonly=True)
    raw_weekly_capacity = fields.Integer(string="Raw Weekly Capacity [h]", readonly=True)
    consultancy_percentage = fields.Integer(string="Consulting [%]", readonly=True)

    days = fields.Integer(string='Days [d]')
    bank_holiday = fields.Integer(string='Bank Holiday [h]')
    days_duration = fields.Integer(string='Day Duration [d]')
    leaves = fields.Integer(string='Leaves [h]')
    worked = fields.Integer(string='Worked [d]')
    effective_capacity = fields.Float(string='Effective Capacity [h]')

    year = fields.Integer(string='Year', readonly=True)
    week_number = fields.Integer(string='Week number', readonly=True, group_operator="avg")
    start_date = fields.Date(string='Week start date', readonly=True)
    end_date = fields.Date(string='Week end date', readonly=True)
    billable_hours = fields.Float(readonly=True, string="Billable Hours [h]")
    valued_billable_hours = fields.Float(readonly=True, string="Revised Billable Hours [h]")
    non_billable_hours = fields.Float(readonly=True, string='Non Billable Hours [h]')
    billability_percent = fields.Float(readonly=True, string='Billability [%]', digits = (12,2), store=True, group_operator="avg", default=None)
    total_time_coded = fields.Float(string='Time Coded [h]', readonly=True)
    total_time_coded_percent = fields.Float(string='Coding Ratio [%]', readonly=True, group_operator="avg")
    amount_fte_billable = fields.Float(string='Computed FTE', help='effective capacity / 40 * consult %', readonly=True)
    fte_billable_per_staff = fields.Float(string='Billable / Staff [h]', readonly=True)
    
    @api.multi
    @api.depends('employee_id.name', 'week_number', 'year')
    def _get_name(self):
        for record in self:
            record.name = '{} {}-{}'.format(record.employee_id.name, str(record.week_number), str(record.year))

    @api.model
    def _set_data(self, last_weeks_count=4):
        """

        :param last_weeks_count: number of weeks to add to the table
        with the current week included
        :return:
        """
        
        assert last_weeks_count > 0
        billability = self.env['export.billability']
        time_sheet = self.env['account.analytic.line']
        today = fields.Date.today()
        last_monday = today - datetime.timedelta(days=today.weekday())
        time_start_recalc = last_monday - datetime.timedelta(weeks=last_weeks_count)
        self.search([('start_date', '>=', time_start_recalc)]).unlink()
        monday_dates = [last_monday]
        data = []
        for x in range(last_weeks_count):
            last_monday = last_monday + datetime.timedelta(weeks=-1)
            monday_dates += [last_monday]
        for monday_date in monday_dates:
            sunday_date = monday_date + datetime.timedelta(days=6)
            week_data = billability.build_data(
                start_date=monday_date,
                end_date=sunday_date
            )
            # we add some data that build_data does not get
            for week_data_line in week_data:
                week_data_line['week_number'] = monday_date.isocalendar()[1]
                week_data_line['year'] = monday_date.year
                week_data_line['active'] = True
                week_data_line['start_date'] = str(monday_date)
                week_data_line['end_date'] = str(sunday_date)
                week_data_line['billable_hours'] = 0
                week_data_line['non_billable_hours'] = 0
                emp_id = int(week_data_line['Employee Internal ID'])
                #this is where the calculations happen

                week_data_line['billable_hours'] = sum(time_sheet.search([('employee_id', '=', emp_id),('date', '>=', monday_date), ('date', '<=', sunday_date), ('billability', '=', 'billable')]).mapped('unit_amount'))
                week_data_line['non_billable_hours'] = sum(time_sheet.search([('employee_id', '=', emp_id),('date', '>=', monday_date), ('date', '<=', sunday_date), ('billability', '=', 'non_billable')]).mapped('unit_amount'))
                week_data_line['valued_non_billable_hours'] = sum(time_sheet.search([('employee_id', '=', emp_id),('date', '>=', monday_date), ('date', '<=', sunday_date), ('billability', '=', 'non_billable')]).mapped('unit_amount_rounded'))
                week_data_line['valued_billable_hours'] = sum(time_sheet.search([('employee_id', '=', emp_id),('date', '>=', monday_date), ('date', '<=', sunday_date), ('billability', '=', 'billable')]).mapped('unit_amount_rounded'))
                week_data_line['total_time_coded'] = week_data_line['billable_hours'] + week_data_line['non_billable_hours']
                consult_decimal = week_data_line['Consult %'] / 100
                week_data_line['Bank Holiday [d]'] *= week_data_line['Day Duration [h]']
                week_data_line['Leaves [d]'] *= week_data_line['Day Duration [h]']
                
                week_data_line['fte_billable_per_staff'] = False
                #to avoid division by 0 if there is no capacity
                if week_data_line['Effective Capacity [h]'] == 0:
                    week_data_line['amount_fte_billable'] = None
                    week_data_line['total_time_coded_percent'] = None
                else:
                    week_data_line['total_time_coded_percent'] = week_data_line['total_time_coded'] / week_data_line['Effective Capacity [h]'] * 100
                    week_data_line['amount_fte_billable'] = (week_data_line['Effective Capacity [h]'] / 40) * consult_decimal
                    week_data_line['fte_billable_per_staff'] = (week_data_line['billable_hours'] / week_data_line['amount_fte_billable']) if consult_decimal>0 else False
                
                if consult_decimal == 0 or week_data_line['Effective Capacity [h]'] == 0:
                    continue
                else:
                    #calculate percentages from data
                    week_data_line['billability_percent'] = (week_data_line['billable_hours'] / (week_data_line['Effective Capacity [h]'] * consult_decimal)) * 100


            data += week_data
        field_mapping = self._get_field_mapping()
        self.search(['|', ('active', '=', False), ('active', '=', False)]).unlink()
        for data_line in data:
            values = dict([(field_name, data_line[data_key]) for field_name, data_key in field_mapping.items() if data_key in data_line])
            self.create(values)



    @api.model
    def _get_field_mapping(self):
        return {
            'employee_id': 'Employee Internal ID',
            'company': 'Company',
            'employee_name': 'Employee Name',
            'email': 'Email',
            'office': 'Office',
            'employee_start_date': 'Employee Start Date',
            'employee_end_date': 'Employee End Date',
            'line_manager': 'Line Manager',
            'line_manager_id': 'Line Manager ID',
            'contract_name': 'Contract Name',
            'contract_start': 'Contract Start',
            'contract_end': 'Contract End',
            'contract_Type': 'Contract Type',
            'department': 'Department',
            'job_title': 'Job Title',
            'working_percentage': 'Working Percentage',
            'consultancy_percentage':'Consult %',
            'raw_weekly_capacity': 'Raw Weekly Capacity [h]',
            'days': 'Days [d]',
            # 'weekends': 'Weekends [d]',
            'bank_holiday': 'Bank Holiday [d]',
            # 'out_of_contract': 'Out of Contract [d]',
            'days_duration': 'Day Duration [h]',
            # 'offs': 'Offs [d]',
            'leaves': 'Leaves [d]',
            'worked': 'Worked [d]',
            'effective_capacity': 'Effective Capacity [h]',
            # 'control': 'Control [d]',

            # 'year': 'year',
            'week_number': 'week_number',
            'start_date': 'start_date',
            'end_date': 'end_date',
            'billable_hours': 'billable_hours',
            'valued_billable_hours': 'valued_billable_hours',
            'non_billable_hours': 'non_billable_hours',
            # 'valued_non_billable_hours': 'valued_non_billable_hours',
            'billability_percent' : 'billability_percent',
            # 'non_billability_percent' : 'non_billability_percent',
            'total_time_coded' : 'total_time_coded',
            'total_time_coded_percent' : 'total_time_coded_percent',
            'amount_fte_billable' : 'amount_fte_billable',
            'fte_billable_per_staff' : 'fte_billable_per_staff'
        }
