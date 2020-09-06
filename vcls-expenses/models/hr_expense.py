# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


import logging
_logger = logging.getLogger(__name__)


class HrExpense(models.Model):

    _inherit = "hr.expense"

    #account_id = fields.Many2one(default=lambda self: self._default_account_id())
    account_id = fields.Many2one()
    is_product_employee = fields.Boolean(related='product_id.is_product_employee', readonly=True, string="Product Employee")


    product_list = fields.Char(
        store = False,
        compute = '_get_product_list',
    )

    company_id = fields.Many2one(
        'res.company',
        related='sheet_id.company_id',)

    project_id = fields.Many2one(
        'project.project', 
        related='sheet_id.project_id',
    )

    """@api.model
    def _default_account_id(self):
        return False"""

    @api.onchange('product_id')
    def _onchange_product_id_account(self):
        self.account_id = self.product_id\
            .with_context(force_company=self.company_id.id)\
            .property_account_expense_id.id or \
            self.product_id.categ_id.with_context(force_company=self.company_id.id)\
                .property_account_expense_categ_id

    @api.model
    def _setup_fields(self):
        super(HrExpense, self)._setup_fields()
        self._fields['unit_amount'].states = None
        self._fields['unit_amount'].readonly = False
        self._fields['product_uom_id'].readonly = True

    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('vcls-expenses', 'action_attachment_expense')
        res['domain'] = [('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense', 'default_res_id': self.id}
        res['view_mode'] = 'form'
        res['view_id'] = self.env.ref('vcls-expenses.view_hr_expense_attachment')
        res['target'] = 'new'
        return res

    @api.multi
    def action_move_create(self):
        expenses_by_company = {}
        for expense in self:
            expenses_by_company.setdefault(expense.company_id, self.env["hr.expense"])
            expenses_by_company[expense.company_id] |= expense
        results = {}
        for company, groupped_expenses in expenses_by_company.items():
            result = super(HrExpense, groupped_expenses.with_context(
                force_company=company.id,
                default_company_id=company.id,
            )).action_move_create()
            results.update(result)
        return results

    @api.multi
    def _prepare_move_values(self):
        move_values = super(HrExpense, self)._prepare_move_values()
        move_values['company_id'] = self.sheet_id.company_id.id or move_values['company_id']
        return move_values

    @api.constrains('company_id', 'sheet_id.company_id')
    def _check_expenses_same_company(self):
        for expense in self:
            if not expense.sheet_id or not expense.company_id:
                continue
            if expense.sheet_id.company_id != expense.company_id:
                raise ValidationError(
                    _('Error! Expense company must be the same as the report company.'))
            if expense.account_id.company_id != expense.company_id:
                raise ValidationError(
                    _('Error! Expense company must be the same as the account company.'))

    @api.multi
    def open_pop_up_line(self):
        self.ensure_one()
        action = self.env.ref('vcls-expenses.action_pop_up_add_expense').read()[0]
        action.update({
            'res_id': self.id,
            'flags': {'mode': 'readonly'},
            'context': {'create': False},
        })
        return action
    
    @api.model
    def create(self, vals):

        expense = super(HrExpense, self).create(vals)
        if expense.project_id:
            if 'Mobility' in expense.project_id.name:
                expense.payment_mode = 'company_account'
            else:
                pass
        else:
            pass
            
        return expense

    @api.multi
    def write(self, vals):
        #_logger.info("EXP WRITE {}".format(vals))
        for exp in self:
            if vals.get('project_id', exp.project_id.id):
                project = self.env['project.project'].browse(vals.get('project_id', exp.project_id.id))
                if 'Mobility' in project.name:
                    vals['payment_mode'] = 'company_account'

        return super(HrExpense, self).write(vals)

    @api.multi
    def action_move_create(self):
        """
        We did not change the original _get_account_move_line_values because payments are generated from those lines
        """
        move_group_by_sheet = self._get_account_move_by_sheet()

        move_line_values_by_expense = self._get_account_move_line_values()

        for expense in self:
            company_currency = expense.company_id.currency_id
            different_currency = expense.currency_id != company_currency

            # get the account move of the related sheet
            move = move_group_by_sheet[expense.sheet_id.id]

            # get move line values
            move_line_values = move_line_values_by_expense.get(expense.id)
            move_line_dst = move_line_values[-1]
            total_amount = move_line_dst['debit'] or -move_line_dst['credit']
            total_amount_currency = move_line_dst['amount_currency']

            # create one more move line, a counterline for the total on payable account
            if expense.payment_mode == 'company_account':
                journal = expense.sheet_id.bank_journal_id
                if not journal.default_credit_account_id:
                    raise UserError(_("No credit account found for the %s journal, please configure one.") % (journal.name))
                # create payment
                payment_methods = journal.outbound_payment_method_ids if total_amount < 0 else journal.inbound_payment_method_ids
                journal_currency = journal.currency_id or journal.company_id.currency_id
                payment = self.env['account.payment'].create({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': 'outbound' if total_amount < 0 else 'inbound',
                    'partner_id': expense.employee_id.address_home_id.commercial_partner_id.id,
                    'partner_type': 'supplier',
                    'journal_id': journal.id,
                    'payment_date': expense.date,
                    'state': 'reconciled',
                    'currency_id': expense.currency_id.id if different_currency else journal_currency.id,
                    'amount': abs(total_amount_currency) if different_currency else abs(total_amount),
                    'name': expense.name,
                })
                move_line_dst['payment_id'] = payment.id

            # link move lines to move, and move to expense sheet
            move.with_context(dont_create_taxes=True).write({
                'line_ids': [(0, 0, line) for line in move_line_values]
            })
            expense.sheet_id.write({'account_move_id': move.id})

            if expense.payment_mode == 'company_account':
                expense.sheet_id.paid_expense_sheets()

        # # # MODIFICATION # # #

        for expense_sheet_id, move in move_group_by_sheet.items():
            move_lines_to_aggregate = {}
            for line in move.line_ids:
                expense = line.expense_id
                # lists are not hashable : we need a tuple if we want to use as a key dictionary
                key = (line.account_id.id, tuple(line.tax_ids.ids), line.tax_line_id.id,
                       expense.currency_id.id, expense.payment_mode)
                if key not in move_lines_to_aggregate:
                    move_lines_to_aggregate[key] = line
                else:
                    move_lines_to_aggregate[key] |= line

            move_lines_to_aggregate = [lines for key, lines in move_lines_to_aggregate.items() if len(lines) > 1]
            for move_lines in move_lines_to_aggregate:
                move_line_to_keep = move_lines[0]
                move_lines_to_unlink = move_lines[1:]
                ml_vals = {
                    'name': ' - '.join(move_lines.mapped('name')),
                    'expense_ids': [(6, 0, move_lines.mapped('expense_id').ids)],
                    'payment_ids': [(6, 0, move_lines.mapped('payment_id').ids)],
                }
                for ml_field in ('debit', 'credit', 'amount_currency', 'quantity'):
                    ml_vals[ml_field] = getattr(move_line_to_keep, ml_field)
                    ml_vals[ml_field] += sum(move_lines_to_unlink.mapped(ml_field))
                move_line_to_keep.write(ml_vals)
                move_lines_to_unlink.unlink()

        # # # /MODIFICATION # # #

        # post the moves
        for move in move_group_by_sheet.values():
            move.post()

        return move_group_by_sheet
