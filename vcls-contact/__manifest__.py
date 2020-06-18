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
    'version': '0.7.3',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'contacts',
        'survey',
        'partner_company_group',
        'vcls_security',
        ],

    # always loaded
    'data': [

        ### CONFIGURATION DATA ###
        'data/res.partner.category.csv',
        'data/ir.config_parameter.csv',
        'data/client.activity.csv',
        'data/client.product.csv',
        'data/partner.seniority.csv',
        'data/partner.functional.focus.csv',
        'data/parameters.xml',
        
        ### SECURITY ###
        'security/vcls_groups.xml',
        'security/ir.model.access.csv',
        'security/contact_rules.xml',
        
        ### VIEWS ###
        'views/dropdown_views.xml',
        'views/contact_views.xml',

        ### MENUS ###
        'views/contact_menu.xml',

        ### ACTIONS ###
        'actions/contact_server_action.xml',
        # 'actions/cronjob.xml',

        ### SEQUENCES ###
        'sequences/partner_sequences.xml',

        ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}