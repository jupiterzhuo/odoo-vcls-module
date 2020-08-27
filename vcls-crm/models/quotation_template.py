# -*- coding: utf-8 -*-

from typing import Sequence
from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError

class QuotationTemplate(models.Model):

    _inherit = 'sale.order.template'

    sequence = fields.Integer()



class QuotationTemplateLine(models.Model):

    _inherit = 'sale.order.template.line'

