# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    expense_ids = fields.Many2many('hr.expense', string="Expenses")
    payment_ids = fields.Many2many('account.payment', string="Payments")
