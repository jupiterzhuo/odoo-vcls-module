# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class CountryGroup(models.Model):
    _inherit = 'res.country.group'

    group_type = fields.Selection([
        ('BD', 'Business Development'),
        ],
        string='Group Type',
        track_visibility='onchange',
        default=False,
    ) 


class ResPartner(models.Model):

    _inherit = 'res.partner'
    
    ### CUSTOM FIELDS FOR EVERY KIND OF CONTACTS ###

    description = fields.Text()

    hidden = fields.Boolean(
        string="Confidential",
        default=False,
    )

    is_internal = fields.Boolean(
        string="Is Internal",
        compute='_compute_is_internal',
        store=True,
        default=False,
    )
    
    stage = fields.Selection([
        (1, 'Undefined'),
        (2, 'New'),
        (3, 'Verified'),
        (4, 'Outdated'),
        (5, 'Archived')], 
        string='Stage',
        track_visibility='onchange',
        default=2,
    )

    sharepoint_folder = fields.Char(
        string='Sharepoint Folder',
        compute='_compute_sharepoint_folder',
        readonly=True,
        store=True,
    )
    manual_sharepoint_folder = fields.Char()

    create_folder = fields.Boolean(
        string="Create Sharepoint Folder",
    )

    ### THe objective of this field is to assist responsible roles in contact completion exercise and maintain a good data quality
    completion_ratio = fields.Float(
        string="Est. Data Completion",
        compute='_compute_completion_ratio',
        default=0.0,
    )

    #Contact fields
    fax = fields.Char()

    ### CLIENT RELATED FIELDS ###

    #override to rename
    user_id = fields.Many2one(
        'res.users',
        string = 'Account Manager',
        domain=lambda self: [("groups_id", "in", [self.env.ref('vcls_security.vcls_account_manager').id])]
    )
    #override to link
    activity_user_id = fields.Many2one(
        'res.users',
        related='user_id',
        store=True,
        domain=lambda self: [("groups_id", "=", self.env['res.groups'].search([('name','=', 'Account Manager')]).id)]
    )

    linkedin = fields.Char(
        string='LinkedIn Profile',
    )
    
    #BD fields
    country_group_id = fields.Many2one(
        'res.country.group',
        string="Geographic Area",
        compute='_compute_country_group',
    )
    
    client_activity_ids = fields.Many2many(
        'client.activity',
        string='Client Activity',
    )

    client_product_ids = fields.Many2many(
        'client.product',
        string='Client Product',
    )

    number_of_employee = fields.Selection(
        selection = [
            ('1_10', '1-10'),
            ('11_50', '11-50'),
            ('51_200', '51-200'),
            ('201_500', '201-500'),
            ('501_2000', '501-2000'),
            ('2000', '+2000'),
            ]
    )

    
    
    #project management fields
    assistant_id = fields.Many2one(
        'res.users',
        string='Project Assistant',
    )

    expert_id = fields.Many2one(
        'res.users',
        string='Main Expert',
    )

    #finance fields
    controller_id = fields.Many2one(
        'res.users',
        string='Project Controller'
    )

    invoice_admin_id = fields.Many2one(
        'res.users',
        string='Invoice Administrator',
    )

    #connection with external systems

    altname = fields.Char(
        string='AltName',
    )

    ### FIELDS FOR INDIVIDUALS ###
    # We override title to rename it
    title = fields.Many2one(
        string='Salutation',
    )
    function = fields.Char(
        string='Job Title',
        help='Please use \"tbc\" if unknown.',
    )

    functional_focus_id = fields.Many2one(
        'partner.functional.focus',
        string='Functional  Focus',
    )

    partner_seniority_id = fields.Many2one(
        'partner.seniority',
        string='Seniority',
    )

    partner_assistant_id = fields.Many2one(
        'res.partner',
        string='Contact Assistant',
    )

    referent_id = fields.Many2one(
        'res.partner',
        string='Referred By',
    )

    ### VIEW VISIBILITY
    see_segmentation = fields.Boolean (
        compute='_compute_visibility',
        default=False,
        store=True,
    )
    see_supplier = fields.Boolean (
        compute='_compute_visibility',
        default=False,
        store=True,
    )
    # log note company change
    parent_id = fields.Many2one(
        track_visibility='always'
    )

    vcls_contact_id = fields.Many2one(
        'res.users',
        string = "VCLS Sponsor",
        domain = "[('employee','=',True)]",
    )

    client_status = fields.Selection([
        ('new', 'New'),
        ('active', 'Active'),
        ('blacklisted', 'Blacklisted'),
    ], compute='_get_client_status')

    #accounting fields for legacy integration
    legacy_account = fields.Char(
        default="/",
    )
    
    external_account = fields.Char(
        compute = '_compute_external_account',
        store = True,
    )

    company_id = fields.Many2one(
        'res.company',
        default=False,
    )

    ###################
    # COMPUTE METHODS #
    ###################

    @api.onchange('stage')
    def _update_stage(self):
        for rec in self:
            rec.active = False if rec.stage == 5 else True


    @api.multi
    @api.depends('legacy_account','customer','supplier','employee')
    def _compute_external_account(self):
        for partner in self:
            if partner.customer:
                partner.external_account = partner.legacy_account
                continue
            if partner.employee:
                #we grab the employee
                employee = self.env['hr.employee'].search([('address_home_id.id','=',partner.id)],limit=1)
                if employee:
                    partner.external_account = employee.employee_external_id
                    continue
            else:
                pass

    @api.multi
    @api.depends('sale_order_ids.state')
    def _get_client_status(self):
        for partner in self:
            client_status = 'new'
            for order_id in partner.sale_order_ids:
                if order_id.state in ('sent', 'sale', 'done'):
                    client_status = 'active'
                    break
            partner.client_status = client_status

    @api.depends('category_id', 'company_type')
    def _compute_visibility(self):
        for contact in self:
            contact.see_segmentation = False
            if self.env.ref('vcls-contact.category_account', raise_if_not_found=False) in contact.category_id and contact.is_company:
                contact.see_segmentation = True
            contact.see_supplier = False
            if self.env.ref('vcls-contact.category_PS', raise_if_not_found=False) in contact.category_id:
                contact.see_supplier = True

    @api.onchange('category_id')
    def _update_booleans(self):
        for contact in self:
            if self.env.ref('vcls-contact.category_account', raise_if_not_found=False) in contact.category_id:
                contact.customer = True
            else:
                contact.customer = False

            if self.env.ref('vcls-contact.category_suppliers', raise_if_not_found=False) in contact.category_id \
                    or self.env.ref('vcls-contact.category_PS', raise_if_not_found=False) in contact.category_id \
                    or self.env.ref('vcls-contact.category_AS', raise_if_not_found=False) in contact.category_id:
                contact.supplier = True
            else:
                contact.supplier = False

    @api.depends('employee')
    def _compute_is_internal(self):
        for contact in self:
            if contact.employee or self.env['res.company'].search([('partner_id.id','=',contact.id)]):
                contact.is_internal = True
    
    @api.depends('country_id')
    def _compute_country_group(self):
        for contact in self:
            #groups = contact.country_id.country_group_ids.filtered([('group_type','=','BD')])
            groups = contact.country_id.country_group_ids
            if groups:
                contact.country_group_id = groups[0]

    def _compute_completion_ratio(self):
        for contact in self:
            pass
            """ This estimator is related to the type of contact."""

    @api.depends('category_id', 'create_folder','altname','manual_sharepoint_folder')
    def _compute_sharepoint_folder(self):
        #manual case
        manual = self.filtered(lambda p: p.manual_sharepoint_folder)
        for partner in manual:
            partner.sharepoint_folder = partner.manual_sharepoint_folder
            partner.create_folder = True

        #suppliers
        auto_suppliers = self.filtered(lambda p: not p.manual_sharepoint_folder and p.supplier and p.is_company)
        pre = self.env.ref('vcls-contact.SP_supplier_root_prefix').value
        for partner in auto_suppliers:
            partner.sharepoint_folder = "{}/{}".format(pre,partner.name)
            partner.create_folder = True

        #clients
        auto_clients = self.filtered(lambda p: not p.manual_sharepoint_folder and p.customer and p.is_company and p.altname)
        pre = self.env.ref('vcls-contact.SP_client_root_prefix').value
        post = self.env.ref('vcls-contact.SP_client_root_postfix').value
        for partner in auto_clients:
            partner.sharepoint_folder = "{}/{}/{}{}".format(pre,partner.altname[0],partner.altname,post)
            partner.create_folder = True

    # We reset the number of bounced emails to 0 in order to re-detect problems after email change
    @api.onchange('email')
    def _onchange_mail(self):
        for contact in self:
            contact.message_bounce = 0
            contact_id = contact.id if not isinstance(contact.id, models.NewId) else 0
            if contact.email and self.sudo().search([('id', '!=', contact_id), ('email', '=', contact.email)], limit=1):
                return {'warning': {
                    'title': _("Warning"),
                    'message': _("A contact with this email already exists."),
                }}

    ##################
    # ACTION METHODS #
    ##################

    @api.multi
    def _set_stage_new(self):
        context = self.env.context
        contact_ids = context.get('active_ids',[])
        self.env['res.partner'].browse(contact_ids).write({'stage': 2,'active':True})
    
    @api.multi
    def _set_stage_verified(self):
        context = self.env.context
        contact_ids = context.get('active_ids',[])
        self.env['res.partner'].browse(contact_ids).write({'stage': 3,'active':True})
    
    @api.multi
    def _set_stage_outdated(self):
        context = self.env.context
        contact_ids = context.get('active_ids',[])
        self.env['res.partner'].browse(contact_ids).write({'stage': 4,'active':True})
    
    @api.multi
    def _set_stage_archived(self):
        context = self.env.context
        contact_ids = context.get('active_ids',[])
        self.env['res.partner'].browse(contact_ids).write({'stage': 5,'active':False})
    
    @api.onchange('category_id', 'company_type')
    def update_individual_tags(self):
        for contact in self:
            if contact.company_type == 'company':
                for child in contact.child_ids:
                    if child.company_type == 'person':
                        child.write({'category_id': [(6, 0, contact.category_id.ids)]})

    @api.model
    def create(self, vals):

        #if no ID defined, then increment using the sequence
        if vals.get('legacy_account','/')=='/':
            vals['legacy_account'] = self.env['ir.sequence'].next_by_code('seq_customer_account_id')

        if vals.get('email',False):
            # we search for existing partners with the same email, but we authorize the creation of a company AND an individual with the same email
            existing = self.env['res.partner'].search([('email','=ilike',vals.get('email'))],limit=1)
            #_logger.info("email {} existing {} all vals {}".format(vals.get('email'),existing.mapped('name'),vals))
            if existing and not '@vcls.com' in vals['email']:
                if vals.get('is_company') == existing.is_company:
                    raise UserError("We already found a entry with the same email {}.".format(existing.mapped('email')))
            
        new_contact = super(ResPartner, self).create(vals)
        if new_contact.type != 'contact':
            type_contact = new_contact.type
            new_contact.write({'display_name' : new_contact.display_name + ' (' + type_contact + ')' })

        #we grab the parent tags
        new_contact.grab_parent_categ()

        return new_contact
    
    def grab_parent_categ(self):
        for contact in self:
            if contact.parent_id:
                contact.category_id |= contact.parent_id.category_id
            
    def add_new_adress(self):
        view_id = self.env.ref('vcls-contact.view_form_contact_address').id
        return {
            'name': 'ADD NEW ADRESS',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'context': {
                'default_name': self.name,
                'default_parent_id': self.id,
                'default_category_id': self.category_id.ids,
                'default_company_type': 'person'
            }
        }
