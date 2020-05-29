# -*- coding: utf-8 -*-
{
    'name': "vcls-hr",

    'summary': """
        VCLS customs for human resource applications.""",

    'description': """
    """,

    'author': "VCLS",
    'website': "http://www.voisinconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.15.7',


    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'contacts',
        'fleet',
        'hr',
        'hr_contract',
        'hr_holidays',
        'hr_appraisal',
        'mail',
        'snailmail',
        'vcls-helpdesk',
        'web_gantt_days_off',
    ],
    # always loaded
    'data': [
        
        ############
        # SECURITY #
        ############
        'security/vcls_groups.xml',
        'security/ir.model.access.csv',
        'security/hr_employee_rules.xml',
        'security/hr_lm_rules.xml',
        #'security/hr_head_rules.xml',
        'security/hr_hrglobal_rules.xml',
        'security/hr_hrlocal_rules.xml',
        'security/hr_leave_officer_rules.xml',
        'security/hr_leave_manager_rules.xml',
        
        #########
        # VIEWS #
        #########
        'views/employee.xml',
        'views/bank_holiday.xml',
        'views/bonuses.xml',
        'views/benefits.xml',
        'views/company_org.xml',
        'views/contract.xml',
        'views/exceptional_leaves.xml',
        'views/job.xml',
        'views/leave_allocation.xml',
        'views/leave.xml',
        'views/leave_report.xml',
        'views/leave_type.xml',
        'views/working_times.xml',

        ########
        # MENU #
        ########
        'views/employee_menu.xml',
        'views/leave_menu.xml',
      
        ###########
        # ACTIONS #
        ###########
        
        'actions/hr_employee_cronjob.xml',
        'actions/hr_leave_cronjob.xml',
        'actions/employee_server_action.xml',
        
        #############
        # SEQUENCES #
        #############
        'sequences/hr_sequences.xml',
        
        ####################
        # EMAILS TEMPLATES #
        ####################
        'data/user_group_history.xml',
        'data/mail_data.xml',
        
        ###################
        # DEFAULT RECORDS #
        ###################
        
        # employee segmentation
        'data/companies.xml',
        'data/hr.department.csv',
        'data/hr.vcls_activities.csv',
        'data/hr.diploma.csv',
        'data/hr.project_business_fct.csv',
        #'data/hr.project_role.csv',
        'data/hr.office.csv',
        'data/hr.employee.category.csv',
        
        #employee contracts etc.
        #'data/hr.benefit_type.csv',
        'data/hr.trial.period.csv',
        'data/hr.contract.type.csv',
        
        # leaves details
        'data/hr.leave.type.csv',
        'data/hr.exceptional.leave.category.csv',
        'data/hr.exceptional.leave.case.csv',
        #'data/hr.job.csv',
  
    ],
    
    # only loaded in demonstration mode
    'demo': [
        'demo/project_role.xml',
        'demo/job.xml',
        'demo/resource.calendar.csv',
        'demo/resource.calendar.attendance.csv',
        'demo/employee.xml',
        'demo/contract.xml',
        'demo/hr.leave.type.csv',
        # Not working
        # 'demo/leave_allocation.xml',
        'demo/hr.leave.xml'
    ],
}