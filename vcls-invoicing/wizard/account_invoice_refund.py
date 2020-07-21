# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AccountInvoiceRefund(models.TransientModel):
    """Credit Notes"""

    _inherit = "account.invoice.refund"

    filter_refund = fields.Selection([
        ('refund', 'Create a draft credit note'), 
        ('cancel', 'Cancel: create credit note and reconcile'), 
        #('modify', 'Modify: create credit note, reconcile and create a new draft invoice') #we comment the modify case
        ],
        default='cancel', string='Credit Method', required=True, help='Choose how you want to credit this invoice. You cannot Modify and Cancel if the invoice is already reconciled')

    @api.multi
    def compute_refund(self, mode='refund'):
        to_process = self.env['account.invoice'].browse(self._context.get('active_ids',False))
        ret = super().compute_refund(mode)
        if mode in ('cancel', 'modify'):
            #if cancel or modify, we release the potential timesheets and add the invoice ref to the so_line for a proper invoiced_qty calculation
            sale_lines = self.env['sale.order.line']
            for inv in to_process:
                _logger.info("INVOICE TO REFUND {}".format(inv.number))
                inv.release_timesheets()
                rinv = self.env['account.invoice'].search([('type','=','out_refund'),('origin','=',inv.number)],limit=1)
                rinv.write({'period_start':inv.period_start,'timesheet_limit_date':inv.timesheet_limit_date})
                if rinv:
                    _logger.info("Found Credit note {} for invoice {}".format(rinv.number,inv.number))
                    rinv.write({'period_start':inv.period_start,'timesheet_limit_date':inv.timesheet_limit_date})
                    for inv_line in inv.invoice_line_ids.filtered(lambda l: l.sale_line_ids and l.product_id):
                        rinv_line = rinv.invoice_line_ids.filtered(lambda r: r.product_id == inv_line.product_id)
                        if rinv_line:
                            _logger.info("Found Matching Line {} {} {} {}".format(inv_line.product_id.name,inv_line.quantity,rinv_line.product_id.name,rinv_line.quantity))
                            rinv_line.sale_line_ids = inv_line.sale_line_ids #we match the sale_order line behind to properly compute the invoiced qty afterwards
                            inv_line.sale_line_ids.write({
                                'invoice_lines':[(4, rinv_line.id, 0)],
                            })
                            sale_lines |= inv_line.sale_line_ids
            
            sale_lines._get_invoice_qty()

        return ret
