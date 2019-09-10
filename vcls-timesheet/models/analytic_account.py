# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

import logging
import datetime
import math
_logger = logging.getLogger(__name__)

class AnalyticLine(models.Model):

    _inherit = 'account.analytic.line'

    stage_id = fields.Selection([
        #('forecast', 'Stock'),
        ('draft', 'Draft'), 
        ('lc_review', 'LC review'), 
        ('pc_review', 'PC review'), 
        ('carry_forward', 'Carry Forward'),
        ('adjustment_validation', 'Adjustment Validation'),
        ('invoiceable', 'Invoiceable'),
        ('invoiced', 'Invoiced'),
        ('outofscope', 'Out Of Scope'),
        ], default='draft')

    lc_comment = fields.Text(string = "Comment")

    deliverable_id = fields.Many2one(
        'product.deliverable',
        string = 'Deliverable',
        related = 'product_id.deliverable_id',
        store = True,
    )

    # Used in order to group by client
    partner_id = fields.Many2one(
        'res.partner',
        string = 'Client',
        related = 'project_id.partner_id',
        store = True,
    )

    adjustment_reason_id = fields.Many2one('timesheet.adjustment.reason', string="Adjustment Reason")

    time_category_id = fields.Many2one(
        comodel_name='project.time_category',
        string="Time Category",
    )

    # Rename description label
    name = fields.Char('External Comment', required=True)

    internal_comment = fields.Char(string = 'Internal Comment')

    at_risk = fields.Boolean(string='Timesheet at risk', readonly=True)

        # OVERWRITE IN ORDER TO UPDATE LABEL
    unit_amount_rounded = fields.Float(
        string="Revised Time",
        default=0.0,
        copy=False,
    )
    
    required_lc_comment = fields.Boolean(compute='get_required_lc_comment')


    so_line_unit_price = fields.Float(
        'Sales Oder Line Unit Price',
        related = 'so_line.price_unit',
        store = True
    )

    so_line_currency_id = fields.Many2one(
        'res.currency',
        related = 'so_line.currency_id',
        store = True,
        string = 'Sales Order Currency',
    )

    @api.model
    def _get_at_risk_values(self, project_id):
        project = self.env['project.project'].browse(project_id)
        if project.sale_order_id.state == 'sale':
            return True
        employee_id = self.env.user.employee_ids
        core_team = project.core_team_id
        if employee_id and core_team:
            project_employee = core_team.consultant_ids | \
                           core_team.ta_ids | \
                           core_team.lead_backup | \
                           core_team.lead_consultant
            if employee_id[0] not in project_employee:
                return True
        return False

    @api.model
    def create(self, vals):
        _logger.info("Create {}".format(vals.get('unit_amount')))
        if 'unit_amount' in vals and vals.get('is_timesheet', False): #do time ceiling for timesheets only
            _logger.info("Before round {}".format(vals.get('unit_amount')))
            if vals['unit_amount'] % 0.25 != 0:
                vals['unit_amount'] = math.ceil(vals.get('unit_amount', 0)*4)/4
                _logger.info("After round {}".format(vals.get('unit_amount')))
        if vals.get('project_id', False):
            vals['at_risk'] = self._get_at_risk_values(vals.get('project_id'))
        return super(AnalyticLine, self).create(vals)

    @api.multi
    def write(self,vals):
        #we automatically update the stage if the ts is validated and stage = draft
        for line in self:
            if vals.get('validated',line.validated):
                if vals.get('stage_id',line.stage_id) == 'draft':
                    vals['stage_id']='lc_review'
            
            _logger.info("Test Stage vals {} origin {}".format(vals.get('stage_id','no'),line.stage_id))
            if (vals.get('date',False) or vals.get('unit_amount_rounded',False)) and (vals.get('stage_id','no') in ['invoiced','invoiceable'] or line.stage_id in ['invoiced','invoiceable']):
                _logger.info("Order timesheet update for {}".format(line.name))
                line.so_line.order_id._compute_timesheet_ids()

        
        return super(AnalyticLine, self).write(vals)

    
    """ @api.onchange('unit_amount')
    def _round_ts(self,rounding=0.25):
        for ts in self.filtered(lambda r: r.)"""

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
        self._finalize_pc_review()

    @api.multi
    def _finalize_pc_review(self):
        context = self.env.context
        timesheet_ids = context.get('active_ids',[])
        timesheets = self.env['account.analytic.line'].browse(timesheet_ids)
        if len(timesheets) == 0:
            raise ValidationError(_("Please select at least one record!"))
        timesheets_in = timesheets.filtered(lambda r: (r.env.user.has_group('vcls-hr.vcls_group_superuser_lvl2') or r.env.user.has_group('vcls-timesheet.vcls_pc'))).write({'stage_id':'invoiceable'})
        #timesheets_out = timesheets - timesheets_in
        timesheets_out = (timesheets - timesheets_in) if timesheets_in else timesheets
        for timesheet in timesheets_in:
            if timesheet.unit_amount_rounded != timesheet.unit_amount:
                timesheet.sudo().write({'stage_id':'adjustment_validation'})
            else:
                timesheet.sudo().write({'stage_id':'invoiceable'})
        if len(timesheets_out) > 0:
            message = "You don't have the permission for the following timesheet(s) :\n"
            for timesheet in timesheets_out:
                message += "- " + timesheet.name + "\n"
            raise ValidationError(_(message))
    
    @api.multi
    def set_outofscope(self):
        context = self.env.context
        timesheet_ids = context.get('active_ids',[])
        timesheets = self.env['account.analytic.line'].browse(timesheet_ids)
        timesheets.filtered(lambda r: (r.task_id.project_id.user_id.id == self._uid or r.env.user.has_group('vcls-timesheet.vcls_pc'))).write({'stage_id':'outofscope'})
    

    @api.depends('user_id')
    def _compute_employee_id(self):
        for record in self:
            if record.user_id:
                resource = self.env['resource.resource'].search([('user_id','=',record.user_id.id)])
                employee = self.env['hr.employee'].search([('resource_id','=',resource.id)])
                record.employee_id = employee
    
    
    """@api.depends('user_id')
    def _is_authorized_lm(self):
        for record in self:
            try:
                resource = self.env['resource.resource'].search([('user_id','=',record.user_id.id)])
                employee = self.env['hr.employee'].search([('resource_id','=',resource.id)])
                record.is_authorized = self._uid == employee.parent_id.id
            except Exception as err:
                print(err)
                # No project / project controller / project manager
                record.is_authorized = False"""
    

    @api.onchange('unit_amount_rounded', 'unit_amount')
    def get_required_lc_comment(self):
        for record in self:
            if float_compare(record.unit_amount_rounded, record.unit_amount, precision_digits=2) == 0:
                record.required_lc_comment = False
            else:
                record.required_lc_comment = True    

    @api.onchange('project_id')
    def onchange_project_id(self):
        # force domain on task when project is set
        if self.project_id:
            if self.project_id != self.task_id.project_id:
                # reset task when changing project
                self.task_id = False
            return {'domain': {
                'task_id': [('project_id', '=', self.project_id.id), ('stage_id.allow_timesheet','=', True)]
            }}

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
            'force_detailed_view': True, },
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
            'force_detailed_view': True, },
            'res_id': self.id,
        }
        return view

    
