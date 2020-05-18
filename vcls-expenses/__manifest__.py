# -*- coding: utf-8 -*-
{
    'name': "vcls-expenses",

    'summary': """
        VCLS custom expenses module
        """,

    'description': """
    """,

    'author': "VCLS",
    'website': "https://voisinconsulting.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.8',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr_expense',
        'sale_expense',
        'project',
        'vcls-project',
        'vcls_security',
        
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/expense_rules.xml',
        'views/expense_sheet_views.xml',
        'views/product.xml',
        'views/expense_views.xml',
        'views/project_portal_templates.xml',
        'views/projects_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}