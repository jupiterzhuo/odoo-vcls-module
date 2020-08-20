# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)


class LeadQuotation(models.TransientModel):
    _name = 'lead.quotation.wizard'
    _description = 'Lead Quotation Wizard'

    quotation_type = fields.Selection([
        ('new', 'New project'),
    #     ('budget_extension', 'Budget extension'),
        ('scope_extension', 'Scope extension'),
    ], string='Quotation type', required=True, default='new'
    )

    existing_quotation_id = fields.Many2one(
        'sale.order', string="Existing quotation"
    )

    partner_id = fields.Many2one(
        'res.partner',
    )

    link_rates = fields.Boolean(
        default = True,
        help="If ticked, rates of the parent quotation will be copied to childs, and linked during the life of the projects",
    )

    @api.multi
    def confirm(self):
        self.ensure_one()
        action = self.env.ref('sale_crm.sale_action_quotations_new').read()[0]
        _logger.info("OPP to QUOTE before: {}".format(action['context']))
        context = self._context
        active_model = context.get('active_model', '')
        active_id = context.get('active_id')
        _logger.info("OPP to QUOTE context {}".format(context))

        if not active_model in ['crm.lead','sale.order'] or not active_id:
            return
        else:
            temp = self.env[active_model].browse(active_id)

        if active_model == 'sale.order':
            lead = temp.opportunity_id
        else:
            lead = temp
        
        #lead = self.env['crm.lead'].browse(active_id)
        _logger.info("OPP to QUOTE lead {}".format(lead.id))
        additional_context = {
            'search_default_partner_id': lead.partner_id.parent_id.id or lead.partner_id.id,
            'default_partner_id': lead.partner_id.parent_id.id or lead.partner_id.id,
            'default_partner_shipping_id': lead.partner_id.id,
            'default_team_id': lead.team_id.id,
            'default_campaign_id': lead.campaign_id.id,
            #'default_medium_id': lead.medium_id.id,
            'default_origin': lead.name,
            'default_source_id': lead.source_id.id,
            'default_opportunity_id': lead.id,
            'default_sale_profile': lead.sale_profile,
            'default_program_id': lead.program_id.id,
            'default_scope_of_work': lead.scope_of_work,
            'default_product_category_id': lead.product_category_id.id,
            'default_expected_start_date': lead.expected_start_date,
            'lead_quotation_type': self.quotation_type,
            'default_link_rates': self.link_rates,
        }

        action['context'] = additional_context
        
        if self.quotation_type == 'new':
            return action
        if self.quotation_type in ('budget_extension', 'scope_extension') and self.existing_quotation_id:
            # copy the quotation content
            fields_to_copy = [
                'pricelist_id', 'currency_id', 'note', 'team_id',#'tag_ids',
                'active', 'fiscal_position_id', 'risk_score', 'program_id', 'opportunity_id',
                'company_id', 'deliverable_id', 'product_category_id', 'business_mode',
                'agreement_id', 'po_id', 'payment_term_id', 'validity_date',
                'scope_of_work', 'user_id', 'core_team_id', 'invoicing_frequency',
                'risk_ids', 'expected_start_date', 'expected_end_date', 'revision_number',
            ]
            values = self.existing_quotation_id.read(fields_to_copy)[0]
            values['revision_number'] += 1
            all_quotation_fields = self.existing_quotation_id._fields
            default_values = dict(
                ('default_{}'
                 .format(k),
                 v and v[0] or False if all_quotation_fields[k].type == 'many2one' else v)
                for k, v in values.items()
            )
            action['context'].update(default_values)

            #we copy rate lines, even for scope extention, in the case of linked_rate
            if self.quotation_type != 'new' and self.link_rates:
                rate_lines = self.existing_quotation_id.order_line.filtered(lambda l: l.vcls_type=='rate')
                if rate_lines:
                    section = rate_lines[0].section_line_id
                    new_lines = [{'display_type': 'line_section','name':section.name}]#we initiate with the Section line
                    for rl in rate_lines:
                        vals = {
                            'product_id':rl.product_id.id,
                            'name':rl.name,
                            'product_uom_qty':rl.product_uom_qty,
                            'product_uom':rl.product_uom.id,
                            'price_unit':rl.price_unit,
                        }
                        _logger.info("New Line:{}".format(vals))
                        new_lines.append(vals)
                    
                    order_lines = [(5, 0, 0)] + [
                    (0, 0, values)
                    for values in new_lines
                    ]
                
                    action['context'].update({
                        'default_order_line': order_lines,
                    })
                    
            # copy parent_id
            action['context'].update({
                'default_parent_sale_order_id': self.existing_quotation_id.id,
                #'default_parent_id': self.existing_quotation_id.id,
            })
            #_logger.info("OPP to QUOTE action context {}".format(action['context']))
        return action
