# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _

import logging
_logger = logging.getLogger(__name__)


class Translation(models.Model):
    _inherit = 'ir.translation'

    @api.model
    def force_name_to_uk(self):
        to_update = self.search([('name','like',',name'),('lang','=','en_GB'),('res_id','!=',0)])
        for item in to_update:
            if item.source != item.value: #we find the case when the name has been updated and not the source
                _logger.info("TRANS to update {}<{}".format(item.source,item.value))