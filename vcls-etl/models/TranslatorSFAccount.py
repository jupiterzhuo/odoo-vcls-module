from . import TranslatorSFGeneral
import logging
_logger = logging.getLogger(__name__)

class TranslatorSFAccount(TranslatorSFGeneral.TranslatorSFGeneral):
    
    def __init__(self,SF):
        super().__init__(SF)

    @staticmethod
    def translateToOdoo(SF_Account, odoo, SF):
        mapOdoo = odoo.env['map.odoo']
        
        result = {}

        ### DEFAULT VALUES
        result['company_type'] = 'company'
        result['is_company'] = 'True'
        
        ### IDENTIFICATION
        result['name'] = SF_Account['Name']
        if SF_Account['VCLS_Alt_Name__c']:
            result['altname'] = SF_Account['VCLS_Alt_Name__c'].upper()
        result['company_group_id'] = TranslatorSFGeneral.TranslatorSFGeneral.extid_to_odooid(SF_Account['ParentId'],odoo)
        result['stage'] = TranslatorSFAccount.convertStatus(SF_Account)
        result['description'] = ''
        if SF_Account['Supplier_Description__c']:
            result['description'] += 'Supplier description : \n' + str(SF_Account['Supplier_Description__c']) + '\n'
        if SF_Account['Key_Information__c']:
            result['description'] += 'Key Information : {}\n'.format(SF_Account['Key_Information__c'])

        if SF_Account['Is_supplier__c'] or SF_Account['Supplier__c']:
            result['supplier'] = True
        elif SF_Account['Project_Controller__c'] or SF_Account['VCLS_Alt_Name__c']:
            result['customer'] = True
        elif SF_Account['Type']:
            if (not SF_Account['Is_supplier__c'] or not SF_Account['Supplier__c']) and 'supplier' in SF_Account['Type'].lower():
                result['supplier'] = True

        ### ADDRESSES
        if SF_Account['BillingAddress']:
            result['city'] = SF_Account['BillingAddress']['city']
            result['zip'] = SF_Account['BillingAddress']['postalCode']
            result['street'] = SF_Account['BillingAddress']['street']
            if SF_Account['BillingAddress']['country']:
                result['country_id'] = mapOdoo.convertRef(SF_Account['BillingAddress']['country'],odoo,'res.country',False)
            if SF_Account['BillingAddress']['state']:
                result['state_id'] = mapOdoo.convertRef(SF_Account['BillingAddress']['state'],odoo,'res.country.state',False)

        ### VCLS ROLES
        result['user_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUserId(SF_Account['OwnerId'],odoo, SF)
        if SF_Account['Project_Assistant__c']:
            result['assistant_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUserId(SF_Account['Project_Assistant__c'],odoo, SF)
        if SF_Account['Project_Controller__c']:
            result['controller_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUserId(SF_Account['Project_Controller__c'],odoo, SF)
        if SF_Account['Invoice_Administrator__c']:
           result['invoice_admin_id'] = mapOdoo.convertRef(SF_Account['Invoice_Administrator__c'],odoo,'res.users',False)
        if SF_Account['VCLS_Main_Contact__c']:
            result['vcls_contact_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUserId(SF_Account['VCLS_Main_Contact__c'],odoo, SF)
        
        ### CONTACT INFO
        result['website'] = SF_Account['Website']
        result['phone'] = SF_Account['Phone']
        result['fax'] = SF_Account['Fax']

        ### ADMIN VALUES
        result['create_folder'] = SF_Account['Create_Sharepoint_Folder__c']

        if 'a href="' in SF_Account['Sharepoint_Folder__c']:
            result['manual_sharepoint_folder'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUrl(SF_Account['Sharepoint_Folder__c']).split('href="')[1]
        else:
            result['manual_sharepoint_folder'] = TranslatorSFGeneral.TranslatorSFGeneral.convertUrl(SF_Account['Sharepoint_Folder__c'])

        if SF_Account['ExternalID__c']:
            result['legacy_account'] = str(int(SF_Account['ExternalID__c']))
        
        ### FINANCIALS
        if SF_Account['KimbleOne__InvoicingCurrencyIsoCode__c']:
            result['default_currency_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertCurrency(SF_Account['KimbleOne__InvoicingCurrencyIsoCode__c'],odoo)
        elif SF_Account['CurrencyIsoCode']:
            result['default_currency_id'] = TranslatorSFGeneral.TranslatorSFGeneral.convertCurrency(SF_Account['CurrencyIsoCode'],odoo)
        else:
            pass
        
        if SF_Account['Communication_Percentage__c']:
            result['communication_rate'] = str(SF_Account['Communication_Percentage__c']/100)
            #_logger.info("COM RATE {}".format(SF_Account['Communication_Percentage__c']))

        ### OTHER
        if SF_Account['Supplier_Project__c']:
            result['project_supplier_type_id'] = mapOdoo.convertRef(SF_Account['Supplier_Project__c'],odoo,'project.supplier.type',False)
        if SF_Account['Area_of_expertise__c']:
            result['expertise_area_ids'] = [(6, 0, mapOdoo.convertRef(SF_Account['Area_of_expertise__c'],odoo,'expertise.area',True))]
        if SF_Account['NumberOfEmployees']:
            result['number_of_employee'] = TranslatorSFAccount.convertEmployees(SF_Account['NumberOfEmployees'])


        result['category_id'] =  [(6, 0, TranslatorSFAccount.convertCategory(SF_Account,odoo))]
        result['message_ids'] = [(0, 0, TranslatorSFAccount.generateLog(SF_Account))]

        result['log_info'] = SF_Account['Name']
        
        ### SEGMENTATION
        #if SFAccount['Is_supplier__c'] or SFAccount['Supplier__c']:
        if SF_Account['Industry']:
            result['industry_id'] = mapOdoo.convertRef(SF_Account['Industry'],odoo,'res.partner.industry',False)
        if SF_Account['Activity__c']:
            result['client_activity_ids'] = [(6, 0, mapOdoo.convertRef(SF_Account['Activity__c'],odoo,'client.activity',True))]
        #if SF_Account['Product_Type__c']:
            #result['client_product_ids'] = [(6, 0, mapOdoo.convertRef(SF_Account['Product_Type__c'],odoo,'client.product',True))]

        #########
        return result

    @staticmethod
    def convertCategory(SFAccount, odoo):
        result = []
        SFtype = SFAccount['Type']
        if SFAccount['Is_supplier__c'] or SFAccount['Supplier__c']:
            result += [odoo.env.ref('vcls-contact.category_PS').id]
        elif SFAccount['Project_Controller__c'] or SFAccount['VCLS_Alt_Name__c']:
            result += [odoo.env.ref('vcls-contact.category_account').id]
        if SFtype:
            if (not SFAccount['Is_supplier__c'] or not SFAccount['Supplier__c']) and 'supplier' in SFtype.lower():
                result += [odoo.env.ref('vcls-contact.category_PS').id]
            if 'competitor' in SFtype.lower():
                result += [odoo.env.ref('vcls-contact.category_competitor').id]
            if 'partner' in SFtype.lower():
                result += [odoo.env.ref('vcls-contact.category_partner').id]
        return result
    
    @staticmethod
    def convertStatus(SF):
        status = SF['Supplier_Status__c']
        if (status == 'Active - contract set up, information completed') or SF['Project_Controller__c'] or SF['VCLS_Alt_Name__c']:
            return 3
        elif status == 'Prospective: no contract, pre-identify' or SF['To_be_Reviewed__c']:
            return 2
        elif status == 'Inactive - reason mentioned':
            return 4
        elif SF['Is_supplier__c'] or SF['Supplier__c']: # New
            return 2
        else: # Undefined
            return 1
    
    @staticmethod
    def convertEmployees(sf_value):
        if sf_value <= 10:
            return '1_10'
        elif 11 <= sf_value <= 50:
            return '11_50'
        elif 51 <= sf_value <= 200:
            return '51_200'
        elif 201 <= sf_value <= 500:
            return '201_500'
        elif 501 <= sf_value <= 2000:
            return '501_2000'
        else:
            return '2000'
    
    @staticmethod
    def generateLog(SF_Account):
        result = {
            'model': 'res.partner',
            'message_type': 'comment',
            'body': '<p>Salesforce Synchronization</p>'
        }

        return result

    @staticmethod
    def translateToSF(Odoo_Contact, odoo):
        result = {}
        # Modify the name with -test
        result['Name'] = Odoo_Contact.name

        if Odoo_Contact.city:
            result['BillingCity'] = Odoo_Contact.city
        if Odoo_Contact.zip:
            result['BillingPostalCode'] = Odoo_Contact.zip
        if Odoo_Contact.street:
            result['BillingStreet'] = Odoo_Contact.street
        if Odoo_Contact.country_id:
            result['BillingCountry'] = TranslatorSFAccount.revertCountry(Odoo_Contact.country_id.id, odoo)

        if Odoo_Contact.altname:
            result['VCLS_Alt_Name__c'] = Odoo_Contact.altname
        if Odoo_Contact.user_id:
            result['OwnerId'] = TranslatorSFGeneral.TranslatorSFGeneral.revertOdooIdToSfId(Odoo_Contact.user_id, odoo)
            
        if Odoo_Contact.phone:
            result['Phone'] = Odoo_Contact.phone
        if Odoo_Contact.fax:
            result['Fax'] = Odoo_Contact.fax
        if Odoo_Contact.website:
            result['Website'] = Odoo_Contact.website
        
        if Odoo_Contact.description:
            if len(Odoo_Contact.description) < 255:   
                result['Supplier_Description__c'] = Odoo_Contact.description

        result['Create_Sharepoint_Folder__c'] = Odoo_Contact.create_folder
        if Odoo_Contact.currency_id:
            result['CurrencyIsoCode'] = Odoo_Contact.currency_id.name
        if Odoo_Contact.expert_id:
            result['VCLS_Main_Contact__c'] = TranslatorSFGeneral.TranslatorSFGeneral.revertOdooIdToSfId(Odoo_Contact.expert_id, odoo)
        if Odoo_Contact.assistant_id:
            result['Project_Assistant__c'] = TranslatorSFGeneral.TranslatorSFGeneral.revertOdooIdToSfId(Odoo_Contact.assistant_id, odoo)
        if Odoo_Contact.controller_id:
            result['Project_Controller__c'] = TranslatorSFGeneral.TranslatorSFGeneral.revertOdooIdToSfId(Odoo_Contact.controller_id, odoo)
        if Odoo_Contact.industry_id:
            result['Industry'] = Odoo_Contact.industry_id.name
        if Odoo_Contact.project_supplier_type_id:
            result['Supplier_Project__c'] = Odoo_Contact.project_supplier_type_id.name
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

    
    
    
    

    