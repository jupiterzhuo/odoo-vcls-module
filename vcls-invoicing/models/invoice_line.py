# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression

import logging
_logger = logging.getLogger(__name__)


class InvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    section_line_id = fields.Many2one(
        'account.invoice.line',
        string='Line section',
        compute='_get_section_line_id',
        store=False
    )

    @api.multi
    def _get_section_line_id(self):
        for line in self:
            invoice_line_ids = line.invoice_id.invoice_line_ids
            current_section_line_id = False
            for invoice_line_id in invoice_line_ids:
                if invoice_line_id.display_type == 'line_section':
                    current_section_line_id = invoice_line_id
                elif line == invoice_line_id:
                    line.section_line_id = current_section_line_id
                    break

    @api.model
    def create(self, values):
        result = super(InvoiceLine, self).create(values)
        if result.purchase_line_id and not result.purchase_line_id.is_rebilled:
            result.account_analytic_id = False
        return result

    @api.model
    def _timesheet_domain_get_invoiced_lines(self, sale_line_delivery):
        """
         We extend the domain to take in account the timesheet_limit date 
         as well as the vcls status of the timesheets.
         Take care to be aligned with the domain used to compute timesheet_ids at the sale.order model.
        """
        domain = super(InvoiceLine, self)._timesheet_domain_get_invoiced_lines(sale_line_delivery)
        #we get any of the timesheet limit dates of the so (all have to be the same)
        limit_date = None

        for line in sale_line_delivery:
            if line.order_id.timesheet_limit_date:
                limit_date = line.order_id.timesheet_limit_date
                break
        if limit_date:
            domain = expression.AND([domain, [('date', '<=', limit_date)]])
        domain = expression.AND([domain, [('stage_id', '=', 'invoiceable')]])
        #_logger.info("TS DOMAIN {}".format(domain))
        return domain
    
    """@api.multi
    def unlink(self):
        if self.filtered(lambda r: r.invoice_id and r.invoice_id.state != 'draft'):
            _logger.info("UNLINK INVOICE LINES {} {} {}".format(self.mapped('invoice_id.name'),self.mapped('invoice_id.state'),self.mapped('name')))
        return super(InvoiceLine, self).unlink()"""

    @api.multi
    def asset_generate(self, vals):
        self.ensure_one()
        if self.asset_category_id.open_asset and self.asset_category_id.date_first_depreciation == 'manual':
            # the asset will auto-confirm, so we need to set its date
            # since in this case the date will be readonly
            vals['first_depreciation_manual_date'] = self.invoice_id.date_invoice
        changed_vals = self.env['account.asset.asset'].onchange_category_id_values(vals['category_id'])
        vals.update(changed_vals['value'])
        asset = self.env['account.asset.asset'].create(vals)
        if self.asset_category_id.open_asset:
            asset.validate()

    @api.one
    def asset_create(self):
        """Overwrite native method.
        Generate one asset for each quantity on the invoice line, if the asset category is parametrized that way."""
        if self.asset_category_id:
            vals = {
                'name': self.name,
                'code': self.invoice_id.number or False,
                'category_id': self.asset_category_id.id,
                'partner_id': self.invoice_id.partner_id.id,
                'company_id': self.invoice_id.company_id.id,
                'currency_id': self.invoice_id.company_currency_id.id,
                'date': self.invoice_id.date_invoice,
                'invoice_id': self.invoice_id.id,
            }
            if self.asset_category_id.generate_multi_asset and self.quantity.is_integer():
                vals['value'] = self.price_subtotal_signed / self.quantity
                for __ in range(int(self.quantity)):
                    asset_vals = dict(vals)
                    self.asset_generate(asset_vals)
            else:
                vals['value'] = self.price_subtotal_signed
                self.asset_generate(vals)
        return True
