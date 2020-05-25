# -*- coding: utf-8 -*-
{
    'name': "vcls-rdd",

    'summary': """
        VCLS SalesForce Odoo migration""",

    'description': """
    """,

    'author': "VCLS",
    'website': "https://voisinconsulting.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.4',

    # any module necessary for this one to work correctly
    'depends': ['vcls-crm',
                'smile_data_integration',
                'office365_framework',
                'vcls-timesheet',
                'vcls-project',
            ],

    # always loaded
    'data': [

    ],
    # only loaded in demonstration mode
    'demo': [

    ],
}
