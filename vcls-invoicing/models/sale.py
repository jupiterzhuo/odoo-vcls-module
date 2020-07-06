# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

from lxml import etree
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

supported_vcls_types = ('rate', 'subscription', 'expense', 'invoice', 'project_supplier', 'admin_supplier', 'vcls_service', 'other')

class SaleOrder(models.Model):

    _inherit = 'sale.order'

    def get_activity_report_template(self):
        order_id = self._context.get('params', {}).get('id')
        model = self._context.get('params', {}).get('model')
        if model == 'sale.order' and order_id:
            order_id = self.env['sale.order'].browse(order_id)
            return order_id.partner_id.activity_report_template
        return False

    risk_ids = fields.Many2many('risk', string='Risk')

    risk_score = fields.Integer(
        string='Risk Score',
        compute='_compute_risk_score',
        store=True,
    )

    po_id = fields.Many2one('invoicing.po', string ='Purchase Order')

    invoicing_frequency = fields.Selection([
        ('month', 'Month'),
        ('trimester', 'Trimester'),
        ('milestone', 'Milestone')],
        default =lambda self: self.partner_id.invoicing_frequency,
    )
    
    
    invoice_template = fields.Many2one('ir.actions.report', domain=[('model', '=', 'account.invoice')])
    activity_report_template = fields.Many2one(
        'ir.actions.report',
        default=lambda self: self.get_activity_report_template())
    communication_rate = fields.Selection([
        ('0.0', '0%'),
        ('0.005', '0.5%'),
        ('0.01', '1%'),
        ('0.015', '1.5%'),
        ('0.02', '2%'),
        ('0.025', '2.5%'),
        ('0.03', '3%'),
    ], 'Communication Rate', default='0.0')

    financial_config_readonly = fields.Boolean(
        compute='compute_financial_config_readonly',
        store=False,
        )

    invoiceable_amount = fields.Monetary(
        compute="_compute_invoiceable_amount",
        store=True,
    )

    pc_id = fields.Many2one(
        'res.users',
        string = 'PC',
        related = 'partner_id.controller_id'
    )

    lc_id = fields.Many2one(
        'hr.employee',
        string = 'LC',
        related = 'core_team_id.lead_consultant',
    )

    merge_subtask = fields.Boolean(default=True)

    invoicing_comment = fields.Text()

    invoice_admin_id = fields.Many2one(
        'res.users',
        compute='_compute_invoice_admin_id_from_partner_id',
        store=True,
    )

    @api.depends('partner_id.invoice_admin_id')
    def _compute_invoice_admin_id_from_partner_id(self):
        for rec in self:
            rec.invoice_admin_id = rec.partner_id.invoice_admin_id

    @api.depends('order_line','order_line.untaxed_amount_to_invoice','order_line.qty_invoiced')
    def _compute_invoiceable_amount(self):
        self = self.sudo()
        _logger.info("vcls-invoicing | _compute_invoiceable_amount {}".format(self.mapped('name')))
        for so in self:
            #if the so has child, then we add child invoiceable amount to the total
            so.invoiceable_amount = sum(so.order_line.mapped('untaxed_amount_to_invoice')) + sum(so.child_ids.mapped('invoiceable_amount'))
            #if there's a parent, then we trigger the recompute
            if so.parent_id:
                so.parent_id._compute_invoiceable_amount()

    @api.depends('partner_id.risk_ids')
    def _compute_risk_ids(self):
        resourceSo = "sale.order,{}".format(self.id)
        risk_ids = self.env['risk'].search([('resource', '=', resourceSo)])
        if self.partner_id:
            resourcePrtn = "res.partner,{}".format(self.partner_id.id)
            risk_ids |= self.env['risk'].search([('resource', '=', resourcePrtn)])
        if risk_ids:
            self.risk_ids |= risk_ids

    @api.one
    @api.depends('project_id.user_id','partner_id.invoice_admin_id', 'parent_id')
    def compute_financial_config_readonly(self):
        self.financial_config_readonly =((self.project_id.user_id == self.env.user) or\
                                        (self.partner_id.invoice_admin_id == self.env.user) or\
                                        (self.partner_id.user_id == self.env.user) or\
                                        (self.env.user.has_group('vcls_security.group_project_controller'))) and not self.parent_id


    def action_risk(self):
        view_ids = [self.env.ref('vcls-risk.view_risk_tree').id,
                    self.env.ref('vcls-risk.view_risk_kanban').id, 
                    self.env.ref('vcls-risk.view_risk_form').id ]

        return {
            'name': 'All Risks',
            'view_type': 'form',
            'view_mode': 'tree,kanban,form',
            'view_ids': view_ids,
            'target': 'current',
            'res_model': 'risk',
            'type': 'ir.actions.act_window',
            'context': {'search_default_id':self.risk_ids.ids,},
        } 

    def check_risk(self):
        risk_company = self.env.ref('vcls-invoicing.non_standard_company', raise_if_not_found=False) or False
        risk_rate = self.env.ref('vcls-invoicing.non_standard_rates', raise_if_not_found=False) or False

        for so in self:

            resource = "sale.order,{}".format(so.id)

            if so.company_id:
                if so.company_id != self.env.ref('vcls-hr.company_VCFR'):
                    existing = self.env['risk'].search([
                        ('resource', '=', resource),
                        ('risk_type_id', '=', risk_company.id)
                    ])
                    if not existing:
                        so.risk_ids |= self.env['risk']._raise_risk(risk_company, resource)
            
            rates = so.order_line.filtered(lambda r: r.product_id.seniority_level_id)

            for rate in rates:
                std_price = rate.product_id.item_ids.filtered(lambda s: s.pricelist_id == so.pricelist_id)
                if std_price:
                    if rate.price_unit < std_price[0].fixed_price:
                        existing = self.env['risk'].search([('resource', '=', resource),('risk_type_id','=',risk_rate.id)])
                        if not existing:
                            so.risk_ids |= self.env['risk']._raise_risk(risk_rate, resource)
                        break
    
    @api.depends('risk_ids','risk_ids.score')
    def _compute_risk_score(self):
        for so in self:
            so.risk_score = sum(so.risk_ids.mapped('score'))

    @api.multi
    def write(self, vals):
        """
        Some fields have to be forced down to childs for the coherence of the invoicing
        """
        for rec in self:
            childs = vals.get('child_ids', False) or rec.child_ids
            if childs:
                params = ('invoicing_frequency', 'invoice_template', 'activity_report_template', 'communication_rate'
                          , 'pricelist_id')
                keys = ('invoicing_frequency', 'invoice_template', 'activity_report_template', 'communication_rate'
                        , 'pricelist_id')
                values = [vals.get(key) for key in params]
                dict_values = {keys[i]: values[i] for i in range(0, len(values)) if values[i]}
                if len(dict_values):
                        for child in childs:
                            super(SaleOrder, child).write(dict_values)
                            child.check_risk()
        result = super(SaleOrder, self).write(vals)
        self.check_risk()
        return result

    @api.model
    def create(self, vals):
        result = super(SaleOrder, self).create(vals)
        result.check_risk()
        result.get_partner_financial_config()
        return result
    
    @api.multi
    def _prepare_invoice(self):
        """
        We Extend the dictionnary for the invoice creation with VCLS customs.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        group_invoice_method = self._context.get('group_invoice_method','')
        if group_invoice_method == 'program':
            invoice_vals['invoice_is_program'] = True
        #project_info

        for vcls_type in self.mapped('order_line.product_id.vcls_type'):
            if vcls_type not in supported_vcls_types:
                raise UserError(_('The type: %s is no supported yet for the invoicing, please contact the Administrator') %vcls_type)

        #invoice period
        if self.timesheet_limit_date:
            invoice_vals['timesheet_limit_date'] = self.timesheet_limit_date
            if self.invoicing_frequency == 'month':
                invoice_vals['period_start'] = self.timesheet_limit_date.replace(day=1) #self.timesheet_limit_date + relativedelta(months=-1,days=1)
            elif self.invoicing_frequency == 'trimester':
                invoice_vals['period_start'] = self.timesheet_limit_date.replace(day=1) + relativedelta(months=-2) #self.timesheet_limit_date + relativedelta(months=-3,days=1)
            else:
                pass
        else:
            pass

        #related models
        if self.program_id:
            invoice_vals['program_id'] = self.program_id.id
        if self.po_id:
            invoice_vals['po_id'] = self.po_id.id
        if self.invoice_template:
            invoice_vals['invoice_template'] = self.invoice_template.id
        if self.activity_report_template:
            invoice_vals['activity_report_template'] = self.activity_report_template.id
        if self.payment_term_id:
            invoice_vals['payment_term_id'] = self.payment_term_id.id
        if self.fiscal_position_id:
            invoice_vals['fiscal_position_id'] = self.fiscal_position_id.id
        if self.analytic_account_id and not self.parent_id: #if this is the parent quotation
            invoice_vals['parent_analytic_account_id'] = self.analytic_account_id.id

        #other values
        invoice_vals['communication_rate'] = float(self.communication_rate)
        invoice_vals['merge_subtask'] = self.merge_subtask
        return invoice_vals

    @api.onchange('partner_id')
    def get_partner_financial_config(self):
        #We look for default values
        default_pterm = self.env['account.payment.term'].search([('name','ilike','30 days following the invoice receipt')],limit=1)
        default_inv_template = self.env.ref('vcls-invoicing.project_invoice_aggregated')


        self.invoicing_frequency = self.partner_id.invoicing_frequency
        self.invoice_template = self.partner_id.invoice_template or default_inv_template
        self.activity_report_template = self.partner_id.activity_report_template
        self.communication_rate = self.partner_id.communication_rate
        self.pricelist_id = self.partner_id.property_product_pricelist
        self.payment_term_id = self.partner_id.property_payment_term_id or default_pterm

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        invoices = super(SaleOrder, self).action_invoice_create(grouped, final)
        invoice_ids = self.env['account.invoice'].browse(invoices)
        orders_follower_ids = self.mapped('message_follower_ids.partner_id')
        if orders_follower_ids:
            for invoice in invoice_ids:
                invoice._message_subscribe(partner_ids=orders_follower_ids.ids)
        return invoices
    
    @api.multi
    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('vcls-invoicing.view_invoice_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
