# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from pytz import timezone
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import zipfile
import time
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

from odoo.tools.safe_eval import safe_eval


class AccountCFDI(models.Model):
    _inherit = "account.cfdi"  

    dashboard_downloader_i_id = fields.Many2one('cfdi.account.dashboard.manager', 'Ref. Descarga Ingresos')
    dashboard_downloader_e_id = fields.Many2one('cfdi.account.dashboard.manager', 'Ref. Descarga Egresos')
    dashboard_downloader_t_id = fields.Many2one('cfdi.account.dashboard.manager', 'Ref. Descarga Traslados')
    dashboard_downloader_n_id = fields.Many2one('cfdi.account.dashboard.manager', 'Ref. Descarga Nomina')
    dashboard_downloader_p_id = fields.Many2one('cfdi.account.dashboard.manager', 'Ref. Descarga Pagos')
    dashboard_downloader_o_id = fields.Many2one('cfdi.account.dashboard.manager', 'Ref. Descarga Otros')

class CFDIAccountDashboardManager(models.Model):
    _inherit = 'cfdi.account.dashboard.manager'

    account_cfdi_i_ids = fields.One2many('account.cfdi', 'dashboard_downloader_i_id', 
            'Ingresos')
    found_cfdis_i = fields.Boolean('Ingresos Encontrados')
    account_cfdi_e_ids = fields.One2many('account.cfdi', 'dashboard_downloader_e_id', 
            'Egresos')
    found_cfdis_e = fields.Boolean('Egresos Encontrados')
    account_cfdi_t_ids = fields.One2many('account.cfdi', 'dashboard_downloader_t_id', 
            'Traslados')
    found_cfdis_t = fields.Boolean('Traslados Encontrados')
    account_cfdi_n_ids = fields.One2many('account.cfdi', 'dashboard_downloader_n_id', 
            'Nominas')
    found_cfdis_n = fields.Boolean('Nominas Encontrados')
    account_cfdi_p_ids = fields.One2many('account.cfdi', 'dashboard_downloader_p_id', 
            'Pagos')
    found_cfdis_p = fields.Boolean('Pagos Encontrados')
    account_cfdi_o_ids = fields.One2many('account.cfdi', 'dashboard_downloader_o_id', 
            'Otros')
    found_cfdis_o = fields.Boolean('Otros Encontrados')

    read_previously = fields.Boolean('Leido Previamente')

    auditoria_count = fields.Integer('No. Documentos Leidos')

    account_cfdis = fields.Many2many('account.cfdi', 'cfdi_account_dashboard_rel', 'cfdi_id', 'dashboard_id', 'Cfdis Leidos')

    @api.multi
    def action_execute_auditor(self):
        account_cfdi_obj = self.env["account.cfdi"]
        for rec in self:
            if rec.number_of_documents <= 0 or not rec.file:
                raise UserError("No existe información para Auditar.")
            if rec.read_previously:
                raise UserError("El Archivo ZIP ya fue procesado anteriormente.")
            wizard_auditor_obj = self.env['account.cfdi.wizard.zipfile']
            vals = {
                'zip_file': rec.file,
            }
            wizard_br = wizard_auditor_obj.create(vals)
            wizard_process_result = wizard_br.get_cfdis_from_zipfile()
            if 'domain' in wizard_process_result:
                domain = wizard_process_result.get('domain') or '[]'
                eval_context = {
                            'domain': domain,
                        }
                
                try:
                    domain = safe_eval(domain, eval_context)
                    account_cfdis = domain[0][2]
                    found_cfdis_i = False
                    found_cfdis_e = False
                    found_cfdis_t = False
                    found_cfdis_n = False
                    found_cfdis_p = False
                    found_cfdis_o = False
                    for acc_cfdi in account_cfdi_obj.browse(account_cfdis):
                        if acc_cfdi.tipo_cfdi in ('INGRESO','I'):
                            acc_cfdi.dashboard_downloader_i_id = rec.id
                            found_cfdis_i = True
                        elif acc_cfdi.tipo_cfdi in ('EGRESO','E'):
                            acc_cfdi.dashboard_downloader_e_id = rec.id
                            found_cfdis_e = True
                        elif acc_cfdi.tipo_cfdi in ('TRASLADO','T'):
                            acc_cfdi.dashboard_downloader_t_id = rec.id
                            found_cfdis_t = True
                        elif acc_cfdi.tipo_cfdi == 'N':
                            acc_cfdi.dashboard_downloader_n_id = rec.id
                            found_cfdis_n = True
                        elif acc_cfdi.tipo_cfdi == 'P':
                            acc_cfdi.dashboard_downloader_p_id = rec.id
                            found_cfdis_p = True
                        else:
                            acc_cfdi.dashboard_downloader_o_id = rec.id
                            found_cfdis_o = True
                    rec.write({'read_previously': True, 'auditoria_count': len(account_cfdis), 'account_cfdis': [(6,0,account_cfdis)]})
                    rec.write({
                            'found_cfdis_i': found_cfdis_i,
                            'found_cfdis_e': found_cfdis_e,
                            'found_cfdis_t': found_cfdis_t,
                            'found_cfdis_n': found_cfdis_n,
                            'found_cfdis_p': found_cfdis_p,
                            'found_cfdis_o': found_cfdis_o,
                        })
                except:
                    raise UserError("No se encontro información por favor revise el Archivo.")
            else:
                raise UserError("No se encontro información por favor revise el Archivo.")
        return True

    @api.multi
    def action_view_auditor_records(self):
        for rec in self:
            return {
                    'domain'    : "[('id','in', ["+','.join(map(str,rec.account_cfdis.ids))+"])]",
                    'name'      : _('CFDIs Descargados del Portal del SAT'),
                    'view_type' : 'form',
                    'view_mode' : 'tree,form',
                    'res_model' : 'account.cfdi',
                    'view_id'   : False,
                    'type'      : 'ir.actions.act_window'
                    }
        