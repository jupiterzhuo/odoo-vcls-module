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
     sales_new_period = fields.Monetary(readonly=True) #OK
     sales_new_cumulative = fields.Monetary(readonly=True)
     sales_retained_period = fields.Monetary(readonly=True) #OK
     sales_retained_cumulative = fields.Monetary(readonly=True)
     sales_total_period = fields.Monetary(readonly=True) #OK
     sales_total_cumulative = fields.Monetary(readonly=True)

     sales_count_new_period = fields.Integer(readonly=True) #OK
     sales_count_new_cumulative = fields.Integer(readonly=True)
     sales_count_retained_period = fields.Integer(readonly=True) #OK
     sales_count_retained_cumulative = fields.Integer(readonly=True)
     sales_count_total_period = fields.Integer(readonly=True) #OK
     sales_count_total_cumulative = fields.Integer(readonly=True)

     #Realized Losses
     losses_new_period = fields.Monetary(readonly=True) #OK
     losses_new_cumulative = fields.Monetary(readonly=True)
     losses_retained_period = fields.Monetary(readonly=True) #OK
     losses_retained_cumulative = fields.Monetary(readonly=True)
     losses_total_period = fields.Monetary(readonly=True) #OK
     losses_total_cumulative = fields.Monetary(readonly=True)

     losses_count_new_period = fields.Integer(readonly=True) #OK
     losses_count_new_cumulative = fields.Integer(readonly=True)
     losses_count_retained_period = fields.Integer(readonly=True) #OK
     losses_count_retained_cumulative = fields.Integer(readonly=True)
     losses_count_total_period = fields.Integer(readonly=True) #OK
     losses_count_total_cumulative = fields.Integer(readonly=True)

     #ratios
     win_loss_count_new_period = fields.Float(readonly=True) #OK
     win_loss_count_new_cumulative = fields.Float(readonly=True)
     win_loss_count_retained_period = fields.Float(readonly=True) #OK
     win_loss_count_retained_cumulative = fields.Float(readonly=True)
     win_loss_count_total_period = fields.Float(readonly=True) #OK
     win_loss_count_total_cumulative = fields.Float(readonly=True)

     win_loss_new_period = fields.Float(readonly=True) #OK
     win_loss_new_cumulative = fields.Float(readonly=True)
     win_loss_retained_period = fields.Float(readonly=True) #OK
     win_loss_retained_cumulative = fields.Float(readonly=True)
     win_loss_total_period = fields.Float(readonly=True) #OK
     win_loss_total_cumulative = fields.Float(readonly=True)

     #pipeline
     pipe_new_period = fields.Monetary(readonly=True) #OK
     pipe_new_period_weighted = fields.Monetary(readonly=True) #OK
     pipe_retained_period = fields.Monetary(readonly=True) #OK
     pipe_retained_period_weighted = fields.Monetary(readonly=True) #OK
     pipe_total_period = fields.Monetary(readonly=True) #OK
     pipe_total_period_weighted = fields.Monetary(readonly=True) #OK
     pipe_count_new_period = fields.Integer(readonly=True) #OK
     pipe_count_retained_period = fields.Integer(readonly=True) #OK
     pipe_count_total_period = fields.Integer(readonly=True) #OK

     pipe_new_cumulative = fields.Monetary(readonly=True) 
     pipe_new_cumulative_weighted = fields.Monetary(readonly=True) 
     pipe_retained_cumulative = fields.Monetary(readonly=True) 
     pipe_retained_cumulative_weighted = fields.Monetary(readonly=True) 
     pipe_total_cumulative = fields.Monetary(readonly=True) 
     pipe_total_cumulative_weighted = fields.Monetary(readonly=True) 
     pipe_count_new_cumulative = fields.Integer(readonly=True)
     pipe_count_retained_cumulative = fields.Integer(readonly=True)
     pipe_count_total_cumulative = fields.Integer(readonly=True)

     #active snapshot
     active_count_new = fields.Integer(readonly=True) #OK
     active_count_retained = fields.Integer(readonly=True) #OK
     active_count_total = fields.Integer(readonly=True) #OK

     active_new = fields.Monetary(readonly=True) #OK
     active_retained = fields.Monetary(readonly=True) #OK
     active_total = fields.Monetary(readonly=True) #OK

     active_new_weighted = fields.Monetary(readonly=True) #OK
     active_retained_weighted = fields.Monetary(readonly=True) #OK
     active_total_weighted = fields.Monetary(readonly=True) #OK
 
     def _compute_active_snapshot(self):
          today = fields.Date.today()
          for perf in self.filtered(lambda p: p.date_start<=today and p.date_end>=today):
               open_sos = self.env['sale.order'].search([
                    ('company_id','=',perf.company_id.id),
                    ('sale_status','in',['draft','sent'])])
               
               perf.active_new = sum(open_sos.filtered(lambda s: s.sale_profile == 'new').mapped('converted_untaxed_amount'))
               perf.active_retained = sum(open_sos.filtered(lambda s: s.sale_profile == 'retained').mapped('converted_untaxed_amount'))
               perf.active_total = perf.active_new + perf.active_retained
               perf.active_count_new = len(open_sos.filtered(lambda s: s.sale_profile == 'new'))
               perf.active_count_retained = len(open_sos.filtered(lambda s: s.sale_profile == 'retained'))
               perf.active_count_total = perf.active_count_new + perf.active_count_retained

               perf.active_new_weighted = sum(open_sos.filtered(lambda s: s.sale_profile == 'new').mapped(lambda p: (p.converted_untaxed_amount*p.probability)/100))
               perf.active_retained_weighted = sum(open_sos.filtered(lambda s: s.sale_profile == 'retained').mapped(lambda p: (p.converted_untaxed_amount*p.probability)/100))
               perf.active_total_weighted = perf.active_new_weighted + perf.active_retained_weighted

     def _compute_period_sales(self):
          ordered_perf = self.sorted(lambda p: (p.period_id.date_start,p.period_index))
          for perf in ordered_perf:
               _logger.info("PERF | Period Sales Calculation | {}-{} index {}-{}".format(perf.period_id.name,perf.period_id.date_start,perf.period_index,perf.date_start))
               #we get the relevant sale.order
               sos = self.env['sale.order'].search([
                    ('company_id','=',perf.company_id.id),
                    ('sales_reporting_date','>=',perf.date_start),
                    ('sales_reporting_date','<=',perf.date_end),
                    ('sale_status','not in',['cancel'])])
               _logger.info("PERF | Found {} SO in period {}".format(len(sos),perf.date_start))

               new_sos = sos.filtered(lambda p: p.sale_profile=='new')
               retained_sos = sos.filtered(lambda p: p.sale_profile=='retained')

               #sales & losses
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

               #ratios
               if (perf.sales_count_new_period + perf.losses_new_period) > 0:
                    perf.win_loss_count_new_period = perf.sales_count_new_period / (perf.sales_count_new_period + perf.losses_count_new_period)
                    perf.win_loss_new_period = perf.sales_new_period / (perf.sales_new_period + perf.losses_new_period)
               else:
                    perf.win_loss_count_new_period = False
                    perf.win_loss_new_period = False
               
               if (perf.sales_count_retained_period + perf.losses_retained_period) > 0:
                    perf.win_loss_count_retained_period = perf.sales_count_retained_period / (perf.sales_count_retained_period + perf.losses_count_retained_period)
                    perf.win_loss_retained_period = perf.sales_retained_period / (perf.sales_retained_period + perf.losses_retained_period)
               else:
                    perf.win_loss_count_retained_period = False
                    perf.win_loss_retained_period = False
               
               if  (perf.sales_total_period + perf.losses_total_period) > 0:
                    perf.win_loss_total_period = perf.sales_total_period / (perf.sales_total_period + perf.losses_total_period)
               else:
                    perf.win_loss_total_period = False
               
               #pipeline
               perf.pipe_new_period = sum(new_sos.filtered(lambda s: s.sale_status in ['draft','sent']).mapped('converted_untaxed_amount'))
               perf.pipe_new_period_weighted = sum(new_sos.filtered(lambda s: s.sale_status in ['draft','sent']).mapped(lambda p: (p.converted_untaxed_amount*p.probability)/100))
               perf.pipe_count_new_period = len(new_sos.filtered(lambda s: s.sale_status in ['draft','sent']))

               perf.pipe_retained_period = sum(retained_sos.filtered(lambda s: s.sale_status in ['draft','sent']).mapped('converted_untaxed_amount'))
               perf.pipe_retained_period_weighted = sum(retained_sos.filtered(lambda s: s.sale_status in ['draft','sent']).mapped(lambda p: (p.converted_untaxed_amount*p.probability)/100))
               perf.pipe_count_retained_period = len(retained_sos.filtered(lambda s: s.sale_status in ['draft','sent']))

               perf.pipe_total_period = perf.pipe_new_period + perf.pipe_retained_period
               perf.pipe_total_period_weighted = perf.pipe_new_period_weighted + perf.pipe_retained_period_weighted
               perf.pipe_count_total_period = perf.pipe_count_new_period + perf.pipe_count_retained_period
     
     def _compute_cumulative_sales(self):
          #we order per period and index
          ordered_perf = self.sorted(lambda p: (p.period_id.date_start,p.period_index))
          for perf in ordered_perf:
               _logger.info("PERF | Cumulative Sales Calculation | {}-{} index {}-{}".format(perf.period_id.name,perf.period_id.date_start,perf.period_index,perf.date_start))


                    





               



    