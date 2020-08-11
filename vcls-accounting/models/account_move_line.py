# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Move(models.Model):
    _inherit = 'account.move'

    period_end = fields.Date()
    origin = fields.Char()

    @api.multi
    def _get_source_info(self):
        for move in self:
            invoice = self.env['account.invoice'].search([('number','=',move.name)],limit=1)
            if invoice:
                move.period_end = invoice.timesheet_limit_date
                move.origin = invoice.origin


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    external_account = fields.Char(
        related = 'partner_id.external_account'
    )

    journal_code = fields.Char(
        related = 'journal_id.code'
    )

    account_code = fields.Char(
        related = 'account_id.code'
    )

    base_currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_base_currency',
        store=True)
    
    period_end = fields.Date(
        related = 'move_id.period_end',
    )

    origin = fields.Char(
        related = 'move_id.origin',
    )

    @api.depends('debit','credit')
    def _compute_base_currency(self):
        for rec in self:
            rec.base_currency_id = self.env.ref('base.EUR')
    
    convertion_rate = fields.Float(
        compute='_compute_base_values',
        store=True)

    debit_base_currency = fields.Monetary(
        default=0.0,
        currency_field='base_currency_id',
        readonly=True)
        
    credit_base_currency = fields.Monetary(
        default=0.0,
        currency_field='base_currency_id',
        readonly=True)

    active = fields.Boolean(default=True)

    @api.depends('debit','credit','company_currency_id')
    def _compute_base_values(self):
        for line in self.filtered(lambda l: l.debit>0 and l.company_currency_id):
            debit_conv = line.company_currency_id._convert(
                line.debit,
                self.env.ref('base.EUR'),
                self.env.user.company_id,
                line.date or fields.Datetime.now(),
            )
            line.convertion_rate = line.company_currency_id.rate
            line.debit_base_currency = debit_conv

        for line in self.filtered(lambda l: l.credit>0 and l.company_currency_id): 
            credit_conv = line.company_currency_id._convert(
                line.credit,
                self.env.ref('base.EUR'),
                self.env.user.company_id,
                line.date or fields.Datetime.now(),
            )
            line.convertion_rate = line.company_currency_id.rate
            line.credit_base_currency = credit_conv

    @api.depends('move_id.line_ids', 'move_id.line_ids.tax_line_id', 'move_id.line_ids.debit', 'move_id.line_ids.credit')
    def _compute_tax_base_amount(self):
        """The base lines have been deactivated (cf _create_tax_cash_basis_base_line),
        but we need to take them into account to compute the tax_base_amount """
        for move_line in self:
            if move_line.tax_line_id:
                base_lines = move_line.move_id.with_context(active_test=False).line_ids\
                    .filtered(lambda line: move_line.tax_line_id in line.tax_ids
                              and move_line.partner_id == line.partner_id)
                move_line.tax_base_amount = abs(sum(base_lines.mapped('balance')))
            else:
                move_line.tax_base_amount = 0


class Invoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_open(self):
        result = super(Invoice, self).action_invoice_open()
        #we edit the date of the moves with the period end account.move.line account.move
        for invoice in self:
            invoice.move_id.period_end = invoice.timesheet_limit_date
            invoice.move_id.origin = invoice.origin

        return result