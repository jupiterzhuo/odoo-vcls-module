# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime,timedelta

import logging
import datetime
import math
_logger = logging.getLogger(__name__)

class Employee(models.Model):
    
    _inherit = 'hr.employee'

    do_smart_timesheeting = fields.Boolean(
        default = False
    )

    # A CRON to set automatically the timesheet approval date
    @api.model
    def approve_timesheets(self,hours_offset_from_now=0):
        validation_date = (datetime.datetime.now() - datetime.timedelta(hours=hours_offset_from_now)).date()
        _logger.info('New Timesheet Validation Date {}'.format(validation_date))
        employees = self.with_context(active_test=False).search([('user_id','!=',self._uid)])
        employees.write({'timesheet_validated':validation_date})

        # Update timesheet stage_id
        self.env['account.analytic.line'].search([('stage_id', '=', 'draft'), ('validated', '=', True)]).write({'stage_id':'lc_review'})

    @api.model
    def smart_timesheeting_init(self):
        to_update = self.search([('active','=',True),('employee_status','=','active'),('employee_type','=','internal')])
        to_update.write({'do_smart_timesheeting':True})

        cron = self.env.ref('vcls-timesheet.cron_smart_timesheeting')
        cron.write({
            'active': True,
            'nextcall': fields.Datetime.now() + timedelta(seconds=30),
            'numbercall': 5,
        })