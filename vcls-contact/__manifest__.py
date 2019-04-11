# -*- coding: utf-8 -*-
{
    'name': "vcls-contact",

    'summary': """
        VCLS custom contact module
        """,

    'description': """
    """,

    'author': "VCLS",
    'website': "https://voisinconsulting.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1.3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts'],

    # always loaded
    'data': [
        
        ### SECURITY ###

        #'security/ir.model.access.csv',
        'security/vcls_groups.xml',
        
        ### VIEWS ###
        'views/company_views.xml',

        ### MENUS ###
        'views/contact_menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}