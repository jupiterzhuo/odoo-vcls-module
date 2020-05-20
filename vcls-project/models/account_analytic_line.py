from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):

    _inherit = 'sale.order'
    def add_product_with_specific_default_rate(self, employee):
        """Add any product with a specific seniority level ot the order."""
        any_product = self.env['product.product'].search(
            [('product_tmpl_id.id', '=', employee.default_rate_ids[0].id)],
            limit=1,
        )
        if not any_product:
            raise UserError(_('No product exists with this default product.'))
        so_line = self.sudo().order_line.create({
            'order_id': self.id,
            'product_id': any_product.id,
            'product_uom_qty': 0,
        })
        so_line.alert_salesman_new_product(employee)
        return so_line

class AccountAnalyticLine(models.Model):

    _inherit = 'account.analytic.line'

    @api.model
    def _update_project_soline_mapping(self, vals):
        #_logger.info("_update_project_soline_mapping {} ".format(vals))
        employee = None
        if 'employee_id' in vals:
            employee = self.env['hr.employee'].browse(vals['employee_id'])
        elif self.env.user.employee_ids:
            employee = self.env.user.employee_ids[0]
        if employee and 'project_id' in vals:
            project = self.env['project.project'].browse(vals['project_id'])
            so = project.sale_order_id
            list_default_rate = employee.default_rate_ids
            if all(not sol.product_id.seniority_level_id
                   for sol in so.order_line):
                # the sale order does not exist, or it does not use seniority
                # products at all -> don't enforce seniority on employee
                # use case : projects not related to a SO or totally fixed
                # price projects
                return
            if not employee.seniority_level_id:
                raise UserError(
                    _('''Employee with no seniority level can not timesheet
                         on project, contact your HR department.
                      ''')
                      
                )
            # Check for existing mapping in project configuration
            employee_mapped_line = project.sale_line_employee_ids.filtered(
                lambda r: r.employee_id.id == employee.id
            )
            if employee_mapped_line:
                # already mapped -> nothing to do
                return

            so_mapped_seniority = so.order_line.filtered(
                lambda r: r.product_id.seniority_level_id != False
            )
            # Find a line on the default rate list
            matched = False
            for so_line in so_mapped_seniority:
                so_product = so_line.product_id
                for default_rate in list_default_rate:
                    _logger.info("Product {} {} | Rate {} {}".format(so_product.product_tmpl_id.id,so_product.product_tmpl_id.name,default_rate.id,default_rate.name))
                    if so_product.product_tmpl_id.name == default_rate.name or so_product.seniority_level_id.code == '00': #we match on names to cover the case of multiproducts with the same name
                        matched = True 
                        _logger.info("FOUND Product {} {} | Rate {} {}".format(so_product.product_tmpl_id.id,so_product.product_tmpl_id.name,default_rate.id,default_rate.name))
                        break
                if matched:
                    break

            else:
                # no line found, Find a line on the sale order with the same seniority level
                for so_line in so_mapped_seniority:
                    line_seniority = so_line.product_id.seniority_level_id
                    _logger.info("SO LINE seniority {} for employee {}".format(line_seniority.name,employee.seniority_level_id.name))                    #we add the code 00 condition to cover the uniformized rate usecase (i.e. everyone to code with the same rate)
                    if line_seniority == employee.seniority_level_id:
                        break
                else:
                    # no line found, create the missing mapped line
                    so_line = so.add_product_with_specific_seniority_level(
                        employee)
            
            project.sudo().write(
                {
                    'sale_line_employee_ids': [
                        (
                            0,
                            False,
                            {
                                'employee_id': employee.id,
                                'sale_line_id': so_line.id,
                            },
                        )
                    ]
                }
            )
