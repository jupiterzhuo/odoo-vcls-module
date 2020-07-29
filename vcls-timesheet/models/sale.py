from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import datetime

import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    travel_invoicing_ratio = fields.Float(string="Travel Invoicing Ratio")
    is_migrated = fields.Boolean(compute = '_compute_is_migrated',store=True)
    fp_delivery_mode = fields.Selection(
        selection=[
        ('task', 'Task Completion'),
        ('manual', 'Manual')],
        string="Delivered Qty Method",
        default='task',
        )
    
    @api.depends('tag_ids')
    def _compute_is_migrated(self):
        for so in self:
            if ('Manual Migration' in so.tag_ids.mapped('name')) or ('Automated Migration' in so.tag_ids.mapped('name')):
                so.is_migrated = True
            else:
                so.is_migrated = False

    @api.multi
    def action_view_forecast(self):
        self.ensure_one()
        parent_project_id, child_ids = self._get_family_projects()
        action = self.env.ref('vcls-project.project_forecast_action').read()[0]
        action['domain'] = [('project_id', 'in', (parent_project_id | child_ids).ids)]
        action['context'] = {
            'active_id': self.id,
            'search_default_group_by_project_id': 1,
            'search_default_group_by_task_id': 1,
        }
        return action

    @api.multi
    def action_view_family_timesheet(self):
        self.ensure_one()
        action = self.env.ref('hr_timesheet.act_hr_timesheet_line_by_project').read()[0]
        parent_order_id, child_orders = self._get_family_sales_orders()
        all_orders = parent_order_id | child_orders
        action['domain'] = [('so_line', 'in', all_orders.mapped('order_line').ids)]
        return action

    @api.model
    def create(self, vals):
        result = super(SaleOrder, self).create(vals)
        result.first_quotation()
        return result

    def first_quotation(self):
        if self.opportunity_id:
            if self.opportunity_id.sale_number == 1 : 
                pre_project = self.env.ref('vcls-timesheet.default_project').id
                stage_id = self.env['project.task.type'].sudo().search([('name','=','0% Progress')], limit=1).id
                self.opportunity_id.task_id = self.env['project.task'].sudo().create({
                                                                                    'name':self.opportunity_id.name,
                                                                                    'project_id':pre_project, 
                                                                                    'stage_id':stage_id, 
                                                                                    'active':True}).id
    
    #We override the OCA to inject the stage domain
    
    @api.multi
    @api.depends('timesheet_limit_date')
    def _compute_timesheet_ids(self):
        _logger.info("TS PATH | vcls-timesheet | sale.order | _compute_timesheet_ids")
        # this method copy of base method, it injects date in domain
        for order in self:
            if order.analytic_account_id:
                domain = [
                    ('so_line', 'in', order.order_line.ids),
                    ('amount', '<=', 0.0),
                    ('project_id', '!=', False),
                    # OCA override
                    ('stage_id', 'in', ['invoiceable','invoiced','historical','fixed_price']),
                ]
                if order.timesheet_limit_date:
                    domain.append(
                        ('date', '<=', order.timesheet_limit_date)
                    )
                order.timesheet_ids = self.env[
                    'account.analytic.line'].search(domain)
                #_logger.info('{} found {}'.format(domain,order.timesheet_ids.mapped('name')))
            else:
                order.timesheet_ids = []
            order.timesheet_count = len(order.timesheet_ids)

    @api.onchange('partner_id')
    def set_travel_invoicing_ratio(self):
        self.travel_invoicing_ratio = self.partner_id.travel_invoicing_ratio

    @api.multi
    def action_projects_followup(self):
        self.ensure_one()
        if not self.project_id:
            return
        family_project_ids = self.project_id._get_family_project_ids()
        action = self.env.ref('vcls-timesheet.project_timesheet_forecast_report_action').read()[0]
        action['domain'] = [('project_id', 'in', family_project_ids.ids)]
        action['context'] = {}
        return action
    
    def action_sync(self):
        super().action_sync()
        for line in self.order_line.filtered(lambda t: t.task_id):
            #we get the default timecategories from the product_template, only if to time_cat already defined
            if not line.task_id.time_category_ids:
                line.task_id.time_category_ids = line.product_id.product_tmpl_id.time_category_ids

    @api.multi
    def recompute_lines(self):
        context = self.env.context
        active_ids = context.get('active_ids',[])
        _logger.info("{}".format(active_ids))
        for so_id in active_ids:
            so = self.browse(so_id)
            _logger.info("{}".format(so.name))
            for line in so.order_line:
                line._compute_qty_delivered()
                _logger.info("Delivered {}".format(line.qty_delivered))
                line._get_invoice_qty()
                _logger.info("Invoiced {}".format(line.qty_delivered))
                line._compute_amount_delivered_from_task()
                _logger.info("Delivered amount from task {}".format(line.amount_delivered_from_task))
                line._compute_amount_invoiced_from_task()
                _logger.info("Invoiced amount from task {}".format(line.amount_invoiced_from_task))
                line._compute_untaxed_amount_to_invoice()
                _logger.info("To Invoice amount{}".format(line.untaxed_amount_to_invoice))
                line._compute_untaxed_amount_invoiced()
                _logger.info("Invoiced amount{}".format(line.untaxed_amount_invoiced))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Historical Invoiced Amount is the amount already invoiced in the previous system
    historical_invoiced_amount = fields.Monetary(string="Historical Invoiced Amount", default=0.0)
    is_migrated = fields.Boolean(related='order_id.is_migrated')

    def _timesheet_compute_delivered_quantity_domain(self):
        domain = super()._timesheet_compute_delivered_quantity_domain()
        # We add the condition on the timesheet stage_id
        domain = expression.AND([
                domain,
                [('stage_id', 'in', ['invoiceable','invoiced','historical','fixed_price'])]]
            )
        #_logger.info("Delivered QTY Domain {}".format(domain))
        return domain

    def _get_timesheet_for_amount_calculation(self, only_invoiced=False):

        timesheets = super()._get_timesheet_for_amount_calculation(only_invoiced=only_invoiced)
        
        if not timesheets:
            return timesheets

        timesheets = timesheets.filtered(
                lambda r: r.stage_id in ['invoiceable', 'invoiced','historical','fixed_price']
            )

        def ts_filter(rec):
            sale = rec.task_id.sale_line_id.order_id
            return (
                sale.state in ('sale', 'done')
                and
                #(sale.timesheet_limit_date or sale.timesheet_limit_date > rec.date)
                (sale.timesheet_limit_date > rec.date if sale.timesheet_limit_date else True)
            )
        timesheets = timesheets.filtered(ts_filter)

        return timesheets

    @api.multi
    @api.depends(
        'product_uom_qty',
        'amount_delivered_from_task',
        'price_unit',
        'historical_invoiced_amount',
        'task_id.stage_id',
        'order_id.invoicing_mode',
        'order_id.fp_delivery_mode',)
    def _compute_qty_delivered(self):
        """Change qantity delivered for lines according to order.invoicing_mode and the line.vcls_type"""

        #self = self.with_context(timesheet_rounding=True)
        _logger.info("COMPUTE QTY DELIVERED")
        super()._compute_qty_delivered()
        for line in self:
            # In Time & Material, we invoice the rate product lines and set the other services to 0
            if line.order_id.invoicing_mode == 'tm':
                if line.product_id.vcls_type == 'vcls_service' and line.product_id.service_tracking != 'no': #if this is a service with a task
                    line.qty_delivered = 0.
                elif line.product_id.vcls_type == 'vcls_service' and line.product_id.service_tracking == 'no': #a service without a taks is like a fixed price in a tm quotation
                    if line.historical_invoiced_amount > line.qty_delivered*line.price_unit:
                        line.qty_delivered_manual = line.historical_invoiced_amount/line.price_unit if line.price_unit>0 else line.historical_invoiced_amount
                    line.qty_delivered = line.qty_delivered_manual
                else:
                    pass
            
            elif line.order_id.invoicing_mode == 'fixed_price':
                #_logger.info("DELIVERED QTY {} for {} {} MANUAL {}".format(line.qty_delivered,line.name,line.product_id.vcls_type,line.qty_delivered_manual))
                if line.product_id.vcls_type in ['vcls_service'] and line.order_id.fp_delivery_mode == 'task':
                    line.qty_delivered = line.task_id.completion_ratio/100
                    if line.historical_invoiced_amount > line.qty_delivered*line.price_unit:
                        line.qty_delivered = line.historical_invoiced_amount/line.price_unit if line.price_unit>0 else line.historical_invoiced_amount
                elif line.product_id.vcls_type in ['vcls_service'] and line.order_id.fp_delivery_mode == 'manual':
                    if line.historical_invoiced_amount > line.qty_delivered*line.price_unit:
                        line.qty_delivered_manual = line.historical_invoiced_amount/line.price_unit if line.price_unit>0 else line.historical_invoiced_amount
                    line.qty_delivered = line.qty_delivered_manual
                elif line.product_id.vcls_type == 'rate':
                    line.qty_delivered = 0.
                else:
                    pass
                #_logger.info("DELIVERED QTY {} for {} {} MANUAL {}".format(line.qty_delivered,line.name,line.product_id.vcls_type,line.qty_delivered_manual))
            
            else:
                pass


    @api.multi
    @api.depends(
        'product_uom_qty',
        'price_unit',
        'historical_invoiced_amount',
        'amount_invoiced_from_task',
        'task_id.stage_id',
        'order_id.invoicing_mode',
        'invoice_lines.invoice_id.state',
        'invoice_lines.quantity')
        
    def _get_invoice_qty(self):
        #Change qantity delivered for lines according to order.invoicing_mode and the line.vcls_type
        super()._get_invoice_qty()
        for line in self:
            _logger.info("qty invoiced for {}\n Type {} | Mode {} | Tracking {}".format(line.name,line.product_id.vcls_type,line.order_id.invoicing_mode,line.product_id.service_tracking))
            #we add the historical invoiced amount for migration purpose
            if (line.product_id.vcls_type in ['vcls_service']) and (line.order_id.invoicing_mode == 'fixed_price' or line.product_id.service_tracking == 'no'):
            #if (line.order_id.invoicing_mode == 'fixed_price' and line.product_id.vcls_type in ['vcls_service']) or (line.order_id.invoicing_mode == 'tm' and line.product_id.service_tracking == 'no'):
                line.qty_invoiced += line.historical_invoiced_amount/line.price_unit if line.price_unit>0 else 0.0
                #_logger.info("Historical Amount for {} : {}".format(line.name,line.historical_invoiced_amount))
            #for rate products, we add the historical timesheets (unit_amount_rounded)
            if (line.order_id.invoicing_mode == 'tm' and line.product_id.vcls_type=='rate'):
                timesheets = line.order_id.timesheet_ids.filtered(lambda ts: ts.stage_id=='historical' and ts.so_line == line)
                
                if timesheets:
                    #_logger.info("Historical QTY for {} : {} | {}".format(line.name,len(timesheets),line.order_id.name))
                    if line.product_uom == self.env.ref('uom.product_uom_day'): #if we are in daily
                        line.qty_invoiced += sum(timesheets.mapped('unit_amount_rounded'))/8
                        #_logger.info("Historical QTY for {} ".format(line.qty_invoiced))
                    else:
                        line.qty_invoiced += sum(timesheets.mapped('unit_amount_rounded'))
                    

    # We need to override the OCA to take the rounded_unit_amount in account rather than the standard unit_amount
    @api.multi
    @api.depends(
        'task_id',
        'task_id.timesheet_ids.timesheet_invoice_id',
        'task_id.timesheet_ids.unit_amount_rounded',
        'task_id.timesheet_ids.stage_id',
    )
    def _compute_amount_delivered_from_task(self):
        for line in self:
            total = 0
            for ts in line._get_timesheet_for_amount_calculation():

                """rate_line = ts.project_id.sale_line_employee_ids.filtered(
                    lambda r: r.employee_id == ts.employee_id
                )
                total += ts.unit_amount_rounded * rate_line.price_unit"""
                total += ts.unit_amount_rounded * ts.so_line_unit_price
            line.amount_delivered_from_task = total
            line.amount_delivered_from_task_company_currency = (
                total * line.order_id.currency_rate
            )

    @api.multi
    @api.depends('task_id', 'task_id.timesheet_ids.timesheet_invoice_id')
    def _compute_amount_invoiced_from_task(self):
        for line in self:
            total = 0
            for ts in line._get_timesheet_for_amount_calculation(True):
                """rate_line = ts.project_id.sale_line_employee_ids.filtered(
                    lambda r: r.employee_id == ts.employee_id
                )
                total += ts.unit_amount_rounded * rate_line.price_unit"""
                total += ts.unit_amount_rounded * ts.so_line_unit_price
            line.amount_invoiced_from_task = total
            line.amount_invoiced_from_task_company_currency = (
                total * line.order_id.currency_rate
            )

    @api.depends('invoice_lines', 'invoice_lines.price_total', 'invoice_lines.invoice_id.state', 'invoice_lines.invoice_id.type')
    def _compute_untaxed_amount_invoiced(self):
        super()._compute_untaxed_amount_invoiced()

        for line in self:
            _logger.info("{}".format(line.vcls_type))
            pass

        for line in self.filtered(lambda l: l.historical_invoiced_amount>0):
            #_logger.info("Historical amount invoiced {} | {}".format(line.historical_invoiced_amount,line.order_id.name))
            line.untaxed_amount_invoiced += line.historical_invoiced_amount

        for line in self.filtered(lambda l: l.vcls_type=='rate' and l.order_id.invoicing_mode == 'tm'):
            ts = self.env['account.analytic.line'].search([('stage_id','=','historical'),('so_line','=',line.id)])
            if ts:
                line.untaxed_amount_invoiced += sum(ts.mapped(lambda r: r.unit_amount_rounded*r.so_line_unit_price))

        
        

    @api.depends('state', 'price_reduce', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered','order_id.invoicing_mode')
    def _compute_untaxed_amount_to_invoice(self):
        #self = self.sudo()
        #_logger.info("vcls-timesheet | _compute_untaxed_amount_to_invoice {} {}".format(self.mapped('order_id.name'),self.mapped('name')))
        super()._compute_untaxed_amount_to_invoice()

        for line in self.filtered(lambda l: l.vcls_type=='rate' and l.order_id.invoicing_mode == 'tm'):
            filter_date = line.order_id.timesheet_limit_date or fields.Date.today()
            ts = line.order_id.timesheet_ids.filtered(lambda t: t.so_line == line and t.date <= filter_date and t.stage_id == 'invoiceable')
            #ts = self.env['account.analytic.line'].search([('stage_id','=','historical'),('so_line','=',line.id)])
            if ts:
                line.untaxed_amount_to_invoice = sum(ts.mapped(lambda r: r.unit_amount_rounded*r.so_line_unit_price))
            else:
                line.untaxed_amount_to_invoice = 0.0
        
        #in fixed price, we force rate lines to 0
        for line in self.filtered(lambda l: l.vcls_type=='rate' and l.order_id.invoicing_mode == 'fixed_price'):
            line.untaxed_amount_to_invoice = 0.0


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    name = fields.Char(
        store=True
    )
