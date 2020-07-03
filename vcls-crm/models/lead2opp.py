from odoo import models, fields, tools, api
from odoo.exceptions import UserError, ValidationError, Warning

class Lead2OpportunityPartner(models.TransientModel):

    # Replace only label for name
    _inherit = 'crm.lead2opportunity.partner'

    name = fields.Selection([
        ('convert', 'Convert to new opportunity'),
        ('merge', 'Merge with existing opportunity')
    ], 'Conversion Action', required=True)

    opp_name = fields.Char(string = 'Opportunity Name', default = False)

    @api.model
    def _get_opp_name(self):
        lead = self.env['crm.lead'].browse(self._context['active_id'])
        lead_name = lead.partner_name
        if lead.partner_id:
            count = len(self.env['crm.lead'].search([('type','=','opportunity'),('partner_id','=', lead.partner_id.id)])) + 1
        else:
            count = 1
        return "{} - {:03}".format(lead_name, count)
    
    @api.multi
    def action_apply(self):
        """ Convert lead to opportunity or merge lead and opportunity and open
            the freshly created opportunity view.
        """
        self.ensure_one()
        values = {
            'team_id': self.team_id.id,
        }
        # removed wizard to choose, always link now
        self.action = 'exist'
        lead_obj = self.env['crm.lead'].browse(self._context.get('active_ids', []))
        if self.partner_id:
            values['partner_id'] = self.partner_id.id
        if self.partner_id.is_company == True:
            existing_contact = self.env['res.partner'].search([('email', '=', lead_obj.email_from)], limit=1)
            if existing_contact and not existing_contact.is_company:
                if existing_contact.parent_id == self.partner_id:
                    values['partner_id']= existing_contact.id
                else:
                    UserError("contact: {} has a differnt company({}) than in lead ({})".format(existing_contact.name,existing_contact.parent_id.name,self.partner_id.name))
                existing_contact.origin_lead_id = lead_obj.id
            else:
                new_contact = self.env['res.partner']
                new_contact = new_contact.create(lead_obj._create_lead_partner_data(lead_obj.contact_name, False, lead_obj.partner_id.id))
                values['partner_id']= new_contact.id
                new_contact.gdpr_status = lead_obj.gdpr_status
                new_contact.opted_in = lead_obj.opted_in
                new_contact.opted_out = lead_obj.opted_out
        if self.name == 'merge':
            leads = self.with_context(active_test=False).opportunity_ids.merge_opportunity()
            if not leads.active:
                leads.write({'active': True, 'activity_type_id': False, 'lost_reason': False})
            if leads.type == "lead":
                values.update({'lead_ids': leads.ids, 'user_ids': [self.user_id.id]})
                self.with_context(active_ids=leads.ids)._convert_opportunity(values)
            elif not self._context.get('no_force_assignation') or not leads.user_id:
                values['user_id'] = self.user_id.id
                leads.write(values)
        else:
            leads = self.env['crm.lead'].browse(self._context.get('active_ids', []))
            values.update({'lead_ids': leads.ids, 'user_ids': [self.user_id.id]})
            self._convert_opportunity(values)
            ### VCLS MODS ###
            # Update lead / opportunity name
            leads[0].write({'name': self.opp_name})
            ### END MODS ###

        return leads[0].redirect_opportunity_view()
