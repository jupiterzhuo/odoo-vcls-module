# -*- coding: utf-8 -*-

#Odoo Imports
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class WizardTicket(models.TransientModel):
    _name = 'wizard.ticket'
    _description = 'tbd'
    
    message = fields.Text('Message')
    ticket_id = fields.Many2one('helpdesk.ticket', 'Ticket')
    
    @api.multi
    def set_to_progess(self):
        self.ensure_one()
        progress_stage = self.env.ref('helpdesk.stage_in_progress')
        self.ticket_id.stage_id = progress_stage
        self.ticket_id.message_post(body=self.message)


class Ticket(models.Model):
    
    _inherit = 'helpdesk.ticket'
    
    ###################
    # Default Methods #
    ###################
    @api.model
    def _get_partner_id(self):
        user = self.env['res.users'].browse(self._uid)
        return user.partner_id
    
    @api.model
    def _get_type_id(self):
        return self.env.ref('vcls-helpdesk.ticket_type_incident').id
    
    #################
    # Custom Fields #
    #################
    
    subcategory_id = fields.Many2one(
        'helpdesk.ticket.subcategory',
        string='Subcategory',
        required=True,)
    
    #change management fields
    change_score = fields.Integer(
        store=True,
        compute='_compute_change_score',
    )

    approval_type = fields.Selection([
        ('no', 'None'),
        ('owner', 'Business Owner'),
        ('board', 'Change Management Board')],
    )

    business_value = fields.Selection([
        (1, 'Minor'),
        (2, 'Moderate'),
        (3, 'Strong'),
        (4, 'Major')],
        string='Business Value',
        help='Evaluate taking in account the number of involved people and the added value (time, quality, security, etc.)'
    )
    business_value_description = fields.Text()

    related_effort = fields.Selection([
        (1, 'Minor'),
        (2, 'Moderate'),
        (3, 'Strong'),
        (4, 'Major')],
        string='Effort Assumption',
        help='Evaluate taking into account the developement, training and suport, etc.')
    related_effort_description = fields.Text()
    planned_effort = fields.Integer(
        default = 0,
    )

    related_risk = fields.Selection([
        (1, 'Minor'),
        (2, 'Moderate'),
        (3, 'Strong'),
        (4, 'Major')],
        string='Risk Assumption',)
    related_risk_description = fields.Text()

    user_company = fields.Many2one("res.company", related="partner_id.company_id", string="User Company", store=True)

    @api.depends('business_value','related_effort','related_risk')
    def _compute_change_score(self):
        for change in self:
            if change.business_value and change.related_effort and change.related_risk:
                change.change_score = change.business_value * change.related_effort * change.related_risk
            else:
                change.change_score = False
    
    #overrides for renaming purpose
    name = fields.Char(
        compute='_get_name',
        reverse='_set_name',)
    
    resolution = fields.Char()
    behalf = fields.Boolean(string="Behalf")
    
    display_name = fields.Char(
        compute='_get_name',)
    
    team_id = fields.Many2one(
        string="Category",
        default=False,
        required=True)
    
    partner_id = fields.Many2one(
        string="Requester",
        default=_get_partner_id,)
    
    partner_name = fields.Char(
        string="Requester Name",)
    
    partner_email = fields.Char(
        string="Email",)
    
    ticket_type_id =fields.Many2one()
    
    help_url = fields.Char(
        string='Click for Help',
        default='http://frb-sp-01/sites/IT/VCLS%20Software/Odoo/OdooTickets_QuickGuide_v1.pdf',
        )
    
    dynamic_description = fields.Html()
    
    #used for dynamic views
    access_level = fields.Selection([ 
        ('base', 'Base'),
        ('support', 'Support'),
    ], compute='_get_access_level', store=False)
    
    set_to_progress_visible = fields.Boolean(compute='_get_set_to_progress_visible', store=False)
    
    @api.depends('stage_id')
    def _get_set_to_progress_visible(self):
        awaiting_stage = self.env.ref('__export__.helpdesk_stage_9_1ddd697e')
        for ticket in self:
            ticket.set_to_progress_visible = (ticket.stage_id == awaiting_stage) 
    
    @api.multi
    def open_wizard_set_in_progress(self):
        self.ensure_one()
        
        wiz = self.env['wizard.ticket'].create({
            'ticket_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reply To Support',
            'view_mode': 'form',
            'res_model': 'wizard.ticket',
            'res_id': wiz.id,
            'target': 'new',
        }
    
    #################################
    # Automated Calculation Methods #
    #################################
    @api.multi
    def _get_access_level(self):
        for rec in self:
            user = self.env['res.users'].browse(self._uid)
            if user.has_group('helpdesk.group_helpdesk_user'):
                rec.access_level = 'support'
            else:
                rec.access_level = 'base'
    
    @api.depends('team_id','subcategory_id')
    def _get_name(self):
        for ticket in self:
            if ticket.team_id:
                try:
                    ticket.name = "{:06} | {}".format(ticket.id,ticket.team_id.name)
                except:
                    ticket.name = "{}".format(ticket.team_id.name)
            if ticket.subcategory_id:
                ticket.name = "{} - {}".format(ticket.name,ticket.subcategory_id.name)
            ticket.display_name = ticket.name
    
    @api.onchange('name')
    def _set_name(self):
        for ticket in self: 
            pass
             
    @api.onchange('team_id')
    def _onchange_team_id(self):
        for ticket in self:
            ticket.subcategory_id = False

    @api.multi
    def set_to_closed(self):
        context = self.env.context
        ticket_ids = context.get('active_ids',[])
        for id in ticket_ids:
            ticket = self.env['helpdesk.ticket'].browse(id)
            if (ticket.stage_id == self.env.ref('helpdesk.stage_solved')):
                ticket.stage_id = self.env.ref('__export__.helpdesk_stage_10_30a17dee')
            else:
                raise ValidationError("{} can't be closed. Please solve it before.".format(ticket.name))

            
 #   @api.onchange('partner_id')
 #   def _onchange_partner_id(self):
 #       user = self.env['res.users'].browse(self._uid)
 #       for ticket in self:
 #           if (ticket.partner_id != user.partner_id):
 #               ticket.behalf = True

              
    @api.constrains('stage_id')
    def _check_resolution(self):
        for ticket in self:
            if (ticket.stage_id.name == 'Solved') and not ticket.resolution:
                raise ValidationError("Please document the resolution field before to save.")
                

class TicketSubCategory(models.Model):
    
    _name = 'helpdesk.ticket.subcategory'
    _description = 'Ticket SubCategory'
    _order = 'name'
    
    #################
    # Custom Fields #
    #################
    
    name = fields.Char()
    
    team_id = fields.Many2one(
        'helpdesk.team',
        string='Category',)
    
 
    

    
