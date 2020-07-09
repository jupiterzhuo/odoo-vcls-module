# -*- coding: utf-8 -*-
{
    'name': "vcls-invoicing",

    'summary': """
        VCLS customs invoicing module.""",

    'description': """
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.7.59',


    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'vcls-crm',
        'vcls-contact',
        'vcls-risk',
        'vcls-hr',
        'account',
        'sale_timesheet_limit_date',
        'sale_timesheet_rounded',
        'vcls_security',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/partner_data.xml',
        'views/product_views.xml',
        'security/security_groups.xml',
        'data/risk_type.xml',
        'views/sale_views.xml',
        'views/invoice_views.xml',
        'views/contact_views.xml',
        'views/res_company.xml',
        'views/res_bank.xml',
        'views/fiscal_position.xml',
        'views/account_mail_template.sql',
        'wizard/sale_make_invoice_advance_views.xml',
        # reports
        'reports/report_project_invoice_detailed.xml',
        'reports/report_project_invoice_aggregated.xml',
        'reports/activity_reports.xml',
        'reports/invoice_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}