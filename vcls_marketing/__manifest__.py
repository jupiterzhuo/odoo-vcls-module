# -*- coding: utf-8 -*-
{

    'name': "VCLS Marketing",

    'summary': """
        VCLS customs marketing module.""",
    'description': """
    """,
    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",
    'category': 'Uncategorized',

    'version': '0.1.20',
  
    'depends': [
        'crm',
        'project',
        'contacts',
        'vcls-contact',
        'vcls-project',
        'vcls-crm',
        'vcls_security',
        'vcls-expenses',
        'marketing_automation',
        'mass_mailing',
    ],
    'data': [
        #'security/ir.model.access.csv',
        'views/marketing_views.xml',
        'views/lead_views.xml',
        'views/partner_views.xml',
        'views/marketing_campaign_views.xml',
    ],
}