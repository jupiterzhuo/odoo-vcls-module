from . import TranslatorSFLedgerEntry
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

class SFLedgerEntrySync(models.Model):
    _name = 'etl.salesforce.ledgerentry'
    _inherit = 'etl.sync.salesforce'

    def getSFTranslator(self, sfInstance):
        return TranslatorSFLedgerEntry.TranslatorSFLedgerEntry(sfInstance.getConnection())


