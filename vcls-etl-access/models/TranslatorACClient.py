from . import TranslatorACGeneral
import logging
_logger = logging.getLogger(__name__)

class TranslatorACClient(TranslatorACGeneral.TranslatorACGeneral):
    def __init__(self,access):
        super().__init__(access)

    @staticmethod
    def translateToOdoo(AC_Client, odoo, access):
        mapOdoo = odoo.env['map.odoo']
        
        result = {}
        ### DEFAULT VALUES
        result['company_type'] = 'company'
        result['is_company'] = 'True'
        result['category_id'] = [(6, 0, [odoo.env.ref('vcls-contact.category_account').id])]
        result['property_product_pricelist'] = odoo.env.ref('vcls-crm.pricelist_std_USD').id

        ### IDENTIFICATION
        result['name'] = AC_Client[1] #ClientName
        result['altname'] = AC_Client[2] #ClientInit
        #AC_Client[3] #DivName
        #AC_Client[4] #DivInit
        #AC_Client[5] #ContractType
        result['street'] = AC_Client[9] #Adress1
        result['street2'] = AC_Client[10] #Adress2
        if AC_Client[11]:
            result['city'] =  TranslatorACGeneral.TranslatorACGeneral.convertCityId(AC_Client[11], access) #CityID
        if AC_Client[12]:
            state = TranslatorACGeneral.TranslatorACGeneral.convertStateId(AC_Client[12], access) #StateID
            if state:
                result['state_id'] = mapOdoo.convertRef(state,odoo,'res.country.state',False)
        result['zip'] = AC_Client[13] #ClientZipCode
        if AC_Client[14]:
            country = TranslatorACGeneral.TranslatorACGeneral.convertCountryId(AC_Client[14], access) #CountryID
            if country:
                result['country_id'] = mapOdoo.convertRef(country,odoo,'res.country',False)

        ccinfo = TranslatorACClient.getCCInfo(AC_Client[0], access)
        if ccinfo:
            description = ''
            result["email"] = False
            for cc in ccinfo:
                if cc[0]:
                    if '@' in cc[0] and not result["email"]:
                        result["email"] = str(cc[0])
                    else:
                        description += str(cc[0]) +'\n'
            result['description'] = description
        if AC_Client[22] :
            result['active'] = False
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
            'model': 'res.partner',
            'message_type': 'comment',
            'body': '<p>Access Synchronization</p>'
        }

        return result


    @staticmethod
    def translatranslateToAccess(Odoo_Contact, odoo):
        pass

    @staticmethod
    def getCCInfo(clientID, access):
        sql = "SELECT CCName FROM tblCC WHERE ClientID = " + str(clientID)
        row = access.execute(sql).fetchall()
        if row:
            return row
        return False
        
    
    
    

    