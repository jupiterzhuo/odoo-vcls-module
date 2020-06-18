# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError


class UserGroupHistory(models.Model):
    _name = 'user.group.history'
    _description = 'user.group.history'

    user_ids = fields.Many2many('res.users')
    group_ids = fields.Many2many('res.groups')
    added = fields.Boolean()

    @api.multi
    def send_notif(self):
        self.ensure_one()
        # TODO: Change the 'test.' when you change the module name
        self.env.ref('vcls-hr.email_template_user_group_history').send_mail(self.id)
    
    @api.multi
    def write(self, vals):
        raise ValidationError("Modification of this record is not authorized.")

    @api.multi
    def unlink(self):
        raise ValidationError("Deletion of this record is not authorized.")


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def write(self, vals):
        # TODO: Groups to be notified
        notif_groups = self.env.ref('vcls-hr.vcls_group_HR_global') | self.env.ref('vcls-hr.vcls_group_HR_local') | self.env.ref('base.group_system') | self.env.ref('base.group_erp_manager')
        hold_groups = {user: user.groups_id for user in self}

        res = super(ResUsers, self).write(vals)

        for user, groups in hold_groups.items():
            added_groups = (user.groups_id - groups) & notif_groups
            removed_groups = (groups - user.groups_id) & notif_groups

            if added_groups:
                self.env['user.group.history'].create({
                    'user_ids': [(6, 0, user.ids)],
                    'group_ids': [(6, 0, added_groups.ids)],
                    'added': True,
                }).send_notif()

            if removed_groups:
                self.env['user.group.history'].create({
                    'user_ids': [(6, 0, user.ids)],
                    'group_ids': [(6, 0, removed_groups.ids)],
                }).send_notif()

        return res


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.multi
    def write(self, vals):
        # TODO: Groups to be notified
        notif_groups = self.env.ref('vcls-hr.vcls_group_HR_global') | self.env.ref('vcls-hr.vcls_group_HR_local') | self.env.ref('base.group_system') | self.env.ref('base.group_erp_manager')
        hold_users = {group: group.users for group in self & notif_groups}

        res = super(ResGroups, self).write(vals)

        for group, users in hold_users.items():
            added_users = group.users - users
            removed_users = users - group.users

            if added_users:
                self.env['user.group.history'].create({
                    'user_ids': [(6, 0, added_users.ids)],
                    'group_ids': [(6, 0, group.ids)],
                    'added': True,
                }).send_notif()

            if removed_users:
                self.env['user.group.history'].create({
                    'user_ids': [(6, 0, removed_users.ids)],
                    'group_ids': [(6, 0, group.ids)],
                }).send_notif()

        return res