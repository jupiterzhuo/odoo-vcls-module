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
    Office = fields.Many2one(related='employee_id.office_id', string="Office", readonly=True)
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

    days = fields.Integer(string='Days [d]')
    weekends = fields.Integer(string='Weekends [d]')
    bank_holiday = fields.Integer(string='Bank Holiday [h]')
    out_of_contract = fields.Integer(string='Out of Contract [d]')
    days_duration = fields.Integer(string='Day Duration [d]')
    offs = fields.Integer(string='Offs [d]')
    leaves = fields.Integer(string='Leaves [h]')
    worked = fields.Integer(string='Worked [d]')
    effective_capacity = fields.Integer(string='Effective Capacity [d]')
    control = fields.Integer(string='Control [d]')

    year = fields.Integer(string='Year', readonly=True)
    week_number = fields.Integer(string='Week number', readonly=True)
    start_date = fields.Date(string='Week start date', readonly=True)
    end_date = fields.Date(string='Week end date', readonly=True)
    billable_hours = fields.Float(readonly=True)
    valued_billable_hours = fields.Float(readonly=True)
    non_billable_hours = fields.Float(readonly=True)
    valued_non_billable_hours = fields.Float(readonly=True)
    billability_percent = fields.Float(readonly=True, digits = (12,2), store=True, group_operator="avg")
    non_billability_percent = fields.Float(readonly=True, digits = (12,2), store=True, group_operator="avg")
    total_time_coded = fields.Float(string='Time coded [h]', readonly=True)
    total_time_coded_percent = fields.Float(string='coding ratio [%]', readonly=True, group_operator="avg")

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
        this_week = datetime.date.today().isocalendar()[1]
        self.search([('week_number', '>', this_week - last_weeks_count)]).unlink()

        assert last_weeks_count > 0
        billability = self.env['export.billability']
        time_sheet = self.env['account.analytic.line']
        today = fields.Date.today()
        last_monday = today - datetime.timedelta(days=today.weekday())
        monday_dates = [last_monday]
        data = []
        for x in range(last_weeks_count-1):
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
                #to avoid division by 0 if there is no capacity
                if week_data_line['Effective Capacity [h]'] == 0:
                    week_data_line['billability_percent'] = None
                    week_data_line['non_billability_percent'] = None
                    week_data_line['total_time_coded_percent'] = None
                    continue
                #calculate percentages from data
                week_data_line['billability_percent'] = week_data_line['valued_billable_hours'] / week_data_line['Effective Capacity [h]'] * 100
                week_data_line['non_billability_percent'] = week_data_line['valued_non_billable_hours'] / week_data_line['Effective Capacity [h]'] * 100
                week_data_line['total_time_coded_percent'] = week_data_line['total_time_coded'] / week_data_line['Effective Capacity [h]'] * 100

                #convert Days to Hours
                week_data_line['Bank Holiday [d]'] *= 8
                week_data_line['Leaves [d]'] *= 8

            data += week_data
        field_mapping = self._get_field_mapping()
        self.search(['|', ('active', '=', False), ('active', '=', False)]).unlink()
        for data_line in data:
            values = dict([(field_name, data_line[data_key]) for field_name, data_key in field_mapping.items()])
            self.create(values)

    @api.model
    def _get_field_mapping(self):
        return {
            'employee_id': 'Employee Internal ID',
            'company': 'Company',
            'employee_name': 'Employee Name',
            'email': 'Email',
            'Office': 'Office',
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
            'raw_weekly_capacity': 'Raw Weekly Capacity [h]',
            'days': 'Days [d]',
            'weekends': 'Weekends [d]',
            'bank_holiday': 'Bank Holiday [d]',
            'out_of_contract': 'Out of Contract [d]',
            'days_duration': 'Day Duration [h]',
            'offs': 'Offs [d]',
            'leaves': 'Leaves [d]',
            'worked': 'Worked [d]',
            'effective_capacity': 'Effective Capacity [h]',
            'control': 'Control [d]',

            'year': 'year',
            'week_number': 'week_number',
            'start_date': 'start_date',
            'end_date': 'end_date',
            'billable_hours': 'billable_hours',
            'valued_billable_hours': 'valued_billable_hours',
            'non_billable_hours': 'non_billable_hours',
            'valued_non_billable_hours': 'valued_non_billable_hours',
            'billability_percent' : 'billability_percent',
            'non_billability_percent' : 'non_billability_percent',
            'total_time_coded' : 'total_time_coded',
            'total_time_coded_percent' : 'total_time_coded_percent',
        }
