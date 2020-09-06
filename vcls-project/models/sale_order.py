# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api, _

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):

    _inherit = 'sale.order'
    parent_project_id = fields.Many2one(
        'project.project', compute='_get_parent_project_id'
    )
    family_task_count = fields.Integer(
        'Family Task Count', compute='_get_family_task_count'
    )

    forecasted_amount = fields.Monetary(
        compute = "_compute_forecasted_amount",
        store = True,
        default = 0.0,
    )
    project_status = fields.Selection(
        selection=[
        ('preproject', 'Pre-Project'),
        ('risk', 'At Risk'),
        ('ongoing', 'Ongoing'),
        ('service_delivered', 'Service Delivered'),
        ('closed', 'Closed')
        ],
        compute='_compute_project_status',
        store= True,
    )

    @api.depends('project_id.project_status')
    def _compute_project_status(self):
        for rec in self:
            rec.project_status =  rec.project_id.project_status if rec.project_id else 'preproject'
    
    def project_status_update(self):
        for rec in self:
            if rec.state in ['done','sale'] and rec.project_id:
                rec.project_id.project_status = 'ongoing'
                rec.project_id.child_id._onchange_project_status()

    @api.multi
    def _get_parent_project_id(self):
        for project in self:
            project.parent_project_id = project.parent_id.project_id if self.parent_id else self.project_id

    @api.multi
    def _get_family_task_count(self):
        for project in self:
            parent_project, child_projects = self._get_family_projects()
            family_projects = (parent_project | child_projects)
            project.family_task_count = len(family_projects.mapped('tasks'))


    @api.multi
    def quotation_program_print(self):
        """ Print all quotation related to the program
        """
        programs = self.mapped('program_id')
        quot = self.search([('program_id', 'in', programs.ids), ('state', '=', 'draft')])
        return self.env.ref('sale.action_report_saleorder').report_action(quot)

    @api.multi
    def action_view_project_ids(self):
        self.ensure_one()
        parent_project = self.parent_id.project_id
        if parent_project and self.env.user.has_group('project.group_project_manager'):
            action = parent_project.action_view_timesheet_plan()
            return action
        return super(SaleOrder, self).action_view_project_ids()

    @api.multi
    def action_view_family_parent_project(self):
        self.ensure_one()
        parent_project_id = self.parent_id.project_id if self.parent_id else self.project_id
        if not parent_project_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _('Project'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.project',
            'res_id': parent_project_id.id,
            'view_id': self.env.ref('vcls-project.vcls_specific_project_form').id,
            'context': self.env.context,
        }

    @api.multi
    def action_view_family_parent_tasks(self):
        self.ensure_one()
        parent_project, child_projects = self._get_family_projects()
        return {
            'name': _('Tasks'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'kanban,tree,form,calendar,pivot,graph,activity',
            'res_model': 'project.task',
            'domain': [('project_id', 'in', (parent_project | child_projects).ids)],
            'context': {
                'search_default_project_id': self.project_id.id,
            },
        }
    
    @api.multi
    @api.depends('order_line','order_line.forecasted_amount')
    def _compute_forecasted_amount(self):
        """
        This methods sums the total of forecast potential revenues.
        Triggered by the forecast write/create methods
        """
        for so in self:
            so.forecasted_amount = sum(so.order_line.mapped('forecasted_amount'))
            # _logger.info("FORECASTED AMOUNT {}".format(so.forecasted_amount))
    
    @api.multi
    def _action_confirm(self):
        for rec in self:
            rec.action_sync()
            rec.project_status_update()
            return super(SaleOrder, rec)._action_confirm()

    @api.multi
    def write(self, values):
        if values.get('active', None) is False:
            project_ids = self.mapped('project_id')
            project_ids.write({'active': False})
        return super(SaleOrder, self).write(values)

    def action_sync(self):
        super(SaleOrder, self).action_sync()
        for order in self.filtered(lambda s:s.parent_id and s.link_rates and s.project_id):
            _logger.info("Linking Project Mapping Tables")
            order.map_match()

        for order in self.filtered(lambda p: p.project_id):
            project_id = order.project_id
            if project_id.scope_of_work:
                order.scope_of_work = project_id.scope_of_work
            if project_id.company_id:
                order.company_id = project_id.company_id
                order.order_line.write({'company_id': project_id.company_id.id})
            tasks_values = {}
            if order.expected_start_date or order.expected_end_date:
                tasks = project_id.tasks | project_id.tasks.mapped('child_ids')
                if order.expected_start_date:
                    tasks_values.update({'date_start': order.expected_start_date})
                if order.expected_end_date:
                    tasks_values.update({'date_end': order.expected_end_date})
                if tasks_values:
                    tasks.write(tasks_values)
            project_id.name = order.name
            for task_id in project_id.tasks.filtered(lambda t: not t.parent_id): #we rename parent task according to the related sale_line
                task_id.name = task_id.sale_line_id.name
            for task_id in project_id.tasks.filtered(lambda t: t.parent_id): #for the childs, we combine
                #we look for the subtask specific name
                parts = task_id.name.split(':')
                if len(parts)>1: #if there is a specific name
                    task_id.name = "{}:{}".format(task_id.sale_line_id.name,parts[1])
                else: #we don't update the name to avoid same naming
                    pass

    def map_match(self):
        self.ensure_one()
        self = self.sudo()
        #we start from the rates of the parent order
        for o_line in self.parent_id.order_line.filtered(lambda l: l.vcls_type == 'rate'):
            n_line = self.order_line.filtered(lambda l: l.vcls_type == 'rate' and l.product_id == o_line.product_id)
            if not n_line:
                _logger.info("map_match | impossible to map line {} to {}. No target found".format(o_line.name,self.name))
            elif len(n_line)>1:
                _logger.info("map_match | impossible to map line {} to {}. Multiple targets found".format(o_line.name,self.name))
            else:
                _logger.info("map_match | mapping line {} to {}.".format(o_line.name,self.name))

                o_map_lines = self.parent_id.project_id.sale_line_employee_ids.filtered(lambda m: m.sale_line_id==o_line)
                _logger.info("{} found in {}".format(o_map_lines.mapped('employee_id.name'),self.parent_id.project_id.sale_line_employee_ids.mapped('employee_id.name')))
                n_map_lines = self.project_id.sale_line_employee_ids
                #we loop in the mapping table
                for map_line in o_map_lines:
                    found = n_map_lines.filtered(lambda f:  f.employee_id==map_line.employee_id and f.sale_line_id==n_line)
                    if found: #the line if already ok
                        _logger.info("map_match | correct mapping line exists.")
                    else:
                        found = n_map_lines.filtered(lambda f:  f.employee_id==map_line.employee_id)
                        if found: #the employee is mapped, but not on the correct line
                            found.sale_line_id = n_line
                            _logger.info("map_match | employee {} re-mapped on correct line.".format(map_line.employee_id.name))
                        else: #the map doesn't exist, we create it
                            self.env['project.sale.line.employee.map'].create({
                                'project_id': self.project_id.id,
                                'sale_line_id': n_line.id,
                                'employee_id': map_line.employee_id.id,
                            })
                            _logger.info("map_match | employee {} map created line.".format(map_line.employee_id.name))