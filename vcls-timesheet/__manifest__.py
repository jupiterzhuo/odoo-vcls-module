# -*- coding: utf-8 -*-
{
    'name': "vcls-timesheet",

    'summary': """
        VCLS customs for timesheet applications.""",

    'description': """
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.8.9',



    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr_timesheet',
        'project_timesheet_forecast',
        'sale_timesheet',
        'sale_timesheet_limit_date',
        'sale_timesheet_rounded',
        'timesheet_useability',
        'vcls-hr',
        'vcls-crm',
        'vcls-project',
        'timesheet_grid',
        'web_grid_extend',
        'project_timesheet_synchro',
        'vcls_security',
    ],

    # always loaded
    'data': [
        ### SECURITY ###
        'security/record_rule.xml',
        'security/ir.model.access.csv',
        #'data/parameters.xml',
        'data/project.xml',
        'data/time_categories.xml',

        ### VIEWS ###
        'views/report_views.xml',
        'views/timesheets_views.xml',
        'views/projects_views.xml',
        'views/sale_order_views.xml',
        'views/crm_views.xml',
        'views/time_category_views.xml',
        'views/timesheet_report_views.xml',
        'views/contact_view.xml',
        'wizard/timesheet_recode_views.xml',


        ### ACTIONS ###
        'actions/timesheet_cron.xml',
        'actions/timesheet_server_action.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
