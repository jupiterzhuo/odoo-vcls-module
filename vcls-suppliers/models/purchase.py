# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    approver_id = fields.Many2one(
        'res.users',
        string='Approver'
        )

class Company(models.Model):
    _inherit = 'res.company'

    supplier_approver_id = fields.Many2one(
        'res.users',
        string='Supplier Approver'
        )


class Invoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('partner_id')
    def _part_change(self):
        inv_type = self.type or self.env.context.get('type', 'out_invoice')

        if inv_type in ('in_invoice', 'in_refund'):
            if self.partner_id:
                if self.company_id != self.partner_id.company_id:
                    self.company_id = self.partner_id.company_id
                if self.partner_id.default_currency_id:
                    self.currency_id = self.partner_id.default_currency_id

    @api.onchange('company_id')
    def vcls_onchange(self):
        context = self.env.context
        if not context.get('journal_id') and context.get('type',self.type) in ['in_invoice', 'in_refund']:
        #if not self.env.context.get('journal_id') and self.partner_id and self.type in ['in_invoice', 'in_refund']:
            _logger.info("SUP INVOICE journal undefined")
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
            ]
            default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                self.journal_id = default_journal_id
        else:
            #self.journal_id = context.get('journal_id')
            _logger.info("SUP INVOICE journal defined {}".format(self.journal_id))

        for invoice_line in self.invoice_line_ids:
            _logger.info("SUP INVOICE LINE {}".format(invoice_line.name))
            invoice_line = invoice_line.with_context(
                default_company_id=self.company_id.id,
                force_company=self.company_id.id
            )
            fpos = self.fiscal_position_id
            company = self.company_id
            type = self.type
            product = invoice_line.product_id

            account = invoice_line.get_invoice_line_account(type, product, fpos, company)
            if account:
                invoice_line.account_id = account.id
            else:
                invoice_line.account_id = False

            invoice_line._set_taxes()

    @api.onchange('journal_id')
    def _get_company_currency(self):
        invoice_type = self.type or self.env.context.get('type', 'out_invoice')
        if invoice_type in ('in_invoice', 'in_refund'):
            if self.journal_id and self.journal_id.company_id.currency_id:
                self.currency_id = self.partner_id.currency_id or self.journal_id.currency_id.id or self.journal_id.company_id.currency_id.id

    @api.multi
    def action_purchase_approval(self):
        for invoice in self:
            activity_type = self.env['mail.activity.type'].search([('name', '=', 'Invoice Review')], limit=1)
            if activity_type:
                users_to_notify = self.env['res.users']

                for invoice_line in invoice.invoice_line_ids:
                    if invoice_line.account_analytic_id.project_ids and invoice_line.account_analytic_id.project_ids.user_id:
                        users_to_notify |= invoice_line.account_analytic_id.project_ids.mapped('user_id')
                    elif invoice_line.company_id.supplier_approver_id:
                        users_to_notify |= invoice_line.company_id.mapped('supplier_approver_id')
                    elif invoice_line.account_analytic_id.approver_id:
                        users_to_notify |= invoice_line.account_analytic_id.mapped('approver_id')
                    else:
                        raise UserError('No one is eligible to approve this: {}'.format(invoice_line.name))
                
                _logger.info("Users to notify {}".format(users_to_notify.mapped('name')))
                invoice.write({'ready_for_approval': True})

                for user in users_to_notify:
                    self.env['mail.activity'].create({
                        'res_id': invoice.id,
                        'res_model_id': self.env.ref('account.model_account_invoice').id,
                        'activity_type_id': activity_type.id,
                        'user_id': user.id,
                        'summary': ('Please review the invoice PDF for {}.').format(
                            invoice.name),
                    })

class PurchaseOrder(models.Model):

    _inherit = 'purchase.order'

    ####################
    # OVERRIDEN FIELDS #
    ####################

    company_id = fields.Many2one(
        string = 'Trading Entity',
        default = lambda self: self.env.ref('vcls-hr.company_VCFR'),
        )

    #################
    # CUSTOM FIELDS #
    #################

    expertise_id = fields.Many2many(
        'expertise.area',
        string="Area of Expertise",
    )

    deliverable_ids = fields.Many2many(
        'product.deliverable',
    )

    access_level = fields.Selection([
        ('rm', 'Resource Manager'),
        ('lc', 'Lead Consultant'),], 
        compute='_get_access_level',
        store=False,
        default='lc',)

    supplier_stage = fields.Selection(
        related='partner_id.stage',
        readonly=True,
    )

    scope_of_work = fields.Html(
        string="Scope of Work"
    )

    default_rate_id = fields.Many2one(
        comodel_name = 'product.template',
        domain = "[('vcls_type','=','rate')]",
        compute = '_compute_default_rate_id',
        store = True,
    )

    ###################
    # COMPUTE METHODS #
    ###################
    @api.depends('partner_id')
    def _compute_default_rate_id(self):
        for purchase in self:
            #we search for an employee, having a user linked to the partner_id
            ext_employee = self.env['hr.employee'].search([('user_id.partner_id','=',purchase.partner_id.id)],limit=1)
            if ext_employee.default_rate_ids:
                purchase.default_rate_id = ext_employee.default_rate_ids[0]

    @api.multi
    def _get_access_level(self):
        user = self.env['res.users'].browse(self._uid)

        for rec in self:           
            #if rm
            if user.has_group('vcls-suppliers.vcls_group_rm'):
                rec.access_level = 'rm'
                continue
