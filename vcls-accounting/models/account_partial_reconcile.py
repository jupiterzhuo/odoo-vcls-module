# -*- coding: utf-8 -*-

from odoo import models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _create_tax_cash_basis_base_line(self, amount_dict, amount_currency_dict, new_move):
        """Inactive those lines, so they do not appear on the account move, or on the tax report"""
        for key in amount_dict.keys():
            base_line = self._get_tax_cash_basis_base_common_vals(key, new_move)
            currency_id = base_line.get('currency_id', False)
            rounded_amt = amount_dict[key]
            amount_currency = amount_currency_dict[key] if currency_id else 0.0
            aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
            aml_obj.create(dict(
                base_line,
                debit=rounded_amt > 0 and rounded_amt or 0.0,
                credit=rounded_amt < 0 and abs(rounded_amt) or 0.0,
                amount_currency=amount_currency,
                active=False))
            aml_obj.create(dict(
                base_line,
                credit=rounded_amt > 0 and rounded_amt or 0.0,
                debit=rounded_amt < 0 and abs(rounded_amt) or 0.0,
                amount_currency=-amount_currency,
                tax_ids=[],
                active=False))
