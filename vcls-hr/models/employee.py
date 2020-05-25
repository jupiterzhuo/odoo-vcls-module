# -*- coding: utf-8 -*-

#Python Imports
from datetime import date, datetime, time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
#Odoo Imports
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class Employee(models.Model):
    
    _inherit = 'hr.employee'
    _sql_constraints = [
                     ('employee_external_id_unique', 
                      'unique(employee_external_id)',
                      'Employee ID is not unique.')
                    ]
    
    #################
    # Custom Fields #
    #################
    
    # Connectivity with other systems
    
    employee_external_id = fields.Char(
        string='Employee ID',
        default="/",)
    
    # Overriden fields
    name = fields.Char()
    
    gender = fields.Selection(
        default=False,)
    
    contract_id = fields.Many2one(store=True)
    
    
    resource_calendar_id = fields.Many2one(
        related='contract_id.resource_calendar_id',
        readonly = True,
        store=True,
        )
    
    job_id = fields.Many2one(
        related='contract_id.job_id',
        readonly = True,
        store = True
        )
    
    department_id = fields.Many2one(
        related='contract_id.job_id.department_id',
        readonly = True,
        store = True
        )
    
    job_title = fields.Char(
        related='contract_id.job_id.project_role_id.name',
        readonly = True,
        store = True
        )

    address_home_id = fields.Many2one(
        comodel_name='res.partner',
        related='user_id.partner_id',
        )
    
    
    # Administrative informations
    employee_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
        ('template', 'Template'),
        ],default = 'internal'
    )

    first_name = fields.Char(
        string='First Name',
        track_visibility='always',)
    
    middle_name = fields.Char(
        string='Middle Name',
        track_visibility='always',)
    
    family_name = fields.Char(
        string='Family Name',
        track_visibility='always',)

    consultancy_percentage = fields.Integer(
        default=100,
        string="Consulting %",)
    
    # Used in ABsent Today view in order to display leave period
    leave_duration_type = fields.Selection(
        [ ('am', 'Morning'),('pm', 'Afternoon') ],
        string = 'Half Day Leave',
        readonly = True,
        compute='_compute_leave_duration_type',
    )
    
    #########################################
    # OVERRIDEN FIELDS FOR GROUP VISIBILITY #
    #########################################
    
    gender = fields.Selection(groups=False)
                                  
    #######################
    # CONFIDENTIAL FIELDS #
    #######################
    confidential_id = fields.One2many('hr.employee.confidential','employee_id')
    
    # Those fields are deported in an external object 
    
    ### /!\ Confidential information
    link_employee_folder = fields.Char(
        string='Employee Folder',
        help='Paste folder url',
        compute='_compute_link_employee_folder',
        #inverse='_set_link_employee_folder'
        )
    
    ### /!\ Confidential information
    birthday = fields.Date(String='Date of Birth',
                          compute='_compute_birthday',
                          inverse='_set_birthday',
                          groups=False)
    
    ### /!\ Confidential information
    family_name_at_birth = fields.Char(
        string='Family Name at Birth',
        compute='_compute_family_name_at_birth',
        inverse='_set_family_name_at_birth')
    
    ### /!\ Confidential information
    children = fields.Integer(
        compute='_compute_children',
        inverse='_set_children')
    
    ### /!\ Confidential information
    #### /!\ Overwritten field
    ssnid = fields.Char(String='Social Security Number',
                       compute='_compute_ssnid',
                       inverse='_set_ssnid',
                       groups=False)
    
    ### /!\ Confidential information
    #### /!\ Overwritten field
    country_id = fields.Many2one(
        'res.country',
        String='Primary Citizenship',
        compute='_compute_country_id',
        inverse='_set_country_id',
        groups=False)
    
    ### /!\ Confidential information
    country2_id = fields.Many2one(
        'res.country',
        String='Secondary Citizenship',
        compute='_compute_country2_id',
        inverse='_set_country2_id')

    ### /!\ Confidential information
    place_of_birth = fields.Char(
        compute='_compute_place_of_birth',
        inverse='_set_place_of_birth')
    
    ### /!\ Confidential information
    #### /!\ Overwritten field
    permit_no = fields.Char(String='Work Permit',
                           track_visibility='always',
                           compute='_compute_permit_no',
                           inverse='_set_permit_no',
                           groups=False)
    
    ### /!\ Confidential information
    work_permit_expire = fields.Date(
        string='Work Permit Expiring Date',
        compute='_compute_work_permit_expire',
        inverse='_set_work_permit_expire',
        groups=False)
    
    ## Contact informations
    ### /!\ Confidential information
    street = fields.Char(
        string='Street',
        compute='_compute_street',
        inverse='_set_street')
    
    ### /!\ Confidential information
    street2 = fields.Char(
        string='Street 2',
        compute='_compute_street2',
        inverse='_set_street2')
    
    ### /!\ Confidential information
    city = fields.Char(
        compute='_compute_city',
        inverse='_set_city')
    
    ### /!\ Confidential information
    state_id = fields.Many2one(
        'res.country.state',
        string = 'State',
        compute='_compute_state_id',
        inverse='_set_state_id')
    
    ### /!\ Confidential information
    zip = fields.Char(
        string='ZIP',
        compute='_compute_zip',
        inverse='_set_zip')
    
    ### /!\ Confidential information
    address_country_id = fields.Many2one(
        'res.country',
        string="Country",
        compute='_compute_address_country_id',
        inverse='_set_address_country_id')
    
     ### /!\ Confidential information
    #### /!\ Overwritten field
    private_email = fields.Char(
        string="Private Email",
        compute='_compute_private_email',
        inverse='_set_private_email',
        groups=False)
   
    ### /!\ Confidential information
    private_phone = fields.Char(
        string='Private Phone',
        compute='_compute_private_phone',
        inverse='_set_private_phone')
    
    ### /!\ Confidential information
    #### /!\ Overwritten field
    emergency_contact = fields.Char(String = 'Emergency Contact',
                                   compute='_compute_emergency_contact',
                                   inverse='_set_emergency_contact',
                                   groups=False)
    
    ### /!\ Confidential information
    #### /!\ Overwritten field
    emergency_phone = fields.Char(String = 'Emergency Phone',
                                 compute='_compute_emergency_phone',
                                 inverse='_set_emergency_phone',
                                 groups=False)
    
    ### /!\ Confidential information
    #### Casted as Char in employee_confidential
    ice_contact_relationship = fields.Selection(
        string='Emergency Contact Relationship',
        selection='_selection_relationship',
        compute='_compute_ice_contact_relationship',
        inverse='_set_ice_contact_relationship')
    
    ### /!\ Confidential information
    notes = fields.Text(
        compute='_compute_notes',
        inverse='_set_notes') # Don't have label
    
    #Health Care Management
    ### /!\ Confidential information
    last_medical_checkup = fields.Date(
        string="Last Medical Check-up",
        track_visibility='always',
        compute='_compute_last_medical_checkup',
        inverse='_set_last_medical_checkup')
    
    ### /!\ Confidential information
    specific_next_medical_checkup = fields.Date(
        compute='_compute_specific_next_medical_checkup',
        inverse='_set_specific_next_medical_checkup') #used to store manually entered value in the below inverse case
    
    ### /!\ Confidential information
    #### Computed field
    ##### onchange -> modify specific_next_medical_checkup -> employee_confidential
    next_medical_checkup = fields.Date(
        string="Next Medical Check-up",
        compute='_compute_next_medical_checkup',
        inverse='_set_next_medical_checkup',
        track_visibility='always',)
    
    ### /!\ Confidential information
    need_specific_medical = fields.Boolean(
        string="Need Specific Medical Follow-up",
        track_visibility='always',
        compute='_compute_need_specific_medical',
        inverse='_set_need_specific_medical')
    
    ## Health insurance
    ### /!\ Confidential information
    affiliation_date = fields.Date(
        string='Affiliation Date',
        compute='_compute_affiliation_date',
        inverse='_set_affiliation_date')
    
    ### /!\ Confidential information
    affiliated_company = fields.Char(
        string='Affiliated Company',
        compute='_compute_affiliated_company',
        inverse='_set_affiliated_company')
    
    ### /!\ Confidential information
    medical_policy_number = fields.Char(
        string='Medical Policy Number',
        compute='_compute_medical_policy_number',
        inverse='_set_medical_policy_number')
    
    #Generic job info (i.e. not linked to the job position object nor the employee contract)
    employee_seniority_date = fields.Date(
        string='Employee Seniority Date',
        track_visibility='always',)
    
    employee_start_date = fields.Date(
        string='Employee Start Date',
        track_visibility='always',)
    
    employee_end_date = fields.Date(
        string='Employee End Date',
        track_visibility='always',)
    
    employee_end_reason = fields.Selection(
        string='End Reason',
        selection='_selection_termination',
        track_visibility='always',)
    
    office_id = fields.Many2one(
        'hr.office',
        string='Office',)
    
    #Trial period management
    trial_period_id = fields.Many2one(
        'hr.trial.period',
        string='Trial Period',
        domain="[('company_id', '=', company_id)]",)
    
    trial_start_date = fields.Date(
        string='Trial Period Start Date',)
    
    trial_end_date = fields.Date(
        string='Trial Period End Date',
        compute='_compute_trial_end_date',)
    
    trial_notification_date = fields.Date(
        string='Trial Period Notification Date',
        compute='_compute_trial_end_date',)
    
    #business card fields
    job_info = fields.Char(
        string='Title',
        compute='_set_job_info',
        track_visibility='always',)
    
    diploma_ids = fields.Many2many(
        'hr.diploma',
        string="Diplomas",)
    
    #Related to job position(s)
    
    job_profile_id = fields.Many2one(
        'hr.job_profile',
        string="Current Job Profile",
        readonly=True,
        )
    
    bonus_ids = fields.Many2many(
        'hr.bonus',
        string="Over Variable Salary",
        compute = "_get_bonuses",)
    """
    contract_ids = fields.Many2many(
        'hr.contract',
        'employee_id',
        readonly = True,
        )
    """
    
    #Benefit related
    benefit_ids = fields.Many2many(
        'hr.benefit',
        string = "Benefits",
        compute = '_get_benefits',)
    
    #technical fields
    #used to grant access in employee view
    access_level = fields.Selection([
        ('base', 'Base'),
        ('lm', 'Line Manager'),
        ('hl', 'Hierarchical Line'),
        ('hr', 'HR'),
        ('me','Me'),
        ('support', 'Support'),], 
        compute='_get_access_level',
        store=False,
        default='hr',)
    
    lm_ids = fields.Many2many(
        'res.users',
        compute='_get_lm_ids',
    )
    
    
    country_name = fields.Char(
        related='company_id.country_id.name',)
    
    employee_status = fields.Selection([
        ('future','Future'),
        ('active','Active'),
        ('departed','Departed'),
        ('undef','Undefined')],
        default = 'future',
        )
    
    
    ################
    # CRUD Methods #
    ################

    #At Employee creation, create a default contract
    @api.model
    def create(self,vals):
        
        #if no external ID defined, then increment using the sequence
        if vals.get('employee_external_id','/')=='/':
            vals['employee_external_id'] = self.env['ir.sequence'].next_by_code('seq_hr_employee_ext_id')
        
        #enter default value in first, middle, family names
        names = vals.get('name','').split(' ')
        if len(names) == 2:
            vals.update({
                'first_name':names[0],
                'family_name':names[1],
            })
        elif len(names) == 3:
            vals.update({
                'first_name':names[0],
                'middle_name':names[1],
                'family_name':names[2],
            })
        
        #employee is created
        empl=super().create(vals)
        
        #we update employee statuses
        empl._check_employee_status
        
       
        return empl
        
    #################################
    # Automated Calculation Methods #
    #################################
    
    #Overrides the contract_id calculation to be replaced by a depends and allow the storage of contract_id
    @api.depends('contract_ids.date_start')
    def _compute_contract_id(self):
        super(Employee, self)._compute_contract_id()
        
    @api.model
    def _update_employee_situation(self):
        
        """ This methos regroups several sub-methods initially called by CRON in order to consolidate the employee situation:
        > status
        > lm group membership
        > resource calendar adjustment (bug work around)
        > automated tag based on wt
        """
        self._check_employee_status()
        self._set_resource_calendar()
        self._wt_to_tag()
        self._check_lm_membership()
        #self._end_contracts()
        self._set_user_tz()
    
    @api.model
    def _set_user_tz(self):
        ''' Set User timezone
        [when] the tz of the employee is false
        [Comments]
            This function set the timezone with 
            the tz from the ressource working time
            of the employee
        '''
        employees = self.env['hr.employee'].search([('user_id.tz','=',False),('resource_calendar_id','!=',False),('user_id','!=',False)])
        for employee in employees:
            employee.user_id.tz = employee.resource_calendar_id.tz
                
    
    #if multiple open contracts exists, then we set the end date of the old ones the day before the start of the new ones
    @api.model
    def _end_contracts(self):
        employees = self.env['hr.employee'].search([])
        for empl in employees:
            #we match the eventual employee end_date on the current contract end date
            """
            if empl.employee_end_date: 
                empl.contract_id.date_end = empl.employee_end_date
            """    
            contracts = self.env['hr.contract'].search([('employee_id.id','=',empl.id)]).sorted(key=lambda s: s.date_start)
            if len(contracts)>1:
                for i in range(len(contracts)-1):
                    contracts[i].date_end = contracts[i+1].date_start - timedelta(days=1)
                    
    
    #adds or remove from the lm group according to the subortinates count
    @api.model #to be called from CRON job
    def _check_lm_membership(self):
        group = self.env.ref('vcls-hr.vcls_group_lm')
        self.search([('child_ids', '!=', False)]).mapped('user_id').write({'groups_id': [(4, group.id)]}) #if a child is found, then we add the LM group to the related user
        self.search([('child_ids', '=', False)]).mapped('user_id').write({'groups_id': [(3, group.id)]}) #if no child found, then we suppress the LM group from the user
    
    @api.model
    def _start_yearly_appraisal(self,deadline_month=2):
        """
            Automated Creation of appraisal
        """
        if not self.env.user.has_group('vcls-hr.vcls_group_HR_global'):
            raise ValidationError(_("Global HR only has the right to perform this action."))

        #We grab the surveys
        ea_name = 'Employee Appraisal (by employee)'
        ma_name = 'Employee Appraisal (by manager)'
        fa_name = 'Annual Contribution Dialogue'
        e_appraisal = self.env['survey.survey'].search([('title','=',ea_name)],limit=1)
        if not e_appraisal:
            raise ValidationError(_("Survey not found {}").format(ea_name))
        m_appraisal = self.env['survey.survey'].search([('title','=',ma_name)],limit=1)
        if not e_appraisal:
            raise ValidationError(_("Survey not found {}").format(ma_name))
        f_appraisal = self.env['survey.survey'].search([('title','=',fa_name)],limit=1)
        if not e_appraisal:
            raise ValidationError(_("Survey not found {}").format(fa_name))

        #we compute the deadline to the end of the nexr month
        deadline = fields.Date.today().replace(day=1) + relativedelta(months=deadline_month,days=-1)

        employees = self.browse(self._context.get('active_ids'))
        for employee in employees:
            lm = employee.parent_id
            vals = {
                'employee_id': employee.id,
                'date_close': deadline,
                'manager_appraisal':True,
                'manager_ids':[(6, 0, [lm.id])],
                'manager_survey_id':m_appraisal.id,
                'employee_appraisal':True,
                'employee_survey_id':e_appraisal.id,
                'collaborators_appraisal':True,
                'collaborators_ids':[(6, 0, [lm.id])],
                'collaborators_survey_id':f_appraisal.id,                
            }
            appraisal = self.env['hr.appraisal'].create(vals)
            if appraisal:
                appraisal.button_send_appraisal()

                
    @api.model #to be called from CRON job
    def _check_employee_status(self):
        date_ref = date.today()
        employees = self.env['hr.employee'].search([])
        for empl in employees:
            if empl.employee_end_date: #if end date configured
                if empl.employee_end_date <= date_ref:
                    empl.employee_status = 'departed'
                    empl.active=False
                    #trigger a new departure ticket
                    empl.create_IT_ticket('departed')
                    continue
                else: #end date is documented but in the fulture
                    empl.employee_status = 'active'
                    continue
                    
            elif empl.employee_start_date: #if start date documented
                if empl.employee_start_date > date_ref: #employee to start in the future
                    empl.employee_status = 'future'
                else:
                    empl.employee_status = 'active' 
            else:
                empl.employee_status = 'future' #no dates
    
        
    @api.model #to be called from CRON
    def _wt_to_tag(self):
        
        """ We use tags for proper allocation of holidays according to the company and the contractual situation.
        THis info is already present in the working time of the employee, so we automate the creation of the tag according to the defined wt."""
        partner_ids=self.env.ref('base.user_admin').partner_id.ids
        
        #get existing wts and loop in
        wts = self.env['resource.calendar'].search([])
        for wt in wts:
            #search the related tag
            specif = wt.name.find(' (')
            if specif < 0:
                tag_search_name = wt.name
            else:
                tag_search_name = wt.name[:specif]
            
            tag=self.env['hr.employee.category'].search([('name','=',tag_search_name)], limit=1)
            tag_id=tag.id
            
            #if the tag exists, then look for employee having a mismatch between the tag and the wt
            if tag_id:
                
                body = 'Employee updated: '
                
                # we look for all wt that can be relatag to this tag in order to identify existing tags to be rmoved
                tag_related_wts=self.env['resource.calendar'].search([('name','like',tag.name)]).ids
                
                #get employees with a tag not having one of the corresponding wt >> we remove the tag
                emp_having = self.env['hr.employee'].search([('resource_calendar_id.id','not in',tag_related_wts),('category_ids','in',tag_id)])
                for emp in emp_having:
                    emp.category_ids -= tag
                    body += '{} '.format(emp.name)
                if emp_having:
                    subject='Kalpa | Employees updated'
                    body += 'removed tag {} '.format(tag_search_name)
                    self.env['mail.thread'].message_notify(
                        partner_ids=partner_ids,
                        body=body,
                        subject = subject,
                        record_name=wt.name,
                        notif_layout='mail.mail_notification_light'
                        )
                
                #get employees with the working time but no corresponding tags
                body = 'Employee updated: '
                emp_missing = self.env['hr.employee'].search([('resource_calendar_id.id','=',wt.id),('category_ids','not in',tag_id)])
                for emp in emp_missing: #employees having the wt without the tag >> we update them
                    emp.category_ids |= tag
                    body += '{} '.format(emp.name)
                
                if emp_missing:
                    subject='Kalpa | Employees updated'
                    body += 'added tag {} '.format(tag_search_name)
                    self.env['mail.thread'].message_notify(
                        partner_ids=partner_ids,
                        body=body,
                        subject = subject,
                        record_name=wt.name,
                        notif_layout='mail.mail_notification_light'
                        )

            #tag is missing or mistyped... notify admin
            else:
                subject='Kalpa | Employee tag to create'
                body='Please create tag for the working time {}'.format(wt.name)
                self.env['mail.thread'].message_notify(
                        partner_ids=partner_ids,
                        body=body,
                        subject = subject,
                        record_name=wt.name,
                        notif_layout='mail.mail_notification_light'
                        )
         
    
    #Ensure the resource.resource calendar is the same than the one configured at the employee level
    @api.model #to be called from CRON job
    def _set_resource_calendar(self):
        employees = self.env['hr.employee'].search([])
        for empl in employees:
            if empl.resource_calendar_id: #if a working time has been configured
                empl.resource_id.calendar_id = empl.resource_calendar_id
        
    
    @api.multi
    def _get_benefits(self):
        for empl in self:
            empl.benefit_ids = self.env['hr.benefit'].search([('employee_id','=',empl.id)])

    @api.multi
    def _get_bonuses(self):
        for empl in self:
            empl.bonus_ids = self.env['hr.bonus'].search([('employee_id','=',empl.id)])
    
