# -*- coding: utf-8 -*-
{
    'name': "vcls-helpdesk",

    'summary': """
        VCLS customs for helpdesk application""",

    'description': """
        VCLS customs for helpdesk application
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.7.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'contacts',
                'helpdesk',
                'hr',
                #'vcls-hr',
               ],

    # always loaded
    'data': [
        ############
        # SECURITY #
        ############
        'security/ir.model.access.csv',
        'security/vcls-helpdesk_rules.xml',
        
        #########
        # VIEWS #
        #########
        'views/ticket.xml',
        'views/wizard_ticket.xml',
        #'views/change_request.xml',
        
        ###########
        # ACTIONS #
        ###########
        'actions/helpdesk_menu.xml',
        'actions/helpdesk_server_action.xml',
        
        ###################
        # DEFAULT RECORDS #
        ###################
        'data/helpdesk.ticket.type.csv',
        
    ],
    
    'qweb': [
        # 'static/src/xml/user_menu.xml',
    ],
    
    # only loaded in demonstration mode
    'demo': [
        #'demo/stage.xml',
        'demo/team.xml',
        'demo/subcategory.xml',
    ],
}
