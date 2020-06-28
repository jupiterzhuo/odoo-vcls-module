# -*- coding: utf-8 -*-
{
    'name': "vcls-crm",

    'summary': """
        VCLS customs for CRM/Sales/Marketing applications.""",

    'description': """
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    'category': 'Uncategorized',


    'version': '1.3.15',


    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'crm',
        'crm_enterprise',
        'website',
        'website_crm',
        'partner_firstname',
        'partner_second_lastname',
        'website_crm_score',
        'vcls-contact',
        'sale',
        'sale_management',
        'sale_crm',
        'sale_order_revision',
        'crm_lead_currency',
        'vcls-hr',
        'crm_lead_firstname',
        'marketing_automation',
        'vcls-risk',
        'sale_timesheet',
        'sale_purchase',
        'sale_subscription',
        'vcls_subscription',
        'vcls_security',
        
    ],

    'data': [

        # ACTIONS #
        # 'actions/cronjob.xml',

        # SECURITY #
        'security/ir.model.access.csv',
        'security/lead_rules.xml',
        'security/security_groups.xml',
        'security/lead_consultant_rules.xml',
        'security/account_manager_rules.xml',

        # VIEWS #
        'views/dropdown_views.xml',
        'views/crm_lead_won_views.xml',
        'views/lead_views.xml',
        'views/partner_relation.xml',
        'views/crm_contact_views.xml',
        'views/product_deliverable_views_menu.xml',
        'views/product_views_menu.xml',
        'views/sale_order_views.xml',
        'views/purchase_views.xml',
        'views/lead2opp.xml',
        'views/core_team_views.xml',
        'wizard/lead_quotation_views.xml',
        'reports/report_order.xml',
        #'views/sale_order_template_views.xml',

        # MENUS #
        'views/lead_menus.xml',
        'views/partner_relation_menus.xml',

        # RECORDS DATA #
        'data/partner.relation.type.csv',
        'data/product.pricelist.csv',
        'data/message_subtype.xml',
        'data/risk_type.xml',
        'data/lead_stage.xml',

    ],
    'demo': [
    ],
}