# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    # We compute as sudo consultant does not have access to invoices which is required when
    # he logs time from a task
    qty_invoiced = fields.Float(compute_sudo=True)

    vcls_type = fields.Selection(
        related='product_id.vcls_type',
        string="Vcls type",
    )

    ts_invoicing_mode = fields.Selection([('tm', 'T&M'),
                                          ('fp', 'fixed_price')],
                                         'Invoicing mode')

    # Override the default ordered quantity to be 0 when we order rates items
    product_uom_qty = fields.Float(
        default = 0,
        )

    def _timesheet_create_project(self):
        project = super(SaleOrderLine, self)._timesheet_create_project()
        project.update({'project_type': 'client'})
        return project

    #We override the line creation in order to link them with existing project
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        
        for line in lines:
            if (line.product_id.service_tracking in ['project_only', 'task_new_project']) and not line.product_id.project_template_id:
                line.project_id = line.order_id.project_id
        
        return lines

    

    