
# -*- coding: utf-8 -*-


import json, re, uuid
from functools import partial
from lxml import etree
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode
from odoo import api, exceptions, fields, models, _
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.tools.misc import formatLang
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    l10n_mx_edi_cfdi_name2 = fields.Char(copy=False)
    is_start_amount = fields.Boolean('Es saldo inicial', help='Si es True, esta factura es de saldos inciiales')


class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    tax_code_mx = fields.Char(string='Codigo cuenta')

