# -*- coding: utf-8 -*-

#Odoo Imports
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class LeaveType(models.Model):
    
    _inherit = 'hr.leave.type'
    #_order = 'sequence'
   
    #################
    # Custom Fields #
    #################
    
    impacts_lunch_tickets = fields.Boolean(
        string='Impact Lunch Ticket',)
    
    max_carry_over = fields.Integer(
        string='Maximum Carry Over',
        default='0',)
    
    comment = fields.Char(
        string='Comment',)
    
    is_managed_by_hr = fields.Boolean(
        string='Is Managed by HR',
        default=False,)
    
    validity_start_ord = fields.Integer(
        compute='_compute_validity_start_ord',
        )
    
    authorize_negative = fields.Boolean(
        string = 'Authorize Negative',
        default = False,
        )
    
    payroll_type = fields.Selection([
        ('rtt', 'RTT'),
        ('cp_paid', 'CP Paid'),
        ('cp_unpaid', 'CP Unpaid'),
        ('sick', 'Sick'),
        ('other_paid','Other Paid'),
        ])
    
    """# this fields will just be used to trigger various path in the _search below.
    # in can be added to the domain in the view, and will then appear in the args values of the _search
    search_args_filter_1 = fields.Char(
        readonly=True,
        default="no0",
    )"""
    
    ##################
    # Search methods #
    ##################
    @api.depends('validity_start')
    def _compute_validity_start_ord(self):
        for type in self:
            if type.validity_start:
                type.validity_start_ord = type.validity_start.toordinal()
            else: type.validity_start_ord = 1
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """
        Override _search to order the results, according to some employee.
        The order is the following

         - allocation fixed first, then allowing allocation, then free allocation
         - virtual remaining leaves (higher the better, so using reverse on sorted)

        This override is necessary because those fields are not stored and depends
        on an employee_id given in context. This sort will be done when there
        is an employee_id in context and that no other order has been given
        to the method.
        """
        
        employee_id = self._get_contextual_employee_id()
        no_zero = self.env.context.get('no_zero',False)
        
        #if this seaerch is called by a view where the below domain has been defined.
        #This is used to have different search function according to the view
        leave_ids = super(LeaveType, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        #_logger.info("LEAVE TYPE SEARCH | {} {} {} \n {}".format(self.env['hr.employee'].browse(employee_id).name if employee_id else 'NO EMPLOYEE',no_zero,args,self.browse(leave_ids).mapped('name') if leave_ids else 'NO LEAVES FOUND'))
        if not count and not order and employee_id and no_zero:
            leaves = self.browse(leave_ids)
            #we remove the leaves types based on allocations but with a counter == 0
            for item in leaves:
                if (item.allocation_type  in ['fixed','fixed_allocation']) and item.virtual_remaining_leaves == 0:
                    leaves -= item
            
            #oldest counter 1st
            sort_key = lambda l: (l.allocation_type == 'fixed', l.allocation_type == 'fixed_allocation', l.virtual_remaining_leaves>0, 1/l.validity_start_ord, l.allocation_type == 'no')
            return leaves.sorted(key=sort_key, reverse=True).ids
        
        return leave_ids
        