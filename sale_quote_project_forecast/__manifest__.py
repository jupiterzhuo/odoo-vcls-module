# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Sale quote project forcast',
    'description': "create a quote from a project forcast",
    'version': '12.0.5.0.5',
    'author': 'Camptocamp',
    'license': 'AGPL-3',
    'category': 'Others',
    'depends': [
        'sale_project_timesheet_by_seniority',
        'project_timesheet_forecast',
        'sale_milestone_profile_invoicing',
    ],
    'website': 'http://www.camptocamp.com',
    'data': [
        'wizard/calculate_price_wizard.xml',
        'views/product_template.xml',
        'views/sale_order.xml',
    ],
    'installable': True,
    'auto_install': True,
}
