# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)


class LeadQuotation(models.TransientModel):
    _name = 'tool.timesheet.recode'
    _description = 'Timesheet Recoder'

    mode = fields.Selection([
        ('replace_rate', 'Replace Rate'),
    ], string='Recompute Mode', required=True, default='replace_rate',
    help="""
    Replace Rate:
    - Update all non-invoiced timesheets from Source Rate to Target Rate
    - Update the mapping table accordingly
    """
    )

    include_childs = fields.Boolean(
        default=True,
    )

    info = fields.Text()

    ### SOURCE FIELDS

    source_project_id = fields.Many2one(
        comodel_name='project.project',
        string= 'Source Project',
    )

    """source_task_id = fields.Many2one(
        comodel_name='project.task',
        string= 'Source Task',
    )"""

    source_rate_id = fields.Many2one(
        comodel_name='sale.order.line',
        string= 'Source Rate',
    ) 

    ### TARGET FIELDS
    target_rate_id = fields.Many2one(
        comodel_name='sale.order.line',
        string= 'Target Rate',
    )

    ### TOOL FIELDS
    rate_ids = fields.Many2many(
        comodel_name='sale.order.line',
        compute='_compute_rate_ids',
    ) 

    @api.depends('source_project_id','include_childs')
    def _compute_rate_ids(self):
        for item in self.filtered(lambda l: l.source_project_id):
            if item.include_childs:
                projects = item.source_project_id | item.source_project_id.child_id
            else:
                projects = item.source_project_id
            
            rates = self.env['sale.order.line']
            for so in projects.mapped('sale_order_id'):
                rate_lines = so.order_line.filtered(lambda r: r.vcls_type == 'rate')
                if rate_lines:
                    rates |= rate_lines
            if rates:
                item.rate_ids = rates




    @api.multi
    def run(self):
        self.ensure_one()
        self.info("RAN")
        self.run_date = fields.Datetime.now()
