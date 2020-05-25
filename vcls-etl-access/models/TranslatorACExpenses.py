from . import TranslatorACGeneral
import logging
_logger = logging.getLogger(__name__)

class TranslatorACExpenses(TranslatorACGeneral.TranslatorACGeneral):
    def __init__(self,access):
        super().__init__(access)

    @staticmethod
    def translateToOdoo(AC_Expense, odoo, access):
        mapOdoo = odoo.env['map.odoo']
        
        result = {}
        ### DEFAULT VALUES
        result["name"] = TranslatorACExpenses.getClientName(AC_Expense[1], access) + " | " + TranslatorACExpenses.getAdditionalExpenseType(AC_Expense[2], access)
        bh_product = odoo.env['product.product'].search([('name','=','B&H Product')],limit=1)
        if bh_product:
            result["product_id"] = bh_product.id
        result["state"] = "done"
        result["project_id"] = TranslatorACExpenses.getProjectID(AC_Expense[1], odoo)
        #result["employee_id"] = TranslatorACGeneral.TranslatorACGeneralgetEmployeeID(EmployeeID, access, odoo)
        result["payment_mode"] = "company_account"
        result["country_id"] = odoo.env.ref('base.us').id
        result["currency_id"] = odoo.env.ref('base.USD').id
        result["unit_amount"] = AC_Expense[4]
        result["quantity"] = 1
        result["date"] = AC_Expense[3]
        result["company_id"] = odoo.env.ref('vcls-hr.company_BH').id

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
    def getAdditionalExpenseType(AddExpTypeID, access):
        sql = "SELECT AdditionalExpenseType FROM tblAddExpType WHERE AddExpTypeID = " + str(AddExpTypeID)
        row = access.execute(sql).fetchall()
        if row:
            return str(row)
        return ""
    
    @staticmethod
    def getClientName(ClientID, access):
        sql = "SELECT ClientName FROM tblClient WHERE ClientID = " + str(ClientID)
        row = access.execute(sql).fetchall()
        if row:
            return str(row)
        return ""

    @staticmethod
    def getProjectID(ClientID, odoo):
        partner_id = TranslatorACGeneral.TranslatorACGeneral.toOdooId(ClientID,"res.partner","client",odoo)
        if partner_id:
            return odoo.env["project.project"].search([("partner_id","=",partner_id)],limit=1)
        return False