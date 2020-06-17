# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class ProjectSummary(models.Model):
    _inherit = 'project.summary'

    valuation_ratio = fields.Float(string='Valuation Ratio')
    #valuation_ratio = fields.Float(compute='compute_valuation_ratio', string='Valuation Ratio', store=True)

    """ @api.multi
    @api.depends("project_id.valuation_ratio")
    def compute_valuation_ratio(self):
        for summary in self:
            summary.valuation_ratio = summary.project_id.valuation_ratio"""
