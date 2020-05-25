from . import TranslatorACGeneral
import logging
import datetime, pytz
from datetime import datetime,timedelta
_logger = logging.getLogger(__name__)

class TranslatorACEmployee(TranslatorACGeneral.TranslatorACGeneral):
    def __init__(self,access):
        super().__init__(access)

    @staticmethod
    def translateToOdoo(AC_Employee, odoo, access):
        mapOdoo = odoo.env['map.odoo']
        
        result = {}

        ## DEFAULT
        result['company_id'] = odoo.env.ref('vcls-hr.company_BH').id
        result['office_id'] = odoo.env.ref('vcls-hr.office_somerville').id
        result['employee_status'] = "active"
        #result['contract_id'] = 
        result['employee_type'] = "internal"

        result['name'] = ""
        if AC_Employee[1]:
            result['first_name'] = AC_Employee[1] #FName
            result['name'] = AC_Employee[1]
        if AC_Employee[2]:
            result['middle_name'] = AC_Employee[2] #Ml
            result['name'] = result['name'] + " " + AC_Employee[2]
        if AC_Employee[3]:
            result['family_name'] = AC_Employee[3] #LName
            result['name'] = result['name'] + " " + AC_Employee[3]
        #sur
        #result[''] = AC_Employee[5] #EmployeeInit
        result['street'] = AC_Employee[6] #EmAddress1
        result['street2'] = AC_Employee[7] #EmAddress2
        if AC_Employee[8]:
            result['city'] =  TranslatorACGeneral.TranslatorACGeneral.convertCityId(AC_Employee[8], access) #CityID
        if AC_Employee[9]:
            state = TranslatorACGeneral.TranslatorACGeneral.convertStateId(AC_Employee[9], access) #StateID
            if state:
                result['state_id'] = mapOdoo.convertRef(state,odoo,'res.country.state',False)
        result['zip'] = AC_Employee[10] #ClientZipCode
        if AC_Employee[11]:
            country = TranslatorACGeneral.TranslatorACGeneral.convertCountryId(AC_Employee[11], access) #CountryID
            if country:
                result['country_id'] = mapOdoo.convertRef(country,odoo,'res.country',False)
        result['employee_start_date'] = AC_Employee[12] #EmStartDt
        result['job_title'] = AC_Employee[13] #EmTitle
        result['employee_end_date'] = AC_Employee[14] #EmEndDt
        #result['middle_name'] = AC_Employee["PMRate"] #PMRate
        #result['middle_name'] = AC_Employee["CLRate"] #CLRate
        #result['middle_name'] = AC_Employee["InRate"] #InRate

        """ if AC_Employee[15]: #PMRate
            result['seniority_level_id'] = odoo.env.ref('vcls-etl-access.project_manager_level').id
        elif AC_Employee[20]: #InRate
            result['seniority_level_id'] = odoo.env.ref('vcls-etl-access.regulatory_associate_level').id
        elif AC_Employee[16]: #CLRate
            result['seniority_level_id'] = odoo.env.ref('vcls-etl-access.clerical_level').id
 """
        _logger.info(result)

        if result['name']:
            return result
        return False

    @staticmethod
    def translateToAccess(Odoo_Account):
        pass

    @staticmethod
    def generateLog(SF_Campaign):
        result = {
            'model': 'hr.employee',
            'message_type': 'comment',
            'body': '<p>Access Synchronization</p>'
        }

        return result


    @staticmethod
    def translatranslateToAccess(Odoo_Contact, odoo):
        pass
    