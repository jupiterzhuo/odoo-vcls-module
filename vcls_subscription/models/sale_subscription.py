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

    services = fields.Text(compute='_compute_services', store=True, readonly=True)

    @api.depends('recurring_invoice_line_ids')
    def _compute_services(self):
        for rec in self:
            tmp_str = ""
            for ids in rec.recurring_invoice_line_ids:
                tmp_str += ids.name + '\n'
            rec.services = tmp_str.rstrip()

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
                break_sub = False
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
                        
                        if len(so_line)!=1:
                            #there is a problem, we need to bypass this subscription
                            break_sub = True
                            _logger.info("SUB | Unable to process {} because no matching so line was found.".format(found.mapped('order_id.name')))
                            break

                        _logger.info("SUB | Adding {} on {} for {} in {}".format(line.quantity,so_line.qty_delivered,so_line.name,so_line.order_id.name)) 
                        _logger.info("SUB | Manual vs  Delivered Before {} {} Method {}".format(so_line.qty_delivered_manual,so_line.qty_delivered,so_line.qty_delivered_method))
                        so_line.qty_delivered += line.quantity
                        #so_line.qty_delivered = so_line.qty_delivered_manual
                        #so_line._inverse_qty_delivered() #we mimic the manual change of the delivered qty by calling the onchange method
                        _logger.info("SUB | Manual vs  Delivered After {} {}".format(so_line.qty_delivered_manual,so_line.qty_delivered))
                
                if break_sub:
                    continue

                next_date = sub.recurring_next_date or current_date
                periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                invoicing_period = relativedelta(**{periods[sub.recurring_rule_type]: sub.recurring_interval})
                new_date = next_date + invoicing_period
                sub.write({'recurring_next_date': new_date.strftime('%Y-%m-%d')})
    
    @api.model
    def clean_subs_delivery_method(self):
        #we look for lines beeing subscription but with a timesheet delivery method
        to_update = self.env['sale.order.line'].search([('vcls_type','=','subscription'),('qty_delivered_method','=','timesheet')])
        for line in to_update:
            _logger.info("BAD SUBS {} with {} {}".format(line.order_id.name,line.product_id.name,line.name))
        if to_update:
            to_update.write({
                'qty_delivered_method':'manual',
            })

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, qty):
        """
        Override to add subscription-specific behaviors.

        Display the invoicing period in the invoice line description, link the invoice line to the
        correct subscription and to the subscription's analytic account if present.
        """
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        temp_name = res['name'].split('\nInvoicing period: ')[0]
        res.update(name=temp_name)
        if self.subscription_id:
            res.update(subscription_id=self.subscription_id.id)
            # In VCLS we invoice the previous period
            if self.order_id.subscription_management != 'upsell':
                periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                next_date = fields.Date.from_string(self.subscription_id.recurring_next_date) - relativedelta(**{periods[self.subscription_id.recurring_rule_type]: self.subscription_id.recurring_interval}) + relativedelta(months=+1)
                previous_date = next_date - relativedelta(**{periods[self.subscription_id.recurring_rule_type]: self.subscription_id.recurring_interval})
                lang = self.order_id.partner_invoice_id.lang
                format_date = self.env['ir.qweb.field.date'].with_context(lang=lang).value_to_html

                # Ugly workaround to display the description in the correct language
                if lang:
                    self = self.with_context(lang=lang)
                period_msg = _("Invoicing period: %s - %s") % (format_date(fields.Date.to_string(previous_date), {}), format_date(fields.Date.to_string(next_date - relativedelta(days=1)), {}))
                res.update(name=res['name'] + '\n' + period_msg)
            if self.subscription_id.analytic_account_id:
                res['account_analytic_id'] = self.subscription_id.analytic_account_id.id
        return res
