from . import TranslatorSFLedgerAccount
from . import ETL_SF
from . import generalSync

import pytz
from simple_salesforce import Salesforce
from tzlocal import get_localzone
from datetime import datetime
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


from odoo import models, fields, api

class SFLedgerAccountSync(models.Model):
    _name = 'etl.salesforce.ledgeraccount'
    _inherit = 'etl.sync.salesforce'

    def getSFTranslator(self, sfInstance):
        return TranslatorSFLedgerAccount.TranslatorSFLedgerAccount(sfInstance.getConnection())



