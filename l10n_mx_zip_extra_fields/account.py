# -*- encoding: utf-8 -*-

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo import api, exceptions, fields, models, _
#import odoo.addons.decimal_precision as dp
import time
from datetime import datetime, timedelta
import base64
import os
import zipfile
import subprocess
import tempfile
from xml.dom.minidom import parse, parseString
import xmltodict
import requests

from odoo.modules import module

import os 

import qrcode
import io

from textwrap import wrap ## Division de cadena en N caracteres ###

import logging
_logger = logging.getLogger(__name__)

from . import BeautifyCFDI ## Conversion de XML a Diccionario

class AccountCFDITaxGlobal(models.Model):
    _name = 'account.cfdi.tax.global'
    _description = 'Auditor CFDI Impuestos Totales'
   
    name = fields.Char('Descripción', size=128) 


class AccountCFDITax(models.Model):
    _name = 'account.cfdi.tax'
    _description = 'Auditor CFDI Impuesto'
   
    name = fields.Char('Codigo', size=128) 
    tipo_impuesto = fields.Char('Tipo Impuesto', size=128) 
    factor = fields.Char('Factor', size=128) 
    tasa_cuota = fields.Float('Tasa/Cuota', digits=(14,2))
    base = fields.Float('Base', digits=(14,2))
    importe = fields.Float('Importe', digits=(14,2))

    concepto_id = fields.Many2one('account.cfdi.concepto', 'Ref. Concepto')

class AccountCFDIConcepto(models.Model):
    _name = 'account.cfdi.concepto'
    _description = 'Auditor CFDI Linea'
   
    name = fields.Char('Descripción', size=128) 
    clave = fields.Char('Clave SAT', size=128) 
    unidad = fields.Char('UdM', size=128)
    cantidad = fields.Float('Cantidad', digits=(14,2))
    precio = fields.Float('Precio U.', digits=(14,2))
    total = fields.Float('Importe', digits=(14,2))

    impuesto_ids = fields.One2many('account.cfdi.tax', 'concepto_id', 'Impuestos')

    cfdi_id = fields.Many2one('account.cfdi', 'Ref. Auditor')

