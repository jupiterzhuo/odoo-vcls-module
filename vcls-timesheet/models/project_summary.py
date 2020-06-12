# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class ProjectSummary(models.Model):
    _inherit = 'project.summary'

    valuation_ratio = fields.Float(string='Valuation Ratio', store=True, related='project_id.valuation_ratio')