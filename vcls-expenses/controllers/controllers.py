# -*- coding: utf-8 -*-

from odoo.addons.project.controllers.portal import CustomerPortal
from odoo.http import request
from odoo import http, _
from odoo.exceptions import AccessError, MissingError


class CustomerPortal(CustomerPortal):

    @http.route(['/my/project/expense_modal'], type='json', auth="user", website=True)
    def portal_my_project_expense_modal(self, project_id=None, expense_id=None, **kw):
        project = request.env['project.project'].sudo()
        expense_sudo = request.env['hr.expense'].sudo()
        if expense_id and expense_id.isdigit():
            expense_sudo = expense_sudo.browse(int(expense_id))
            project = expense_sudo.sheet_id.project_id
        if expense_id and not project:
            # expense is not related to a project
            return {}
        try:
            project_sudo = self._document_check_access('project.project', int(project_id))
        except (AccessError, MissingError):
            # If user does not have access to this project
            return {}

        values = {
            'currencies': request.env['res.currency'].sudo().search([('active', '=', True)]),
            'products': request.env['product.product'].sudo().search([('can_be_expensed', '=', True)]),
            'expense': expense_sudo,
            'project': project,
            'project_id': project_id,
            'countries' : request.env['res.country'].sudo().search([])
        }
        return {
            'html': request.env.ref('vcls-expenses.expense_modal').render(values),
        }

    @http.route([
        '/my/project/expense/edit'
    ], type='http', auth="user", methods=['POST'], website=True)
    def portal_my_project_expense_modal_confirm(self, project_id=None, expense_id=None, **kw):
        employee_id = request.env.user.sudo().employee_ids
        employee_id = employee_id and employee_id[0]
        if not employee_id:
            # user has no employee, this action cannot be done
            return
        if not project_id or \
                (project_id and not project_id.isdigit()) or \
                (expense_id and not expense_id.isdigit()):
            return
        project_sudo = None
        project_url = '/my/project/{}'.format(project_id)
        try:
            project_sudo = self._document_check_access('project.project', int(project_id))
        except (AccessError, MissingError):
            # If user does not have access to this project
            return request.render("website.403")

        errors = []
        required_fields = [
            'name', 'product_id', 'currency_id', 
        ]
        for field in required_fields:
            if not kw.get(field):
                errors.append(_('A required field is missing.'))
                break
        if errors:
            return request.redirect(project_url)
        expense_sudo = request.env['hr.expense'].sudo()
        if expense_id:
            expense_sudo = expense_sudo.browse(int(expense_id))
            expense_sudo.write(kw)
        else:
            sheet_sudo = request.env['hr.expense.sheet'].sudo()
            sheet_id = sheet_sudo.search([
                ('employee_id', '=', employee_id.id),
                ('project_id', '=', project_sudo.id),
                ('state', '=', 'draft')
            ], limit=1)
            if not sheet_id:
                vals = {
                    'name': kw.get('name'),
                    'project_id': int(project_id),
                    'employee_id': employee_id.id,
                    'type': 'project',
                    'analytic_account_id': project_sudo.analytic_account_id.id,
                    'sale_order_id' : project_sudo.sale_order_id.id,
                    'country_id' : kw.get('country_id', False),
                }
                vals = sheet_sudo._get_info_from_employee(employee_id,vals)
                sheet_id = sheet_sudo.create(vals)
            if not sheet_id.country_id:
                sheet_id.country_id = employee_id.country_id
            kw.update({
                'employee_id': employee_id.id,
                'sheet_id': sheet_id.id,
                'sale_order_id' : sheet_id.project_id.sale_order_id.id,
                'analytic_account_id' : sheet_id.project_id.analytic_account_id.id,
            })
            expense_sudo.create(kw)
        return request.redirect(project_url)

    @http.route([
        '/my/project/expense/delete'
    ], type='http', auth="user", methods=['POST'], website=True)
    def portal_my_project_expense_delete(self, expense_id=None, **kw):
        employee_id = request.env.user.sudo().employee_ids
        employee_id = employee_id and employee_id[0]
        if not employee_id:
            # user has no employee, this action cannot be done
            return
        expense_sudo = request.env['hr.expense'].sudo().browse(int(expense_id))
        sheet_sudo = expense_sudo.sheet_id
        project_sudo = sheet_sudo.project_id
        if not project_sudo:
            return request.redirect('/my')
        project_url = '/my/project/{}'.format(project_sudo.id)
        try:
            # Check that user has access to the linked project
            project_sudo = self._document_check_access('project.project', project_sudo.id)
        except (AccessError, MissingError):
            # If user does not have access to this project
            return request.render("website.403")
        # user does not have access if his linked employee is not the same
        # as the expense report employee
        if employee_id != sheet_sudo.employee_id:
            return request.render("website.403")
        expense_sudo.unlink()
        return request.redirect(project_url)

    @http.route([
        '/my/project/expense/validate'
    ], type='http', auth="user", methods=['POST'], website=True)
    def portal_my_project_expense_validate(self, project_id=None, **kw):
        employee_id = request.env.user.sudo().employee_ids
        employee_id = employee_id and employee_id[0]
        if not employee_id:
            # user has no employee, this action cannot be done
            return
        if not project_id or not project_id.isdigit():
            return
        project_sudo = None
        project_url = '/my/project/{}'.format(project_id)
        try:
            project_sudo = self._document_check_access('project.project', int(project_id))
        except (AccessError, MissingError):
            # If user does not have access to this project
            return request.render("website.403")
        sheet_sudo = request.env['hr.expense.sheet'].sudo()
        sheet_id = sheet_sudo.search([
            ('employee_id', '=', employee_id.id),
            ('project_id', '=', project_sudo.id),
            ('state', '=', 'draft')
        ], limit=1)
        if not sheet_id:
            return
        sheet_id.action_submit_sheet()
        return request.redirect(project_url)
