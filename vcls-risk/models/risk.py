# -*- coding: utf-8 -*-
import datetime
from odoo import models, fields, api, http, _

from odoo.exceptions import UserError, ValidationError


class RiskType(models.Model):
    _name = 'risk.type'
    _description = 'A Type of Risk'

    name = fields.Char(required=True)
    active = fields.Boolean(required=True, default=True)
    description = fields.Char()
    model_name = fields.Char(required=True)
    group_id = fields.Many2one('res.groups')
    notify = fields.Boolean()
    weight = fields.Integer(default=1)
    category = fields.Char()


class Risk(models.Model):
    _name = 'risk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A Risk'

    risk_type_id = fields.Many2one(
        'risk.type', string="Type of risk",
        required=True)

    note = fields.Char()

    resource = fields.Char(string='Resource', index=True, help="If not set, acts as a default value for new resources")

    risk_level = fields.Selection(
        [(0, 'Solved'), (1, 'Low'), (2, 'Moderate'), (3, 'Significant'), (4, 'High')],
        'Risk Level',
        default=2,
        track_visibility="onchange",
    )

    last_notification = fields.Datetime(readonly=True)

    score = fields.Integer(string="Score", compute="_compute_score", store=True)

    name = fields.Char(
        compute = '_compute_name',
        store = True
    )

    @api.depends('risk_type_id','risk_level')
    def _compute_name(self):
        for risk in self:
            risk.name = "{} - {}".format(risk.risk_type_id.name,risk.risk_level)

    @api.depends('risk_level', 'risk_type_id.weight')
    def _compute_score(self):
        for risk in self:
            if risk.risk_level:
                risk.score = risk.risk_level * risk.risk_type_id.weight
            else:
                risk.score = 0

    @api.model
    def _raise_risk(self, risk_type, resource):
        risk = self.create({'risk_type_id': risk_type.id, 'resource': resource})
        risk.send_notification()
        return risk
    
    def _populate_risk_ids(self):
        for risk in self:
            parts = risk.resource.split(',')
            target = self.env[parts[0]].browse(int(parts[1]))
            if target:
                target._compute_risk_ids()

    def send_notification(self):
        risk_type = self.risk_type_id
        if risk_type.notify:
            partner_ids = []
            for user in risk_type.group_id.users:
                partner_ids.append(user.partner_id.id)
            if partner_ids:
                self.message_subscribe(partner_ids=partner_ids)
                self.message_post(body="Risk created", partner_ids=[4, partner_ids])
                self.last_notification = datetime.datetime.now()

    @api.onchange('risk_level')
    def _onchange_risk_level(self):
        if not self._context.get('new_risk',False):
            group_id = self.risk_type_id.group_id
            if group_id:
                if self.env.user not in self.risk_type_id.group_id.users:
                    raise UserError("You need to be part of {} to modify the risk level".format(group_id.name))

    def go_to_record(self):
        resource = str(self.resource).split(',')
        if len(resource) == 2:
            url = http.request.env['ir.config_parameter'].get_param('web.base.url')
            link = "{}/web#id={}&model={}".format(url, resource[1], resource[0])
            return {
                'type': 'ir.actions.act_url',
                'url': link,
                'target': 'current',
            }

    @api.constrains('resource')
    def _check_resource(self):
        if self.resource:
            resource_parts = self.resource.split(',')
            if len(resource_parts) != 2:
                raise ValidationError(_('Wrong resource field format'))
            res_model, res_id = resource_parts[0], resource_parts[1]
            if res_model not in self.env:
                raise ValidationError(_('Resource model is not valid'))
            if not res_id.isdigit() or not self.env[res_model].browse(int(res_id)).exists():
                raise ValidationError(_('Resource id is not valid'))

    @api.model
    def create(self, vals):
        risk = super(Risk, self).create(vals)
        risk_resource = risk.resource
        model = risk_resource.split(',')[0]
        model_id = risk_resource.split(',')[1]
        obj = self.env[model].browse(int(model_id))
        obj._compute_risk_ids()
        return risk

    def write(self, vals):
        risk = super(Risk, self).write(vals)
        risk_resource = self.resource
        model = risk_resource.split(',')[0]
        model_id = risk_resource.split(',')[1]
        obj = self.env[model].browse(int(model_id))
        obj._compute_risk_ids()
        return risk
