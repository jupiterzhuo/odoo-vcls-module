# -*- coding: utf-8 -*-
{
    'name': "vcls security",

    'summary': """
        VCLS groups and security.""",
    'description': """
    """,
    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",
    'version': '0.2.2',
    'depends': [
        'base',
        'project',
        'sale',
        'sales_team',
        'purchase',
        'hr_timesheet',
        'project_forecast',
        'crm',
        'web_access_rule_buttons',
        'agreement_legal',
    ],
    'data': [
        'security/security_rules_fix.sql',
        'security/security_rules_fix.xml',
        'security/vcls_groups.xml',
        'security/ir.model.access.csv',
        'security/account_manager_security/ir.model.access.csv',
        'security/account_manager_security/account_manager_security.xml',
        'security/lead_consultant_security/ir.model.access.csv',
        'security/lead_consultant_security/lead_consultant_security.xml',
        'security/consultant_security/ir.model.access.csv',
        'security/consultant_security/consultant_security.xml',
        'security/project_controller_security.xml',
        'security/cross_company_invoicing.xml',
        'views/menus.xml',
        'actions/cronjob.xml',
    ],
    'demo': [
    ],
}
