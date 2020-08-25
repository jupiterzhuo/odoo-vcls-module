# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'

    generate_multi_asset = fields.Boolean("Generate Multi Assets", default=True)
