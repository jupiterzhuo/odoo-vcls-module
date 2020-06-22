from . import TranslatorSFGeneral
import logging
_logger = logging.getLogger(__name__)

class TranslatorSFContact(TranslatorSFGeneral.TranslatorSFGeneral):
    def __init__(self,SF):
        super().__init__(SF)

    @staticmethod
    def translateToOdoo(SF_Contact, odoo, SF):
        mapOdoo = odoo.env['map.odoo']
        result = {}
        context = odoo.env.context
        #_logger.info("ETL Contact | {}".format(SF_Contact))

        ### DEFAULT VALUES
        result['is_company'] = False
        result['company_type'] = 'person'
        result['type'] = 'contact'

        if SF_Contact['Inactive_Contact__c']:
            result['active'] = False
        else:
            result['active'] = True
        if SF_Contact['Unsubscribed_from_Marketing_Comms__c']:
            if SF_Contact['Unsubscribed_from_Marketing_Comms__c'] == 'Unsubscribed':
                result['opted_in'] = False
                result['gdpr_status'] = 'out'

        if context.get('custom_context')=='small_update':
            result['log_info'] = 'small_update {}'.format(result['active'])
            return result

        ### IDENTIFICATION
        if SF_Contact['Salutation']:
            result['title'] = mapOdoo.convertRef(SF_Contact['Salutation'], odoo,'res.partner.title',False)
        if SF_Contact['FirstName']:
            result['firstname'] = SF_Contact['FirstName']
        if SF_Contact['MiddleName']:
            if SF_Contact['MiddleName'] != 'None':
                result['lastname2'] = SF_Contact['MiddleName']
        if SF_Contact['LastName']:
            result['lastname'] = SF_Contact['LastName']
        
        temp = "{} {} {}".format(result.get('firstname',''),result.get('lastname2',''),result.get('lastname',''))
        result['name'] = temp.replace('  ',' ')
        
        result['function'] = SF_Contact['Title']
        result['description'] = 'Contact description : \n' + str(SF_Contact['Description']) + '\n'
        # Parent company info
        company = TranslatorSFContact.get_parent(SF_Contact, odoo)
        if company:
            result['category_id'] =  [(6, 0, company.category_id.ids)]
            result['customer'] = company.customer
            result['supplier'] = company.supplier
        
        ### RELATIONS
        result['user_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUserId(SF_Contact['OwnerId'],odoo, SF)
        result['parent_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Contact['AccountId'],"res.partner","Account",odoo)
        if SF_Contact['VCLS_Main_Contact__c']:
            result['vcls_contact_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUserId(SF_Contact['VCLS_Main_Contact__c'],odoo, SF)

        ### ADDRESS
        if SF_Contact['MailingAddress']:
            result['city'] = SF_Contact['MailingAddress']['city']
            result['zip'] = SF_Contact['MailingAddress']['postalCode']
            result['street'] = SF_Contact['MailingAddress']['street']
            if SF_Contact['MailingAddress']['country']:
                result['country_id'] = mapOdoo.convertRef(SF_Contact['MailingAddress']['country'],odoo,'res.country',False)
            if SF_Contact['MailingAddress']['state']:
                result['state_id'] = mapOdoo.convertRef(SF_Contact['MailingAddress']['state'],odoo,'res.country.state',False)
        
        ### CONTACT INFO
        result['linkedin'] = SF_Contact['LinkedIn_Profile__c']
        result['phone'] = SF_Contact['Phone']
        result['fax'] = SF_Contact['Fax']
        result['mobile'] = SF_Contact['MobilePhone']
        result['email'] = SF_Contact['Email']
        result['website'] = SF_Contact['AccountWebsite__c']

        ### ADMIN
        result['stage'] = TranslatorSFContact.convertStatus(SF_Contact)
        result['message_ids'] = [(0, 0, TranslatorSFContact.generateLog(SF_Contact))]
        result['log_info'] = result['name']

        ### MARKETING
        result['opted_in'] = SF_Contact['Opted_In__c']
        if SF_Contact['Unsubscribed_from_Marketing_Comms__c']:
            result['opted_out'] = True if SF_Contact['Unsubscribed_from_Marketing_Comms__c'] == 'Unsubscribed' else False

        #if SF_Contact['VCLS_Initial_Contact__c']:
            #result['vcls_contact_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUserId(SF_Contact['VCLS_Initial_Contact__c'],odoo, SF)
        if SF_Contact['Opt_in_Campaign__c']:
            result['marketing_task_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Contact['Opt_in_Campaign__c'],"project.task","Campaign",odoo)
        if SF_Contact['Unsubscribe_Campaign__c']:
            result['marketing_task_out_id'] = TranslatorSFGeneral.TranslatorSFGeneral.toOdooId(SF_Contact['Unsubscribe_Campaign__c'],"project.task","Campaign",odoo)

        return result
    
    @staticmethod
    def convertStatus(SF):
        if SF['Inactive_Contact__c']:
            return 5 #archived
        elif SF['Opted_In__c'] or SF['Unsubscribed_from_Marketing_Comms__c']:
            return 3 #verified
        else: # New
            return 2
    
    @staticmethod
    def get_parent(SF, odoo):
        #we catch the category of the parent company
        if SF['AccountId']:
            #get the key
            key = odoo.env['etl.sync.keys'].search([('externalId','=',SF['AccountId'])],limit=1)
            if key:
                parent = odoo.env['res.partner'].browse(int(key.odooId))
                return parent
            else:
                return False
        else:
            return False
    
    @staticmethod
    def generateLog(SF_Contact):
        result = {
            'model': 'res.partner',
            'message_type': 'comment',
            'body': '<p>Updated.</p>'
        }

        return result

    @staticmethod
    def translateToSF(Odoo_Contact, odoo):
        result = {}
        # Modify the name with -test
        if ' ' in Odoo_Contact.name:
            name = Odoo_Contact.name.split(" ")
            if len(name) > 2:
                result['LastName'] = Odoo_Contact.name
            else:
                result['FirstName'], result['LastName'] = name
        else:
            result['LastName'] = Odoo_Contact.name
        if Odoo_Contact.city:
            result['MailingCity'] = Odoo_Contact.city
        if Odoo_Contact.zip:
            result['MailingPostalCode'] = Odoo_Contact.zip
        if Odoo_Contact.street:
            result['MailingStreet'] = Odoo_Contact.street
        if Odoo_Contact.phone:
            result['Phone'] = Odoo_Contact.phone
        if Odoo_Contact.fax:
            result['Fax'] = Odoo_Contact.fax
        if Odoo_Contact.mobile:
            result['MobilePhone'] = Odoo_Contact.mobile
        if '@' in str(Odoo_Contact.email):
           result['Email'] = Odoo_Contact.email
        if Odoo_Contact.description:
            result['Description'] = Odoo_Contact.description
            
        result['AccountId'] = TranslatorSFGeneral.TranslatorSFGeneral.toSfId(Odoo_Contact.parent_id.id,"res.partner", "Account",odoo)
        
        # Ignore company_type
        result['MailingCountry'] = TranslatorSFGeneral.TranslatorSFGeneral.revertCountry(Odoo_Contact.country_id.id, odoo)
        result['CurrencyIsoCode'] = Odoo_Contact.currency_id.name
        if Odoo_Contact.user_id:
            result['OwnerId'] = TranslatorSFGeneral.TranslatorSFGeneral.revertOdooIdToSfId(Odoo_Contact.user_id,odoo)
        elif Odoo_Contact.parent_id:
            result['OwnerId'] = TranslatorSFGeneral.TranslatorSFGeneral.revertOdooIdToSfId(Odoo_Contact.parent_id.user_id,odoo)
        """ for c in Odoo_Contact.category_id:
            category += c.name 
        result['Category__c'] = category"""
        result['Salutation'] = Odoo_Contact.title.name
        result['Title'] = Odoo_Contact.function


        return result

    
    
    @staticmethod
    def revertStatus(status):
        if status == 3:
            return 'Active - contract set up, information completed'
        elif status == 2:
            return 'Prospective: no contract, pre-identify'
        elif status == 5:
            return 'Inactive - reason mentioned'
        else: # Undefined
            return 'Undefined - to fill'

    