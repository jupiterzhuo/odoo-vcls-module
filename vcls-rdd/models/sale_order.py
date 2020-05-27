# -*- coding: utf-8 -*-
# (C) 2019 Smile (<http://www.smile.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models, api


"""class CoreTeam(models.Model):
    _inherit = 'core.team'

    old_id = fields.Char(copy=False, readonly=True)

    @api.multi
    def write(self, vals):
        if isinstance(vals.get('consultant_ids'), int) and \
                self.env.user.context_data_integration:
            vals['consultant_ids'] = [(4, vals['consultant_ids'])]
        return super(CoreTeam, self).write(vals)"""


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    old_id = fields.Char("Old Id", copy=False, readonly=True)

    
