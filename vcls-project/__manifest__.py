# -*- coding: utf-8 -*-
{
    'name': "vcls-project",

    'summary': """
        VCLS customs project module.""",

    'description': """
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0.21',
    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'mail',
        'project',
        'vcls-crm',
        'vcls-hr',
        'project_forecast',
        'sale_project_timesheet_by_seniority',
        'project_task_stage_allow_timesheet',
        'project_task_default_stage',
        'project_parent_task_filter',
        'sale_quote_project_forecast',
        'project_timeline',
        'project_timeline_task_dependency',
        'sale_timesheet',
        'account',
        'hr_timesheet',
        'vcls_security',
        'vcls-risk',
        'vcls-invoicing',
        'vcls-helpdesk',
    ],

    # always loaded
    'data': [

        ### SECURITY ###
        'security/vcls_groups.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/lc_security.xml',
        # DATA
        'data/end_of_project_cron.xml',
        'data/project_server_action.xml',
        ### VIEWS ###
        'views/project_summary_views.xml',
        'views/task_type_views.xml',
        'views/dev_project_views.xml',
        'views/dev_task_views.xml',
        
        'views/employee_views.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/lead_views.xml',
        'views/res_partner_views.xml',
        'views/template.xml',
        'views/project_forecast_views.xml',
        'views/dev_project_menu.xml',

        'views/project_views.xml',
        'views/program_views_menu.xml',
        'views/task_views.xml',

        'views/helpdesk_ticket_views.xml',

        ### SEQUENCES ###
        'sequences/project_sequences.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}