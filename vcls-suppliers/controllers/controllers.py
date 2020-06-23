# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.project.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.tools import groupby as groupbyelem
from collections import OrderedDict
from operator import itemgetter
from odoo.http import request
from odoo.osv.expression import OR
from datetime import datetime


class CustomerPortal(CustomerPortal):
    
    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()

        uid = request.env.context.get('uid')

        # Only count user's project
        # (a project where a user has a task assigned)
        values['project_count'] = len(request.env['project.task'].search([('user_id','=',uid)]).mapped('project_id'))

        # Only count user's task
        values['task_count'] = request.env['project.task'].search_count([('user_id','=',uid)])
        return values

    # add domain to show only user's project
    @http.route(['/my/projects', '/my/projects/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_projects(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Project = request.env['project.project']

        uid = request.env.context.get('uid')
        project_ids = request.env['project.task'].search([('user_id','=',uid)]).mapped('project_id')

        domain = [('id', 'in', project_ids.ids)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.project', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        # projects count
        project_count = Project.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/projects",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=project_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        projects = Project.sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_projects_history'] = projects.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'projects': projects,
            'page_name': 'project',
            'archive_groups': archive_groups,
            'default_url': '/my/projects',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("project.portal_my_projects", values)

    @http.route(['/my/tasks', '/my/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_tasks(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', groupby='project', **kw):
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Title'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'stage': {'input': 'stage', 'label': _('Search in Stages')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'project': {'input': 'project', 'label': _('Project')},
        }

        # extends filterby criteria with project the customer has access to
        projects = request.env['project.project'].search([])
        for project in projects:
            searchbar_filters.update({
                str(project.id): {'label': project.name, 'domain': [('project_id', '=', project.id)]}
            })

        # extends filterby criteria with project (criteria name is the project id)
        # Note: portal users can't view projects they don't follow
        project_groups = request.env['project.task'].read_group([('project_id', 'not in', projects.ids)],
                                                                ['project_id'], ['project_id'])
        for group in project_groups:
            proj_id = group['project_id'][0] if group['project_id'] else False
            proj_name = group['project_id'][1] if group['project_id'] else _('Others')
            searchbar_filters.update({
                str(proj_id): {'label': proj_name, 'domain': [('project_id', '=', proj_id)]}
            })

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters[filterby]['domain']

        ## ADD DOMAIN FILTER HERE ##

        # ADD FILTER TO SHOW ONLY ASSIGNED TASK
        uid = request.env.context.get('uid')
        domain += [('user_id','=',uid)]

        ## END OF VCLS MODIFICATIONS ##

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.task', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search)]])
            if search_in in ('stage', 'all'):
                search_domain = OR([search_domain, [('stage_id', 'ilike', search)]])
            domain += search_domain

        # task count
        task_count = request.env['project.task'].search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/tasks",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            total=task_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        if groupby == 'project':
            order = "project_id, %s" % order  # force sort on project first to group by project in view
        tasks = request.env['project.task'].search(domain, order=order, limit=self._items_per_page, offset=(page - 1) * self._items_per_page)
        request.session['my_tasks_history'] = tasks.ids[:100]
        if groupby == 'project':
            grouped_tasks = [request.env['project.task'].concat(*g) for k, g in groupbyelem(tasks, itemgetter('project_id'))]
        else:
            grouped_tasks = [tasks]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'grouped_tasks': grouped_tasks,
            'page_name': 'task',
            'archive_groups': archive_groups,
            'default_url': '/my/tasks',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("project.portal_my_tasks", values)
    
    def check_timesheet(post):
        error = []
        if not post.get('date'):
            error += [_('Date not specified.')]
        if not post.get('name'):
            error += [_('Description not specified.')]
        if not post.get('unit_amount'):
            error += [_('Duration not specified.')]
        else:
            try:
                if float(post['unit_amount']) < 0:
                    error += [_('Duration cannot be negative.')]
                else:
                    post['unit_amount'] = float(post['unit_amount'])
            except:
                error += [_('Invalid duration format.')]
        try:
            datetime.strptime(post['date'], '%Y-%m-%d')
        except:
            error += [_('Invalid date format. Valid format should be YYYY-MM-DD')]
        
        return error
    
    # Override in order to support error messages
    @http.route(['/my/task/<int:task_id>'], type='http', auth="public", website=True)
    def portal_my_task(self, task_id, access_token=None, error = [], **kw):
        try:
            task_sudo = self._document_check_access('project.task', task_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._task_get_page_view_values(task_sudo, access_token, **kw)
        values['errors'] = error

        # GET ALL TIME_CATEGORY
        values['time_categories'] = task_sudo.time_category_ids

        return request.render("project.portal_my_task", values)
    
    @http.route(['/my/task/<int:task_id>/timesheets/new'], type='http', auth='user', methods=['POST'], website=True)
    def add_new_timesheet(self, task_id, redirect=None, **post):
        try:
            task_sudo = self._document_check_access('project.task', task_id, None)
        except (AccessError, MissingError):
            return request.render("website.403")

        if post and task_sudo.user_id == request.env.user:
            # START PROCESSING DATA
            error = CustomerPortal.check_timesheet(post)
            if not error:

                project = task_sudo.project_id
                if not project:
                    error += [_('Please ask the website administrator to link this task to a project')]

                employee = request.env['hr.employee'].sudo().search([('user_id','=',request.env.user.id)])
                if not employee:
                    error += [_("No external employee found for {}").format(request.env.user.name)]
                
                #Over budget error
                if task_sudo.total_hours_spent + float(post['unit_amount']) > task_sudo.planned_hours:
                    error += [_('Overbudget error, only {} hours remaing in this task. Please contact your lead consultant.').format(task_sudo.planned_hours-task_sudo.total_hours_spent)]

                if not error:
                    values = {
                        'date': datetime.strptime(post['date'], '%Y-%m-%d'),
                        'project_id': project.id,
                        'task_id': task_sudo.id,
                        'employee_id': employee.id,
                        'unit_amount': float(post['unit_amount']),
                        'name': post['name'],
                    }
                    if post.get('time_category_id', False):
                        values.update({'time_category_id': post['time_category_id']})
                    analytic_line = request.env['account.analytic.line'].sudo().create(values)
                    analytic_line._link_portal_analytic_line_purchase(request.env.user)
                    # END OF PROCESSING DATA
            return self.portal_my_task(task_id, error=error)
        else:
            return request.render("website.403")
    
    @http.route(['/my/task/<int:task_id>/timesheets/<int:timesheet_id>/edit'], type='http', auth='user', methods=['POST'], website=True)
    def edit_timesheet(self, task_id, timesheet_id, redirect=None, **post):
        try:
            task_sudo = self._document_check_access('project.task', task_id, None)
        except (AccessError, MissingError):
            return request.render("website.403")

        if post and task_sudo.user_id == request.env.user:
            # START PROCESSING DATA
            error = CustomerPortal.check_timesheet(post)
            if len(error) == 0:
                values = post.copy()
                values['date'] = datetime.strptime(values['date'], '%Y-%m-%d')
                #values['stage_id'] = 'draft'
                timesheet = request.env['account.analytic.line'].sudo().search([('id', '=', timesheet_id)])
                if timesheet and not timesheet.validated:
                    timesheet.write(values)
            return self.portal_my_task(task_id, error=error)
        else:
            return request.render("website.403")
