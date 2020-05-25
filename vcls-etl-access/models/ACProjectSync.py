from . import TranslatorACProject
from . import ETL_ACCESS
from . import generalSync
import logging
_logger = logging.getLogger(__name__)

from tzlocal import get_localzone
import pytz
from datetime import datetime

from odoo import exceptions, models, fields, api

class ACProjectSync(models.Model):
    _name = 'etl.access.project'
    _inherit = 'etl.sync.access'

    def getAccessTranslator(self, accessInstance):
        return TranslatorACProject.TranslatorACProject(accessInstance)