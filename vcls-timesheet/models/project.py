# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class Project(models.Model):
    _inherit = 'project.project'

    contractual_budget = fields.Float(string="Contractual Budget",readonly=True)
    forecasted_budget = fields.Float(string="Forecasted Budget",readonly=True)
    realized_budget = fields.Float(string="Realized Budget",readonly=True)
    valued_budget = fields.Float(string="Valued Budget",readonly=True)
    invoiced_budget = fields.Float(string="Invoiced Budget",readonly=True)
    forecasted_hours = fields.Float(string="Forecasted Hours",readonly=True)
    realized_hours = fields.Float(string="Realized Hours",readonly=True)
    valued_hours = fields.Float(string="Valued Hours",readonly=True)
    invoiced_hours = fields.Float(string="Invoiced Hours",readonly=True)
    valuation_ratio = fields.Float(string="Valuation Ratio",readonly=True)
    remaining_budget = fields.Float(string="Remain Budget",readonly=True, 
        help='Remaing Budget provides whatever is left to be consumed, based on coded hours in our systems, please note, for fixed prices scopes, hours are evaluated against rates set in the quotation')

    pc_budget = fields.Float(string="PC Review Budget",readonly=True)
    cf_budget = fields.Float(string="Carry Forward Budget",readonly=True)
    pc_hours = fields.Float(string="PC Review Hours",readonly=True)
    cf_hours = fields.Float(string="Carry Forward Hours",readonly=True)
    timesheet_open = fields.Boolean(string="Timesheet is Open",compute='_compute_timesheet_open', store=True,)

    budget_consumed = fields.Float(
        string="Budget Consumed",
        readonly=True,
        compute='compute_budget_consumed',
        help='realised budget / contractual budget percentage'
    )

    currency_id = fields.Many2one(
        comodel_name = 'res.currency',
        related = 'sale_order_id.currency_id',
    )

    @api.multi
    @api.depends("realized_budget", "contractual_budget")
    def compute_budget_consumed(self):
        for project in self:
            if project.contractual_budget:
                project.budget_consumed = project.realized_budget / project.contractual_budget * 100
            else:
                project.budget_consumed = False

    @api.depends('task_ids.stage_allow_ts')
    def _compute_timesheet_open(self):
        for rec in self:
            all_tasks = rec.task_ids | rec.child_id.mapped('task_ids') | rec.child_id.mapped('task_ids').mapped('child_ids') | rec.task_ids.mapped('child_ids') 
            bools = all_tasks.mapped('stage_allow_ts')
            rec.timesheet_open = True if any(bools) else False

    @api.multi
    def _get_kpi(self):
        for project in self:
            project.contractual_budget = sum(project.task_ids.mapped('contractual_budget'))
            project.forecasted_budget = sum(project.task_ids.mapped('forecasted_budget'))
            project.realized_budget = sum(project.task_ids.mapped('realized_budget'))
            project.valued_budget = sum(project.task_ids.mapped('valued_budget'))
            project.invoiced_budget = sum(project.task_ids.mapped('invoiced_budget'))

            project.forecasted_hours = sum(project.task_ids.mapped('forecasted_hours'))
            project.realized_hours = sum(project.task_ids.mapped('realized_hours'))
            project.valued_hours = sum(project.task_ids.mapped('valued_hours'))
            project.invoiced_hours = sum(project.task_ids.mapped('invoiced_hours'))

            project.pc_budget = sum(project.task_ids.mapped('pc_budget'))
            project.cf_budget = sum(project.task_ids.mapped('cf_budget'))
            project.pc_hours = sum(project.task_ids.mapped('pc_hours'))
            project.cf_hours = sum(project.task_ids.mapped('cf_hours'))
            project.remaining_budget = project.contractual_budget - project.valued_budget

            project.valuation_ratio = 100.0*(project.valued_hours / project.realized_hours) if project.realized_hours else False

            # we recompute the invoiceable amount
            project.sale_order_id.order_line._compute_qty_delivered()

    @api.multi
    def action_projects_followup(self):
        self.ensure_one()
        family_project_ids = self._get_family_project_ids()
        action = self.env.ref('vcls-timesheet.project_timesheet_forecast_report_action').read()[0]
        action['domain'] = [('project_id', 'in', family_project_ids.ids)]
        action['context'] = {}
        return action
    
    @api.multi
    def action_view_forecast(self):
        self.ensure_one()
        family_project_ids = self._get_family_project_ids()
        action = self.env.ref('vcls-project.project_forecast_action').read()[0]
        action['domain'] = [('project_id', 'in', family_project_ids.ids)]
        action['context'] = {
            'active_id': self.id,
            'search_default_group_by_project_id': 1,
            'search_default_group_by_task_id': 1,
        }
        return action
    
    @api.model
    def clean_pre_project(self):
        completed = self.env['project.task.type'].search([('name','=','Completed'),('case_default','=',True),('project_type_default','=',False)],limit=1)
        pre_project = self.env.ref('vcls-timesheet.default_project')
        for task in pre_project.task_ids.filtered(lambda t: t.active):
            related_opp = self.env['crm.lead'].search([('name','=',task.name),('type', '=', 'opportunity')],limit=1)
            if related_opp:
                if related_opp.probability == 100  and completed: #closed won state, the task is completed
                    _logger.info("PP TASK COMPLETED | {}".format(task.name))
                    task.stage_id = completed
            else: #task is archived if timesheets or deleted if not
                if task.timesheet_ids:
                    _logger.info("PP TASK ARCHIVE | {}".format(task.name))
                    task.active = False #archived
                else:
                    _logger.info("PP TASK UNLINK | {}".format(task.name))
                    task.unlink()


