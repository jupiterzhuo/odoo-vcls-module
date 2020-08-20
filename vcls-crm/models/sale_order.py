# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api
from collections import OrderedDict
from odoo.tools import OrderedSet

from odoo.exceptions import UserError, ValidationError, Warning
import math

import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    product_category_id = fields.Many2one(
        'product.category',
        string='Business Line',
        domain="[('is_business_line','=',True)]"
    )

    catalog_mode = fields.Selection([
        ('generic','Generic'),
        ('template','Template'),
        ('migration','Migration'),
        ], compute = '_compute_catalog_mode')
    
    catalog_details = fields.Boolean(
        default = False,
    )
    
    company_id = fields.Many2one(default=lambda self: self.env.ref('vcls-hr.company_VCFR'))

    business_mode = fields.Selection([ 
        ('all', 'All'),
        ('services', 'Services'),
        ('rates', 'Rates'),
        ('subscriptions', 'Subscriptions'),
        ], default='all',
        string="Product Type")
    
    invoicing_mode = fields.Selection([
        ('tm', 'Time & Material'), 
        ('fixed_price', 'Fixed Price'), 
        ], default='tm',
        string="Invoicing Mode")

    deliverable_id = fields.Many2one(
        'product.deliverable',
        string="Deliverable"
    )
    expected_start_date = fields.Date()
    expected_end_date = fields.Date()

    scope_of_work = fields.Html(
        string="Scope of Work"
    )

    user_id = fields.Many2one(
        'res.users', 
        track_visibility='onchange', 
        domain=lambda self: [("groups_id", "=", self.env['res.groups'].search([('name','=', 'Account Manager')]).id)]
    )

    # We never use several projects per quotation, so we highlight the 1st of the list
    project_id = fields.Many2one(
        'project.project',
        string='Project Name',
        compute='_compute_project_id',
        store=True,
    )

    parent_id = fields.Many2one(
        'sale.order',
        string="Parent Quotation",
        copy=True,
    )
    child_ids = fields.One2many(
        'sale.order', 'parent_id',
        'Child Quotations'
    )

    link_rates = fields.Boolean(
        default = False,
        help="If ticked, rates of the parent quotation will be copied to childs, and linked during the life of the projects",
    )

    # Used as a hack to get the parent_id value
    # as for odoo default_parent_id in context is assigned
    # message.message parent_id
    parent_sale_order_id = fields.Many2one(
        'sale.order',
        string="Hack Parent Quotation",
    )

    internal_ref = fields.Char(
        string="Ref",
        store=True,
    )

    name = fields.Char(
        string='Order Reference',
        required=True, copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        index=True, default=lambda self: 'New'
    )
    family_order_count = fields.Integer(
        'Family Order Count', compute='_get_family_order_count'
    )
    
    family_quotation_count = fields.Integer(
        'Family Quotation Count', compute='_get_family_order_count'
    )

    report_details = fields.Selection([
        ('simple', 'simple'),
        ('detailed', 'detailed')],
        'Report details', default='simple'
    )
    report_rate = fields.Boolean(
        'Report rate', default=True
    )

    validity_duration = fields.Selection([
        ('1', '1 month'),
        ('2', '3 month'),
        ('5', '5 month')],
        string='Validity duration', default='1')
    
    probability = fields.Float(
        help='Related to the parent opportunity',
        compute='_compute_probability',
        readonly=True,
        store=True,
        default=0.01,
    )

    @api.depends('opportunity_id','opportunity_id.probability')
    def _compute_probability(self):
        for so in self.filtered(lambda p: p.opportunity_id):
            so.probability = so.opportunity_id.probability
    

    sale_status = fields.Selection(
        selection=[
            ('draft','Draft'),
            ('sent','Sent'),
            ('cancel','Cancelled'),
            ('lost','Lost'),
            ('won','Won'),],
        default='draft',
        store=True,
        compute='_compute_sale_status',
    )

    @api.depends('probability','state')
    def _compute_sale_status(self):
        for so in self:
            if so.probability == 0.0:
                so.sale_status = 'lost'
            elif so.state in ['cancel','sent']:
                so.sale_status = so.state
            elif so.probability == 100:
                so.sale_status = 'won'
            else:
                so.sale_status = 'draft'
    
    sale_profile = fields.Selection(
        selection=[
            ('new','NEW'),
            ('retained','RETAINED'),
            ('filtered','FILTERED OUT'),
        ],
    )



    ###############
    # ORM METHODS #
    ###############

    @api.multi
    def _get_family_order_count(self):
        for project in self:
            parent_order, child_order = self._get_family_sales_orders()
            all_family_orders = (parent_order | child_order)
            family_orders = all_family_orders.filtered(lambda o: o.state not in ('draft', 'cancel'))
            family_quotation = all_family_orders.filtered(lambda o: o.state == 'draft')
            project.family_order_count = len(family_orders)
            project.family_quotation_count = len(family_quotation)

    @api.onchange('parent_sale_order_id')
    def _onchange_parent_sale_order_id(self):
        if self.parent_sale_order_id:
            self.parent_id = self.parent_sale_order_id

    @api.model
    def create(self, vals):
        _logger.info("SO CREATE: {}".format(vals))
        if self.env.user.context_data_integration:
            _logger.info("SO CREATE: {}".format(vals))
        # if we force the creation of a quotation with an exiting internal ref (e.g. during migration)
        if vals.get('internal_ref'):
            vals['name'] = self._get_name_without_ref(vals['internal_ref'], vals['name'])

        # if related to an opportunity, we build the internal ref accordingly
        elif 'opportunity_id' in vals:
            opp_id = vals.get('opportunity_id')
            opp = self.env['crm.lead'].browse(opp_id)

            #we check if the partner is an individual, if yes, we change it to the parent company
            if not opp.partner_id.is_company:
                if opp.partner_id.parent_id:
                    vals['partner_id'] = opp.partner_id.parent_id.id
                    vals['partner_invoice_id'] = opp.partner_id.id
                    vals['partner_shipping_id'] = opp.partner_id.id
                else:
                    raise ValidationError("You can't create a quotation with an individual ({}) without a configured company.".format(opp.partner_id.name))


            # parent_id is readonly, so it cant go on vals upon creation
            # we use parent_sale_order_id as an intermediate value for that
            if vals.get('parent_sale_order_id') and not vals.get('parent_id'):
                vals['parent_id'] = vals['parent_sale_order_id']
                vals.pop('parent_sale_order_id')
                

            if 'parent_id' in vals: #in this case, we are upselling and add a numerical index to the reference of the original quotation
                parent_id = vals.get('parent_id')
                parent = self.env['sale.order'].browse(parent_id)
                other_childs = self.sudo().with_context(active_test=False).search([('opportunity_id','=',opp_id),('parent_id','=',parent_id)])
                if other_childs: #this is not the 1st upsell
                    index = len(other_childs)+1
                else: #this is the 1st upsell
                    index = 1
                vals['internal_ref'] = "{}.{}".format(parent.internal_ref,index)

            
            else: #in this case, we add an alpha index to the reference of the opp
                prev_quote = self.sudo().with_context(active_test=False).search([('opportunity_id','=',opp_id),('parent_id','=',False)])
                if prev_quote: 
                    index = len(prev_quote)+1
                else:
                    index = 1
                vals['internal_ref'] = "{}-{}".format(opp.internal_ref,self.get_alpha_index(index))

            quotation_original_name = vals['name']
            if 'lead_quotation_type' in self._context and vals.get('parent_id'):
                lead_quotation_type = self._context.get('lead_quotation_type')
                if lead_quotation_type in ('budget_extension', 'scope_extension'):
                    additional_name = 'Budget extension' if lead_quotation_type == 'budget_extension' \
                        else 'Scope extension'
                    vals['name'] = "{} | {}".format(quotation_original_name, additional_name)
                    
            vals['name'] = "{} | {}".format(vals['internal_ref'], vals['name'])

            # default expected_start_date and expected_end_date
            expected_start_date = opp.expected_start_date
            if expected_start_date:
                vals['expected_start_date'] = expected_start_date
                #vals['expected_end_date'] = expected_start_date + relativedelta(months=+3)
        #_logger.info("{}".format(vals))     
        order = super(SaleOrder, self).create(vals)
        return order

    @api.multi
    def write(self, vals):
        # we keep the duration fixed, even if we change the start date
        if 'expected_start_date' in vals:
            expected_start_date = fields.Date.from_string(vals['expected_start_date'])
            for so in self:
                if so.expected_end_date and so.expected_start_date and expected_start_date:
                    so.expected_end_date = expected_start_date + (so.expected_end_date - so.expected_start_date)
        ret = super(SaleOrder, self).write(vals)
        self.remap()
        """#we take in account changes in the rate products to be reported in childs
        if vals.get('order_line',False):
            _logger.info("Write SO lines: {}".format(vals['order_line']))"""
        return ret 

    ###################
    # COMPUTE METHODS #
    ###################

    @api.multi
    @api.onchange('partner_shipping_id', 'partner_id')
    def onchange_partner_shipping_id(self):
        #we force the context to the sales order company
        self.fiscal_position_id = self.env['account.fiscal.position'].with_context(force_company=self.company_id.id).get_fiscal_position(self.partner_id.id, self.partner_shipping_id.id)
        return {}


    @api.depends('product_category_id','tag_ids')
    def _compute_catalog_mode(self):
        for so in self:
            auto_migration_tag = self.env['crm.lead.tag'].search([('name','=','Automated Migration')],limit=1)
            generic_catalog = self.env['product.category'].search([('name','=','General Services')])
            so.catalog_mode = 'template'
            if generic_catalog:
                if so.product_category_id == generic_catalog[0]:
                    so.catalog_mode = 'generic'
                    so.catalog_details = 'True'
            if auto_migration_tag:
                if auto_migration_tag in so.tag_ids:
                    so.catalog_mode = 'migration'
                    

    @api.depends('project_ids')
    def _compute_project_id(self):
        for so in self:
            if so.project_ids:
                so.project_id = so.project_ids[0]

    @api.multi
    def _get_family_sales_orders(self):
        """
        :return: parent sale order, children sales orders
        """
        self.ensure_one()
        parent_order = self.parent_id or self
        child_ids = parent_order.child_ids
        return parent_order, child_ids

    @api.multi
    def _get_family_projects(self):
        """
        :return: parent project record, children projects records
        """
        parent_order, child_orders = self._get_family_sales_orders()
        return parent_order.project_id, child_orders.mapped('project_id')

    @api.multi
    def action_view_family_quotations(self):
        self.ensure_one()
        action = self.env.ref('sale_crm.sale_action_quotations').read()[0]
        parent_order_id, child_orders = self._get_family_sales_orders()
        all_orders = parent_order_id | child_orders
        action['domain'] = [('state', '=', 'draft'), ('id', 'in', all_orders.ids)]
        return action

    @api.multi
    def action_view_family_sales_orders(self):
        self.ensure_one()
        action = self.env.ref('sale_crm.sale_action_quotations').read()[0]
        parent_order_id, child_orders = self._get_family_sales_orders()
        all_orders = parent_order_id | child_orders
        action['domain'] = [('state', 'not in', ('draft', 'cancel')), ('id', 'in', all_orders.ids)]
        return action

    @api.multi
    def action_confirm(self):
        ret = super().action_confirm()
        self._check_sale_profile()
        return ret
    
    

    ################
    # TOOL METHODS #
    ################
    def _check_sale_profile(self):
        """
        If this is a new client related quote and we confirm it, then:
            - The client turns from new to retained
            - All quotations related the same opportunity remains NEW
            - The related opportunity remains NEW
            - All other records (Opps and Quotes) are turned to RETAINED
        """
        self.ensure_one()
        if self.sale_profile == 'new':
            #we update the parter and related
            partners = self.env['res.partner']
            partners |= self.partner_id | self.partner_id.parent_id | self.partner_id.child_ids
            partners.write({'sale_profile':'retained'})

            if self.opportunity_id:
                #we look for opportunities related to the same partner, the related one is new, the others turn into retained
                opps = self.env['crm.lead'].with_context(active_test=False).search([('partner_id','in',partners.ids),'|',('sale_profile','!=','filtered'),('sale_profile','=',False)])
                _logger.info("OPPS {} | {}".format(opps.mapped('name'),partners.mapped('name')))
                self.opportunity_id.sale_profile = 'new'
                opps -= self.opportunity_id
                _logger.info("OPPS {}".format(opps.mapped('name')))
                opps.write({'sale_profile':'retained'})

                #we do the same with sales orders
                new_sos = self.search([('opportunity_id','=',self.opportunity_id.id),'|',('sale_profile','!=','filtered'),('sale_profile','=',False)])
                _logger.info("SOS {}".format(new_sos.mapped('name')))
                new_sos.write({'sale_profile':'new'})
                all_sos = self.search([('partner_id','in',partners.ids),'|',('sale_profile','!=','filtered'),('sale_profile','=',False)])
                all_sos -= new_sos
                all_sos.write({'sale_profile':'retained'})
                _logger.info("SOS {}".format(all_sos.mapped('name')))

            

    def _get_name_without_ref(self,ref="ALTNAME-XXX",raw_name=""):
        parts = raw_name.lower().split(ref.lower()) #we use the ref to split
        parts.reverse() #we reverse to get the last part for any length
        return parts[0].strip()

    @api.multi
    def _write(self, values):
        """ We override to cancel the automated creation of upselling messages"""
        if values.get('invoice_status','') == 'upselling':
            self = self.with_context(mail_activity_automation_skip = True)
            _logger.info("UPSELLING {}".format(self.env.context))
        """if 'invoice_status' in values:
            rem = values.pop('invoice_status')""" 

        return super(SaleOrder, self)._write(values)
    
    @api.multi
    def upsell(self):
        for rec in self:
            new_order = rec.copy({'order_line': False,'parent_id':rec.id})

            """
            pending_section = None

            #we loop in source lines to copy rate ones only
            for line in rec.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                elif line.product_id.type == 'service' and \
                    line.product_id.service_policy == 'delivered_timesheet' and \
                    line.product_id.service_tracking in ('no', 'project_only'):
                    if pending_section:
                        pending_section.copy({'order_id': new_order.id})
                        pending_section = None
                    line.copy({'order_id': new_order.id,
                               'project_id': line.project_id.id,
                               'analytic_line_ids': [(6, 0, line.analytic_line_ids.ids)]})"""
        return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order',
                'target': 'current',
                'res_id': new_order.id,
            }

    @api.model
    def get_alpha_index(self, index):
        map = {1:'A', 2:'B', 3:'C', 4:'D', 5:'E', 6:'F', 7:'G', 8:'H', 9:'I', 10:'J',
                11:'K', 12:'L', 13:'M', 14:'O', 15:'P', 16:'Q', 17:'R', 18:'S', 19:'T',
                20:'U', 21:'V', 22:'W', 23:'X', 24:'Y', 26:'Z'}
        
        suffix = ""
        for i in range(math.ceil(index / 26)):
            key = index - i * 26
            suffix += "{}".format(map[key % 26])
        
        # need to add scope
        return suffix

    @api.multi
    def _get_aggregated_order_report_data(self):
        services_data, services_subtotal = self._get_aggregated_order_report_services()
        return {
            'services_subtotal': services_subtotal,
            'services_data': services_data,
        }

    @api.multi
    def _get_detailed_order_report_data(self):
        services_data, services_subtotal = self._get_detailed_order_report_services()
        return {
            'services_subtotal': services_subtotal,
            'services_data': services_data,
        }

    @api.multi
    def _get_detailed_order_report_services(self):
        """
        :param self:
        :return: ordered dictionary with the following structure
        { 'service_section_line_record': {
                service_line_record : {
                    'subtotal': subtotal,
                    'currency_id': currency,
                }
            },...
        }
        """
        self.ensure_one()
        services_data = OrderedDict()
        services_subtotal = 0.
        for line in self.order_line:
            if line.product_id.vcls_type != 'vcls_service':
                continue
            section_line_id = line.section_line_id
            section_services_data = services_data.setdefault(section_line_id, OrderedDict())
            section_services_data.setdefault(line, {
                'subtotal': line.price_subtotal,
                'currency_id': line.currency_id,
            })
            services_subtotal += line.price_subtotal
        for services_data_key in services_data:
            for key in list(services_data[services_data_key]):
                value = services_data[services_data_key][key]
                if not value['subtotal']:
                    del services_data[services_data_key][key]
        return services_data, services_subtotal

    @api.multi
    def _get_aggregated_order_report_services(self):
        """
        :param self:
        :return: ordered dictionary with the following structure
        { 'service_section_line_record': {
                    'subtotal': subtotal,
                    'currency_id': currency,
            },...
        }
        """
        self.ensure_one()
        services_data = OrderedDict()
        services_subtotal = 0.
        for line in self.order_line:
            if line.product_id.vcls_type != 'vcls_service':
                continue
            section_line_id = line.section_line_id
            section_services_data = services_data.setdefault(section_line_id, {
                'subtotal': 0.,
                'currency_id': line.currency_id,
            })
            section_services_data['subtotal'] += line.price_subtotal
            services_subtotal += line.price_subtotal
        for key in list(services_data):
            value = services_data[key]
            if not value['subtotal']:
                del services_data[key]
        return services_data, services_subtotal

    @api.multi
    def remap(self):
        #_logger.info("SO remap")
        for so in self:
            sect_index = 0
            for line in so.order_line:
                if not line.section_line_id: #this is a section line
                    sect_index += 100
                    line_index = 0

                line.sequence = sect_index + line_index
                line_index += 1
                
            #we order the rates in decreasing price_unit order
            rate_lines = so.order_line.filtered(lambda r: r.product_id.vcls_type == 'rate')
            if rate_lines:
                min_seq = min(rate_lines.mapped('sequence'))
                for line in rate_lines.sorted(lambda s: s.price_unit, reverse=True):
                    line.sequence = min_seq
                    min_seq += 1

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        # keep partner_shipping_id as the original one, don't change it
        # unless it was not set
        partner_shipping_id = self.partner_shipping_id
        super(SaleOrder, self).onchange_partner_id()
        if partner_shipping_id:
            self.update({
               'partner_shipping_id': partner_shipping_id,
            })
    
    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):
        """
         We override this to manage the case of link_rates=True.
         In the case of Linked Rates, the parent order is defineing the rates, not the template.
        """
        super(SaleOrder,self).onchange_sale_order_template_id()
        if self.link_rates and self.parent_id and self.sale_order_template_id:

            #we remove the newly created rate lines
            self.order_line = self.order_line.filtered(lambda l: l.vcls_type != 'rate')

            order_lines = []
            #then copy the parent_ones
            for rl in self.parent_id.order_line.filtered(lambda l: l.vcls_type == 'rate'):
                vals = {
                    'product_id':rl.product_id.id,
                    'name':rl.name,
                    'product_uom_qty':rl.product_uom_qty,
                    'product_uom':rl.product_uom.id,
                    'price_unit':rl.price_unit,
                }
                #_logger.info("New Line:{}".format(vals))
                order_lines.append((0, 0, vals))
            
            _logger.info("KPI | {}".format(order_lines))
          
            self.order_line = order_lines
            self.order_line._compute_tax_id()
    
    

