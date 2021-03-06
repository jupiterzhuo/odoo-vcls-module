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
     sales_new_cumulative = fields.Monetary(readonly=True) #OK
     sales_retained_period = fields.Monetary(readonly=True) #OK
     sales_retained_cumulative = fields.Monetary(readonly=True) #OK
     sales_total_period = fields.Monetary(readonly=True) #OK
     sales_total_cumulative = fields.Monetary(readonly=True) #OK

     sales_count_new_period = fields.Integer(readonly=True) #OK
     sales_count_new_cumulative = fields.Integer(readonly=True) #OK
     sales_count_retained_period = fields.Integer(readonly=True) #OK
     sales_count_retained_cumulative = fields.Integer(readonly=True) #OK
     sales_count_total_period = fields.Integer(readonly=True) #OK
     sales_count_total_cumulative = fields.Integer(readonly=True) #OK

     #Realized Losses
     losses_new_period = fields.Monetary(readonly=True) #OK
     losses_new_cumulative = fields.Monetary(readonly=True) #OK
     losses_retained_period = fields.Monetary(readonly=True) #OK
     losses_retained_cumulative = fields.Monetary(readonly=True) #OK
     losses_total_period = fields.Monetary(readonly=True) #OK
     losses_total_cumulative = fields.Monetary(readonly=True) #OK

     losses_count_new_period = fields.Integer(readonly=True) #OK
     losses_count_new_cumulative = fields.Integer(readonly=True) #OK
     losses_count_retained_period = fields.Integer(readonly=True) #OK
     losses_count_retained_cumulative = fields.Integer(readonly=True) #OK
     losses_count_total_period = fields.Integer(readonly=True) #OK
     losses_count_total_cumulative = fields.Integer(readonly=True) #OK

     #ratios
     win_loss_count_new_period = fields.Float(readonly=True) #OK
     win_loss_count_new_cumulative = fields.Float(readonly=True) #OK
     win_loss_count_retained_period = fields.Float(readonly=True) #OK
     win_loss_count_retained_cumulative = fields.Float(readonly=True) #OK
     win_loss_count_total_period = fields.Float(readonly=True) #OK
     win_loss_count_total_cumulative = fields.Float(readonly=True) #OK

     win_loss_new_period = fields.Float(readonly=True) #OK
     win_loss_new_cumulative = fields.Float(readonly=True) #OK
     win_loss_retained_period = fields.Float(readonly=True) #OK
     win_loss_retained_cumulative = fields.Float(readonly=True) #OK
     win_loss_total_period = fields.Float(readonly=True) #OK
     win_loss_total_cumulative = fields.Float(readonly=True) #OK

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

     pipe_new_cumulative = fields.Monetary(readonly=True) #OK
     pipe_new_cumulative_weighted = fields.Monetary(readonly=True)  #OK
     pipe_retained_cumulative = fields.Monetary(readonly=True)  #OK
     pipe_retained_cumulative_weighted = fields.Monetary(readonly=True)  #OK
     pipe_total_cumulative = fields.Monetary(readonly=True)  #OK
     pipe_total_cumulative_weighted = fields.Monetary(readonly=True)  #OK
     pipe_count_new_cumulative = fields.Integer(readonly=True) #OK
     pipe_count_retained_cumulative = fields.Integer(readonly=True) #OK
     pipe_count_total_cumulative = fields.Integer(readonly=True) #OK

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
               
               new_sos = sos.filtered(lambda p: p.sale_profile=='new')
               retained_sos = sos.filtered(lambda p: p.sale_profile=='retained')
               _logger.info("PERF | Found {} SO in period {}\n{} NEW and {} RETAINED".format(len(sos),perf.date_start,len(new_sos),len(retained_sos)))

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
          c_fields = [
               'sales_new_cumulative',
               'sales_retained_cumulative',
               'sales_total_cumulative',
               'sales_count_new_cumulative',
               'sales_count_retained_cumulative',
               'sales_count_total_cumulative',
               'losses_new_cumulative',
               'losses_retained_cumulative',
               'losses_total_cumulative',
               'losses_count_new_cumulative',
               'losses_count_retained_cumulative',
               'losses_count_total_cumulative',
               'pipe_new_cumulative',
               'pipe_new_cumulative_weighted', 
               'pipe_retained_cumulative', 
               'pipe_retained_cumulative_weighted', 
               'pipe_total_cumulative', 
               'pipe_total_cumulative_weighted', 
               'pipe_count_new_cumulative',
               'pipe_count_retained_cumulative',
               'pipe_count_total_cumulative',
               ]
          
          p_fields = [f.replace('cumulative','period') for f in c_fields]

          ordered_perf = self.sorted(lambda p: (p.period_id.date_start,p.period_index))
          for perf in ordered_perf:
               _logger.info("PERF | Cumulative Sales Calculation | {}-{} index {}-{}".format(perf.period_id.name,perf.period_id.date_start,perf.period_index,perf.date_start))
               #prev_perfs = self.search([('period_id','=',perf.period_id.id),('period_index','<=',perf.period_index)])
               last_perf = self.search([('period_id','=',perf.period_id.id),('period_index','=',perf.period_index-1)],limit=1)
               if last_perf:
                    last_data = last_perf.read(c_fields)[0]
               else:
                    last_data = {field_name:0 for field_name in c_fields}
               current_data = perf.read(p_fields)[0]
               _logger.info("PERF | \nLast Data {}\nCurrent Data {}".format(last_data,current_data))

               vals = {}
               for field in c_fields:
                    vals.update({field: last_data[field] + current_data[field.replace('cumulative','period')]})
               
               _logger.info("PERF | New Values {}".format(vals))
               perf.write(vals)

               #ratios
               if (perf.sales_count_new_cumulative + perf.losses_new_cumulative) > 0:
                    perf.win_loss_count_new_cumulative = perf.sales_count_new_cumulative / (perf.sales_count_new_cumulative + perf.losses_count_new_cumulative)
                    perf.win_loss_new_cumulative = perf.sales_new_cumulative / (perf.sales_new_cumulative + perf.losses_new_cumulative)
               else:
                    perf.win_loss_count_new_cumulative = False
                    perf.win_loss_new_cumulative = False
               
               if (perf.sales_count_retained_cumulative + perf.losses_retained_cumulative) > 0:
                    perf.win_loss_count_retained_cumulative = perf.sales_count_retained_cumulative / (perf.sales_count_retained_cumulative + perf.losses_count_retained_cumulative)
                    perf.win_loss_retained_cumulative = perf.sales_retained_cumulative / (perf.sales_retained_cumulative + perf.losses_retained_cumulative)
               else:
                    perf.win_loss_count_retained_cumulative = False
                    perf.win_loss_retained_cumulative = False
               
               if  (perf.sales_total_cumulative + perf.losses_total_cumulative) > 0:
                    perf.win_loss_total_cumulative = perf.sales_total_cumulative / (perf.sales_total_cumulative + perf.losses_total_cumulative)
               else:
                    perf.win_loss_total_cumulative = False




                    





               



    