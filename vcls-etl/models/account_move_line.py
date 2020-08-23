# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    processed = fields.Boolean('Processed', default=False)