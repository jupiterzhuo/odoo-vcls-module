# Copyright 2015 Incaser Informatica S.L. - Sergio Teruel
# Copyright 2015 Incaser Informatica S.L. - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    completion_ratio = fields.Float(
        string = "Completion Ratio",
        help = "Task at this stage are inheriting related completion ratio."
    )

    project_type_default = fields.Selection([
        ('dev', 'Developement'),
        ('client', 'Client'),
        ('internal','Internal')],
        string = 'Project Type for Default',
    )
