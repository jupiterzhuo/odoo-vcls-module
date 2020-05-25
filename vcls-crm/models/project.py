# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class Project(models.Model):

    _inherit = 'project.project'

    core_team_id = fields.Many2one(
        'core.team',
        related="sale_order_id.core_team_id",
        store=True
    )

    link_rates = fields.Boolean(
        default = True,
        help="If ticked, rates of the parent quotation will be copied to childs, and linked during the life of the projects",
    )

    @api.multi
    def core_team(self):
        self.ensure_one()
        if self.sale_order_id:
            return self.sale_order_id.core_team()
