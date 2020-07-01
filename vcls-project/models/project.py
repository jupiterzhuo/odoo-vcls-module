# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)


class Project(models.Model):

    _name = 'project.project'
    _inherit = ['project.project', 'mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # We Override this method from 'project_task_default_stage
    def _get_default_type_common(self):
        ids = self.env['project.task.type'].search([
            ('case_default', '=', True),
            ('project_type_default', '=', self.project_type)])
        _logger.info("Default Stages: {} for project type {}".format(ids.mapped('name'),self.project_type))
        return ids

    type_ids = fields.Many2many(
        default=lambda self: self._get_default_type_common())

    user_id = fields.Many2one('res.users', string='Project Manager', default=lambda self: self._default_user_id() , track_visibility="onchange")

    project_type = fields.Selection([
        ('dev', 'Developement'),
        ('client', 'Client'),
        ('internal','Internal')],
        string = 'Project Type',
        default = 'client',
    )

    # Maximum parent level here is meant to be 1 at max for now
    parent_id = fields.Many2one(
        'project.project', 'Parent project',
        index=True, ondelete='cascade',
        compute='_get_parent_id',
        store=True
    )
    child_id = fields.One2many('project.project', 'parent_id', 'Child projects')

    parent_task_count = fields.Integer(
        compute='_compute_parent_task_count'
    )

    child_task_count = fields.Integer(
        compute='_compute_child_task_count'
    )

    #consultant_ids = fields.Many2many('hr.employee', string='Consultants')
    #ta_ids = fields.Many2many('hr.employee', string='Ta')
    completion_ratio = fields.Float('Task Complete', compute='compute_project_completion_ratio', store=True, help='All parent tasks completion %, weighted by contractual budget')
    consummed_completed_ratio = fields.Float('BC / TC',
                                             compute='compute_project_consummed_completed_ratio', store=True, help='BC/TC in Percentage, lower is "better", 100 is on target')
    summary_ids = fields.One2many(
        'project.summary', 'project_id',
        'Project summaries'
    )
    is_project_manager = fields.Boolean(compute="_get_is_project_manager")
    scope_of_work = fields.Html(string='Scope of work')
    orders_count = fields.Integer(compute='compute_orders_count')
    tasks_count = fields.Integer()
    timesheets_count = fields.Integer()
    lead_consultant = fields.Many2one('hr.employee', related='core_team_id.lead_consultant', string='Lead Consultant')
    assistant_id = fields.Many2one('hr.employee', related='core_team_id.assistant_id', string='Project Assistant')
    lead_backup = fields.Many2one('hr.employee', related='core_team_id.lead_backup',
                                  string='Lead Consultant Backup')
    consultant_ids = fields.Many2many('hr.employee', 'rel_project_consultants', related='core_team_id.consultant_ids',
                                      string='Consultants')
    ta_ids = fields.Many2many('hr.employee', relation='rel_project_tas', related='core_team_id.ta_ids',
                              string='Ta')
    controller_id = fields.Many2one('res.users', related='partner_id.controller_id', string='Project Controller')
    invoice_admin_id = fields.Many2one('res.users', related='partner_id.invoice_admin_id', string='Invoice Administrator')
    account_manager_id = fields.Many2one('res.users', related='sale_order_id.user_id', string='Account Manager', store=True)

    invoices_count = fields.Integer(
        compute='_get_out_invoice_ids',
        compute_sudo = True
    )
    out_invoice_ids = fields.Many2many(
        string='Out invoices',
        compute='_get_out_invoice_ids',
        comodel_name="account.invoice",
        relation="project_out_invoice_rel",
        column1="project_id",
        column2="invoice_id",
        store=True,
        copy=False, readonly=True,
        compute_sudo=True
    )

    risk_ids = fields.Many2many(
        'risk', string='Risk',
        compute='_compute_risk_ids',
        # store=True,
    )

    risk_score = fields.Integer(
        string='Risk Score',
        compute='_compute_risk_score',
        store=True,
    )

    risk_last_update = fields.Datetime(
        string='Risk Last Update',
        compute='_compute_risk_last_update',
        # store=True,
    )

    invoiceable_amount = fields.Monetary(
       related="sale_order_id.invoiceable_amount",
       readonly=True,
       store=True,
    )

    invoicing_mode = fields.Selection(related="sale_order_id.invoicing_mode", readonly=True)

    last_summary_date = fields.Datetime(string="Last Summary Date", compute="_compute_last_create_date", readonly=True)

    subscription_count = fields.Integer(compute='_compute_subscription_count')

    date_start = fields.Date(
        string='Start Date',
        compute='_compute_dates',)

    date = fields.Date(
        string='Expiration Date',
        compute='_compute_dates',
        index=True,
        track_visibility='onchange',
    ) 
    
    # accounting fields for legacy integration
    external_account = fields.Char(
        default="/",
    )

    sharepoint_folder = fields.Char(
        string='Sharepoint Folder',
        compute='_compute_sharepoint_folder',
        readonly=True,
        store=True,
    )

    show_folder_path = fields.Boolean()

    @api.depends('sale_order_id', 'project_type', 'parent_id','partner_id')
    def _compute_sharepoint_folder(self):
        pre = self.env.ref('vcls-contact.SP_client_root_prefix').value
        post = self.env.ref('vcls-contact.SP_client_root_postfix').value
        for project in self.filtered(lambda p: p.project_type=='client' and p.sale_order_id and p.partner_id.altname):
            reference = project.parent_id.sale_order_id.internal_ref if project.parent_id \
                else project.sale_order_id.internal_ref or ''
            if reference:
                reference = "{}-{}".format(reference.split('-')[0],reference.split('-')[1])
            project.sharepoint_folder = "{}/{}/{}/{}{}".format(pre,project.partner_id.altname[0],project.partner_id.altname,reference,post)
            project.show_folder_path = True
    
    def _compute_dates(self):
        for project in self:
            tasks = project.task_ids.filtered(lambda t: t.date_start and t.date_end)
            if tasks:
                project.date_start = min(tasks.mapped('date_start')).date()
                project.date = max(tasks.mapped('date_end')).date()
            elif project.sale_order_id:
                project.date_start = project.sale_order_id.expected_start_date
                project.date = project.sale_order_id.expected_end_date
            else:
                project.date_start = False
                project.date = False


    def _compute_subscription_count(self):
        """Compute the number of distinct subscriptions linked to the orders of the project(s)."""
        for project in self:
            all_projects = project
            if project.child_id:
                all_projects |= project.child_id
            if project.parent_id:
                all_projects |= project.parent_id

            sub_count = len(self.env['sale.order.line'].read_group([('order_id', 'in', all_projects.mapped('sale_order_id.id')), ('subscription_id', '!=', False)],
                                                    ['subscription_id'], ['subscription_id']))
            project.subscription_count = sub_count
    
    def action_open_subscriptions(self):
        """Display the linked subscription and adapt the view to the number of records to display."""
        self.ensure_one()

        all_projects = self
        if self.child_id:
            all_projects |= self.child_id
        if self.parent_id:
            all_projects |= self.parent_id

        subscriptions = all_projects.mapped('sale_order_id.order_line.subscription_id')

        action = self.env.ref('sale_subscription.sale_subscription_action').read()[0]
        if len(subscriptions) > 1:
            action['domain'] = [('id', 'in', subscriptions.ids)]
        elif len(subscriptions) == 1:
            form_view = [(self.env.ref('sale_subscription.sale_subscription_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = subscriptions.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.depends('summary_ids')
    def _compute_last_create_date(self):
        for project in self:
            if project.summary_ids:
                project.last_summary_date = project.summary_ids.sorted(lambda s: s.create_date, reverse=True)[0].create_date

    @api.depends('sale_order_id.risk_ids')
    def _compute_risk_ids(self):
        for project in self:
            project.risk_ids = self.env['risk'].search([
                ('resource', '=', 'project.project,{}'.format(project.id)),
            ])

    @api.depends('risk_ids', 'risk_ids.score')
    def _compute_risk_score(self):
        for project in self:
            project.risk_score = sum(project.risk_ids.mapped('score'))

    @api.depends('risk_ids.write_date')
    def _compute_risk_last_update(self):
        for project in self:
            last_one = datetime(1970, 1, 1)
            for individual_risks in project.risk_ids:
                if not last_one or individual_risks.write_date > last_one:
                    last_one = individual_risks.write_date
                elif not last_one or individual_risks.create_date > last_one:
                    last_one = individual_risks.create_date
            if last_one != datetime(1970, 1, 1):
                project.risk_last_update = last_one
            else:
                project.risk_last_update = False


    @api.one
    @api.depends(
        'sale_line_id.order_id.order_line.invoice_lines',
        'tasks.sale_order_id',
    )
    def _get_out_invoice_ids(self):
        # use of sudo here because of the non possibility of lc to read some invoices
        project_sudo = self.sudo()
        out_invoice_ids = project_sudo.mapped('sale_line_id.order_id.invoice_ids') \
            | project_sudo.mapped('tasks.sale_order_id.invoice_ids')
        self.out_invoice_ids = out_invoice_ids
        self.invoices_count = len(out_invoice_ids)

    @api.multi
    @api.depends(
        'sale_order_id', 'sale_order_id.parent_id',
        'sale_order_id.parent_id.project_id'
    )
    def _get_parent_id(self):
        for project in self:
            if project.sale_order_id:
                project.parent_id = project.sale_order_id.parent_id.project_id

    ##################
    # CUSTOM METHODS #
    ##################
    @api.multi
    def get_tasks_not_cancelled_and_completable(self):
        """This function will return all the tasks and subtasks that can be completed and is not cancelled"""
        self.ensure_one()
        all_tasks = self.task_ids
        return all_tasks.filtered(lambda task: task.sale_line_id.product_id.product_tmpl_id.completion_elligible and
                                  task.stage_id.status not in  ['cancelled'])

    @api.multi
    def action_raise_new_invoice(self):
        """This function will trigger the Creation of invoice regrouping all the sale orders."""
        orders = self.env['sale.order']
        for project in self:
            if not project.sale_order_id and project.sale_order_id.invoice_status != 'to invoice':
                raise UserError(_("The selected Sales Order should contain something to invoice."))
            else:
                orders |= project.sale_order_id

        action = self.env.ref('sale.action_view_sale_advance_payment_inv').read()[0]
        action['context'] = {
            'active_ids': orders.ids
        }
        return action

    @api.multi
    def action_raise_new_risk(self):
        self.ensure_one()
        action = self.env.ref('vcls-risk.action_view_risk_wizard').read()[0]
        action['context'] = {
            'default_resource': 'project.project,{}'.format(self.id),
            'new_risk':True,
        }
        return action

    @api.multi
    def show_risks(self):
        self.ensure_one()
        action = self.env.ref('vcls-risk.action_view_risk').read()[0]
        action['domain'] = [('resource', '=', 'project.project,{}'.format(self.id))]
        action['target'] = 'current'
        return action

    @api.multi
    def sale_orders_tree_view(self):
        action = self.env.ref('sale.action_quotations').read()[0]
        action['domain'] = [('project_id', 'child_of', self.id)]
        action['context'] = {}
        return action

    @api.multi
    def invoices_tree_view(self):
        self.ensure_one()
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action['domain'] = [('id', 'in', self.out_invoice_ids.ids)]
        return action

    @api.multi
    def tasks_tree_view(self):
        action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]
        return action

    @api.multi
    def forecasts_tree_view(self):
        action = self.env.ref('project_forecast.project_forecast_action_from_project').read()[0]
        action['domain'] = [('project_id', 'child_of', self.id)]
        return action

    @api.multi
    def timesheets_tree_view(self):
        action = self.env.ref('hr_timesheet.act_hr_timesheet_line_by_project').read()[0]
        action['domain'] = [('project_id', 'child_of', self.id)]
        return action

    @api.multi
    def report_analysis_tree_view(self):
        action = self.env.ref('vcls-timesheet.project_timesheet_forecast_report_action').read()[0]
        action['domain'] = [('project_id', 'child_of', self.id)]
        action['context'] = {'active_id': self.id, 'active_model': 'project.project'}
        return action

    ###############
    # ORM METHODS #
    ###############
    @api.model
    def create(self, vals):

        #default visibility
        vals['privacy_visibility'] = 'portal'

        #if no ID defined, then increment using the sequence
        if vals.get('external_account','/')=='/':
            vals['external_account'] = self.env['ir.sequence'].next_by_code('seq_customer_project_id')
        
        #we automatically assign the project manager to be the one defined in the core team
        if vals.get('sale_order_id',False):
            so = self.env['sale.order'].browse(vals.get('sale_order_id'))
            vals['scope_of_work'] = so.scope_of_work
            lc = so.core_team_id.lead_consultant
            _logger.info("SO info {}".format(lc.name))
            if lc:
                vals['user_id']=lc.user_id.id


        project = super(Project, self).create(vals)
        ids = project._get_default_type_common()
        project.type_ids = ids if ids else project.type_ids

        if project.project_type != 'client':
            project.privacy_visibility = 'employees'
        
        return project

    @api.multi
    def unlink(self):
        authorized = self.env.user.has_group('vcls_security.group_project_controller') or self.env.user.has_group('vcls_security.group_bd_admin')

        if not authorized:
            raise UserError(_("PROJECT UNLINK | You need to be a member of 'BD Admin' or 'Project Controller' to delete project(s)."))
        
        #we catch all child projects
        projects = self.env['project.project']
        for project in self:
            if project.active:
                raise UserError(_("PROJECT UNLINK | To avoid un-wanted deletion, we don't delete active project(s). Please archive {} 1st").format(project.name))
            else:
                projects |= project
                projects |= project.child_id
        
        #we look for invoices
        invoices = projects.mapped('out_invoice_ids')
        if invoices:
                raise UserError(_("PROJECT UNLINK | We can't delete projects having invoices, please archive instead\n{}").format(invoices.mapped('name')))
        
        for project in projects:
            _logger.info("PROJECT UNLINK | Cleaning {}".format(project.name))
            #we look for timesheets 
            ts = self.env['account.analytic.line'].with_context(active_test=False).search([('project_id','=',project.id)])
            if ts:
                _logger.info("PROJECT UNLINK | Timesheets found {}".format(len(ts)))
                if not self.env.user.has_group('vcls_security.group_project_controller'):
                    raise UserError(_("PROJECT UNLINK | You need to be a member of 'Project Controller' to delete timesheet(s)."))
                ts.unlink()
            #we look for forecasts
            fc = self.env['project.forecast'].with_context(active_test=False).search([('project_id','=',project.id)])
            if fc:
                _logger.info("PROJECT UNLINK | Forecasts found {}".format(len(fc)))
                fc.unlink()
            #we clean the tasks
            tasks = self.env['project.task'].with_context(active_test=False).search([('project_id','=',project.id)])
            if tasks:
                _logger.info("PROJECT UNLINK | Tasks found {}".format(len(tasks)))
                tasks.write({'sale_line_id':False})
                tasks.unlink()
            #we clean the mapping
            if project.sale_line_employee_ids:
                _logger.info("PROJECT UNLINK | SO line mappings {}".format(len(project.sale_line_employee_ids)))
                project.sale_line_employee_ids.unlink()

        return super(Project, self).unlink()
    

    ###################
    # COMPUTE METHODS #
    ###################

    @api.model
    def _default_user_id(self):
        if self.project_type == 'client': 
            if self.sale_order_id:
                return self.sale_order_id.opportunity_id.user_id  
        return self.env.user

    def _compute_parent_task_count(self):
        task_data = self.env['project.task'].read_group([('parent_id','=',False),('project_id', 'in', self.ids), '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)], ['project_id'], ['project_id'])
        result = dict((data['project_id'][0], data['project_id_count']) for data in task_data)
        for project in self:
            project.parent_task_count = result.get(project.id, 0)
    
    def _compute_child_task_count(self):
        task_data = self.env['project.task'].read_group([('parent_id','!=',False),('project_id', 'in', self.ids), '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)], ['project_id'], ['project_id'])
        result = dict((data['project_id'][0], data['project_id_count']) for data in task_data)
        for project in self:
            project.child_task_count = result.get(project.id, 0)
    
    def _compute_task_count(self):
        read_group_res = self.env['project.task'].read_group([('project_id', 'child_of', self.ids), '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)], ['project_id'], ['project_id'])
        group_data = dict((data['project_id'][0], data['project_id_count']) for data in read_group_res)
        for project in self:
            task_count = 0
            for sub_project_id in project.search([('id', 'child_of', project.id)]).ids:
                task_count += group_data.get(sub_project_id, 0)
            project.task_count = task_count

    @api.multi
    @api.depends('task_ids.completion_ratio')
    def compute_project_completion_ratio(self):
        for project in self:
            tasks = project.get_tasks_not_cancelled_and_completable()
            weight_sum = 0
            num_times_weight_factor = 0
            #this weights the tasks complete with the contractual budget
            for task in tasks:
                weight_sum += task.contractual_budget
                num_times_weight_factor += ( task.completion_ratio / 100) * task.contractual_budget
            project.completion_ratio = num_times_weight_factor * 100 / weight_sum if weight_sum > 0 else 0


    @api.multi
    @api.depends('task_ids.consummed_completed_ratio')
    def compute_project_consummed_completed_ratio(self):
        for project in self:
            project.consummed_completed_ratio = (project.budget_consumed / project.completion_ratio) * 100 if project.completion_ratio > 0 else 0


    @api.multi
    def _get_is_project_manager(self):
        for p in self:
            p.is_project_manager = p.user_id == self.env.user

    @api.multi
    def compute_orders_count(self):
        for project in self:
            project.orders_count = self.env['sale.order'].search_count([('project_id', 'child_of', project.id)])

    @api.multi
    def compute_invoices_count(self):
        self.ensure_one()
        projects = self.env['project.project'].search([('id', 'child_of', self.id)])
        sale_orders = projects.mapped('sale_line_id.order_id') | projects.mapped('tasks.sale_order_id')
        invoices = sale_orders.mapped('invoice_ids').filtered(lambda inv: inv.type == 'out_invoice')
        self.invoices_count = len(invoices)

    @api.multi
    def toggle_active(self):
        if any(project.activity_ids for project in self):
            raise ValidationError(_("Its not possible to archive a project while there is still undone activities "))
        super(Project, self).toggle_active()

    @api.model
    def end_project_activities_scheduling(self):
        for project_id in self.search([('active', '=', True), ('parent_id', '=', False)]):
            task_ids = [task for child_id in project_id.child_id for task in child_id.task_ids]
            if task_ids and all(task.stage_id.status in ("completed", "cancelled") for task in task_ids):
                users_summary = {
                    project_id.partner_id.user_id.id: _('Client Feedback'),
                    project_id.user_id.id: _('End of project form filling'),
                    project_id.partner_id.invoice_admin_id.id: _('Invoicing Closing')
                }
                for user_id, summary in users_summary.items():
                    if user_id:
                        activity_vals = {
                            'user_id': user_id,
                            'summary': summary,
                            'act_type_xmlid': 'mail.mail_activity_data_todo',
                            'automated': True,
                        }
                        project_id.sudo().activity_schedule(**activity_vals)
        return True

    def invoicing_session_done(self):
        """
            Timesheets stage_id from pc_review to invoiceable
        """
        if not self.env.user.has_group('vcls_security.group_project_controller'):
            raise ValidationError(_("You need to have the project controller access right."))
        project_ids = self.browse(self._context.get('active_ids'))
        all_projects = project_ids.filtered(lambda p: p.project_type=='client')
        for project in project_ids:
            all_projects += project.child_id

        #we update the timesheet limit date to the end of the previous month
        today = fields.Date.today()
        ts_limit_date =  today.replace(day=1) - relativedelta(days=1)
        

        timesheet_ids = self.env['account.analytic.line'].search([('main_project_id', 'in', all_projects.ids),
                                                                 ('stage_id', '=', 'pc_review'),
                                                                 ('date','<=',ts_limit_date)])
        if timesheet_ids:
            #fixed price usecase
            fp_ts = timesheet_ids.filtered(lambda t: t.so_line.order_id.invoicing_mode == 'fixed_price')
            if fp_ts:
                fp_ts.write({'stage_id': 'fixed_price'})
            #t&m usecase
            tm_ts = timesheet_ids.filtered(lambda t: t.so_line.order_id.invoicing_mode == 'tm')
            if tm_ts:
                tm_ts.write({'stage_id': 'invoiceable'}) 
        
        
        if all_projects:
            all_projects.mapped('sale_order_id').write({'timesheet_limit_date':ts_limit_date})


        #we trigger the computation of KPIs
        self.env['project.task']._cron_compute_kpi()

    @api.multi
    def write(self, values):
        if values.get('active', None) is False:
            tasks = self.mapped('tasks')
            tasks |= tasks.mapped('child_ids')
            tasks.write({'active': False})
        return super(Project, self).write(values)

    @api.multi
    def _get_family_project_ids(self):
        self.ensure_one()
        parent_project_id = self.parent_id or self
        family_project_ids = parent_project_id | parent_project_id.child_id
        return family_project_ids
    
    @api.model
    def detect_bad_tasks(self):
        projects = self.search([('project_type','=','client')])
        tag = self.env.ref('vcls-project.proj_tag_bad_task')
        for project in projects:
            #we get authorized parent taks from the sale_order
            authorized_tasks = project.sale_order_id.order_line.mapped('task_id')
            to_update = self.env['project.task']
            bad = project.task_ids.filtered(lambda t: (t.id not in authorized_tasks.ids) and not t.parent_id)
            for task in bad:
                to_update |= task | task.child_ids
            if bad:
                _logger.info("Bad Tasks in {} | {}".format(project.name,to_update.mapped('name')))
                to_update.write({
                    'tag_ids':[(4,tag.id,0)],
                })

    """@api.onchange('sale_line_employee_ids')
    def _onchange_sale_line_employee_ids(self):
        for project in self.filtered(lambda p: not p.sale_order_id.parent_id and p.sale_order_id.child_ids): #if we make the change in a parent with childs
            for so in project.sale_order_id.child_ids.filtered(lambda o: o.link_rates): #for linked orders
                so.map_match()"""
