# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api


class Ticket(models.Model):

    _inherit = 'helpdesk.ticket'

    project_id = fields.Many2one(
        'project.project',
        string='Related Project',
    )

    task_id = fields.Many2one(
        'project.task',
        string='Related Task',
    )
