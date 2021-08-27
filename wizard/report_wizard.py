# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from functools import partial
from odoo.osv import expression

import psycopg2
import pytz
import locale

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons import decimal_precision as dp


class Report_wizard(models.AbstractModel):

    _name = 'report.ostation.etat'


    @api.model
    def get_ca(self, debut=False, fin=False):
        factures = self.env['account.invoice'].search([
            ('date_invoice', '>=', debut),
            ('date_invoice', '<=', fin)
            ])
        

  
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        data.update(self.get_ca(data['debut'], data['fin']))
        #locale.setlocale(locale.LC_ALL, 'fr_FR')
        return data