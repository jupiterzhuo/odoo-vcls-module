# -*- coding: utf-8 -*-
{
    'name': "vcls-interfaces",

    'summary': """
        In/Out interfaces of the Odoo VCLS implementation""",
    
    'description': """
        This module contains the following interfaces:
        - Payroll export -> Extract employee & leaves data to be shared with payroll suppliers
        - Billability Export -> Extract employee identification and capacity over a defined period
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',

    'version': '1.8.13',


    # any module necessary for this one to work correctly
    'depends': ['base',
                'vcls-hr',
                ],

    # always loaded
    'data': [
        
        ############
        # SECURITY #
        ############
        'security/ir.model.access.csv',
        'security/export_payroll_rules.xml',
        
        #########
        # VIEWS #
        #########
        'views/export_billability_views.xml',
        'views/export_payroll_line_views.xml',
        'views/export_payroll_views.xml',
        'views/export_payroll_overriden_views.xml',
        'views/billability_overivew_views.xml',

        #########
        # MENUS #
        #########
        'actions/export_payroll_menu.xml', 
        'actions/export_billability_menu.xml',
        'actions/billablility_report_cron.xml',
        'actions/billability_overview.xml',

    ],
    
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}