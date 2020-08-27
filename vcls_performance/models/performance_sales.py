# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class PerformanceSales(models.Model):
     _name = 'performance.sales'
     _description = 'Performance Sales'
     _inherit = 'performance.mixin'

     currency_id = fields.Many2one(
          comodel_name = 'res.currency',
          readonly = True,
     )

     #Objectives
     sales_objective_period = fields.Monetary()
     sales_objective_cumulative = fields.Monetary(
          compute = '_compute_sales_objective_cumulative',
          store = True,
     )

     @api.depends('sales_objective_period')
     def _compute_sales_objective_cumulative(self):
          for perf in self:
               perf.sales_objective_cumulative = perf.sales_objective_period*(perf.period_index+1)

     #Realized Sales
     sales_new_period = fields.Monetary(readonly=True)
     sales_new_cumulative = fields.Monetary(readonly=True)
     sales_retained_period = fields.Monetary(readonly=True)
     sales_retained_cumulative = fields.Monetary(readonly=True)
     sales_total_period = fields.Monetary(readonly=True)
     sales_total_cumulative = fields.Monetary(readonly=True)

     sales_count_new_period = fields.Integer(readonly=True)
     sales_count_new_cumulative = fields.Integer(readonly=True)
     sales_count_retained_period = fields.Integer(readonly=True)
     sales_count_retained_cumulative = fields.Integer(readonly=True)
     sales_count_total_period = fields.Integer(readonly=True)
     sales_count_total_cumulative = fields.Integer(readonly=True)

     #Realized Losses
     losses_new_period = fields.Monetary(readonly=True)
     losses_new_cumulative = fields.Monetary(readonly=True)
     losses_retained_period = fields.Monetary(readonly=True)
     losses_retained_cumulative = fields.Monetary(readonly=True)
     losses_total_period = fields.Monetary(readonly=True)
     losses_total_cumulative = fields.Monetary(readonly=True)

     losses_count_new_period = fields.Integer(readonly=True)
     losses_count_new_cumulative = fields.Integer(readonly=True)
     losses_count_retained_period = fields.Integer(readonly=True)
     losses_count_retained_cumulative = fields.Integer(readonly=True)
     losses_count_total_period = fields.Integer(readonly=True)
     losses_count_total_cumulative = fields.Integer(readonly=True)

     #ratios
     win_loss_new_period = fields.Float(readonly=True)
     win_loss_new_cumulative = fields.Float(readonly=True)
     win_loss_retained_period = fields.Float(readonly=True)
     win_loss_retained_cumulative = fields.Float(readonly=True)
     win_loss_total_period = fields.Float(readonly=True)
     win_loss_total_cumulative = fields.Float(readonly=True)

     #active snapshot
     active_new = fields.Integer(readonly=True)
     active_retained = fields.Integer(readonly=True)
     active_total = fields.Integer(readonly=True)

     def _compute_period_sales(self):
          #today = date.today()
          for perf in self:
               #we get the relevant sale.order
               sos = self.env['sale.order'].search([
                    ('company_id','=',perf.company_id.id),
                    ('sales_reporting_date','>=',perf.date_start),
                    ('sales_reporting_date','<=',perf.date_end),
                    ('sale_status','not in',['cancel'])])
               _logger.info("PERF | Found {} SO in period {}".format(len(sos),perf.date_start))

               new_sos = sos.filtered(lambda p: p.sale_status=='new')
               retained_sos = sos.filtered(lambda p: p.sale_status=='retained')

               perf.sales_new_period = sum(new_sos.filtered(lambda s: s.sale_status == 'won').mapped('converted_untaxed_amount'))
               perf.sales_retained_period = sum(retained_sos.filtered(lambda s: s.sale_status == 'won').mapped('converted_untaxed_amount'))
               perf.sales_total_period  = perf.sales_new_period + perf.sales_retained_period

               perf.sales_count_new_period = len(new_sos.filtered(lambda s: s.sale_status == 'won'))
               perf.sales_count_retained_period = len(retained_sos.filtered(lambda s: s.sale_status == 'won'))
               perf.sales_count_total_period  = perf.sales_count_new_period + perf.sales_count_retained_period

               perf.losses_new_period = sum(new_sos.filtered(lambda s: s.sale_status == 'lost').mapped('converted_untaxed_amount'))
               perf.losses_retained_period = sum(retained_sos.filtered(lambda s: s.sale_status == 'lost').mapped('converted_untaxed_amount'))
               perf.losses_total_period  = perf.losses_new_period + perf.losses_retained_period

               perf.losses_count_new_period = len(new_sos.filtered(lambda s: s.sale_status == 'lost'))
               perf.losses_count_retained_period = len(retained_sos.filtered(lambda s: s.sale_status == 'lost'))
               perf.losses_count_total_period  = perf.losses_count_new_period + perf.losses_count_retained_period





               



    