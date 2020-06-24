# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging
from datetime import datetime
_logger = logging.getLogger(__name__)


class ProjectForecast(models.Model):
    _inherit = 'project.forecast'

    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        string='Department',
        store=True,
        readonly=True
    )

    hourly_rate = fields.Float(
        readonly=True,
        default=False,
    )

    task_id = fields.Many2one('project.task', string="Task", group_expand='_read_forecast_tasks_vcls')
    start_date = fields.Date(compute='_get_start_end_date', store=True)
    end_date = fields.Date(compute='_get_start_end_date', store=True)
    deliverable_id = fields.Many2one(
        'product.deliverable',
        readonly=True, store=True,
        related='task_id.sale_line_id.product_id.deliverable_id'
    )

    comment = fields.Html()

    rate_id = fields.Many2one(
        comodel_name='product.template',
        default = False,
        readonly = True,
    )

    @api.multi
    def get_rate(self,project,employee):
        #self.ensure_one()
        map_line = project.sale_line_employee_ids.filtered(lambda l: l.employee_id == employee)
        if map_line:
            return map_line[0].sale_line_id.product_id.product_tmpl_id
        else:
            return False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.ensure_one()
        self.rate_id = self.get_rate(self.project_id,self.employee_id)
    
    @api.model
    def update_rate_id(self):
        to_update = self.search([('rate_id','=',False)])
        for forecast in to_update:
            forecast._onchange_employee_id()
            _logger.info("Forecast update Rate_id {} for employee {}".format(forecast.rate_id.name,forecast.employee_id.name))

    @api.depends('task_id.date_start', 'task_id.date_end')
    def _get_start_end_date(self):
        for forecast in self:
            task_date_start = forecast.task_id.date_start
            task_date_end = forecast.task_id.date_end
            if task_date_start and task_date_end:
                forecast.start_date = task_date_start.date()
                forecast.end_date = task_date_end.date()
            else:
                forecast.start_date = self._default_start_date()
                forecast.end_date = self._default_end_date()

    # planned_hours on a task must be equal to the sum of forecast hours related to this task
    # only if this sum it is superior to zero.
    @api.multi
    def _force_forecast_hours(self):
        self = self.with_context(tracking_disable=True)
        for forecast in self:
            if not forecast.task_id:
                continue
            total_resource_hours = sum(self.search([('task_id', '=', forecast.task_id.id)]).mapped('resource_hours'))
            if total_resource_hours > 0:
                forecast.task_id.planned_hours = total_resource_hours
    
    @api.multi
    def _project_forecasted_amount(self):
        self.mapped('order_line_id')._compute_forecasted_amount()

    @api.multi
    def write(self, values):
        result = super(ProjectForecast, self).write(values)
        for forecast in self:
            employee_id = forecast.employee_id.id
            project_id = forecast.project_id.id
            hourly_rate = forecast._get_hourly_rate(employee_id, project_id)
            super(ProjectForecast, forecast).write({
                'hourly_rate': hourly_rate,
            })
        self.sudo()._force_forecast_hours()
        self.sudo()._project_forecasted_amount()
        return result

    @api.model
    def create(self, vals):
        
        if vals.get('project_id',False) and vals.get('employee_id',False):
            """#if we create a forecast, we update the project mapping accordingly
            self.env['account.analytic.line']._update_project_soline_mapping({
                        'employee_id':vals['employee_id'],
                        'project_id':vals['project_id'],
                    })"""
            
            if not vals.get('rate_id',False):
                #if the rate_id is not provided we look for the related employee in the mapping table
                project = self.env['project.project'].browse(vals['project_id'])
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                rate = self.get_rate(project,employee)
                if rate:
                    vals['rate_id']=rate.id
               
        forecast = super(ProjectForecast, self).create(vals)
        
        forecast.sudo()._force_forecast_hours()
        forecast.sudo()._project_forecasted_amount()

        if forecast.task_id.date_start and forecast.task_id.date_end:
            forecast.start_date = forecast.task_id.date_start.date()
            forecast.end_date = forecast.task_id.date_end.date()

        return forecast

    @api.model
    def _read_forecast_tasks_vcls(self, tasks, domain, order):
        search_domain = [('id', 'in', tasks.ids)]
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_id', 'child_of', [self.env.context['default_project_id']])] + search_domain
        return tasks.sudo().search(search_domain, order=order)
    
    @api.model
    def _get_hourly_rate(self, employee_id, project_id):
        if project_id and employee_id:
            rate_map = self.env['project.sale.line.employee.map'].search([
                ('employee_id', '=', employee_id),
                ('project_id', '=', project_id)],
                limit=1
            )
            if rate_map:
                if rate_map.sale_line_id.product_uom == self.env.ref('uom.product_uom_day'): #if we are in daily
                    return round(rate_map.price_unit/8,2)
                else:
                    return rate_map.price_unit
        return 0.0

    # Tis server action is meant to return a window action with proper model and active id
    # This is a solution to allow getting the right computed domain when page is being refreshed,
    @api.model
    def _action_server_forecast(self, server_action_id, active_model=False):
        active_id = self._context.get('active_id') or self._context.get('params', {}).get('active_id')
        if active_id and active_model:
            action = self.env[active_model].browse(active_id).action_view_forecast()
            # fake id to force coming back to the server action that triggers this method,
            # when user refreshes the page
            action['id'] = server_action_id
            return action
        return self.env.ref('vcls-project.project_forecast_action').read()[0]

    @api.model
    def _action_server_forecast_from_order(self):
        server_action_id = self.env.ref('vcls-project.action_server_project_forecast_from_order').id
        return self._action_server_forecast(server_action_id, 'sale.order')
    
    @api.model
    def _action_server_forecast_from_project(self):
        server_action_id = self.env.ref('vcls-project.action_server_project_forecast_from_project').id
        return self._action_server_forecast(server_action_id, 'project.project')

    @api.multi
    def button_form_from_list(self):
        self.ensure_one()
        view = {
            'name': _('Details'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.forecast',
            'view_id': self.env.ref('vcls-project.project_forecast_view_form').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }
        return view
