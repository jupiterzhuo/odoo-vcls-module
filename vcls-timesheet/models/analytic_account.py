# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from datetime import timedelta
from odoo.osv import expression

import logging
import datetime
import math
_logger = logging.getLogger(__name__)


class AnalyticLine(models.Model):

    _inherit = 'account.analytic.line'

    stage_id = fields.Selection([
        # ('forecast', 'Stock'),
        ('draft', '0. Draft'), 
        ('lc_review', '1. LC review'), 
        ('pc_review', '2. PC review'), 
        ('carry_forward', 'Carry Forward'),
        ('fixed_price', '4. Fixed Price'),
        ('invoiceable', '5. Invoiceable'),
        ('invoiced', '6. Invoiced'),
        ('historical','7. Historical'),
        ('outofscope', 'Out Of Scope'),
        ], default='draft')

    lc_comment = fields.Char(string="Comment")

    deliverable_id = fields.Many2one(
        'product.deliverable',
        string='Deliverable',
        related='task_id.sale_line_id.product_id.deliverable_id',
        store=True,
    )
    
    reporting_task_id = fields.Many2one(
        comodel_name = 'project.task',
        compute = '_compute_reporting_task',
        store=True,
    )

    # Used in order to group by client
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='project_id.partner_id',
        store=True,
    )

    adjustment_reason_id = fields.Many2one('timesheet.adjustment.reason', string="Adjustment Reason")

    time_category_id = fields.Many2one(
        comodel_name='project.time_category',
        string="Time Category",
    )

    # Rename description label
    name = fields.Char('External Comment', required=True)

    internal_comment = fields.Char(string='')

    at_risk = fields.Boolean(string='Timesheet at risk', readonly=True)

    # OVERWRITE IN ORDER TO UPDATE LABEL
    unit_amount_rounded = fields.Float(
        string="Revised Time",
        default=0.0,
        copy=False,
    )

    required_lc_comment = fields.Boolean(compute='get_required_lc_comment')

    rate_id = fields.Many2one(
        comodel_name='product.template',
        default = False,
        readonly = True,
    )

    so_line_unit_price = fields.Monetary(
        'Sales Oder Line Unit Price',
        readonly=True,
        store=True,
        default=0.0,
        group_operator="avg",
    )

    so_line_currency_id = fields.Many2one(
        'res.currency',
        related='so_line.currency_id',
        store=True,
        string='Sales Order Currency',
    )
    adj_reason_required = fields.Boolean()
    main_project_id = fields.Many2one(
        'project.project', string='Main Project',
        domain=[('parent_id', '=', False)],
    )

    billability = fields.Selection([
        ('na', 'N/A'),
        ('billable', 'BILLABLE'),
        ('non_billable', 'NON BILLABLE'),],
        compute = '_compute_billability',
        store = True,
        default = 'na',
        )

    employee_type = fields.Selection(
        related='employee_id.employee_type',
    )

    calculated_amount = fields.Float(
        compute='_compute_calculated_amount',
        compute_sudo=True,
        string="Revenue",
        help="Unite Price x Revised Time",
        store=True,
        group_operator="sum",
        )

    calculated_delta_time = fields.Float(
        compute='_compute_calculated_delta_time',
        string="Delta Time",
        help="Revised Time - Coded Time",
        store=True,
        group_operator="sum",
        )

    @api.depends('unit_amount_rounded', 'so_line_unit_price')
    def _compute_calculated_amount(self):
        for line in self:
            line.calculated_amount = line.unit_amount_rounded * line.so_line_unit_price

    @api.depends('unit_amount_rounded', 'unit_amount')
    def _compute_calculated_delta_time(self):
        for line in self:
            line.calculated_delta_time = line.unit_amount_rounded - line.unit_amount

    @api.depends('task_id','task_id.parent_id')
    def _compute_reporting_task(self):
        for ts in self:
            ts.reporting_task_id = ts.task_id.parent_id if ts.task_id.parent_id else ts.task_id

    @api.depends('project_id')
    def _compute_billability(self):
        timesheets = self.filtered(lambda t: t.is_timesheet and t.project_id)
        for ts in timesheets:
            if ts.project_id.project_type == 'client':
                ts.billability = 'billable'
            else:
                ts.billability = 'non_billable'


    @api.model
    def show_grid_cell(self, domain=[], column_value='', row_values={}):
        line = self.sudo().search(domain, limit=1)
        date = column_value
        if not line:
            # fetch the latest line
            task_value = row_values.get('task_id')
            task_id = task_value and task_value[0] or False
            if task_id:
                direct_previous_line = self.sudo().search([
                    ('date', '<', date),
                    ('task_id', '=', task_id),
                ], limit=1, order='date desc')
                if direct_previous_line:
                    task_id = direct_previous_line.task_id
                    main_project_id = direct_previous_line.main_project_id
                    #main_project_id = main_project_id or main_project_id.parent_id
                    values = {
                        'unit_amount': 0,
                        'date': date,
                        'project_id': direct_previous_line.project_id.id,
                        'task_id': task_id.id,
                        'main_project_id': main_project_id.id,
                        'name': direct_previous_line.name,
                        'time_category_id': direct_previous_line.time_category_id.id,
                    }
                    line = self.create(values)

        form_view_id = self.env.ref('timesheet_grid.timesheet_view_form').id
        return {
            'name': _('Timesheet'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': line.id,
            'view_id': form_view_id,
            'views': [(form_view_id, 'form')],
            'target': 'new',
            'context': {},
        }

    @api.multi
    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        """
        We override this to avoit the default naming 'Timesheet Adjustment' when using the grid view
        """
        if column_field != 'date' or cell_field != 'unit_amount':
            raise ValueError(
                "{} can only adjust unit_amount (got {}) by date (got {})".format(
                    self._name,
                    cell_field,
                    column_field,
                ))

        additionnal_domain = self._get_adjust_grid_domain(column_value)
        domain = expression.AND([row_domain, additionnal_domain])
        line = self.search(domain)

        day = column_value.split('/')[0]
        if len(line) > 1:  # copy the last line as adjustment
            line[0].copy({
                #'name': _('Timesheet Adjustment'),
                column_field: day,
                cell_field: change
            })
        elif len(line) == 1:  # update existing line
            line.write({
                cell_field: line[cell_field] + change
            })
        else:  # create new one
            self.search(row_domain, limit=1).copy({
                #'name': _('Timesheet Adjustment'),
                column_field: day,
                cell_field: change
            })
        return False

    @api.model
    def _get_at_risk_values(self, project_id, employee_id):
        project = self.env['project.project'].browse(project_id)
        if project.sale_order_id.state not in ['sale', 'done']:
            return True
        employee_id = self.env['hr.employee'].browse(employee_id)

        core_team = project.core_team_id
        if employee_id and core_team:
            project_employee = core_team.consultant_ids | \
                           core_team.ta_ids | \
                           core_team.lead_backup | \
                           core_team.lead_consultant
            if employee_id[0] not in project_employee:
                return True
        return False
    
    #we override this to force the creation of a map line when not found rather than taking the one of the task
    @api.model
    def _timesheet_determine_sale_line(self, task, employee):
        """ Deduce the SO line associated to the timesheet line:
            1/ timesheet on task rate: the so line will be the one from the task
            2/ timesheet on employee rate task: find the SO line in the map of the project (even for subtask), or fallback on the SO line of the task, or fallback
                on the one on the project
            NOTE: this have to be consistent with `_compute_billable_type` on project.task.
        """
        if task.billable_type != 'no':
            if task.billable_type == 'employee_rate':
                map_entry = self.env['project.sale.line.employee.map'].search([('project_id', '=', task.project_id.id), ('employee_id', '=', employee.id)])
                if map_entry:
                    return map_entry.sale_line_id
                #VCLS custom
                else:
                    so_line = self._update_project_soline_mapping({
                        'employee_id':employee.id,
                        'project_id':task.project_id.id,
                    })
                    if so_line:
                        return so_line
                if task.sale_line_id:
                    return task.sale_line_id
                return task.project_id.sale_line_id
            elif task.billable_type == 'task_rate':
                return task.sale_line_id
        return self.env['sale.order.line']
    
    @api.model
    def _timesheet_preprocess(self, vals):
       
        _logger.info("TS PRE pre | {}".format(vals))
        #if we have task_id, we enforce project_id and main_project_id and related accounts
        if vals.get('task_id'):
            task = self.env['project.task'].sudo().browse(vals['task_id'])
            vals.update({
                'project_id': task.project_id.id,
                'main_project_id': task.project_id.parent_id.id or task.project_id.id,
                'account_id': task.project_id.analytic_account_id.id,
                'company_id': task.project_id.analytic_account_id.company_id.id,
                'so_line_unit_price': 0.0, #we force it to zero to trigger the recompute in post process
            })
        
        if vals.get('project_id') or self.mapped('project_id'): #if we have a project ID, we are in the context of a timesheet
            #we round values if modified
            for field in ['unit_amount','unit_amount_rounded']:
                if vals.get(field):
                    if vals[field] % 0.25 != 0:
                        old = vals[field]
                        vals[field] = math.ceil(old * 4) / 4
            
            # when attached to an invoice, a TS turns in 'invoiced'
            if vals.get('timesheet_invoice_id'):
                vals['stage_id'] = 'invoiced'

        #_logger.info("TS PRE post | {}".format(vals))
        vals = super(AnalyticLine, self)._timesheet_preprocess(vals)
   
        return vals
    
    @api.multi
    def _timesheet_postprocess_values(self, values):
        """
        # Get the addionnal values to write on record
        #    :param dict values: values for the model's fields, as a dictionary::
        #        {'field_name': field_value, ...}
        #    :return: a dictionary mapping each record id to its corresponding
        #        dictionnary values to write (may be empty).
        """
        result = super(AnalyticLine, self)._timesheet_postprocess_values(values)
        sudo_self = self.sudo()  # this creates only one env for all operation that required sudo()
        orders = self.env['sale.order'] 

        #_logger.info("TS POST pre | {}".format(values))

        #we check if the timesheet is 'At Risk'
        if any([field_name in values for field_name in ['employee_id','project_id']]):
            #_logger.info("TS POST | at risk test")
            for timesheet in sudo_self:
                result[timesheet.id].update({
                    'at_risk': sudo_self._get_at_risk_values(values.get('project_id',timesheet.project_id.id),values.get('employee_id',timesheet.employee_id.id)),
                })
        
        #below fields need a kpi recompute of the related task
        if any([field_name in values for field_name in ['task_id','unit_amount','unit_amount_rounded','stage_id']]):
            tasks = sudo_self.env['project.task']
            if values.get('task_id'):
                tasks = sudo_self.env['project.task'].browse(values['task_id'])
            else:
                tasks |= sudo_self.mapped('task_id')
            #_logger.info("TS POST | task recompute {}".format(tasks.mapped('name')))
            tasks.write({'recompute_kpi':True})
        
        #if we move a ts to draft, it's automatically set to lc_review if already approved
        if values.get('stage_id','/') == 'draft':
            for timesheet in sudo_self.filtered(lambda t: t.validated):
                #_logger.info("TS POST | direct lc_rev {}".format(timesheet.name))
                result[timesheet.id].update({
                    'stage_id': 'lc_review',
                })
        
        #if some timesheets have no so_line_unit_price
        for timesheet in sudo_self.filtered(lambda p: p.so_line_unit_price == 0.0 and p.so_line):
            if timesheet.task_id.sale_line_id != timesheet.so_line:  # if we map to a rate based product
                #we check if the line unit is hours or days to ensure the hourly price
                if timesheet.so_line.product_uom == self.env.ref('uom.product_uom_day'): #if we are in daily
                    price = round((timesheet.so_line.price_unit/8.0),2)
                else:
                    price = timesheet.so_line.price_unit
                rate = timesheet.so_line.product_id.product_tmpl_id

                up_vals = {
                    'so_line_unit_price':price,
                    'rate_id': rate.id,
                }

                result[timesheet.id].update(up_vals)

                #_logger.info("TS POST | so_line update {} {}".format(timesheet.name,up_vals))

        #trigger order update according to modified values in the timesheet
        if any([field_name in values for field_name in ['task_id','unit_amount_rounded','stage_id','date']]):
            for timesheet in sudo_self:
                # test case where original stage is one of them
                if values.get('stage_id') in ['invoiced','invoiceable','historical','fixed_price'] or timesheet.stage_id in ['invoiced','invoiceable','historical','fixed_price']:
                    orders |= timesheet.so_line.order_id

        #trigger some recompute
        """
        if orders:
            orders._compute_timesheet_ids()
            _logger.info("TS POST | order update {}".format(orders.mapped('name')))
        """

        for order in orders:
            order.timesheet_limit_date = order.timesheet_limit_date
            #_logger.info("TS POST | order update {}".format(order.name))
        
        
        #TODO travel time category to take in account
        #_logger.info("TS POST post | {}".format(result))
        
        return result

    """@api.model
    def create(self, vals):
        if not self._context.get('migration_mode',False):
            if vals.get('employee_id', False) and vals.get('project_id', False):
                # rounding to 15 mins
                if vals['unit_amount'] % 0.25 != 0:
                    old = vals.get('unit_amount', 0)
                    vals['unit_amount'] = math.ceil(old * 4) / 4

                # check if this is a timesheet at risk
                vals['at_risk'] = self.sudo()._get_at_risk_values(vals.get('project_id'),
                                                        vals.get('employee_id'))

            if vals.get('time_category_id') == self.env.ref('vcls-timesheet.travel_time_category').id:
                task = self.env['project.task'].browse(vals['task_id'])
                if task.sale_line_id:
                    unit_amount_rounded = vals['unit_amount'] * task.sale_line_id.order_id.travel_invoicing_ratio
                    vals.update({'unit_amount_rounded': unit_amount_rounded})
        #else:
            #_logger.info("TS FAST create")
                
        if not vals.get('main_project_id') and vals.get('project_id'):
            project_id = self.env['project.project'].browse(vals['project_id'])
            main_project_id = project_id.parent_id or project_id
            vals['main_project_id'] = main_project_id.id

        line = super(AnalyticLine, self).create(vals)
        if line.task_id:
            line.task_id.recompute_kpi=True

        return line"""

    @api.multi
    def write(self, vals):
        """# we automatically update the stage if the ts is validated and stage = draft
        so_update = False
        orders = self.env['sale.order']"""
        _logger.info("ANALYTIC WRITE {}".format(vals))

        temp_self = self
        #if this is a modification authorized for lc during lc_review, we do it in sudo
        if self.filtered(lambda p: p.stage_id == 'lc_review'):
            #we test protected fields and filter based on LC
            #all ts are in lc_review and the connected user is the lc
            if (len(self) == len(self.filtered(lambda p: p.stage_id == 'lc_review' and p.project_id.user_id.id == self._uid))) \
                and (not any([field_name in vals for field_name in ['unit_amount','employee_id']])): 
                temp_self = self.sudo()
                #_logger.info("TS CHECK WRITE | LC review case sudo")

        # we check the case where we change the unit_amount only and not the rounded value.
        #this case can't be done in post_process because we need the delta value before it's recomputed
        if vals.get('unit_amount', False) and not vals.get('unit_amount_rounded', False):
            for timesheet in self.filtered(lambda t: t.is_timesheet):
                vals['unit_amount_rounded'] = vals['unit_amount'] + timesheet.calculated_delta_time
                #_logger.info("TS CHECK WRITE | Delta Time {} + {} = {}".format(vals['unit_amount'],timesheet.calculated_delta_time,vals['unit_amount_rounded']))
                ok = super(AnalyticLine, temp_self).write(vals)
        
        else:
            #_logger.info("TS CHECK WRITE | Regular Case")
            ok = super(AnalyticLine, temp_self).write(vals)

        return ok

        """
            # Timesheet cases
            if line.is_timesheet and line.project_id and line.employee_id:

                if vals.get('unit_amount', False) and not vals.get('unit_amount_rounded', False):
                    #if unit amount is changed, we preserve the delta
                    delta = vals['unit_amount'] - line.unit_amount
                    vals['unit_amount_rounded'] = line.unit_amount_rounded + delta

                if vals.get('unit_amount', False):
                    #the coded amount is changed
                    if vals['unit_amount'] % 0.25 != 0:
                        old = vals.get('unit_amount', 0)
                        vals['unit_amount'] = math.ceil(old * 4) / 4
                    
                    #we preserve a potential modification of the rounded_value in the past
                    delta = vals['unit_amount'] - line.unit_amount
                    vals['unit_amount_rounded'] = vals.get('unit_amount_rounded', line.unit_amount_rounded)+delta

                # automatically set the stage to lc_review according to the conditions
                if vals.get('validated', line.validated):
                    if vals.get('stage_id', line.stage_id) == 'draft':
                        vals['stage_id'] = 'lc_review'

                # review of the lc needs sudo() to write on validated ts
                if line.stage_id == 'lc_review':
                    project = self.env['project.project'].browse(
                        vals.get('project_id', line.project_id.id))
                    if project.user_id.id == self._uid:  # if the user is the lead consultant, we autorize the modification
                        self = self.sudo()

                # if one of the 3 important value has changed, and the stage changes the delivered amount
                if (vals.get('date', False) or vals.get('unit_amount_rounded',False) or vals.get('stage_id', False)) and (vals.get('stage_id', line.stage_id) in ['invoiced','invoiceable','historical']):
                    _logger.info("Order timesheet update for {}".format(line.name))
                    so_update = True
                    orders |= line.so_line.order_id

                # if the sale order line price as not been captured yet
                if vals.get('so_line',line.so_line.id) and line.so_line_unit_price == 0.0:
                    task = self.env['project.task'].browse(
                        vals.get('task_id', line.task_id.id))
                    so_line = self.env['sale.order.line'].browse(
                        vals.get('so_line', line.so_line.id))

                    if task.sale_line_id != so_line:  # if we map to a rate based product
                        #we check if the line unit is hours or days to ensure the hourly price
                        if so_line.product_uom == self.env.ref('uom.product_uom_day'): #if we are in daily
                            vals['so_line_unit_price'] = round((so_line.price_unit/8.0),2)
                        else:
                            vals['so_line_unit_price'] = so_line.price_unit
                        vals['rate_id'] = so_line.product_id.product_tmpl_id.id
                        so_update = True
                        orders |= line.so_line.order_id

            if (vals.get('time_category_id') == self.env.ref('vcls-timesheet.travel_time_category').id or
                (vals.get('unit_amount') and line.time_category_id.id == self.env.ref('vcls-timesheet.travel_time_category').id)) and\
                    line.task_id.sale_line_id:
                unit_amount = vals.get('unit_amount') or line.unit_amount
                vals.update({
                    'unit_amount_rounded': unit_amount * line.task_id.sale_line_id.order_id.travel_invoicing_ratio
                            })
        if vals.get('timesheet_invoice_id'):
            vals['stage_id'] = 'invoiced'
        ok = super(AnalyticLine, self).write(vals)

        if ok: #we trigger the kpi recompute
            to_recompute = self.filtered(lambda t: t.task_id)
            to_recompute.mapped('task_id').write({'recompute_kpi':True})

        if ok and so_update:
            orders._compute_timesheet_ids()
            # force recompute
            #_logger.info("SO UPDATE {} CONTEXT MIG {}".format(orders.mapped('name'),self._context.get('migration_mode',False)))
            for order in orders:
                order.timesheet_limit_date = order.timesheet_limit_date

        return ok
    """

    @api.multi
    def finalize_lc_review(self):
        self._finalize_lc_review()

    @api.multi
    def _finalize_lc_review(self):
        context = self.env.context
        timesheet_ids = context.get('active_ids',[])
        timesheets = self.env['account.analytic.line'].browse(timesheet_ids)
        if len(timesheets) == 0:
            raise ValidationError(_("Please select at least one record!"))

        timesheets_in = timesheets.filtered(lambda r: r.stage_id=='lc_review' and (r.project_id.user_id.id == r.env.user.id or r.env.user.has_group('vcls-hr.vcls_group_superuser_lvl2')))
        timesheets_out = (timesheets - timesheets_in) if timesheets_in else timesheets
        #_logger.info("names {} stage {} user {} out {}".format(timesheets.mapped('name'),timesheets.mapped('stage_id'),timesheets_out.mapped('name')))
        for timesheet in timesheets_in:
                timesheet.sudo().write({'stage_id':'pc_review'})
        if len(timesheets_out) > 0:
            message = "You don't have the permission for the following timesheet(s) :\n"
            for timesheet in timesheets_out:
                message += " - " + timesheet.name + "\n"
            raise ValidationError(_(message))

    @api.multi
    def finalize_pc_review(self):
        self._pc_change_state('invoiceable')

    @api.multi
    def _pc_change_state(self,new_stage='invoiceable'):
        """
            THis method covers all the use cases of the project controller, modifying timesheet stages.
            Server actions and buttons are calling this method.
        """
        context = self.env.context
        timesheet_ids = context.get('active_ids',[])
        timesheets = self.env['account.analytic.line'].browse(timesheet_ids)
        if len(timesheets) == 0:
            raise ValidationError(_("Please select at least one record!"))

        user_authorized = (self.env.user.has_group('vcls-hr.vcls_group_superuser_lvl2') or self.env.user.has_group('vcls_security.group_project_controller'))
        if not user_authorized:
            raise ValidationError(_("You need to be part of the 'Project Controller' group to perform this operation. Thank you."))

        #_logger.info("NEW TS STAGE:{}".format(new_stage))

        if new_stage=='invoiceable':
            timesheets_in = timesheets.filtered(lambda r: (r.stage_id=='pc_review' or r.stage_id=='carry_forward'))
            #fixed price usecase
            fp_ts = timesheets_in.filtered(lambda t: t.so_line.order_id.invoicing_mode == 'fixed_price')
            if fp_ts:
                fp_ts.write({'stage_id': 'fixed_price'})
            #t&m usecase
            tm_ts = timesheets_in.filtered(lambda t: t.so_line.order_id.invoicing_mode == 'tm')
            if tm_ts:
                tm_ts.write({'stage_id': 'invoiceable'})

        elif new_stage=='outofscope':
            timesheets_in = timesheets.filtered(lambda r: (r.stage_id=='pc_review' or r.stage_id=='carry_forward'))
            _logger.info("NEW TS STAGE outofscope:{}".format(timesheets_in.mapped('name')))
            timesheets_in.write({'stage_id': 'outofscope'})

        elif new_stage=='carry_forward':
            timesheets_in = timesheets.filtered(lambda r: (r.stage_id=='pc_review'))
            _logger.info("NEW TS STAGE carry_forward:{}".format(timesheets_in.mapped('name')))
            timesheets_in.write({'stage_id': 'carry_forward'})

        else:
            timesheets_in = False

        timesheets_out = (timesheets - timesheets_in) if timesheets_in else timesheets
        if len(timesheets_out) > 0:
            message = "Following timesheet(s) are not in the proper stage to perform the required action:\n"
            for timesheet in timesheets_out:
                message += " - " + timesheet.name + "\n"
            raise ValidationError(_(message))

    @api.multi
    def _finalize_pc_review(self):
        self._pc_change_state('invoiceable')

    @api.multi
    def set_outofscope(self):
        self._pc_change_state('outofscope')

    @api.multi
    def set_carry_forward(self):
        self._pc_change_state('carry_forward')

    @api.depends('user_id')
    def _compute_employee_id(self):
        for record in self:
            if record.user_id:
                resource = self.env['resource.resource'].search([('user_id','=',record.user_id.id)])
                employee = self.env['hr.employee'].search([('resource_id','=',resource.id)])
                record.employee_id = employee

    @api.onchange('unit_amount_rounded', 'unit_amount')
    def get_required_lc_comment(self):
        for rec in self:
            #we round to quarter to avoir the minute entry
            if rec.unit_amount % 0.25 != 0:
                rec.unit_amount = math.ceil(rec.unit_amount * 4) / 4
            else:
                pass
            if rec.unit_amount_rounded % 0.25 != 0:
                rec.unit_amount_rounded = math.ceil(rec.unit_amount_rounded * 4) / 4
            else:
                pass
                 
            #if the values aren't the same, then we force the lc_comment.
            if float_compare(rec.unit_amount_rounded, rec.unit_amount, precision_digits=2) == 0:
                rec.required_lc_comment = False
            else:
                rec.required_lc_comment = True

    @api.onchange('unit_amount_rounded')
    def onchange_adj_reason_readonly(self):
        adj_reason_required = False
        if self.unit_amount != self.unit_amount_rounded:
            adj_reason_required = True
        self.adj_reason_required = adj_reason_required

    @api.onchange('main_project_id')
    def onchange_task_id_project_related(self):
        #we clear the existing task_id and project_id if not logged from task
        if not self._context.get('log_from_task',False):
            self.task_id = False
            self.project_id = False
        #we return the proper domain
        if self.main_project_id:
            projects = self.main_project_id | self.main_project_id.child_id
            return {'domain': {
                'task_id': [('project_id', 'in', projects.ids), ('stage_id.allow_timesheet', '=', True)]
            }}

    @api.onchange('task_id')
    def onchange_task_id(self):
        #if self._context.get('desc_order_display'):
        if self.task_id.project_id != self.project_id:
            self.project_id = self.task_id.project_id
            self.so_line_unit_price = 0 #in case the price of the mapped line is not the same
        if not self.main_project_id and self.task_id:
            main_project_id = self.task_id.project_id
            self.main_project_id = main_project_id.parent_id or main_project_id

    @api.multi
    def button_details_lc(self):
        view = {
            'name': _('Details'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.analytic.line',
            'view_id': self.env.ref('vcls-timesheet.vcls_timesheet_lc_view_form').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
                'force_detailed_view': True,
                'set_fields_readonly': self.stage_id != 'lc_review'
            },
            'res_id': self.id,
        }
        return view
    
    @api.multi
    def button_details_pc(self):
        view = {
            'name': _('Details'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.analytic.line',
            'view_id': self.env.ref('vcls-timesheet.vcls_timesheet_pc_view_form').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
                'force_detailed_view': True,
            },
            'res_id': self.id,
        }
        return view

    def lc_review_approve_timesheets(self):
        self.search([('stage_id', '=', 'lc_review')]).write({'stage_id': 'pc_review'})

    def pc_review_approve_timesheets(self):
        self.search([('stage_id', '=', 'pc_review'), ('lc_comment', '=', False)])._pc_change_state('invoiceable')

    @api.model
    def _clean_0_ts(self):
        to_clean = self.search([
            ('is_timesheet', '=', True),
            ('validated', '=', True),
            ('unit_amount','=',0.0),
            ('timesheet_invoice_id','=',False),
        ])

        if to_clean:
            to_clean.unlink()

    @api.model
    def _smart_timesheeting_cron(self,hourly_offset=0):
        days = hourly_offset//24
        remainder = hourly_offset%24
        now = fields.Datetime.now()
        timestamp_end = now + timedelta(minutes=9)

        #we look for employees to smart_timesheets
        employees = self.env['hr.employee'].search([('do_smart_timesheeting','=',True)])

        for emp in employees:
            if fields.Datetime.now()>timestamp_end:#to avoid timeout
                break
            else:
                tasks = self.env['project.task']
                #we get timesheets
                timesheets = self.search([
                    ('employee_id','=',emp.id),
                    ('project_id', '!=', False),
                    ('unit_amount', '>', 0),
                    ('date', '>', now - timedelta(days=days+7,hours=remainder)),
                    ('date', '<', now - timedelta(days=days,hours=remainder)),
                ])
                
                if timesheets:
                    _logger.info("SMART TIMESHEETING: Found {} timesheets for {}".format(len(timesheets),emp.name))
                    tasks |= timesheets.mapped('task_id')
                    for task in tasks.filtered(lambda t: t.stage_allow_ts):
                        if task.project_id.parent_id:
                            parent_project_id = task.project_id.parent_id
                        else:
                            parent_project_id = task.project_id

                        _logger.info("SMART TIMESHEETING: {} on {}".format(task.name,emp.name))
                        #we finally create the ts
                        self.create({
                            'date': now + timedelta(days=1),
                            'task_id': task.id,
                            'unit_amount': 0.0,
                            'company_id': task.company_id.id,
                            'project_id': task.project_id.id,
                            'main_project_id': parent_project_id.id,
                            'employee_id': emp.id,
                            'name': "/",
                        })
                
                #employee processed
                emp.do_smart_timesheeting = False 

    
    @api.model
    def _get_task_domain(self):
        #return "[" \
        #       "('project_id', '=', project_id)," \
        #      "('stage_id.allow_timesheet', '=', True)," \
        #       "]"
        return "[" \
               "('stage_id.allow_timesheet', '=', True)," \
               "]"

    @api.multi
    def unlink(self):
        for time_sheet in self:
            if time_sheet.timesheet_invoice_id:
                raise ValidationError(_('You cannot delete a timesheet linked to an invoice'))
        return super(AnalyticLine, self).unlink()

    @api.multi
    def _check_can_write(self, values):
        super(AnalyticLine, self)._check_can_write(values)
        if self.filtered(lambda t: t.timesheet_invoice_id):
            if any([field_name in values for field_name in ['unit_amount_rounded']]):
                raise UserError(
                    _('You can not modify already invoiced '
                      'timesheets (linked to a Sales order '
                      'items invoiced on Time and material).')
                )

    @api.model
    def _force_rate_id(self):
        timesheets = self.search([('is_timesheet','=',True),('employee_id','!=',False),('project_id','!=',False)])

        for project in timesheets.mapped('project_id'):
            _logger.info("Processing Rate_id for project {}".format(project.name))
            for map_line in project.sale_line_employee_ids:
                rate_id = map_line.sale_line_id.product_id.product_tmpl_id
                ts = timesheets.filtered(lambda t: t.so_line == map_line.sale_line_id)
                if ts:
                    _logger.info("Processing Rate_id for map line for {} as {} with {} timesheets".format(map_line.employee_id.name,rate_id.name,len(ts)))
                    ts.write({'rate_id':rate_id.id})

    @api.model
    def _set_fixed_price_timesheets(self):
        timesheets = self.search([('is_timesheet','=',True),('employee_id','!=',False),('project_id','!=',False),('stage_id','=','invoiceable')])
        fp_ts = timesheets.filtered(lambda t: t.so_line.order_id.invoicing_mode == 'fixed_price')
        if fp_ts:
            fp_ts.write({'stage_id': 'fixed_price'})
            _logger.info("Found {} invoiceable timesheets set as fixed_price status.".format(len(fp_ts)))
    
    @api.model
    def _force_main_project(self):
        #we look for child projects
        projects = self.env['project.project'].search([('project_type','=','client'),('parent_id','!=',False)])
        for project  in projects:
            main_project  = project.parent_id
            timesheets = project.timesheet_ids.filtered(lambda t: t.main_project_id != main_project and (t.stage_id not in ['invoiced']))
            if timesheets:
                timesheets.write({'main_project_id':main_project.id})
                _logger.info("Updating {} TS with main project {} for {}".format(len(timesheets),main_project.name,project.name))

    @api.model
    def merge_negative_ts(self):
        do_it = True
        while do_it:
            ts = self.search([('is_timesheet','=',True),('employee_id','!=',False),('project_id','!=',False),('stage_id','not in',['invoiced','draft']),('unit_amount_rounded','<',0)],limit=1)
            if not ts:
                do_it = False
                break
            else:
                _logger.info("NEG TS | {} {} on {} {} with {} {} {}".format(ts.date,ts.employee_id.name,ts.project_id.name,ts.task_id.name,ts.time_category_id.name,ts.name,ts.unit_amount))
                #we look for others to merge
                twins = self.search([
                    ('is_timesheet','=',True),
                    ('date','=',ts.date),
                    ('employee_id','=',ts.employee_id.id),
                    ('project_id','=',ts.project_id.id),
                    ('task_id','=',ts.task_id.id),
                    ('time_category_id','=',ts.time_category_id.id if ts.time_category_id else False),
                    ('name','=',ts.name),
                    ('stage_id','!=','invoiced'),
                    ])
                
                _logger.info("NEG TS | Found {} twins".format(len(twins)))
                #we update the source ts
                new_com = list(set(twins.filtered(lambda p: p.lc_comment).mapped('lc_comment')))
                vals={
                    'unit_amount': max(sum(twins.mapped('unit_amount')),0),
                    'unit_amount_rounded': max(sum(twins.mapped('unit_amount_rounded')),0),
                    'lc_comment': new_com if len(new_com)>0 else False,
                }
                _logger.info("NEG TS | Update {}".format(vals))
                to_delete = twins - ts
                
                if (vals['unit_amount'] + vals['unit_amount_rounded']) == 0:
                    ts.unlink()
                else:
                    ts.write(vals)
                
                if to_delete:
                    to_delete.unlink()
                    #pass
            
                

        
            

