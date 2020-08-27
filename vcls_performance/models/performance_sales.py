# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class PerformanceSales(models.AbstractModel):
     _name = 'performance.sales'
     _description = 'Performance Sales'
     _inherit = 'performance.mixin'
    
     performance_type = fields.Selection(
          default = 'sales'
     )

     sale_profile = fields.Selection(
          selection=[
               ('new','NEW'),
               ('retained','RETAINED'),
               ('filtered','FILTERED OUT'),
          ],
          default = False,
          )



    