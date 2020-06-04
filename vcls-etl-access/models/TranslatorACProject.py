from . import TranslatorACGeneral
import logging
from datetime import datetime
_logger = logging.getLogger(__name__)

class TranslatorACProject(TranslatorACGeneral.TranslatorACGeneral):
    def __init__(self,access):
        super().__init__(access)

    @staticmethod
    def translateToOdoo(AC_Project, odoo, access):
        mapOdoo = odoo.env['map.odoo']
        
        result = {}
        ### DEFAULT VALUES
        result['company_id'] = odoo.env.ref('vcls-hr.company_BH').id
        result['pricelist_id'] = odoo.env.ref('vcls-crm.pricelist_std_USD').id
        result['name'] = AC_Project[1]
        result['partner_id'] = False
        o_tag = odoo.env['crm.lead.tag'].search([('name','=','Automated Migration')],limit=1)
        tag = o_tag.id if o_tag else False
        result['tag_ids'] = [(4, tag, 0)]
        
        if AC_Project[2]:
            partner_id = TranslatorACGeneral.TranslatorACGeneral.toOdooId(AC_Project[2],"res.partner","client",odoo)
            result['partner_id'] = partner_id
            result['partner_invoice_id'] = partner_id
            result['partner_shipping_id'] = partner_id

        if AC_Project[3]:
            lastname = TranslatorACProject.getEmployeeLastName(AC_Project[3],access)
            firstname = TranslatorACProject.getEmployeeFirstName(AC_Project[3],access)
            result['user_id'] = TranslatorACProject.getUserID(firstname, lastname, odoo)
        
        if AC_Project[4]:
            result['expected_start_date'] = AC_Project[4]
        else:
            result['expected_start_date'] = "01/01/1999"
        if AC_Project[5]:     
            result['expected_end_date'] =  AC_Project[5]
        else:
            result['expected_end_date'] = datetime.now()
        
        result['product_category_id'] = odoo.env.ref('vcls-etl-access.bh_category').id

        sale_exist = odoo.env['sale.order'].search([('unrevisioned_name', '=', result['name']),('company_id', '=', result['company_id'])]).id
        _logger.info(result)
        if result['name'] and result['partner_id'] and not sale_exist:
            return result 
        else:
            return False
    @staticmethod
    def translateToAccess(Odoo_Account):
        pass

    @staticmethod
    def generateLog(SF_Campaign):
        result = {
            'model': 'sale.order',
            'message_type': 'comment',
            'body': '<p>Access Synchronization</p>'
        }

        return result

    @staticmethod
    def getEmployeeLastName(employeeID, access):
        sql = "SELECT LName FROM tblEmployee WHERE EmployeeID = " + str(employeeID)
        row = access.execute(sql).fetchall()
        if row:
            return row[0][0]
        return False

    @staticmethod
    def getEmployeeFirstName(employeeID, access):
        sql = "SELECT FName FROM tblEmployee WHERE EmployeeID = " + str(employeeID)
        row = access.execute(sql).fetchall()
        if row:
            return row[0][0]
        return False

    @staticmethod
    def getUserID(firstname, lastname, odoo):
        user_id = odoo.env['res.users'].search([('firstname','=',firstname),('lastname','=',lastname)],limit=1)
        if user_id:
            return user_id.id
        user_id = odoo.env['res.users'].search([('firstname','=',firstname)],limit=1)
        if user_id:
            return user_id.id
        user_id = odoo.env['res.users'].search([('lastname','=',lastname)],limit=1)
        if user_id:
            return user_id.id
        return False

    @staticmethod
    def getPmRate(clientID, access):
        sql = "SELECT PMRate FROM tblClient WHERE ClientID = " + str(clientID)
        row = access.execute(sql).fetchall()
        if row:
            return row[0][0]
        return False
        
    @staticmethod
    def getClRate(clientID, access):
        sql = "SELECT CLRate FROM tblClient WHERE ClientID = " + str(clientID)
        row = access.execute(sql).fetchall()
        if row:
            return row[0][0]
        return False

    @staticmethod
    def getRaRate(clientID, access):
        sql = "SELECT InRate FROM tblClient WHERE ClientID = " + str(clientID)
        row = access.execute(sql).fetchall()
        if row:
            return row[0][0]
        return False
    
    @staticmethod
    def setOrderLine(odoo, AC_Project, access, so_id):
        if AC_Project[2]:
            pm_rate = TranslatorACProject.getPmRate(AC_Project[2], access)
            cl_rate = TranslatorACProject.getClRate(AC_Project[2], access)
            ra_rate = TranslatorACProject.getRaRate(AC_Project[2], access)

            service_product = odoo.env['product.product'].search([('name','=','Migration Default')],limit=1)
            pm_product = odoo.env.ref('vcls-etl-access.project_manager_product').product_variant_ids
            cl_product = odoo.env.ref('vcls-etl-access.clerical_product').product_variant_ids
            ra_product = odoo.env.ref('vcls-etl-access.regulatory_associate_product').product_variant_ids
            #we create a section services
            section = odoo.env['sale.order.line'].create({
                                'order_id':so_id,
                                'display_type': 'line_section',
                                'name':'Services',
                })
            vals = {
                    'order_id':so_id,
                    'name':AC_Project[1],
                    'product_id':service_product.id,
                    'product_uom_qty':1,
                    'price_unit':0
                }
            TranslatorACProject.so_line_create_with_changes(odoo,vals)
            #we create a section hours
            section = odoo.env['sale.order.line'].create({
                'order_id':so_id,
                'display_type': 'line_section',
                'name':'Hourly Rates',
                })
            if pm_rate and pm_product:
                vals = {
                    'order_id':so_id,
                    'product_id': pm_product.ids[0],
                    'product_uom_qty':0,
                    'section_line_id':section.id,
                    }
                if pm_rate > 0:
                    vals.update({'price_unit':pm_rate})
                TranslatorACProject.so_line_create_with_changes(odoo,vals)
            if cl_rate and cl_product:
                vals = {
                    'order_id':so_id,
                    'product_id': cl_product.ids[0],
                    'product_uom_qty':0,
                    'section_line_id':section.id,
                    }
                if cl_rate > 0:
                    vals.update({'price_unit':cl_rate})
                TranslatorACProject.so_line_create_with_changes(odoo,vals)
            if ra_rate and ra_product:
                vals = {
                    'order_id':so_id,
                    'product_id': ra_product.ids[0],
                    'product_uom_qty':0,
                    'section_line_id':section.id,
                    }
                if ra_rate > 0:
                    vals.update({'price_unit':ra_rate})
                TranslatorACProject.so_line_create_with_changes(odoo,vals)
    
    @staticmethod
    def so_line_create_with_changes(odoo,vals):
        line = odoo.env['sale.order.line'].create(vals)
        if line.display_type != 'line_section':
            line.product_id_change()
            line.product_uom_change()
            line.write(vals)