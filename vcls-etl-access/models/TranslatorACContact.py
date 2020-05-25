from . import TranslatorACGeneral
import logging
_logger = logging.getLogger(__name__)

class TranslatorACContact(TranslatorACGeneral.TranslatorACGeneral):
    def __init__(self,access):
        super().__init__(access)

    @staticmethod
    def translateToOdoo(AC_Contact, odoo, access):
        #mapOdoo = odoo.env['map.odoo']
        
        result = {}
        
        ### DEFAULT VALUES
        result['is_company'] = False
        result['company_type'] = 'person'
        result['type'] = 'contact'
        result['category_id'] = [(6, 0, [odoo.env.ref('vcls-contact.category_account').id])]

        ### IDENTIFICATION
        ### Individual
        result['name'] = AC_Contact[6] #ContactName
        result['altname'] = AC_Contact[7] #ContactInit
        result['function'] = AC_Contact[8] #ContactTitle

        result['parent_id'] = TranslatorACGeneral.TranslatorACGeneral.toOdooId(AC_Contact[0],"res.partner","client",odoo)
        #AC_Contact['Salutation']

        #AC_Contact['PMRate']
        #AC_Contact['CLRate']
        #AC_Contact['PONum']
        #AC_Contact['SeqNum']
        #AC_Contact['SegNumYear']

        #AC_Contact['InRate']
        #Inactive
        #CustomerCopy
        #OtherProjectRatesID 
        if AC_Contact[22] :
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
    