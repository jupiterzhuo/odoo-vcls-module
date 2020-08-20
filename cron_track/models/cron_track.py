# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import Warning


class CronTrack(models.Model):
    _name = "cron.track"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Cron Track"
    _rec_name = 'cron_name'

    cron_name = fields.Char(string="Cron Name")
    start_time = fields.Char(string="Start Time")
    end_time = fields.Char(string="End Time")
    total_time = fields.Char(string="Total Taken Time (in Sec)")
    total_count = fields.Integer(string="Total Count Of Cron Executed", default=0)
    last_date_cron_executed = fields.Datetime(string="Last Date Cron Executed")
    user_id = fields.Many2one('res.users', string="User")
    failed_cron_count = fields.Integer(string="Cron Failed Count", default=0)
    cron_track_log = fields.One2many('cron.track.log', 'cron_track_id', string="Cron Track Log")

    @api.multi
    def open_cron_tracking(self):
        action = self.env.ref('cron_track.action_cron_tracking_log').read()[0]
        cron_log_ids = self.mapped('cron_track_log')
        if len(cron_log_ids) > 1:
            action['domain'] = [('id', 'in', cron_log_ids.ids)]
        elif cron_log_ids:
            action['views'] = [(self.env.ref('cron_track.cron_track_tracking_log_form_view').id, 'form')]
            action['res_id'] = cron_log_ids.id
        if not cron_log_ids:
            raise Warning('There is no Cron Tracking Log Because Every Time Cron Executed Successfully')
        if cron_log_ids:
            return action

    @api.multi
    def action_send_cron_status(self):
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('cron_track', 'cron_status_template')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'cron.track',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_partner_ids': self.user_id.partner_id.ids,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


class CronTrackLog(models.Model):
    _name = "cron.track.log"
    _order = "error_msg_time desc"
    _description = "Cron Track Log"

    cron_track_id = fields.Many2one('cron.track')
    error_msg = fields.Text(string="Error Message")
    error_msg_time = fields.Datetime(string="Error DateTime")
