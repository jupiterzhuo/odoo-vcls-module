# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from collections import OrderedDict
from odoo.tools import OrderedSet

from odoo.exceptions import UserError, ValidationError, Warning
import math

import logging
_logger = logging.getLogger(__name__)


class SaleReport(models.Model):

    _inherit = 'sale.report'

    expected_start_date = fields.Date(
        string="Expected Start Date",
    )

    expected_end_date = fields.Date(
        string="Expected End Date",
    )

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['expected_end_date'] = ",  s.expected_end_date as expected_end_date"
        fields['expected_start_date'] = ", s.expected_start_date as expected_start_date"

        groupby += ', s.expected_end_date'
        groupby += ', s.expected_start_date'

        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)