# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError

import logging
import datetime
import math
_logger = logging.getLogger(__name__)

class Employee(models.Model):
    
    _inherit = 'hr.employee'

    do_smart_timesheeting = fields.Boolean(
        default = True
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