# -*- coding: utf-8 -*-
{
    'name': "vcls-admin",

    'summary': """
        VCLS customs for admin applications""",

    'description': """
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.2.7',

    # any module necessary for this one to work correctly
    'depends': [
                    'vcls-hr',
                    'vcls-helpdesk',
                    'vcls-contact',
                    'vcls-crm',
                    'vcls-interfaces',
                    'vcls-project',
                    'vcls-timesheet',
                    'vcls-suppliers',
                    'vcls-legal',
                    'vcls-theme',
                    'vcls-risk',
                    'vcls-expenses',
                    'vcls-invoicing',
                    'vcls-accounting',
                    
                ],

    # always loaded
    'data': [

        ### SECURITY ###
        #'security/ir.model.access.csv',
        'security/group_vcls.xml',

        ### ACTIONS
        'actions/admin_user_cronjob.xml',

        ### VIEWS
        #'views/vcls_admin.xml',
        'views/quick_vcls_filter.xml',
        'views/new_template_restriction.xml'

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}