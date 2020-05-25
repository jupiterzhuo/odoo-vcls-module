# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, api, _, fields
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_sync(self):
        self.mapped('order_line').sudo().with_context(
            default_company_id=self.company_id.id,
            force_company=self.company_id.id,
        )._timesheet_service_generation()

        #we update the sequence of the task related
        for line in self.order_line.filtered(lambda t: t.task_id):
            line.task_id.sequence = line.sequence

        milestone_tasks = self.get_milestone_tasks()
        rate_order_lines = self.get_rate_tasks()
        for order_line in rate_order_lines:
            employee = order_line.product_id.forecast_employee_id
            _logger.info("SYNC | Forecast for line {} with employee {}".format(order_line.product_id.name,employee.name))
            """if not employee:
                    employee = self.env['hr.employee'].search(
                        [('seniority_level_id', '=', sen_level)], limit=1)"""
            if not employee:
                sen_level = order_line.product_id.seniority_level_id
                raise UserError(
                    _("No Employee available for Seniority level \
                    {}").format(sen_level.name)
                )

            for task in milestone_tasks:
                existing_forecast = self.env['project.forecast'].search([
                    ('project_id', '=', task.project_id.id),
                    ('task_id', '=', task.id),
                    ('employee_id', '=', employee.id)
                ], limit=1)
                if not existing_forecast:
                    self.env['project.forecast'].create({
                        'project_id': task.project_id.id,
                        'task_id': task.id,
                        'employee_id': employee.id,
                        'rate_id': order_line.product_id.product_tmpl_id.id,
                    })
                    #_logger.info("SYNC | Forecast created in task {}".format(task.name))
            project = self.mapped('tasks_ids.project_id')
            _logger.info("Mapping For Product {} Employee {} Line {}".format(order_line.product_id.name,employee.name,order_line.name))
            if len(project) == 1:
                existing_mapping = self.env['project.sale.line.employee.map'].search([
                    ('project_id', '=', project.id),
                    #('sale_line_id', '=', order_line.id),
                    ('employee_id', '=', employee.id)
                ], limit=1)
                
                if not existing_mapping:
                    _logger.info("SYNC | MAP CREATE For Product {} Employee {} Line {} in project {}".format(order_line.product_id.name,employee.name,order_line.name,project.name))
                    self.env['project.sale.line.employee.map'].sudo().create({
                        'project_id': project.id,
                        'sale_line_id': order_line.id,
                        'employee_id': employee.id,
                    })
                else:
                    _logger.info("SYNC | MAP FOUND For Product {} Employee {} Line {} in project {}".format(order_line.product_id.name,employee.name,order_line.name,project.name))

    @api.multi
    def get_milestone_tasks(self):
        order_lines = self.order_line.filtered(
            lambda r: r.product_id.type == 'service' and
            r.product_id.service_policy == 'delivered_manual' and
            r.product_id.service_tracking == 'task_new_project'
        )
        return order_lines.mapped('task_id')

    @api.multi
    def get_rate_tasks(self):
        order_lines = self.order_line.filtered(
            lambda r: r.product_id.type == 'service' and
            r.product_id.service_policy == 'delivered_timesheet' and
            r.product_id.service_tracking in ('no', 'project_only')
        )
        return order_lines
    
    


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    service_policy = fields.Selection(
        'Service Policy',
        related='product_id.service_policy',
        readonly=True,
    )

class Forecast(models.Model):

    _inherit = "project.forecast"

    rate_id = fields.Many2one(
        comodel_name='product.template',
        default = False,
        readonly = True,
    )