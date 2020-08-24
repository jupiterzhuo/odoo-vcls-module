# -*- coding: utf-8 -*-
{
    'name': "vcls-accounting",

    'summary': """
        VCLS accounting customizations""",

    'description': """
        VCLS accounting customizations
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.4.9',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'account',
        'account_reports',
        'vcls-contact',
        ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',

        ### VIEWS ###
        'views/account_move_line_views.xml',
        'views/general_ledger_assets.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}