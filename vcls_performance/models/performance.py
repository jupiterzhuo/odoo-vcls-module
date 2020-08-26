# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PerformancePeriod(models.Model):
     _name = 'performance.period'
     _description = 'Performance Period'

     name = fields.Char()
     company_id = fields.Many2one(
          comodel_name = 'res.company'
     )
     date_start = fields.Date()
     date_end = fields.Date()

class PerformanceMixin(models.AbstractModel):
    _name = 'performance.mixin'
    _description = 'Performance Mixin'
    
    name = fields.Char()
    period_id = fields.Many2one(
         comodel_name = 'performance.period',
         required = True,
         indexed = True,
    )
    performance_type = fields.Selection(
         selection = [
              ('sales','Sales'),
              ('revenues','Revenues'),
         ]
    )
    