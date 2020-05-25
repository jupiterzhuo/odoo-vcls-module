from . import TranslatorACGeneral
import logging
from datetime import datetime
_logger = logging.getLogger(__name__)

class TranslatorACTimesheet(TranslatorACGeneral.TranslatorACGeneral):
    def __init__(self,access):
        super().__init__(access)
    @staticmethod
    def translateToOdoo(AC_Project, odoo, access):
        pass

    @staticmethod
    def translateToAccess(Odoo_Account):
        pass

    @staticmethod
    def createTimesheet(odoo, clientID, access, counter, lenClient):
        if str(clientID) == "164":
            sql = "Select ProjHoursID, ProjID, EmployeeID, Invoiced FROM tblProjHours WHERE ClientID = " + str(clientID)
            projHours = access.execute(sql).fetchall()
            timesheet = {}
            counterProjHours = 0
            for projHour in projHours:
                counterProjHours += 1
                projHoursID = projHour[0]
                sale_id = TranslatorACGeneral.TranslatorACGeneral.toOdooId(projHour[1], 'sale.order', 'project', odoo)
                project_id = odoo.env['project.project'].search([('sale_order_id','=',sale_id)],limit=1)
                task_id = odoo.env['project.task'].search([('sale_order_id','=',sale_id)], limit=1)
                employeeID = TranslatorACGeneral.TranslatorACGeneral.getEmployeeID(projHour[2], access, odoo)
                if str(sale_id) == "1051":
                    if project_id and employeeID and sale_id and task_id:
                        if projHour[3]:
                            timesheet['stage_id'] = "invoiced"
                        else:
                            timesheet['stage_id'] = "invoiceable"
                        timesheet['is_timesheet'] = True
                        timesheet['main_project_id'] = project_id.id
                        timesheet['project_id'] = project_id.id
                        timesheet['task_id'] = task_id.id
                        timesheet['employee_id'] = employeeID.id
                        timesheet['user_id'] = employeeID.user_id.id

                        so_line = TranslatorACTimesheet.getSo_Line(projHour[2], sale_id, access, odoo)
                        rate_id = TranslatorACTimesheet.getRateId(projHour[2], access, odoo)
                        sql2 = "SELECT * FROM tblHours WHERE ProjHoursID = " + str(projHoursID)
                        hours = access.execute(sql2).fetchall()
                        counterHour = 0
                        for hour in hours:
                            counterHour += 1
                            i = 2
                            while i < 21:
                                if hour[i+1] > 0:
                                    timesheet['date'] = hour[i]
                                    timesheet['unit_amount'] = hour[i+1]
                                    timesheet['name'] = hour[i+2]
                                    print(timesheet)
                                    time = odoo.env['account.analytic.line'].with_context(tracking_disable=1).create(timesheet)
                                    time.write({'so_line': so_line})
                                    if rate_id:
                                        time.write({'rate_id': rate_id})
                                    _logger.info("ETL | Client {}/{} | ProjectHours {}/{} | Hours {}/{} |".format(counter,lenClient,counterProjHours,len(projHours),counterHour,len(hours)))
                                i = i + 3


    @staticmethod
    def generateLog(AC_Timesheet):
        result = {
            'model': 'account.analytic.line',
            'message_type': 'comment',
            'body': '<p>Access Synchronization</p>'
        }

        return result

    @staticmethod
    def getRateId(employeeID, access, odoo):
        sql = "Select PMRate, CLRate, InRate FROM tblEmployee WHERE EmployeeID = " + str(employeeID)
        employee = access.execute(sql).fetchall()
        if employee:
            if employee[0][0]:
                return odoo.env['product.product'].search([('name','=','Clinical Project Manager')],limit=1).id
            elif employee[0][1]:
                return odoo.env['product.product'].search([('name','=','Clinical Project Assistant')],limit=1).id
            elif employee[0][2]:
                return odoo.env['product.product'].search([('name','=','Senior Regulatory Scientist, Clinical Operations')],limit=1).id
            
            

        return False

    @staticmethod
    def getSo_Line(employeeID, sale_id, access, odoo):
        rate = TranslatorACTimesheet.getRateId(employeeID, access, odoo)
        sale = odoo.env['sale.order'].search([('id','=',sale_id)],limit=1)
        for line in sale.order_line:
            if rate == line.product_id.id:
                return line.id
        return False



