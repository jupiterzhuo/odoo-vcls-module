# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

class PerformancePeriod(models.Model):
     _name = 'performance.period'
     _description = 'Performance Period'

     name = fields.Char()
     company_id = fields.Many2one(
          comodel_name = 'res.company'
     )
     date_start = fields.Date(required=True)
     date_end = fields.Date(required=True)

     objective_sales = fields.Integer()

     def _build_performances(self,type_model=False,delta_month=1):
          if not type_model:
               return
          else:
               perf_obj = self.env[type_model]

          for period in self:
               loop_date = period.date_start
               index = 0
               while loop_date < period.date_end:
                    p_date_end = loop_date + relativedelta(months=delta_month,days=-1)
                    #we check if already exists
                    existing = perf_obj.search([('period_id','=',period.id),('date_start','=',loop_date),('date_end','=',p_date_end)],limit=1)
                    if not existing:
                         new = perf_obj.create({
                              'period_id':period.id,
                              'date_start':loop_date,
                              'date_end':p_date_end,
                              'period_index':index,
                         })
                         _logger.info("PERF | {} created {} {} {}".format(type_model,new.date_start,new.date_end,new.period_index))
                    index +=1
                    loop_date += relativedelta(months=delta_month) 


class PerformanceMixin(models.AbstractModel):
     _name = 'performance.mixin'
     _description = 'Performance Mixin'
    
     name = fields.Char()
     period_id = fields.Many2one(
          comodel_name = 'performance.period',
          required = True,
          indexed = True,
     )
     company_id = fields.Many2one(
          comodel_name = 'res.company',
          related = 'period_id.company_id',
          store = True,
     )
     performance_type = fields.Selection(
          selection = [
               ('sales','Sales'),
               ('revenues','Revenues'),
          ]
     )

     date_start = fields.Date()
     date_end = fields.Date()

     period_index = fields.Integer()
     need_recompute = fields.Boolean(default=True)

     """@api.model
     def build_performances(self,period_id=False,frequency='monthly',performance_type=False):
          pass"""
    