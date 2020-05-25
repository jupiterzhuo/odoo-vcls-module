from odoo import tools
from odoo import api, fields, models


class TimesheetForecastReport(models.Model):

    _inherit = "project.timesheet.forecast.report.analysis"

    stage_id = fields.Selection([
        ('forecast', 'Stock'),
        ('draft', '0. Draft'), 
        ('lc_review', '1. LC review'), 
        ('pc_review', '2. PC review'), 
        ('carry_forward', 'Carry Forward'),
        ('adjustment_validation', '3. Adjustment Validation'),
        ('invoiceable', '4. Invoiceable'),
        ('invoiced', '5. Invoiced'),
        ('historical','6. Historical'),
        ('outofscope', 'Out Of Scope'),
    ], 'Stage', readonly=True)

    revenue = fields.Float('Revenue', readonly=True)

    rate_product_id = fields.Many2one(
        'product.template',
        'Rate Product', readonly=True
    )

    deliverable_id = fields.Many2one(
        'product.deliverable', string='Deliverable',
        readonly=True
    )

    employee_seniority_level_id = fields.Many2one(
        'hr.employee.seniority.level',
        String='Seniority Level', readonly=True
    )

    # EDIT SQL REQUEST IN ORDER TO GET STAGE & REVENUE
    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                (
                    SELECT
                        (select prod_template.seniority_level_id
                            from hr_employee_product_template_rel emp_product_rel 
                            join product_template prod_template
                            on (emp_product_rel.hr_employee_id = F.employee_id
                            and prod_template.id = emp_product_rel.product_template_id)
                            order by prod_template.name
                            limit 1
                        ) AS employee_seniority_level_id,
                        F.employee_id AS employee_id,
                        F.task_id AS task_id,
                        F.project_id AS project_id,
                        F.resource_hours AS number_hours,
                        null AS date,
                        'forecast' AS type,
                        'forecast' AS stage_id,
                        F.resource_hours*F.hourly_rate AS revenue,
                        F.rate_id AS rate_product_id,
                        F.id AS id,
                        (select deliverable.id 
                            from product_deliverable deliverable
                             join product_template prod_temp
                            on deliverable.id = prod_temp.deliverable_id
                             join product_product pp
                            on prod_temp.id = pp.product_tmpl_id
                             join sale_order_line sol
                            on pp.id = sol.product_id
                             join project_task task 
                            on task.sale_line_id = sol.id
                            where F.task_id = task.id
                        ) AS deliverable_id
                    FROM project_forecast F
                        LEFT JOIN hr_employee E ON F.employee_id = E.id
                        LEFT JOIN resource_resource R ON E.resource_id = R.id
                    WHERE
                        F.active=true
                ) UNION (
                    SELECT
                        (select prod_template.seniority_level_id
                            from hr_employee_product_template_rel emp_product_rel 
                            join product_template prod_template
                            on (emp_product_rel.hr_employee_id = E.id
                            and prod_template.id = emp_product_rel.product_template_id)
                            order by prod_template.name
                            limit 1
                        ) AS employee_seniority_level_id,
                        E.id AS employee_id,
                        A.reporting_task_id AS task_id,
                        A.project_id AS project_id,
                        -A.unit_amount_rounded AS number_hours,
                        null AS date,
                        'timesheet' AS type,
                        A.stage_id AS stage_id,
                        (-A.so_line_unit_price * A.unit_amount_rounded) AS revenue,
                        A.rate_id AS rate_product_id,
                        -A.id AS id,
                        (select deliverable.id 
                            from product_deliverable deliverable
                             join product_template prod_temp
                            on deliverable.id = prod_temp.deliverable_id
                             join product_product pp
                            on prod_temp.id = pp.product_tmpl_id
                             join sale_order_line sol
                            on pp.id = sol.product_id
                             join project_task task 
                            on task.sale_line_id = sol.id
                            where A.task_id = task.id
                        ) AS deliverable_id
                    FROM hr_employee E, ((account_analytic_line A
                    LEFT JOIN sale_order_line S ON A.so_line = S.id)
                    LEFT JOIN product_template P ON S.product_id = P.id)
                    WHERE A.project_id IS NOT NULL
                        AND A.employee_id = E.id
                )
            )
        """ % (self._table,))

    @api.model
    def _read_group_prepare(self, orderby, aggregated_fields, annotated_groupbys, query):
        groupby_terms, orderby_terms = super(TimesheetForecastReport, self)._read_group_prepare(
            orderby, aggregated_fields, annotated_groupbys, query
        )
        if '"stage_id"' in orderby_terms:
            orderby_terms[orderby_terms.index('"stage_id"')] = """
                CASE WHEN "{table}"."stage_id" = 'draft' THEN 0 
                 WHEN "{table}"."stage_id" = 'lc_review' THEN 1  
                 WHEN "{table}"."stage_id" = 'pc_review' THEN 2 
                 WHEN "{table}"."stage_id" = 'adjustment_validation' THEN 3 
                 WHEN "{table}"."stage_id" = 'invoiceable' THEN 4 
                 WHEN "{table}"."stage_id" = 'invoiced' THEN 5 
                 WHEN "{table}"."stage_id" = 'historical' THEN 6
                 ELSE 7 END
            """.format(table=self._table)
        return groupby_terms, orderby_terms