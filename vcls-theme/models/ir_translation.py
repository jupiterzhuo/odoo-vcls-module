# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _

import logging
_logger = logging.getLogger(__name__)


class Translation(models.Model):
    _inherit = 'ir.translation'

    @api.model
    def force_name_to_uk(self):
        to_update = self.search([('name','like',',name'),('lang','=','en_GB'),('res_id','!=',0)])
        count = 0
        for item in to_update:
            count += 1
            if item.source != item.value: #we find the case when the name has been updated and not the source
                force_val = item.value
                #we get other related translations
                to_force = self.search([('name','=',item.name),('res_id','=',item.res_id)])
                _logger.info("TRANS update {}/{} | {} {} {} > {} {}".format(count, len(to_update),to_force.mapped('res_id'),to_force.mapped('source'),to_force.mapped('value'),item.res_id,item.value))
                to_force.write({
                    'source':item.value,
                    'value':item.value,
                })
                