"""
class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    @api.model
    def _get_fpos_by_region(self, country_id=False, state_id=False, zipcode=False, vat_required=False):
        if not country_id:
            return False
        base_domain = [('auto_apply', '=', True), ('vat_required', '=', vat_required)]
        if self.env.context.get('force_company'):
            base_domain.append(('company_id', 'in', [self.env.context.get('force_company'), False]))
        null_state_dom = state_domain = [('state_ids', '=', False)]
        null_zip_dom = zip_domain = [('zip_from', '=', 0), ('zip_to', '=', 0)]
        null_country_dom = [('country_id', '=', False), ('country_group_id', '=', False)]

        # DO NOT USE zipcode.isdigit() b/c '4020²' would be true, so we try/except
        try:
            zipcode = int(zipcode)
            if zipcode != 0:
                zip_domain = [('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]
        except (ValueError, TypeError):
            zipcode = 0

        if state_id:
            state_domain = [('state_ids', '=', state_id)]

        domain_country = base_domain + [('country_id', '=', country_id)]
        domain_group = base_domain + [('country_group_id.country_ids', '=', country_id)]

        # Build domain to search records with exact matching criteria
        fpos = self.search(domain_country + state_domain + zip_domain, limit=1)
        _logger.info("FP exact {}".format(domain_country + state_domain + zip_domain))
        # return records that fit the most the criteria, and fallback on less specific fiscal positions if any can be found
        if not fpos and state_id:
            fpos = self.search(domain_country + null_state_dom + zip_domain, limit=1)
            _logger.info("FP state {}".format(domain_country + null_state_dom + zip_domain))
        if not fpos and zipcode:
            fpos = self.search(domain_country + state_domain + null_zip_dom, limit=1)
            _logger.info("FP zip {}".format(domain_country + state_domain + null_zip_dom))
        if not fpos and state_id and zipcode:
            fpos = self.search(domain_country + null_state_dom + null_zip_dom, limit=1)
            _logger.info("FP state and zip {}".format(domain_country + null_state_dom + null_zip_dom))

        # fallback: country group with no state/zip range
        if not fpos:
            fpos = self.search(domain_group + null_state_dom + null_zip_dom, limit=1)
            _logger.info("FP country {}".format(domain_group + null_state_dom + null_zip_dom))

        if not fpos:
            # Fallback on catchall (no country, no group)
            fpos = self.search(base_domain + null_country_dom, limit=1)
            _logger.info("FP fallback {}".format(base_domain + null_country_dom))

        _logger.info("FP fp {}".format(fpos))
        return fpos or False

    @api.model
    def get_fiscal_position(self, partner_id, delivery_id=None):
        if not partner_id:
            return False
        # This can be easily overridden to apply more complex fiscal rules
        PartnerObj = self.env['res.partner']
        partner = PartnerObj.browse(partner_id)

        # if no delivery use invoicing
        if delivery_id:
            delivery = PartnerObj.browse(delivery_id)
        else:
            delivery = partner

        # partner manually set fiscal position always win
        if delivery.property_account_position_id or partner.property_account_position_id:
            return delivery.property_account_position_id.id or partner.property_account_position_id.id

        # First search only matching VAT positions
        vat_required = bool(partner.vat)
        fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, vat_required)

        # Then if VAT required found no match, try positions that do not require it
        if not fp and vat_required:
            fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, False)

        return fp.id if fp else False
"""