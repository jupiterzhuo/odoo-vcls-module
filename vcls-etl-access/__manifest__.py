# -*- coding: utf-8 -*-
{
    'name': "vcls-etl-access",

    'summary': """
    """,

    'description': """
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'vcls-contact',
                'vcls-hr',
                'vcls-project',
                'vcls-timesheet',
                'vcls-expenses',
                ],

    # always loaded
    'data': [
        'data/product.category.csv',
        'data/hr.employee.seniority.level.csv',
        'data/product.pricelist.item.csv',
        'data/resource.calendar.csv',
        'data/res.users.csv',
        'data/employee.xml',
        'data/products.xml',
        'security/ir.model.access.csv',
        'views/etl_views.xml',
        'views/etl_menu.xml',
        'data/queries.xml',
        'actions/etl_cronjob.xml',

        
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
