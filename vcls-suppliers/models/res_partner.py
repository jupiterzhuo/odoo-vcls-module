# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class ExpertiseArea(models.Model):

    _name = 'expertise.area'
    _description = 'Used to search for specific project suppliers.'

    active = fields.Boolean(
        default = True,
    )
    name = fields.Char(
        required = True,
    )

class ProjectSupplierType(models.Model):

    _name = 'project.supplier.type'
    _description = 'Defines contractual situation of the supplier.'

    active = fields.Boolean(
        default = True,
    )
    name = fields.Char(
        required = True,
    )

class ContactExt(models.Model):

    _inherit = 'res.partner'

    _sql_constraints = [
                     ('supplier_code_unique', 
                      'unique(supplier_legacy_code)',
                      'This supplier code already exists.')
                    ]
    
    #################
    # CUSTOM FIELDS #
    #################

    evaluation_ids = fields.One2many(
        'survey.user_input',
        'supplier_id',
        string = 'Evaluations',
    )

    project_supplier_type_id = fields.Many2one(
        'project.supplier.type',
        string = "Project Supplier Type",
    )

    expertise_area_ids = fields.Many2many(
        'expertise.area',
        string="Area of Expertise",
    )

    user_skill_ids = fields.One2many(
        string='Skills',
        comodel_name='res.partner.skill',
        inverse_name='user_id',
    )

    supplier_legacy_code = fields.Char()
    freeze_legacy_code = fields.Boolean(
        readonly=True
    )

    siren = fields.Char()
    vat_number = fields.Char()

    def action_po(self):
        return {
            'name': 'Purchase Order',
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'current',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'context': {'search_default_partner_id': self.id},
        } 
    
    def merge_yooz(self):
        for rec in self:
            if not rec.supplier_legacy_code:
                raise UserError("Please document a legacy supplier code for {}".format(rec.name))

            related_contact = self.with_context(active_test=False).search([('active','=',False),('name','=',rec.supplier_legacy_code)])
            if related_contact:
                rec.write({
                    'company_type': 'company',
                    'name': rec.name if rec.name else related_contact[0].name,
                    'company_id': False if len(related_contact)>1 else related_contact[0].company_id.id,
                    'country_id': related_contact[0].country_id.id if related_contact[0].country_id else False,
                    'siret': self.merge_list_string(related_contact.mapped('siret')),
                    'siren': self.merge_list_string(related_contact.mapped('siren')),
                    'vat_number': self.merge_list_string(related_contact.mapped('vat_number')),
                    'phone': self.merge_list_string(related_contact.mapped('phone')),
                    'fax': self.merge_list_string(related_contact.mapped('fax')),
                    'email': self.merge_list_string(related_contact.mapped('email')),
                    'street': self.merge_list_string(related_contact.mapped('street')),
                    'street2': self.merge_list_string(related_contact.mapped('street2')),
                    'zip': self.merge_list_string(related_contact.mapped('zip')),
                    'city': self.merge_list_string(related_contact.mapped('city')),
                    'website': self.merge_list_string(related_contact.mapped('website')),
                })

                banking = self.merge_list_string(related_contact.mapped('comment')),
                if len(banking)>1:
                    sep = banking.find('|')
                    if sep == 1:
                        iban = False
                        bic = banking[1:]
                    elif sep == len(banking):
                        iban = banking[:-1]
                        bic = False
                    else:
                        iban = banking.split('|')[0]
                        bic = banking.split('|')[1]
                    
                    if iban:
                        existing_account = self.env['res.partner.bank'].search([('acc_number','=',iban)],limit=1)
                        if not existing_account:
                            self.env['res.partner.bank'].create({
                                'acc_number':iban,
                                'company_id':False,
                                'partner_id':rec.id,
                            })
                        else:
                            existing_account.write({'partner_id':rec.id})

    
    def merge_list_string(self,source):
        for item in source:
            if item != '':
                return item
        return False
        
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):

        supplier_search = self._context.get('supplier_search')

        #if we are in the context of a vcls custom search
        if supplier_search:
            expertise_ids = self._context.get('expertise_ids')[0][2]
            expertises = self.env['expertise.area'].browse(expertise_ids)

            partner_ids = super(ContactExt, self)._search(args, offset, None, order, count=count, access_rights_uid=access_rights_uid)
            partners = self.browse(partner_ids)

            #we filter according to the expertises
            if expertises:
                partners = partners.filtered(lambda p: expertises in p.expertise_area_ids)
            
            #if no one has been found,propose default one
            if len(partners)==0:
                try:
                    not_found = self.env.ref('vcls-suppliers.not_found_sup')
                    return not_found.id
                except:
                    pass
        
            return partners.ids
        
        else:
            partner_ids = super(ContactExt, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)
            return partner_ids