#    @api.multi
#    def _get_contracts(self):
#        for empl in self:
#            empl.contract_ids = self.env['hr.contract'].search(['&',('employee_id','=',empl.id),('company_id','=',empl.company_id.id)])
    
    @api.depends('parent_id','parent_id.parent_id','contract_id','contract_id.job_id','contract_id.job_id.department_id','contract_id.job_id.department_id.manager_id')  
    def _get_lm_ids(self):
        
        for rec in self:
            empl = rec
            managers = rec.user_id
            while empl.parent_id:
                empl = empl.parent_id
                managers |= empl.user_id
            #add heads related to job profile
            managers |= rec.sudo().contract_id.job_id.department_id.manager_id.user_id
            
            rec.lm_ids = managers
            
    
    @api.multi
    def _get_access_level(self):
        for rec in self:
            
            user = self.env['res.users'].browse(self._uid)
            
            #if admin
            if user.has_group('base.group_system'):
                rec.access_level = 'hr'
                continue
                
            #for the employee himself 
            if rec.user_id.id == self._uid: 
                rec.access_level = 'me'
                continue
            
            #globalHR
            if user.has_group('vcls-hr.vcls_group_HR_global'):
                rec.access_level = 'hr'
                continue        
            
            #localHR
            if user.has_group('vcls-hr.vcls_group_HR_local'):
                if rec.company_id in user.company_ids: #if authorized company
                    rec.access_level = 'hr'
                else:
                    rec.access_level = 'hl'
                continue
            
            #management line
            if (user in rec.lm_ids):
                if user.has_group('vcls-hr.vcls_group_head'): #if he's a head
                    rec.access_level = 'lm'
                elif (user == rec.parent_id.user_id): #if this is the lm
                    rec.access_level = 'lm'
                else:
                    rec.access_level = 'hl'
                continue
                
            #if user is in support group
            if user.has_group('vcls-hr.vcls_group_superuser_lvl1'):
                rec.access_level = 'support'
                continue
            
            #controlling
            if user.has_group('vcls_security.group_project_controller'):
                rec.access_level = 'hl'
                continue
            
            #default access right
            rec.access_level = 'base'
                
                        

    #Automatically update the job_info string if one of the component is changed
    @api.depends('job_title','diploma_ids')
    def _set_job_info(self):
        for rec in self:
            rec.job_info = rec.job_title
            if len(rec.diploma_ids) > 0: #If one or more diplomas have been defined, add the separator
                rec.job_info = "{} | ".format(rec.job_info) 
            for id in rec.diploma_ids: #Loop in diplomas to build the string
                rec.job_info = "{} {}".format(rec.job_info, id.name)
    
    # When the nex_medical_checkup is changed, then it is stored on specific_next_medical_checkup
    @api.onchange('next_medical_checkup')
    def _set_next_medical_checkup(self):
        for rec in self:
            rec.specific_next_medical_checkup = rec.next_medical_checkup
    
    # If the last_medical_checkup is updated, then the new one is automatically calculated if the employee does not need specific follow-up
    @api.onchange('last_medical_checkup')
    def _set_specific_next_medical_checkup(self):
        for rec in self:
            if (not rec.need_specific_medical):
                try: rec.specific_next_medical_checkup = rec.last_medical_checkup + relativedelta(years=5)
                except: pass
            
    # Calculate next_medical_checkup according to other fields.
    # Uses try/except to cover cases when fields aren't documented.
    @api.depends('last_medical_checkup','specific_next_medical_checkup')
    def _get_next_medical_checkup(self):
        for rec in self:
            try:
                rec.next_medical_checkup = min(rec.specific_next_medical_checkup, rec.last_medical_checkup + relativedelta(years=5))
            except:
                if rec.last_medical_checkup: 
                    rec.next_medical_checkup = rec.last_medical_checkup + relativedelta(years=5)
                elif rec.specific_next_medical_checkup:
                    rec.next_medical_checkup = rec.specific_next_medical_checkup + relativedelta(years=5)
                else:
                    pass   
    
    #Calculate the Trial Period end date & notification delay
    @api.depends('trial_start_date','trial_period_id','trial_period_id.duration','trial_period_id.notification_delay')
    def _compute_trial_end_date(self):
        for rec in self:
            if rec.trial_start_date and rec.trial_period_id: #if enough info documented
                #add a one day offset
                rec.trial_end_date = rec._get_previous_working_day(rec.trial_start_date + relativedelta(months=rec.trial_period_id.duration,days=-1))
                rec.trial_notification_date = rec._get_previous_working_day(rec.trial_end_date + relativedelta(days=-1*rec.trial_period_id.notification_delay))
    
    @api.one
    def _compute_leave_duration_type(self):
        today_date = datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', self.id),
            ('state', 'not in', ['cancel', 'refuse']),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start)
        ])
        if len(holidays) == 1:
            for holiday in holidays:
                if holiday.request_unit_half:
                    self.leave_duration_type = holiday.request_date_from_period
                else:
                    self.leave_duration_type = False
        else:
            self.leave_duration_type = False

    @api.multi
    def _is_worked_day(self, worked_day):
        self.ensure_one()
        if worked_day.weekday() in (5, 6):
            return False
        if self.env['hr.bank.holiday'].sudo().search([
            ('company_id', '=', self.company_id.id),
            ('date', '=', worked_day)
        ]):
            return False
        attendance_ids = self.resource_calendar_id.attendance_ids
        if not attendance_ids:
            return True
        for attendance_id in attendance_ids:
            dayofweek = attendance_id.dayofweek
            if dayofweek.isdigit() and int(dayofweek) == worked_day.weekday():
                return True
        return False

    @api.multi
    def _compute_leave_status(self):
        # Used SUPERUSER_ID to forcefully get status of other user's leave, to bypass record rule
        super(Employee, self)._compute_leave_status()
        today_date = fields.Date.context_today(self)
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        # for each employee check if all dates between each two holidays are not worked days,
        current_holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('state', 'not in', ('cancel', 'refuse')),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start),
        ])
        current_holidays_by_employee = {}
        for current_holiday in current_holidays:
            current_holidays_by_employee[current_holiday.employee_id.id] = current_holiday
        # Process holidays coming next the current ones
        self._get_holidays(current_holidays_by_employee, today_start, today_end, 'future')
        # Process holidays coming next the current ones
        self._get_holidays(current_holidays_by_employee, today_start, today_end, 'past')

    @api.multi
    def _get_holidays(
            self, current_holidays_by_employee, today_start, today_end,
            holiday_type
    ):
        # Fetch all future holidays (or past depending on holiday_type variable)
        # for all employees who are absent today
        domain = [
            ('employee_id', 'in', self.ids),
            ('state', 'not in', ('cancel', 'refuse')),
        ]
        order_by = 'employee_id'
        if holiday_type == 'future':
            domain += [('date_from', '>', today_end)]
            order_by += ', date_to asc'
        elif holiday_type == 'past':
            domain += [('date_to', '<', today_start)]
            order_by += ', date_from desc'
        holidays = self.env['hr.leave'].sudo().search(domain, order=order_by)
        leave_data = {}
        holidays_by_employee = {}
        ref_date_field = 'date_to' if holiday_type == 'future' else 'date_from'
        # arrange holidays to be grouped by employee
        for holiday in holidays:
            employee_id = holiday.employee_id.id
            if not holidays_by_employee.get(employee_id):
                holidays_by_employee[employee_id] = holiday
            else:
                holidays_by_employee[employee_id] += holiday
        for employee_id, holidays in holidays_by_employee.items():
            # for each employee search all valid holidays
            # A valid holiday is a holiday which all date between it and the current holiday (or the last valid hliday)
            # today are not worked,
            current_holiday = current_holidays_by_employee.get(employee_id)
            if not holidays or not current_holiday:
                continue
            valid_holidays = current_holiday
            # Iterate over ordered by date_from (or date_to) holidays
            # to guess the valid ones.
            # We break this iterations when we find a worked day between two holidays
            for holiday in holidays:
                day_between_holidays = holiday.date_from if holiday_type == 'future' else holiday.date_to
                iteration = 0
                day_step = -1 if holiday_type == 'future' else 1
                ref_date = valid_holidays[-1][ref_date_field].date()
                no_stop_condition = ref_date < day_between_holidays.date() if holiday_type == 'future' else \
                    ref_date > day_between_holidays.date()
                # Check that there is not a worked day between two holidays
                # in this case consider the second holiday as a valid one
                while no_stop_condition:
                    day_between_holidays += relativedelta(days=day_step)
                    employee = self.sudo().browse(employee_id)
                    if employee.sudo()._is_worked_day(day_between_holidays.date()):
                        break
                    no_stop_condition = ref_date < day_between_holidays.date() if holiday_type == 'future' else \
                        ref_date > day_between_holidays.date()
                    iteration += 1
                    if iteration > 730:  # max iterations (730 days ~= 2 years between two holidays)
                        break
                if ref_date == day_between_holidays.date():
                    # this holiday is valid
                    valid_holidays += holiday
                else:
                    # this holiday is not valid so we move on to the next employee
                    # as there is no need to explore further future/past holidays
                    break
            if valid_holidays:
                leave_data[employee_id] = valid_holidays
        for employee in self:
            employee_holiday_field = 'leave_date_to' if holiday_type == 'future' else 'leave_date_from'
            valid_holidays = leave_data.get(employee.id, [])
            valid_holiday = valid_holidays and valid_holidays[-1]
            current_holiday = current_holidays_by_employee.get(employee.id)
            leave_date = valid_holiday and valid_holiday[ref_date_field] or False
            leave_date = leave_date or (current_holiday and current_holiday[ref_date_field]) or False
            if leave_date:
                employee[employee_holiday_field] = leave_date.date()


    ########################
    # CREATE TICKET METHOD #
    ########################

    # GENERAL VARIABLES
    IT_TEAM_NAME = 'IT General Support'
    SUB_CAT = 'Onboard / Offboard'
    TYPE = 'Service Request'
    ODOO_ADDRESS = 'https://vcls.odoo.com'
    
    @api.multi
    def create_IT_ticket(self, type_of_ticket):
        #raise ValidationError('{}'.format(type_of_ticket))
        for employee in self:
            self.env['helpdesk.ticket'].create({
                'team_id' : self.env['helpdesk.team'].search([('name', '=', self.IT_TEAM_NAME)], limit=1).id,
                'subcategory_id' : self.env['helpdesk.ticket.subcategory'].search([('name', '=', self.SUB_CAT)], limit=1).id,
                'ticket_type_id' : self.env['helpdesk.ticket.type'].search([('name', '=', self.TYPE)], limit=1).id,
                'dynamic_description' : self.generate_ticket_description(type_of_ticket),
            })
    '''
    @api.onchange('first_name', 'middle_name', 'family_name')
    def _ticket_onchange_employee(self):
       trigger in order to send ticket when an existing employee is modified
        When:
            used when first_name, middle_name, family_name, company_id or parent_id is changed
        Args:
            self: only current employee is needed
        Raises:
            Nothing
        Returns:
            Nothing
        
        for employee in self:
            #we create a modif only if a contract already exists
            if employee.contract_id:
                employee.create_IT_ticket('modify')
    '''
    '''
    @api.onchange('parent_id')
    def _ticket_onchange_LM(self):
        trigger in order to send ticket when an existing employee is modified
        When:
            used when Line Manager is changed
        Args:
            self: only old LM is needed
        Raises:
            Nothing
        Returns:
            Nothing
        
        for employee in self:
            #we create a modif only if a contract already exists
            if self._origin.parent_id:
                employee.create_IT_ticket('newLM')
    '''
    
    # Override write to send only one ticket replace above
    def write(self, vals): 

        if 'parent_id' in vals:
            if vals.get('contract_id',self.contract_id.id):
                self.create_IT_ticket('newLM')

                #_logger.info("NEW LM TICKET CREATED: {}".format(self.name))
        
        if 'first_name' in vals or 'middle_name' in vals or 'last_name' in vals or 'name' in vals:
            if vals.get('contract_id',self.contract_id.id):
                self.create_IT_ticket('modify')
                #_logger.info("NEW MODIFY TICKET CREATED: {}".format(self.name))

        return super(Employee, self).write(vals)
    
    @api.depends('job_title')
    def notify_title_changes(self):
        for record in self:
            record.create_IT_ticket('job_title_changed')

    
    def generate_ticket_description(self, typeOfTicket):
        
        ''' Generate ticket dynamic_description
        When:
            called in create_IT_ticket
        Args:
            self: current employee
            typeOfTicket: string type of ticket (in order to generate description)
                type = 'join'   : Joining employee
                type = 'departure' : Leaving employee
                else : Modified employee
        Raises:
            Nothing
        Returns:
            description: string description (html)
        '''
        self.ensure_one()
        
        if typeOfTicket == 'join':
            description = '<h2>New employee : {} </h2><h3>Date of arrival : {}'.format(self.name,self.employee_start_date)

        elif typeOfTicket == 'newLM':
            description = '<h2>Line Manager updated : {} </h2> <h3>'.format(self.parent_id.name)
            return description
            
        elif typeOfTicket == 'departed':
            description = '<h2>Leaving employee : {} </h2><h3>Date of departure : {}'.format(self.name,self.employee_end_date)
            
        elif typeOfTicket == 'modify':
            description = '<h2>Modified employee (The name has changed) : {} </h2><h3>'.format(self.name)
        
        elif typeOfTicket == 'job_title_changed':
            description = '<h2>Modified employee (The Job Title changed) : {} </h2><h3>'.format(self.name)
           
        else:
            raise ValidationError("{}: Unknow type of ticket".format(typeOfTicket))
            
        # Button to employee
        description += '</h3><p style="text-align: left; margin-left: 1.5em;"><a href="'
        description += self.ODOO_ADDRESS + '/web?debug#id='
        description += str(self.id)
        description += '&model=hr.employee'
        description += '" class="btn btn-alpha btn-lg" target="_blank" title=""><font style="color: rgb(255, 255, 255);">Employee</font></a><br></p><div style="        display: flex;        flex-direction: column;        "> </div>'
        
        return description
                         
    #####################
    # Selection Methods #
    #####################
    
    @api.model
    def _selection_relationship(self):
        return [
            ('wife_husband','Wife/Husband'),
            ('mother_father','Mother/Father'),
            ('daughter_son','Daughter/Son'),
            ('sister_brother','Sister/Brother'),
            ('partner','Partner'),
            ('friend','Friend'),
            ('neighbour','Neighbour'),
            ('other','Other'),
        ]
    
    @api.model
    def _selection_termination(self):
        return [
            ('termination','Termination'),
            ('resignation','Resignation'),
            ('lay_off','Lay Off'),
            ('retirement','Retirement'),
            ('other','Other'),
        ]
    
    #################
    # Tools Methods #
    #################
    
    def _get_previous_working_day(self,target_date):
        is_worked = False
        while not is_worked:
            bank = False
            if self.env['hr.bank.holiday'].search([('company_id','=',self.company_id.id),('date','=',target_date)]): #check if date is a bank holiday in this company
                bank = True
            if target_date.weekday()<5 and not bank: #this is a worked day
                is_worked = True
                return target_date
            else:
                is_worked = False
                target_date = target_date + timedelta(days=-1)
        
    ##########################
    # Pop-up windows Methods #
    ##########################
    
    def new_bonus_pop_up(self):
        return {
            'name': 'Create a new over variable salary',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'hr.bonus',
            'type': 'ir.actions.act_window',
            'context': "{{'default_employee_id': {}}}".format(self.id),
        }
    
    def new_contract_pop_up(self):
        view_id = self.env.ref('vcls-hr.vcls_contract_form1').id
        count = len(self.env['hr.contract'].search([('employee_id','=',self.id)]))
        contract_name = "{} | {:02}".format(self.name,count+1),
        
        return {
            'name': 'Create a new contract',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'res_model': 'hr.contract',
            'type': 'ir.actions.act_window',
            'context': "{{'default_employee_id': {},'default_name': {}}}".format(self.id,contract_name),
        } 

    def new_benefit_pop_up(self):
        view_id = self.env.ref('vcls-hr.view_benefit_form').id
        return {
            'name': 'Create a new benefit set',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'res_model': 'hr.benefit',
            'type': 'ir.actions.act_window',
            'context': "{{'default_employee_id': {}}}".format(self.id),
        }
    
    ###############################
    # CONFIDENTIAL ACCESS METHODS #
    ###############################

    ### place of birth
    @api.depends('confidential_id.place_of_birth')
    def _compute_place_of_birth(self):
        for rec in self:
            if rec.confidential_id:
                rec.place_of_birth = rec.confidential_id[0]['place_of_birth']
            else:
                rec.place_of_birth = False
    
    def _set_place_of_birth(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'place_of_birth': self.place_of_birth})
            else:
                rec.confidential_id[0].write({'place_of_birth': self.place_of_birth})

    ### birthday
    @api.depends('confidential_id.birthday')
    def _compute_birthday(self):
        for rec in self:
            if rec.confidential_id:
                rec.birthday = rec.confidential_id[0]['birthday']
            else:
                rec.birthday = False
    
    def _set_birthday(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'birthday': self.birthday})
            else:
                rec.confidential_id[0].write({'birthday': self.birthday})
                
    ### family_name_at_birth
    @api.depends('confidential_id.family_name_at_birth')
    def _compute_family_name_at_birth(self):
        for rec in self:
            if rec.confidential_id:
                rec.family_name_at_birth = rec.confidential_id[0]['family_name_at_birth']
            else:
                rec.family_name_at_birth = False
    
    def _set_family_name_at_birth(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'family_name_at_birth': self.family_name_at_birth})
            else:
                rec.confidential_id[0].write({'family_name_at_birth': self.family_name_at_birth})
                
    ### children
    @api.depends('confidential_id.children')
    def _compute_children(self):
        for rec in self:
            if rec.confidential_id:
                rec.children = rec.confidential_id[0]['children']
            else:
                rec.children = False
    
    def _set_children(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'children': self.children})
            else:
                rec.confidential_id[0].write({'children': self.children})
                
           
    ### country_id
    #### Many2one field
    @api.depends('confidential_id.country_id')
    def _compute_country_id(self):
        for rec in self:
            if rec.confidential_id:
                rec.country_id = rec.confidential_id[0]['country_id']
            else:
                rec.country_id = False
    
    def _set_country_id(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'country_id': self.country_id.id})
            else:
                rec.confidential_id[0].write({'country_id': self.country_id.id})
    
    ### country2_id
    #### Many2one field
    @api.depends('confidential_id.country2_id')
    def _compute_country2_id(self):
        for rec in self:
            if rec.confidential_id:
                rec.country2_id = rec.confidential_id[0]['country2_id']
            else:
                rec.country2_id = False
    
    def _set_country2_id(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'country2_id': self.country2_id.id})
            else:
                rec.confidential_id[0].write({'country2_id': self.country2_id.id})
    
    ### ssnid
    @api.depends('confidential_id.ssnid')
    def _compute_ssnid(self):
        for rec in self:
            if rec.confidential_id:
                rec.ssnid = rec.confidential_id[0]['ssnid']
            else:
                rec.ssnid = False
    
    def _set_ssnid(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'ssnid': self.ssnid})
            else:
                rec.confidential_id[0].write({'ssnid': self.ssnid})
    
    ### permit_no
    @api.depends('confidential_id.permit_no')
    def _compute_permit_no(self):
        for rec in self:
            if rec.confidential_id:
                rec.permit_no = rec.confidential_id[0]['permit_no']
            else:
                rec.permit_no = False
    
    def _set_permit_no(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'permit_no': self.permit_no})
            else:
                rec.confidential_id[0].write({'permit_no': self.permit_no})
    
    ### work_permit_expire
    @api.depends('confidential_id.work_permit_expire')
    def _compute_work_permit_expire(self):
        for rec in self:
            if rec.confidential_id:
                rec.work_permit_expire = rec.confidential_id[0]['work_permit_expire']
            else:
                rec.work_permit_expire = False
    
    def _set_work_permit_expire(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'work_permit_expire': self.work_permit_expire})
            else:
                rec.confidential_id[0].write({'work_permit_expire': self.work_permit_expire})
    
    ### link_employee_folder
    @api.depends('confidential_id.link_employee_folder')
    def _compute_link_employee_folder(self):
        for rec in self:
            if rec.confidential_id:
                rec.link_employee_folder = rec.confidential_id[0]['link_employee_folder']
            else:
                rec.link_employee_folder = False
    
    def _set_link_employee_folder(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'link_employee_folder': self.link_employee_folder})
            else:
                rec.confidential_id[0].write({'link_employee_folder': self.link_employee_folder})
    
    
    ## Contact information
    ### street
    @api.depends('confidential_id.street')
    def _compute_street(self):
        for rec in self:
            if rec.confidential_id:
                rec.street = rec.confidential_id[0]['street']
            else:
                rec.street = False
    
    def _set_street(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'street': self.street})
            else:
                rec.confidential_id[0].write({'street': self.street})
    
    ### street2
    @api.depends('confidential_id.street2')
    def _compute_street2(self):
        for rec in self:
            if rec.confidential_id:
                rec.street2 = rec.confidential_id[0]['street2']
            else:
                rec.street2 = False
    
    def _set_street2(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'street2': self.street2})
            else:
                rec.confidential_id[0].write({'street2': self.street2})
    
    ### city
    @api.depends('confidential_id.city')
    def _compute_city(self):
        for rec in self:
            if rec.confidential_id:
                rec.city = rec.confidential_id[0]['city']
            else:
                rec.city = False
    
    def _set_city(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'city': self.city})
            else:
                rec.confidential_id[0].write({'city': self.city})
    
    ### state_id
    #### Many2one field
    @api.depends('confidential_id.state_id')
    def _compute_state_id(self):
        for rec in self:
            if rec.confidential_id:
                rec.state_id = rec.confidential_id[0]['state_id']
            else:
                rec.state_id = False
    
    def _set_state_id(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'state_id': self.state_id.id})
            else:
                rec.confidential_id[0].write({'state_id': self.state_id.id})
    
    ### zip
    @api.depends('confidential_id.zip')
    def _compute_zip(self):
        for rec in self:
            if rec.confidential_id:
                rec.zip = rec.confidential_id[0]['zip']
            else:
                rec.zip = False
    
    def _set_zip(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'zip': self.zip})
            else:
                rec.confidential_id[0].write({'zip': self.zip})
    
    ### address_country_id
    #### Many2one field
    @api.depends('confidential_id.address_country_id')
    def _compute_address_country_id(self):
        for rec in self:
            if rec.confidential_id:
                rec.address_country_id = rec.confidential_id[0]['address_country_id']
            else:
                rec.address_country_id = False
    
    def _set_address_country_id(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'address_country_id': self.address_country_id.id})
            else:
                rec.confidential_id[0].write({'address_country_id': self.address_country_id.id})
    
    ### private_email
    @api.depends('confidential_id.private_email')
    def _compute_private_email(self):
        for rec in self:
            if rec.confidential_id:
                rec.private_email = rec.confidential_id[0]['private_email']
            else:
                rec.private_email = False
    
    def _set_private_email(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'private_email': self.private_email})
            else:
                rec.confidential_id[0].write({'private_email': self.private_email})
    
    ### private_phone
    @api.depends('confidential_id.private_phone')
    def _compute_private_phone(self):
        for rec in self:
            if rec.confidential_id:
                rec.private_phone = rec.confidential_id[0]['private_phone']
            else:
                rec.private_phone = False
    
    def _set_private_phone(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'private_phone': self.private_phone})
            else:
                rec.confidential_id[0].write({'private_phone': self.private_phone})
    
    ### emergency_contact
    @api.depends('confidential_id.emergency_contact')
    def _compute_emergency_contact(self):
        for rec in self:
            if rec.confidential_id:
                rec.emergency_contact = rec.confidential_id[0]['emergency_contact']
            else:
                rec.emergency_contact = False
    
    def _set_emergency_contact(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'emergency_contact': self.emergency_contact})
            else:
                rec.confidential_id[0].write({'emergency_contact': self.emergency_contact})
    
    ### emergency_phone
    @api.depends('confidential_id.emergency_phone')
    def _compute_emergency_phone(self):
        for rec in self:
            if rec.confidential_id:
                rec.emergency_phone = rec.confidential_id[0]['emergency_phone']
            else:
                rec.emergency_phone = False
    
    def _set_emergency_phone(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'emergency_phone': self.emergency_phone})
            else:
                rec.confidential_id[0].write({'emergency_phone': self.emergency_phone})
    
    ### ice_contact_relationship
    #### Selection field casted as Char in employee_confidential
    @api.depends('confidential_id.ice_contact_relationship')
    def _compute_ice_contact_relationship(self):
        for rec in self:
            if rec.confidential_id:
                rec.ice_contact_relationship = rec.confidential_id[0]['ice_contact_relationship']
            else:
                rec.ice_contact_relationship = False
    
    def _set_ice_contact_relationship(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'ice_contact_relationship': self.ice_contact_relationship})
            else:
                rec.confidential_id[0].write({'ice_contact_relationship': self.ice_contact_relationship})
    
    ### notes
    @api.depends('confidential_id.notes')
    def _compute_notes(self):
        for rec in self:
            if rec.confidential_id:
                rec.notes = rec.confidential_id[0]['notes']
            else:
                rec.notes = False
    
    def _set_notes(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'notes': self.notes})
            else:
                rec.confidential_id[0].write({'notes': self.notes})
    
    # End of Personal information
    
    # Job information
    # *EMPTY*
    # End of Job information
    
    ### last_medical_checkup
    @api.depends('confidential_id.last_medical_checkup')
    def _compute_last_medical_checkup(self):
        for rec in self:
            if rec.confidential_id:
                rec.last_medical_checkup = rec.confidential_id[0]['last_medical_checkup']
            else:
                rec.last_medical_checkup = False
    
    def _set_last_medical_checkup(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'last_medical_checkup': self.last_medical_checkup})
            else:
                rec.confidential_id[0].write({'last_medical_checkup': self.last_medical_checkup})
    
    ### next_medical_checkup
    @api.depends('confidential_id.next_medical_checkup')
    def _compute_next_medical_checkup(self):
        for rec in self:
            if rec.confidential_id:
                rec.next_medical_checkup = rec.confidential_id[0]['next_medical_checkup']
            else:
                rec.next_medical_checkup = False
    
    
    ### need_specific_medical
    @api.depends('confidential_id.need_specific_medical')
    def _compute_need_specific_medical(self):
        for rec in self:
            if rec.confidential_id:
                rec.need_specific_medical = rec.confidential_id[0]['need_specific_medical']
            else:
                rec.need_specific_medical = False
    
    def _set_need_specific_medical(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'need_specific_medical': self.need_specific_medical})
            else:
                rec.confidential_id[0].write({'need_specific_medical': self.need_specific_medical})
    
    ### affiliation_date
    @api.depends('confidential_id.affiliation_date')
    def _compute_affiliation_date(self):
        for rec in self:
            if rec.confidential_id:
                rec.affiliation_date = rec.confidential_id[0]['affiliation_date']
            else:
                rec.affiliation_date = False
    
    def _set_affiliation_date(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'affiliation_date': self.affiliation_date})
            else:
                rec.confidential_id[0].write({'affiliation_date': self.affiliation_date})
    
    ### affiliated_company
    @api.depends('confidential_id.affiliated_company')
    def _compute_affiliated_company(self):
        for rec in self:
            if rec.confidential_id:
                rec.affiliated_company = rec.confidential_id[0]['affiliated_company']
            else:
                rec.affiliated_company = False
    
    def _set_affiliated_company(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'affiliated_company': self.affiliated_company})
            else:
                rec.confidential_id[0].write({'affiliated_company': self.affiliated_company})
    
    ### medical_policy_number
    @api.depends('confidential_id.medical_policy_number')
    def _compute_medical_policy_number(self):
        for rec in self:
            if rec.confidential_id:
                rec.medical_policy_number = rec.confidential_id[0]['medical_policy_number']
            else:
                rec.medical_policy_number = False
    
    def _set_medical_policy_number(self):
        for rec in self:
            if not rec.confidential_id:
                self.env['hr.employee.confidential'].create({'employee_id':rec.id, 'medical_policy_number': self.medical_policy_number})
            else:
                rec.confidential_id[0].write({'medical_policy_number': self.medical_policy_number})