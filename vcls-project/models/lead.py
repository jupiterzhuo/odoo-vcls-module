# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api


class Lead(models.Model):
    _inherit = 'crm.lead'

    program_id = fields.Many2one(
        comodel_name='project.program',
        string='Related Program',
    )

    app_country_group_id = fields.Many2one(
        'res.country.group',
        string="Application Geographic Area",
        related='program_id.app_country_group_id',
        readonly=True
    )

    program_stage_id = fields.Selection([
        ('pre', 'Preclinical'),
        ('exploratory', 'Exploratory Clinical'),
        ('confirmatory', 'Confirmatory Clinical'),
        ('post', 'Post Marketing')],
        string='Program Stage',
    )

    product_name = fields.Char(
        string="Product Name",
        help='The client product name',
        related='program_id.product_name',
    )

    product_description = fields.Text(
        related="program_id.product_description",
    )

    program_info = fields.Text(
        related='program_id.program_info'
    )

    @api.onchange('program_id')
    def _onchange_program_id(self):
        self.program_stage_id = self.program_id.stage_id

    @api.multi
    def write(self, values):
        if values.get('active', None) is False:
            orders = self.mapped('order_ids')
            orders.write({'active': False})
        return super(Lead, self).write(values)
