# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PerformanceSales(models.AbstractModel):
    _name = 'performance.sales'
    _description = 'Performance Sales'
    _inherit = 'performance.mixin'
    
    performance_type = fields.Selection(
         default = 'sales'
    )
    