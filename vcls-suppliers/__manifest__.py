# -*- coding: utf-8 -*-
{
    'name': "vcls-suppliers",

    'summary': """
        External Resource Management""",

    'description': """
        External Resource Management
    """,

    'author': "VCLS",
    'website': "https://voisinconsulting.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.2.8',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'survey',
        'vcls-contact',
        'vcls-hr',
        'vcls-project',
        'vcls-crm',
        'sale_purchase',
        'vcls_security',
        'vcls-invoicing',
    ],

    # always loaded
    'data': [
        ### RECORDS
        'data/expertise.area.csv',
        'data/project.supplier.type.csv',
        'data/hr_data.xml',
        'data/product_data.xml',

        ### SECURITY
        'security/vcls_groups.xml',
        'security/ir.model.access.csv',

        ### VIEWS
        'views/sup_contact_views.xml',
        'views/sup_employee_views.xml',
        'views/purchase_views.xml',
        'views/project_portal_templates.xml',
        'views/skill_views.xml',
        'views/sale_report_rm_views.xml',
        'views/portal_templates.xml',
        'views/bill_approval_views.xml',

        ### MENUS
        'views/supplier_menu.xml', 
        
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