class AccountCFDI(models.Model):
    _inherit = "account.cfdi"  

    iva_amount = fields.Float('Total IVA', digits=(14,4))
    subtotal_amount = fields.Float('Subtotal', digits=(14,4))

    serie = fields.Char('Serie', size=64)
    folio = fields.Char('Folio', size=64)

    pay_method_id = fields.Many2one('pay.method', 'Forma de Pago')
    metodo_pago_id = fields.Many2one('sat.metodo.pago', 'Metodo de Pago')

    ### Emisor ####
    nombre_emisor = fields.Char('E. Nombre', size=128)
    rfc_emisor = fields.Char('E. RFC', size=128)
    regimen_emisor = fields.Char('E. Régimen Fiscal', size=128)

    ### Receptor ####
    nombre_receptor = fields.Char('R. Nombre', size=128)
    rfc_receptor = fields.Char('R. RFC', size=128)
    # regimen_receptor = fields.Char('R. Régimen Fiscal', size=128)
    uso_cfdi_receptor = fields.Char('Uso CFDI', size=128)

    ### Conceptos ###
    concepto_ids = fields.One2many('account.cfdi.concepto', 'cfdi_id', 'Conceptos')

    ### Comprobante ###
    comprobante_fecha = fields.Datetime('Fecha Emision')
    metodo_pago = fields.Char('Metodo Pago', size=128)
    version = fields.Char('Versión', size=128)
    tipo_comprobante = fields.Char('Tipo Comprobante', size=128)
    certificado_documento = fields.Char('Certificado', size=512)
    no_certificado_documento = fields.Char('No. Certificado', size=128)
    forma_pago = fields.Char('Forma de Pago', size=128)
    sello_emisor = fields.Char('Sello Emisor', size=512)
    sello_sat = fields.Char('Sello SAT', size=512)
    lugar_expedicion = fields.Char('Lugar Expedicion', size=128)
    moneda = fields.Char('Moneda', size=128)
    tipo_cambio = fields.Monetary('T.C.', digits=(14,2))

    serie_documento = fields.Char('Serie', size=64)
    folio_documento = fields.Char('Folio', size=64)


    documento_uuid = fields.Char('UUID', size=128)
    fechatimbrado_doc = fields.Datetime('Fecha Timbrado')
    rfc_pac = fields.Char('Rfc Prov. Certif.', size=128)
    no_certificado_sat = fields.Char('No. Certificado SAT', size=128)

    total = fields.Monetary('Total', digits=(14,2))
    subtotal = fields.Monetary('Subtotal', digits=(14,2))

    certificado_documento_show = fields.Char('Certificado', size=512)
    sello_emisor_show = fields.Char('Sello Emisor', size=512)
    sello_sat_show = fields.Char('Sello SAT', size=512)

    cfdi_cbb = fields.Binary(string='Código Bidimensional', readonly=True, copy=False)

    cadena_original = fields.Char('Cadena Original', size=512)
    cadena_original_show = fields.Char('Cadena Original', size=512)

    def get_type_doc(self):
        doc_name = ""
        tipo_doc_dict = {
                            'E': 'Nota de Credito', 
                            'I': 'Factura', 
                            'EGRESO': 'Nota de Credito (3.2)', 
                            'P': 'Pago', 
                            'T': 'Factura Traslado', 
                            'N': 'Nomina', 
                            'TRASLADO': 'Fac. Traslado (3.2)', 
                            'INGRESO': 'Factura (3.2)'
                        }
        doc_name = tipo_doc_dict[self.tipo_cfdi]
        return doc_name

    def get_taxes_amount(self):
        tax_amount = 0.0
        for concepto in self.concepto_ids:
            for tax in concepto.impuesto_ids:
                tax_amount += tax.importe
        return tax_amount

