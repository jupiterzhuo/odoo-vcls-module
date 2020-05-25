from . import TranslatorACTimesheet
from . import ETL_ACCESS
from . import generalSync
import logging
_logger = logging.getLogger(__name__)

from tzlocal import get_localzone
import pytz
from datetime import datetime

from odoo import exceptions, models, fields, api

class ACTimesheetSync(models.Model):
    _name = 'etl.access.timesheet'
    _inherit = 'etl.sync.access'

    def getAccessTranslator(self, accessInstance):
        return TranslatorACTimesheet.TranslatorACTimesheet(accessInstance)