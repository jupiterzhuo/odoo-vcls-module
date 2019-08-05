from odoo import tools
from odoo import api, fields, models


class TimesheetForecastReport(models.Model):

    _inherit = "project.timesheet.forecast.report.analysis"

    stage_id = fields.Selection([
        ('forecast', 'Forecast'),
        ('draft', 'Draft'), 
        ('lc_review', 'LC review'), 
        ('pc_review', 'PC review'), 
        ('carry_forward', 'Carry Forward'),
        ('adjustment_validation', 'Adjustment Validation'),
        ('invoiceable', 'Invoiceable'),
        ('outofscope', 'Out Of Scope'),
    ], 'Stage', readonly = True)
    
    
    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                (
                    SELECT
                        d::date AS date,
                        F.employee_id AS employee_id,
                        F.task_id AS task_id,
                        F.project_id AS project_id,
                        F.resource_hours / NULLIF(F.working_days_count, 0) AS number_hours,
                        'forecast' AS type,
                        'forecast' AS stage_id,
                        F.id AS id
                    FROM generate_series(
                        (SELECT min(start_date) FROM project_forecast WHERE active=true)::date,
                        (SELECT max(end_date) FROM project_forecast WHERE active=true)::date,
                        '1 day'::interval
                    ) d
                        LEFT JOIN project_forecast F ON d.date >= F.start_date AND d.date <= end_date
                        LEFT JOIN hr_employee E ON F.employee_id = E.id
                        LEFT JOIN resource_resource R ON E.resource_id = R.id
                    WHERE
                        EXTRACT(ISODOW FROM d.date) IN (
                            SELECT A.dayofweek::integer+1 FROM resource_calendar_attendance A WHERE A.calendar_id = R.calendar_id
                        )
                        AND F.active=true
                ) UNION (
                    SELECT
                        A.date AS data,
                        E.id AS employee_id,
                        A.task_id AS task_id,
                        A.project_id AS project_id,
                        A.unit_amount AS number_hours,
                        'timesheet' AS type,
                        A.stage_id AS stage_id,
                        -A.id AS id
                    FROM account_analytic_line A, hr_employee E
                    WHERE A.project_id IS NOT NULL
                        AND A.employee_id = E.id
                )
            )
        """ % (self._table,))