class AccountCFDItWizardZipFile(models.TransientModel):
    _inherit = 'account.cfdi.wizard.zipfile'

    def b64str_to_tempfile(self, b64_str=None, file_suffix=None, file_prefix=None):
        """
        @param b64_str : Text in Base_64 format for add in the file
        @param file_suffix : Sufix of the file
        @param file_prefix : Name of file in TempFile
        """
        (fileno, fname) = tempfile.mkstemp(file_suffix, file_prefix)
        f = open(fname, 'wb')
        f.write(base64.decodestring(b64_str or str.encode('')))
        f.close()
        os.close(fileno)
        return fname


    def xml_b64_str_to_physical_file(self, b64_str, file_extension='xml', prefix='xml_auditor_odoo'):
        _logger.info("\n####################### logo_b64_str_to_physical_file >>>>>>>>>>> ")
        _logger.info("\n####################### file_extension %s " % file_extension)
        _logger.info("\n####################### prefix %s " % prefix)
        certificate_lib = self.env['facturae.certificate.library']
        # b64_temporal_route = certificate_lib.b64str_to_tempfile(base64.encodestring(b''), 
        #                                                   file_suffix='.%s' % file_extension, 
        #                                                   file_prefix='odoo_%s_' % prefix)
        b64_temporal_route = self.b64str_to_tempfile(base64.encodestring(b''), 
                                                          file_suffix='.%s' % file_extension, 
                                                          file_prefix='odoo__%s__' % prefix)
        _logger.info("\n### b64_temporal_route %s " % b64_temporal_route)
        ### Guardando el Logo  ###
        f = open(b64_temporal_route, 'wb')
        f.write(b64_str)
        f.close()

        file_result = open(b64_temporal_route, 'rb').read()
        
        return file_result, b64_temporal_route

    def attachment_xml_to_audit(self, xml_data, xml_name, audit_record):
        attachment_obj = self.env['ir.attachment']
        if not xml_name:
            xml_name = 'XML AUDITOR: %s.xml' % audit_record.id
        #tmpl_result, tmp_xml_path = self.xml_b64_str_to_physical_file(base64.encodestring(str.encode(xml_data)))

        ### Guardandolo en el TMP ####
        (fileno, fname_xml_path) = tempfile.mkstemp(".xml", "odoo_xml_to_sifei__")
        file_temp_audit = open(fname_xml_path, 'w')
        file_temp_audit.write(xml_data)
        file_temp_audit.close()

        os.close(fileno)

        data_attach = {
                'name'        : xml_name,
                'datas'       : base64.encodestring(str.encode(xml_data)),
                'datas_fname' : xml_name,
                'description' : 'Archivo XML generado por el Auditor: %s' % (audit_record.id),
                'res_model'   : 'account.cfdi',
                'res_id'      : audit_record.id,
                'type'        : 'binary',
            }
        attach = attachment_obj.with_context({}).create(data_attach)
        result = {
                'attachment': attach,
                'path': fname_xml_path,
                'base64': base64.encodestring(str.encode(xml_data)),
        }
        return result

    def return_index_floats(self,decimales):
        i = len(decimales) - 1
        indice = 0
        while(i > 0):
            if  decimales[i] != '0':
                indice = i
                i = -1
            else:
                i-=1
        return  indice

    def create_qr_image(self, cfdi_xml, amount_total, timbre_uuid, cfdi_sello, qr_emisor, qr_receptor):
        #Get info for QRC
        
        # Para CFDI: https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx
        # Para retenciones: https://prodretencionverificacion.clouda.sat.gob.mx/
        url = "https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx"
        UUID = timbre_uuid

        total = "%.6f" % ( amount_total or 0.0)
        total_qr = ""
        qr_total_split = total.split('.')
        decimales = qr_total_split[1]
        index_zero = self.return_index_floats(decimales)
        decimales_res = decimales[0:index_zero+1]
        if decimales_res == '0':
            total_qr = qr_total_split[0]
        else:
            total_qr = qr_total_split[0]+"."+decimales_res

        last_8_digits_sello = ""

        last_8_digits_sello = cfdi_sello[len(cfdi_sello)-8:]

        qr_string = '%s?id=%s&re=%s&rr=%s&tt=%s&fe=%s'% (url, UUID, qr_emisor, qr_receptor, total_qr, last_8_digits_sello)

        # try:
        img = qrcode.make(qr_string.encode('utf-8'))
        output = io.BytesIO()
        img.save(output, format='JPEG')
        qr_bytes = base64.encodestring(output.getvalue())
        # except e:
        #     raise UserError(_('Advertencia !!!\nNo se pudo crear el Código Bidimensional. Error %s') % e)
        return qr_bytes or False
    

    @api.multi
    def get_cfdis_from_zipfile(self):
        account_cfdi_obj = self.env['account.cfdi']
        
        ### Lectura del XML
        concepto_obj = self.env['account.cfdi.concepto']

        currency_obj = self.env['res.currency']
        (fileno, fname) = tempfile.mkstemp('sat_cfdi_zip_', '.zip')
        f = open(fname, 'wb')
        f.write(base64.decodestring(self.zip_file))
        f.close()
        os.close(fileno)
        try:
            archivo_zip = zipfile.ZipFile(fname, 'r')
        except:
            archivo_zip = False
        if not archivo_zip:
            raise UserError(_("Error ! El archivo no es un archivo ZIP o no contiene archivos XML de CFDIs..."))
        #### Parametros para el manejo de la cadena original ###
        context_control = {}
        factura_module_path = module.get_module_path('l10n_mx_einvoice')
        context_control['fname_xslt'] = factura_module_path and os.path.join(
                factura_module_path, 'SAT', 'cadenaoriginal_3_3',
                'cadenaoriginal_3_3.xslt') or ''
        ### TFD CADENA ORIGINAL XSLT ###
        context_control['fname_xslt_tfd'] = factura_module_path and os.path.join(
            factura_module_path, 'SAT', 'cadenaoriginal_3_3',
            'cadenaoriginal_TFD_1_1.xslt') or ''

        cfdi_ids = []
        for file_name in archivo_zip.namelist():
            _logger.info(_('Importando: %s') % (file_name))
            try:
                x = file_name.split('.')[1]
            except:
                continue
            if file_name.split('.')[1] != 'xml':
                _logger.info(_('Archivo %s descartado porque no es un archivo XML') % (file_name))
                continue
            
            #_logger.info(_("-- Procesando: %s") % file_name)
             
            cfdi_str = archivo_zip.read(file_name).decode("utf-8").replace('\xef\xbb\xbf','')
            cfdi_str_original = cfdi_str
            cfdi_str = cfdi_str.lower()
            try: 
                arch_xml = parseString(cfdi_str)
            except:
                _logger.info(_('Error al procesar archivo %s donde al parecer no es archivo XML') % (file_name))
                continue
            res = account_cfdi_obj.search([('folio_fiscal','=',file_name.split('.')[0].upper())])    
            if not res:
                timbre = arch_xml.getElementsByTagName('tfd:timbrefiscaldigital')[0]    
                cfdi_data = arch_xml.getElementsByTagName('cfdi:comprobante')[0]
                data = {
                    #'clasificacion_cfdi':*
                    'tipo_cfdi'         : cfdi_data.attributes['tipodecomprobante'].value.upper() or False,
                    'folio_fiscal'      : timbre.attributes['uuid'].value.upper(),
                    'subtotal'          : cfdi_data.attributes['subtotal'].value,
                    'total'             : cfdi_data.attributes['total'].value,
                    'no_certificado'    : cfdi_data.attributes['nocertificado'].value.upper() or False,
                    }
                               
                forma_pago = ""
                metodo_pago = ""
                try:
                    metodo_pago = cfdi_data.attributes['metodopago'].value.upper() or False
                except:
                    pass
                try:
                    forma_pago = cfdi_data.attributes['formapago'].value.upper() or False
                except:
                    pass

                forma_de_pago_obj = self.env['pay.method']
                metodo_de_pago_obj = self.env['sat.metodo.pago']

                if data['tipo_cfdi'] == 'P':

                    data['monto_pago'] = 0.0
                    cadena = ['pago10:pago', 'pag:pago', 'pag:Pago']
                    root = 'pago10:pago'
                    # for cad in cadena:
                    #     try:
                    #         w = arch_xml.getElementsByTagName(cad)
                    #         root = cad
                    #     except:
                    #         pass
                    try:
                        for pago in arch_xml.getElementsByTagName(root):                        
                            data['monto_pago'] += pago.attributes['monto'].value and round(float(pago.attributes['monto'].value),4) or 0.0
                            moneda = False
                            try:
                                moneda = pago.attributes['monedap'].value.upper()
                            except:
                                pass
                            try:
                                forma_pago = pago.attributes['formadepagop'].value.upper() or False
                            except:
                                pass
                            if moneda and moneda not in ('MN','MXN','PESOS', 'PESOS MEXICANOS','NACIONAL'):
                                currency_id = currency_obj.search([('name','=',moneda)], limit=1)                
                                if currency_id:
                                    data['pago_currency_id'] = currency_id.id
                            try:
                                for docto in pago.getElementsByTagName('pago10:doctorelacionado'):
                                    try:
                                        forma_pago = docto.attributes['metododepagodr'].value.upper() or False
                                    except:
                                        pass
                            except:
                                pass

                    except:
                        pass
                if metodo_pago:
                    metodo_de_pago_id = metodo_de_pago_obj.search([('code','=',metodo_pago.upper())])
                    if metodo_de_pago_id:
                        data['metodo_pago_id'] = metodo_de_pago_id[0].id
                if forma_pago:
                    forma_de_pago_id = forma_de_pago_obj.search([('code','=',forma_pago.upper())])
                    if forma_de_pago_id:
                        data['pay_method_id'] = forma_de_pago_id[0].id
                subtotal_amount = 0.0
                try:
                    subtotal_amount = cfdi_data.attributes['subtotal'].value.upper() or False
                except:
                    pass
                if float(subtotal_amount) > 0.0:
                    data['subtotal_amount'] = float(subtotal_amount) 

                iva_amount = 0.0
                # try:
                if arch_xml.getElementsByTagName('cfdi:impuestos'):
                    impuestos_globales = arch_xml.getElementsByTagName('cfdi:impuestos')[-1]
                    # for impuesto in arch_xml.getElementsByTagName('cfdi:impuestos'):                        
                    # try:
                    if impuestos_globales.getElementsByTagName('cfdi:traslado'):
                        for traslado in impuestos_globales.getElementsByTagName('cfdi:traslado'):
                            # try:
                            code_impuesto = traslado.attributes['impuesto'].value.upper() or False
                            traslado_attribute_items = traslado.attributes.items()
                            traslado_attribute_items = [x[0] for x in traslado_attribute_items]
                            if 'importe' in traslado_attribute_items:
                                importe_impuesto = traslado.attributes['importe'].value.upper() or False
                                if code_impuesto == '002':
                                    iva_amount += float(importe_impuesto)
                    data['iva_amount'] = iva_amount
                htz = -6
                fecha_timbrado = timbre.attributes['fechatimbrado'].value or False
                fecha_timbrado = fecha_timbrado and time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(fecha_timbrado[:19], '%Y-%m-%dt%H:%M:%S')) or False
                data['fecha_certificacion'] = fecha_timbrado and datetime.strptime(fecha_timbrado, '%Y-%m-%d %H:%M:%S') + timedelta(hours=htz) or False

                fecha_emision = cfdi_data.attributes['fecha'].value or False
                fecha_emision = fecha_emision and time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(fecha_emision[:19], '%Y-%m-%dt%H:%M:%S')) or False
                data['fecha_emision'] = fecha_emision and datetime.strptime(fecha_emision, '%Y-%m-%d %H:%M:%S') + timedelta(hours=htz) or False
                serie_documento = ''
                folio_documento = ''
                try:
                    data['serie'] = cfdi_data.attributes['serie'].value.upper()
                    serie_documento = cfdi_data.attributes['serie'].value.upper()
                except:
                    pass
                try:
                    data['folio'] = cfdi_data.attributes['folio'].value.upper()
                    folio_documento = cfdi_data.attributes['folio'].value.upper()
                except:
                    pass

                moneda = False
                try:
                    moneda = cfdi_data.attributes['moneda'].value.upper()
                except:
                    pass

                if moneda and moneda not in ('MN','MXN','PESOS', 'PESOS MEXICANOS','NACIONAL'):
                    currency_id = currency_obj.search([('name','=',moneda)], limit=1)                
                    if currency_id:
                        data['currency_id'] = currency_id.id

                cfdi_emisor = arch_xml.getElementsByTagName('cfdi:emisor')[0]
                data['rfc_emisor'] = cfdi_emisor.attributes['rfc'].value.upper()
                try:
                    data['razon_social_emisor'] = cfdi_emisor.attributes['nombre'].value.upper()
                except:
                    pass
                cfdi_receptor = arch_xml.getElementsByTagName('cfdi:receptor')[0]
                data['rfc_receptor'] = cfdi_receptor.attributes['rfc'].value.upper()
                try:
                    data['razon_social_receptor'] = cfdi_receptor.attributes['nombre'].value.upper()
                except:
                    pass
                try:
                    data['uso_cfdi'] = cfdi_receptor.attributes['usocfdi'].value.upper() or False
                except:
                    pass

                res = account_cfdi_obj.create(data)
                #### Adjuntando el XML ####
                xml_name = file_name
                if '.xml' not in xml_name:
                    xml_name = file_name+'.xml'
                xml_data = cfdi_str_original
                attachment_process_result = self.attachment_xml_to_audit(xml_data, xml_name, res)
                #### Procesando el XML con libreria Beauty #####
                ### El metodo regresa
                # attachment
                # path
                # base64
                module_path = module.get_module_path('l10n_mx_zip_extra_fields')
                json_config = module_path+'/config.json'

                beauty_res = BeautifyCFDI.BeautifyCFDI(attachment_process_result['path'], 'pdf', json_config)
                ### El metodo regresa
                # emisor
                # receptor
                # conceptos
                # comprobante
                beauty_emisor = beauty_res['emisor']
                vals_emisor = {
                                    'nombre_emisor': beauty_emisor['NombreEmisor'],
                                    'rfc_emisor': beauty_emisor['RfcEmisor'],
                                    'regimen_emisor': beauty_emisor['RegimenEmisor'],
                }
                res.write(vals_emisor)

                beauty_receptor = beauty_res['receptor']
                vals_receptor = {
                                    'nombre_receptor': beauty_receptor['NombreReceptor'],
                                    'rfc_receptor': beauty_receptor['RfcReceptor'],
                                    'uso_cfdi_receptor': beauty_receptor['UsoReceptor'],
                }
                res.write(vals_receptor)
                ### Conceptos ####
                conceptos_vals = beauty_res['conceptos']
                if conceptos_vals:
                    for concepto in conceptos_vals:
                        impuestos_list = []
                        concepto_impuestos = concepto.get('Impuestos', False)
                        if concepto_impuestos:
                            for impuesto in concepto_impuestos.keys():
                                impuesto_vals = concepto_impuestos[impuesto]
                                ivals = (0,0, {
                                            'name': impuesto_vals['Impuesto'],
                                            'tipo_impuesto': impuesto_vals['TipoImpuesto'],
                                            'factor': impuesto_vals['TipoFactor'],
                                            'tasa_cuota': impuesto_vals['TasaOCuota'],
                                            'base': impuesto_vals['Base'],
                                            'importe': impuesto_vals['Importe'],
                                })
                                impuestos_list.append(ivals)
                        c_vals = {
                                    'cfdi_id': res.id,
                                    'name': concepto['Descripcion'],
                                    'clave': concepto['ClaveProdServ'],
                                    'unidad': concepto['ClaveUnidad'],
                                    'cantidad': concepto['Cantidad'],
                                    'precio': concepto['ValorUnitario'],
                                    'total': concepto['Importe'],
                                    'impuesto_ids': impuestos_list,

                        }
                        concepto_obj.create(c_vals)
                #### Comprobante #####
                beauty_comprobante = beauty_res['comprobante']
                comprobante_vals = {
                                        'comprobante_fecha': fecha_emision,
                                        'metodo_pago': beauty_comprobante['MetodoPago'],
                                        'version': beauty_comprobante['Version'],
                                        'tipo_comprobante': beauty_comprobante['TipoDeComprobante'],
                                        'certificado_documento': beauty_comprobante['Certificado'],
                                        'no_certificado_documento': beauty_comprobante['NoCertificado'],
                                        'forma_pago': beauty_comprobante['FormaPago'],
                                        'sello_emisor': beauty_comprobante['SelloCFD'],
                                        'sello_sat': beauty_comprobante['SelloSAT'],
                                        'lugar_expedicion': beauty_comprobante['LugarExpedicion'],
                                        'moneda': beauty_comprobante['Moneda'],
                                        'documento_uuid': beauty_comprobante['UUID'],
                                        'fechatimbrado_doc': fecha_timbrado,
                                        'rfc_pac': beauty_comprobante['RfcProvCertif'],
                                        'no_certificado_sat': beauty_comprobante['NoCertificadoSAT'],
                                        'total': beauty_comprobante['Total'],
                                        'subtotal': beauty_comprobante['Subtotal'],
                                        'serie_documento': serie_documento,
                                        'folio_documento': folio_documento,
                                        'tipo_cambio': beauty_comprobante['TipoCambio'],
                                    }

                #### Aplicando un Wrap a las cadenas grandes ####
                certificado_documento_show = ""
                certificado_wrap = wrap(comprobante_vals['certificado_documento'], 120)
                for x in certificado_wrap:
                    certificado_documento_show = certificado_documento_show+"\n"+x if certificado_documento_show else x
                comprobante_vals.update(certificado_documento_show=certificado_documento_show)

                sello_emisor_show = ""
                sello_wrap = wrap(comprobante_vals['sello_emisor'], 120)
                for x in sello_wrap:
                    sello_emisor_show = sello_emisor_show+"\n"+x if sello_emisor_show else x
                comprobante_vals.update(sello_emisor_show=sello_emisor_show)

                sello_sat_show = ""
                sello_sat_wrap = wrap(comprobante_vals['sello_sat'], 120)
                for x in sello_sat_wrap:
                    sello_sat_show = sello_sat_show+"\n"+x if sello_sat_show else x
                comprobante_vals.update(sello_sat_show=sello_sat_show)
                res.write(comprobante_vals)      

                ### Creando el QR ####
                cfdi_cbb = self.create_qr_image(cfdi_str_original, float(beauty_comprobante['Total']), 
                                                beauty_comprobante['UUID'], beauty_comprobante['SelloCFD'], 
                                                beauty_emisor['RfcEmisor'],
                                                beauty_receptor['RfcReceptor'])          
                res.write({'cfdi_cbb': cfdi_cbb})   

                ### Cadena Original ####
                context_control.update({'xml_prev': cfdi_str_original})
                try:
                    txt_str = self.env['account.invoice'].with_context(context_control)._xml2cad_orig()
                except:
                    txt_str = ""
                cadena_original = txt_str
                
                cadena_original_show =""
                cadena_original_wrap = wrap(cadena_original, 120)
                for x in cadena_original_wrap:
                    cadena_original_show = cadena_original_show+"\n"+x if cadena_original_show else x
                res.write({'cadena_original': cadena_original, 'cadena_original_show': cadena_original_show})   

            else:
                data = {}
                cfdi_data = arch_xml.getElementsByTagName('cfdi:comprobante')[0]                
                data['folio_fiscal'] = file_name.split('.')[0].upper()
                cfdi_emisor = arch_xml.getElementsByTagName('cfdi:emisor')[0]
                data['rfc_emisor'] = cfdi_emisor.attributes['rfc'].value.upper()
                cfdi_receptor = arch_xml.getElementsByTagName('cfdi:receptor')[0]
                data['rfc_receptor'] = cfdi_receptor.attributes['rfc'].value.upper()
                data['total'] = cfdi_data.attributes['total'].value and round(float(cfdi_data.attributes['total'].value),4) or 0.0
                
            #_logger.info('Revisando Vigencia: %s' % (data['folio_fiscal']))
            #res.write({'sat_estado': self.check_cfdi_satus(data['folio_fiscal'],data['rfc_emisor'], data['rfc_receptor'],data['total']).replace(' ','_'), 'date_sat_estado': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            for x in res:
                cfdi_ids.append(x.id)
        # raise UserError("### AQUI >>>  ")
        archivo_zip.close()
        if cfdi_ids:
            return {
                    'domain'    : "[('id','in', ["+','.join(map(str,cfdi_ids))+"])]",
                    'name'      : _('CFDIs Descargados del Portal del SAT'),
                    'view_type' : 'form',
                    'view_mode' : 'tree,form',
                    'res_model' : 'account.cfdi',
                    'view_id'   : False,
                    'type'      : 'ir.actions.act_window'
                    }
        else:
            raise UserError(_('Advertencia !!!\nNo se encontró ningún archivo XML en el archivo ZIP que subió...'))
            
        ########################################