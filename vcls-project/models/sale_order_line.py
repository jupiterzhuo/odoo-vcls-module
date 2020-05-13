from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    forecasted_amount = fields.Monetary(
        readonly = True,
        store = True,
        default = 0.0,
    )

    @api.onchange('name','price_unit')
    def _onchange_replicate(self):
        for line in self.filtered(lambda l: l.vcls_type=='rate' and not l.order_id.parent_id): #if this is a rate in a parent quotations
            _logger.info("Linked Rate Line Modification | {} {}".format(line.name,line.order_id.name))
            #we search for child quotations
            for child in line.order_id.child_ids.filtered(lambda c: c.link_rates):
                _logger.info("Linked Rate Child Found | {}".format(child.name))
                to_update = child.order_line.filtered(lambda f: f.product_id == line.product_id)
                if to_update:
                    _logger.info("Linked Rate Line Updated | {} {} linked to {} {}".format(to_update.name,to_update.order_id.name,line.name,line.order_id.name))
                    to_update.write({
                        'name':line.name,
                        'price_unit':line.price_unit,
                    })

    @api.onchange('product_id')
    def _onchange_product(self):
        for line in self:
            if line.product_id.seniority_level_id: #if there's a seniority level defined, it means this is a rate
                line.product_uom_qty = 0
    
    @api.multi
    def unlink(self):
        for line in self.filtered(lambda p: not p.order_id.parent_id and p.vcls_type == 'rate'):
            #we delete any linked rate product if we find it
            for child in line.order_id.child_ids.filtered(lambda c: c.link_rates):
                to_delete = child.order_line.filtered(lambda f: f.product_id == line.product_id)
                to_delete.unlink()
        super().unlink()

    
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.product_id.seniority_level_id: #if there's a seniority level defined, it means this is a rate
                line.product_uom_qty = 0
        
        to_replicate = lines.filtered(lambda p: not p.order_id.parent_id and p.vcls_type == 'rate') #if we create a rate line in a parent quotation
        update = self.prepare_linked_line(to_replicate,'create')
        for child in line.order_id.child_ids.filtered(lambda c: c.link_rates):
            child.order_line = update
            _logger.info("Linked Rate Line Creation | {} in {}".format(update,child.name))

        return lines

    def _timesheet_create_task_prepare_values(self, project):
        task_vals = super(SaleOrderLine, self)._timesheet_create_task_prepare_values(project)
        task_vals.update(completion_elligible=self.product_id.completion_elligible)
        return task_vals
    
    @api.multi
    def _compute_forecasted_amount(self):
        """
        This methods sums the total of forecast potential revenues.
        Triggered by the forecast write/create methods
        """
        for sol in self:
            forecasts = self.env['project.forecast'].search([('order_line_id','=',sol.id)])
            #_logger.info("Hours {} Rates {}".format(forecasts.mapped('resource_hours'),forecasts.mapped('hourly_rate')))
            total = 0.0
            for item in forecasts:
                total += item.resource_hours*item.hourly_rate
            sol.forecasted_amount = total

    def prepare_linked_line(self,source_lines=False,mode='create'):
        updated_lines = []
        if mode == 'create':
            for rl in source_lines:
                vals = {
                        'product_id':rl.product_id.id,
                        'name':rl.name,
                        'product_uom_qty':rl.product_uom_qty,
                        'product_uom':rl.product_uom.id,
                        'price_unit':rl.price_unit,
                    }
                updated_lines.append((0, 0, vals))

        return updated_lines



