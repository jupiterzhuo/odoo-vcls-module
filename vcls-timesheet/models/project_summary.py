# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class ProjectSummary(models.Model):
    _inherit = 'project.summary'

    # valuation_ratio = fields.Float('Valuation Ratio')
    # valuation_ratio = fields.Many2one(related='project_id.valuation_ratio', string='Valuation Ratio')
    # valuation_ratio = fields.Many2one('project.project', related='project_id.valuation_ratio', string='Valuation Ratio')


    valuation_ratio = fields.Float(string='Valuation Ratio', store=True, related='project_id.valuation_ratio')
    maximum_rate = fields.Float(default=100)