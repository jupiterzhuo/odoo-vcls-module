# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import datetime
import traceback

from collections import Counter
from dateutil.relativedelta import relativedelta
from uuid import uuid4

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import format_date
from odoo.tools.safe_eval import safe_eval

from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    management_mode = fields.Selection([
        ('std', 'Standard'),
        ('deliver', 'Deliver in Source Order'),], 
        string="Management Mode",
        store=True,
        compute = '_compute_management_mode',
        help="Standard | Use the Odoo way of managing subscriptions.\nDeliver | No invoice is generated, but the quantity is delivered after each period.",
        )

    @api.depends('recurring_invoice_line_ids')
    def _compute_management_mode(self):
        for sub in self:
            product_policies = sub.recurring_invoice_line_ids.mapped('product_id.product_tmpl_id.service_policy')
            if list(set(product_policies)) == ['delivered_manual']: #if all products are in delivered_manual policy
                sub.management_mode='deliver'
            else:
                sub.management_mode='std'
            
            _logger.info("SUB | {} | {} | {}".format(sub.display_name,list(set(product_policies)),sub.management_mode))

    @api.multi
    def _recurring_create_invoice(self, automatic=False):
        #we initiate the list of subscriptions to be processed before to filter according to the management_mode
        current_date = datetime.date.today()

        if len(self) > 0:
            subscriptions = self
        else:
            domain = [('recurring_next_date', '<=', current_date),
                      '|', ('in_progress', '=', True), ('to_renew', '=', True)]
            subscriptions = self.search(domain)

        std_subs = subscriptions.filtered(lambda s: s.management_mode=='std')
        if std_subs:
            _logger.info("SUB | {} standard subscriptions to process.".format(len(std_subs)))
            super(SaleSubscription,std_subs)._recurring_create_invoice(automatic)

        deliver_subs = subscriptions.filtered(lambda s: s.management_mode=='deliver')
        if deliver_subs:
            _logger.info("SUB | {} deliver subscriptions to process.".format(len(deliver_subs)))
            for sub in deliver_subs:
                #we find related so_lines
                so_lines = self.env['sale.order.line'].search([('subscription_id','=',sub.id)])
                _logger.info("SUB | Found SO lines {} related to {}".format(so_lines.mapped('name'),sub.display_name))
                for line in sub.recurring_invoice_line_ids:
                    #we get the related so_line
                    found = so_lines.filtered(lambda s: s.product_id == line.product_id)
                    if found:
                        if len(found)>1: #if several lines related to the same product, we try to match the name
                            so_line = found.filtered(lambda n: n.name == line.name)
                        else:
                            so_line = found
                        _logger.info("SUB | Adding {} on {} for {} in {}".format(line.quantity,so_line.qty_delivered,so_line.name,so_line.order_id.name))
                        so_line.qty_delivered += line.quantity

                next_date = sub.recurring_next_date or current_date
                periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                invoicing_period = relativedelta(**{periods[sub.recurring_rule_type]: sub.recurring_interval})
                new_date = next_date + invoicing_period
                sub.write({'recurring_next_date': new_date.strftime('%Y-%m-%d')})