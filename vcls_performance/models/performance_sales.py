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
          for perf in self:
               #we get the relevant sale.order
               #sos = self.env['sale.order'].search([('company_id','=',perf.company_id),('opp_date_closed.date()','>=',perf.date_start),('opp_date_closed.date()','<=',perf.date_end)])
               sos = self.env['sale.order'].search([('company_id','=',perf.company_id.id),('opp_date_closed','>=',perf.date_start),('opp_date_closed','<=',perf.date_end)])
               _logger.info("PERF | Found {} SO in period {}".format(len(sos),perf.date_start))



    