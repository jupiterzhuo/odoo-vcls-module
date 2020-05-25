from odoo import api, fields, models
from odoo.osv import expression


class Forecast(models.Model):

    _inherit = "project.forecast"

    product_name = fields.Char(
        compute = '_compute_product_name',
        store = True
    )

    

    @api.depends('employee_id')
    def _compute_product_name(self):
        for record in self:
            product = self.env['product.product'].search([('forecast_employee_id', '=', record.employee_id.id)], limit = 1)
            if product:
                record.product_name = product.name
            else:
                record.product_name = None