# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    total_ticket_effort = fields.Float(
        compute='_compute_total_ticket_effort',
        store=True,
        default=0.0,
        group_operator='sum',
    )

    ticket_ids = fields.One2many(
        'helpdesk.ticket',
        'task_id',
        )

    task_type = fields.Selection([
        ('gen', 'Generic'),
        ('dev.vers', 'Development Version'),
        ('dev.task', 'Development Task'),
        ('marketing','Marketing Campaign')],
        default='gen',
        string='Task Type',
        compute='_compute_task_type',
        store=True,)

    info_string = fields.Char(
        compute='_get_info_string',
        store=True,
    )

    completion_ratio = fields.Float(
        string='Task Complete',
        related='stage_id.completion_ratio',
        group_operator='avg',
    )
    completion_elligible = fields.Boolean(string='Completion eligibility')
    consummed_completed_ratio = fields.Float(compute='compute_consummed_completed_ratio', store=True, string="BC/TC", help='BC/TC percent, 100 is normal, lower is "better"')

    stage_allow_ts = fields.Boolean(
        related = 'stage_id.allow_timesheet', string='Stage allow timesheets'
    )
    description_evolutions = fields.Html(string="Description Evolutions")
    deliverable_id = fields.Many2one(
        'product.deliverable',
        readonly=True,
        store=True,
        related='sale_line_id.product_id.deliverable_id',
        compute_sudo=True
    )

    ###################
    # COMPUTE METHODS #
    ###################
    @api.depends ('ticket_ids','ticket_ids.planned_effort')
    def _compute_total_ticket_effort(self):
        for task in self.filtered(lambda t: t.ticket_ids):
            task.total_ticket_effort = sum(task.ticket_ids.mapped('planned_effort'))

    @api.depends('parent_id', 'project_id.project_type')
    def _compute_task_type(self):
        for task in self:
            if task.project_id.project_type == 'dev':
                if task.parent_id:
                    task.task_type = 'dev.task'
                else:
                    task.task_type = 'dev.vers'
    
    @api.depends('project_id.name')
    def _get_info_string(self):
        for task in self:
            info_string = task.project_id.name
            if task.sale_line_id.product_id.deliverable_id:
                info_string = "{} [{}]".format(info_string,task.sale_line_id.product_id.deliverable_id.name)
            task.info_string = info_string
    
    @api.depends('completion_elligible', 'stage_id','progress')
    def compute_consummed_completed_ratio(self):
        for task in self:
            task.consummed_completed_ratio = (task.budget_consumed / task.completion_ratio) * 100 if task.completion_ratio > 0 else task.budget_consumed / 0.1 * 100

    # We Override below method in order to take the unit_amount_rounded amount rather than the initial unit_amount
    @api.depends('timesheet_ids.unit_amount_rounded')
    def _compute_effective_hours(self):
        for task in self:
            task.effective_hours = round(sum(task.timesheet_ids.mapped('unit_amount_rounded')), 2)

    # We Override below method to authorize the progress (i.e. consumption) to go higher than 100%
    @api.depends('effective_hours', 'subtask_effective_hours', 'planned_hours')
    def _compute_progress_hours(self):
        for task in self:
            if (task.planned_hours > 0.0):
                task_total_hours = task.effective_hours + task.subtask_effective_hours
                task.progress = round(100.0 * task_total_hours / task.planned_hours, 2)
                """if task_total_hours > task.planned_hours:
                    task.progress = 100
                else:
                    task.progress = round(100.0 * task_total_hours / task.planned_hours, 2)"""
            else:
                task.progress = 0.0

    ###############
    # ORM METHODS #
    ###############
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        return super(ProjectTask, self.with_context(allow_timesheets=True)).search(
            args=args, offset=offset, limit=limit,
            order=order, count=count)

    ##########################
    # Button Actions METHODS #
    ##########################
    
    @api.multi
    def action_log_time(self):
        self.ensure_one()
        action = self.env.ref('hr_timesheet.act_hr_timesheet_line').read()[0]
        action['views'] = [
          (self.env.ref('vcls-timesheet.account_analytic_line_grid_view_form').id, 'form'),
        ]
        ctx = self.env.context.copy()
        ctx.update(default_main_project_id=self.project_id.parent_id.id or self.project_id.id,
            default_project_id=self.project_id.id,
            default_task_id=self.id,
            # One Employee/USer
            default_employee_id=self.env.user.employee_ids.id,
            log_from_task=True,)
        action.update({'context': ctx,
                       'target': 'new'})
        return action

    @api.onchange('sale_line_id')
    def onchange_sale_line_id(self):
        if self.sale_line_id:
            self.completion_elligible = self.sale_line_id.product_id.completion_elligible
