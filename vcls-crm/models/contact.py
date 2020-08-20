# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class ContactExt(models.Model):

    _inherit = 'res.partner'
    
    ###  ###
    relation_ids = fields.Many2many(
        'res.partner.relation',
        readonly = True,
        string = 'Mapped Relations',
    )

    sale_order_count_without_cancelled = fields.Integer(compute='_compute_sale_order_count_without_cancelled', string='Sale Order Number')

    ### MARKETING FIELDS FOR TRACEABILITY ###
    
    #Marketing fields
    opted_in = fields.Boolean(
        string = 'Opted In',
    )

    opted_out = fields.Boolean(
        string = 'Opted Out',
    )

    """vcls_contact_id = fields.Many2one(
        'res.users',
        string = "Initial Contact",
        domain = "[('employee','=',True)]",
    )"""

    default_currency_id = fields.Many2one(
        'res.currency',
        compute='_get_default_currency',
        inverse='_set_default_currency',
    )

    core_process_index = fields.Integer(
        default = 0,
        )

    contact_us_message = fields.Char(
        readonly = True,
    )

    sale_profile = fields.Selection(
        selection=[
            ('new','NEW'),
            ('retained','RETAINED'),
            ('black','BLACKLISTED'),
        ],
        default = 'new',
    )

    def _compute_sale_order_count_without_cancelled(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        sale_order_groups = self.env['sale.order'].read_group(
            domain=[('partner_id', 'in', all_partners.ids),('state', '!=', 'cancel')],
            fields=['partner_id'], groupby=['partner_id']
        )
        for group in sale_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.sale_order_count_without_cancelled += group['partner_id_count']
                partner = partner.parent_id

    @api.multi
    @api.depends('property_product_pricelist')
    def _get_default_currency(self):
        ### handle the case where the user's company was created after the currency was set
        for rec in self:
            rec.default_currency_id = rec.property_product_pricelist.currency_id
    
    def _set_default_currency(self):
        #raise UserError('{}'.format(self.default_currency_id.name))
        for rec in self:
            if rec.default_currency_id:
                pricelist = self.sudo().env['product.pricelist'].search([('company_id', '=', False), ('currency_id', '=', rec.default_currency_id.id)], limit=1)
                if not pricelist:
                    raise UserError('Please define a company independent pricelist with currency {} for Contact {}'.format(rec.default_currency_id.name,rec.name))
                for company in self.sudo().env['res.company'].search([]):
                    rec.with_context(force_company=company.id).property_product_pricelist = pricelist[0].id
    
    @api.one
    def _get_new_ref(self):
        #we look for the configuration of the company/parent_company of the current contact to build a reference
        if self.company_type == 'company':
            company = self
        else:
            company = self.parent_id
        
        #if no ALTNAME, then we raise an error
        if not company.altname:
            raise ValidationError("Please document an ALTNAME in the {} client sheet to automate refence calculation.".format(company.name))
        
        else:
            reference = "{}-{:03}".format(company.altname.upper(), company.core_process_index+1)
            company.core_process_index += 1
            return reference

    
    """
    # NOT OVERWRITE CONTEXT
    @api.one
    def _inverse_product_pricelist(self):
        pls = self.env['product.pricelist'].search(
            [('country_group_ids.country_ids.code', '=', self.country_id and self.country_id.code or False)],
            limit=1
        )
        default_for_country = pls and pls[0]
        actual = self.env['ir.property'].get('property_product_pricelist', 'res.partner', 'res.partner,%s' % self.id)

        # update at each change country, and so erase old pricelist
        if self.property_product_pricelist or (actual and default_for_country and default_for_country.id != actual.id):
            # keep the company of the current user before sudo
            self.env['ir.property'].sudo().set_multi(
                'property_product_pricelist',
                self._name,
                {self.id: self.property_product_pricelist or default_for_country.id},
                default_value=default_for_country.id
            )"""