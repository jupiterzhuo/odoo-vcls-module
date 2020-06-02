# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class LeadQuotation(models.TransientModel):
    _name = 'tool.timesheet.recode'
    _description = 'Timesheet Recoder'

    mode = fields.Selection([
        ('replace_rate', 'Replace Rate'),
        ('update_status', 'Update Status')
    ], string='Recompute Mode', required=True, default='replace_rate',
    help="""
    Replace Rate:
    - Update all non-invoiced timesheets from Source Rate to Target Rate, single employee if documented
    - Update the mapping table accordingly
    """
    )

    include_childs = fields.Boolean(
        default=True,
    )

    info = fields.Text()

    run_date = fields.Datetime()

    ### SOURCE FIELDS

    source_project_id = fields.Many2one(
        comodel_name='project.project',
        string= 'Source Project',
    )

    source_task_id = fields.Many2one(
        comodel_name='project.task',
        string= 'Source Task',
    )

    source_rate_id = fields.Many2one(
        comodel_name='sale.order.line',
        string= 'Source Rate',
    )

    source_employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string= 'Source Employee',
    )

    source_status = fields.Selection([
        # ('forecast', 'Stock'),
        ('draft', '0. Draft'), 
        ('lc_review', '1. LC review'), 
        ('pc_review', '2. PC review'), 
        ('carry_forward', 'Carry Forward'),
        #('adjustment_validation', '4. Adjustment Validation'),
        ('invoiceable', '5. Invoiceable'),
        #('invoiced', '6. Invoiced'),
        ('historical','7. Historical'),
        #('outofscope', 'Out Of Scope'),
        ], default=False)

    date_range_start = fields.Date()
    date_range_end = fields.Date()


    ### TARGET FIELDS
    target_rate_id = fields.Many2one(
        comodel_name='sale.order.line',
        string= 'Target Rate',
    )

    target_status = fields.Selection([
        # ('forecast', 'Stock'),
        ('draft', '0. Draft'), 
        ('lc_review', '1. LC review'), 
        ('pc_review', '2. PC review'), 
        ('carry_forward', 'Carry Forward'),
        #('adjustment_validation', '4. Adjustment Validation'),
        ('invoiceable', '5. Invoiceable'),
        #('invoiced', '6. Invoiced'),
        ('historical','7. Historical'),
        #('outofscope', 'Out Of Scope'),
        ], default=False)

    ### TOOL FIELDS
    rate_ids = fields.Many2many(
        comodel_name='sale.order.line',
        compute='_compute_rate_ids',
    ) 

    @api.depends('source_project_id','include_childs')
    def _compute_rate_ids(self):
        for item in self.filtered(lambda l: l.source_project_id):
            """if item.include_childs:
                projects = item.source_project_id | item.source_project_id.child_id
            else:"""
            projects = item.source_project_id
            
            rates = self.env['sale.order.line']
            for so in projects.mapped('sale_order_id'):
                rate_lines = so.order_line.filtered(lambda r: r.vcls_type == 'rate')
                if rate_lines:
                    rates |= rate_lines
            if rates:
                item.rate_ids = rates


    @api.multi
    def get_ts_source_domain(self,projects=False):
        self.ensure_one()
        if not projects: #we exclude the case of missing project info
            return False

        domain = [('project_id','in',projects.ids),('timesheet_invoice_id', '=', False),('is_timesheet','=',True)] #we don't change invoiced timesheets, too risky
        
        if self.source_employee_id:
            domain.append(('employee_id','=',self.source_employee_id.id))
        if self.source_task_id:
            domain.append(('task_id','=',self.source_task_id.id))
        if self.date_range_start:
            domain.append(('date','>=',self.date_range_start))
        if self.date_range_end:
            domain.append(('date','<=',self.date_range_end))
        if self.source_status:
            domain.append(('stage_id','=',self.source_status))

        return domain



    @api.multi
    def run_test(self):
        self.ensure_one()
        self.run('test')
    
    @api.multi
    def run_real(self):
        self.ensure_one()
        self.run('real')
        self.run_date = fields.Datetime.now()

    @api.multi
    def run(self,mode='test'):
        self.ensure_one()

        if self.include_childs:
            projects = self.source_project_id | self.source_project_id.child_id
        else:
            projects = self.source_project_id
       
        info = ""
        if mode=='test':
            info += "TEST:\n"

        domain = self.get_ts_source_domain(projects)
        timesheets = self.env['account.analytic.line'].search(domain)

        if self.mode == 'update_status':
            if timesheets:
                if mode=='real':
                    timesheets.write({
                        'stage_id':self.target_status,
                        })
                info += "INFO | {} timesheets updated with domain {}.\n".format(len(timesheets),domain)
            else: 
                info += "INFO | No timesheet found with domain {}.\n".format(domain)

        if self.mode == 'replace_rate':
            maps = self.env['project.sale.line.employee.map']
            ps_name = self.source_rate_id.product_id.name
            pt_name = self.target_rate_id.product_id.name
            
            for project in projects:

                source_sol = project.sale_order_id.order_line.filtered(lambda l: l.product_id.name == ps_name)
                target_sol = project.sale_order_id.order_line.filtered(lambda l: l.product_id.name == pt_name)
                if not target_sol:
                    info += "ERROR | No target {} rate line found in quotation {}. Remapping not possible.\n".format(pt_name,project.sale_order_id.name)
                    continue
                elif not source_sol:
                    info += "ERROR | No source {} rate line found in quotation {}. Remapping not possible.\n".format(ps_name,project.sale_order_id.name)
                    continue
                else:
                    ts = timesheets.filtered(lambda t: t.so_line == source_sol[0])

                    if self.source_employee_id:
                        maps = project.sale_line_employee_ids.filtered(lambda m: m.employee_id == self.source_employee_id and m.sale_line_id.product_id.name == ps_name)
                        #ts = project.timesheet_ids.filtered(lambda t: not t.timesheet_invoice_id and t.so_line == source_sol[0] and t.employee_id == self.source_employee_id)
                    else:
                        maps = project.sale_line_employee_ids.filtered(lambda m: m.sale_line_id.product_id.name == ps_name)
                        #ts = project.timesheet_ids.filtered(lambda t: not t.timesheet_invoice_id and t.so_line == source_sol[0])

                    if maps:
                        if mode=='real':
                            maps.write({'sale_line_id':target_sol[0].id})
                        info += "INFO | {} map lines updated in project {}.\n".format(len(maps),project.name)
                    else: 
                        info += "INFO | No map lines updated in project {}.\n".format(project.name)

                    if ts:
                        if mode=='real':
                            ts.write({
                                'so_line':target_sol[0].id,
                                'so_line_unit_price':target_sol[0].price_unit,
                                'rate_id':target_sol[0].product_id.product_tmpl_id.id,
                                })
                        info += "INFO | {} timesheets updated in project {}.\n".format(len(ts),project.name)
                    else: 
                        info += "INFO | No timesheets updated in project {}.\n".format(project.name)
            
        self.info=info
        
