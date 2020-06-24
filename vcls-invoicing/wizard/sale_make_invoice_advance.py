from odoo import api, fields, models, _
from itertools import groupby
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    group_invoice_method = fields.Selection([
        #('one', 'Only this order'),
        ('project', 'Project and Extensions'),
        ('program', 'Program'),
        #('agreement', 'agreement'),
        ],
        string='Grouping Invoice by', default='project')

    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        self = self.with_context(
            default_company_id=sale_orders[0].company_id.id,
            force_company=sale_orders[0].company_id.id,
        )

        if self.advance_payment_method in ('percentage', 'fixed'):
            return super(SaleAdvancePaymentInv, self).create_invoices()
        context = self._context.copy()
        context['group_invoice_method'] = self.group_invoice_method
        active_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        related_orders = active_orders
        pos = self.env['invoicing.po']

        if self.group_invoice_method == 'project':
            for order in active_orders:
                related_orders |= order.parent_id | order.parent_sale_order_id | order.child_ids

        elif self.group_invoice_method == 'program':
            program_id = False
            for order in active_orders:
                #we test if program_id is populated and unique
                if not order.program_id and not order.parent_id:
                    raise ValidationError("The Order {} has no defined program. Please update or select another mode.".format(order.name))
                if not program_id and order.program_id:
                    program_id = order.program_id
                if program_id and order.program_id:
                    if program_id != order.program_id:
                        raise ValidationError("The Order {} is not part of the program {}.".format(order.name,program_id.name))
            if not program_id:
                raise ValidationError("No program found, please select another invoicing mode.")
            else:
                sale_orders = self.env['sale.order'].search([('program_id', '=', program_id.id)])
                for order in sale_orders:
                    related_orders |= order.parent_id | order.parent_sale_order_id | order.child_ids
                

        # we filter out orders without anything to invoice
        related_orders = related_orders.filtered(lambda so: sum(so.order_line.mapped('untaxed_amount_to_invoice')) > 0)
        pos = related_orders.mapped('po_id')
        # we can't raise an invoice concerning multiple PO's
        if pos and len(pos) > 1:
            raise UserError("You can't raise an invoice related to multiple sales orders ({}) linked to different Client Purchase Orders ({}).".format(related_orders.mapped('name'), pos.mapped('name')))
        context['active_ids'] = related_orders.mapped('id')

        return super(SaleAdvancePaymentInv, self.with_context(context)).create_invoices()

    @api.model
    def _get_children(self, project, children=[]):
        children += project
        for child in project.child_id:
            children += child
            self._get_children(child, children)
        return children

    def get_projects(self,project_id):
        parent_project = project_id.parent_id or project_id
        while parent_project.parent_id:
            parent_project = parent_project.parent_id
        projects = list(set(self._get_children(parent_project)))
        return projects

    def _create_invoice(self, order, so_line, amount):
        self = self.with_context(
            force_company=order.company_id.id,
            company_id=order.company_id.id,
            default_currency_id=order.currency_id.id)
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        # Add the same followers to from the order to the invoice
        order_follower_partner_ids = order.message_partner_ids
        if order_follower_partner_ids:
            invoice._message_subscribe(partner_ids=order_follower_partner_ids.ids)
        return invoice
