# -*- coding: utf-8 -*-

####### IMPORTANDO LAS LIBRERIAS PRINCIPÁLES PARA EL MANEJO DE WEBSERVICES EN PYTHON #######
from xmlrpc.server import SimpleXMLRPCServer
import os
import sys
import subprocess
import string

from datetime import datetime
### libreria de conexion con el SAT ###
import cfdiclient
from cfdiclient import Autenticacion
from cfdiclient import Fiel
from cfdiclient import SolicitaDescarga
from cfdiclient import Autenticacion
from cfdiclient import VerificaSolicitudDescarga
from cfdiclient import DescargaMasiva

user_access = 'super_argil'
password_access = 'myf1r$sts3rv1113+@'

allow_none=True

### RUTA DEL WEBSERVICE Y METODOS DADOS DE ALTA
class DescargaCFDIFunctions(object):

    def __init__(self, arg=None):
        super(DescargaCFDIFunctions, self).__init__()
        self.arg = arg

    def _get_token(self, cer_der, key_der, file_pass):
        token = ""
        fiel = Fiel(cer_der, key_der, file_pass)
        auth = Autenticacion(fiel)
        token = auth.obtener_token()
        return token

    def get_token_as_var(self, file_globals):
        token = ""
        file_cer_path = file_globals['file_cer_path']
        file_key_path = file_globals['file_key_path']
        file_pass = file_globals['file_pass']

        FIEL_KEY = str(file_key_path)
        FIEL_CER = str(file_cer_path)
        FIEL_PAS = str(file_pass)
        cer_der = open(FIEL_CER, 'rb').read()
        key_der = open(FIEL_KEY, 'rb').read()

        fiel = Fiel(cer_der, key_der, file_pass)
        auth = Autenticacion(fiel)
        token = auth.obtener_token()
        return {'token':token}

    def solicita_descarga(self, file_globals, user, password, type_download=False):
        """
            Debemos enviar los siguientes valores
            file_globals = {
                'file_cer_path': ,
                'file_key_path': ,
                'file_pass': ,
                'rfc_solicitante': ,
                'fecha_inicial': ,
                'fecha_final': ,
                'rfc_emisor': ,
                'rfc_receptor': ,
            }
        type_download = Tipo de Descarga
        """
        if user != user_access or password != password_access:
            return {'error': 'Se ha bloqueado el Acceso Temporalmente.'}
        if 'file_cer_path' not in file_globals or not 'file_key_path' in file_globals or not 'file_pass' in file_globals:
            return {'error': 'No se proporciono toda la información.'}

        file_cer_path = file_globals['file_cer_path']
        file_key_path = file_globals['file_key_path']
        file_pass = file_globals['file_pass']
        rfc_solicitante = str(file_globals['rfc_solicitante'])
        fecha_inicial = file_globals['fecha_inicial']
        fecha_final = file_globals['fecha_final']
        rfc_emisor = str(file_globals['rfc_emisor'])
        rfc_receptor = str(file_globals['rfc_receptor'])

        fecha_inicial = datetime.strptime(fecha_inicial, '%Y-%m-%d %H:%M:%S')
        fecha_final = datetime.strptime(fecha_final, '%Y-%m-%d %H:%M:%S')

        FIEL_KEY = str(file_key_path)
        FIEL_CER = str(file_cer_path)
        FIEL_PAS = str(file_pass)
        cer_der = open(FIEL_CER, 'rb').read()
        key_der = open(FIEL_KEY, 'rb').read()

        fiel = Fiel(cer_der, key_der, FIEL_PAS)

        descarga = SolicitaDescarga(fiel)

        # token = self._get_token(cer_der, key_der, file_pass)
        token = file_globals['token']
        if not token:
           token = self._get_token(cer_der, key_der, file_pass) 

        if type_download == 'Emitidos' or not type_download:
            # Emitidos
            result = descarga.solicitar_descarga(token, rfc_solicitante, fecha_inicial, fecha_final, rfc_emisor=rfc_emisor)
            resultado_final = {}
            for ky in result.keys():
                resultado_final.update({
                    ky: result[ky] if result[ky] else False,
                    })
            return resultado_final
        if type_download == 'Recibidos':
            # Recibidos
            result = descarga.solicitar_descarga(token, rfc_solicitante, fecha_inicial, fecha_final, rfc_receptor=rfc_receptor)
            resultado_final = {}
            for ky in result.keys():
                resultado_final.update({
                    ky: result[ky] if result[ky] else False,
                    })
            return resultado_final
        return {'token': '69/3==imposible'}


    def descargar_paquete(self, file_globals,  rfc_solicitante, id_paquete):
        
        result = {}

        file_cer_path = file_globals['file_cer_path']
        file_key_path = file_globals['file_key_path']
        file_pass = file_globals['file_pass']
        
        FIEL_KEY = str(file_key_path)
        FIEL_CER = str(file_cer_path)
        FIEL_PAS = str(file_pass)
        cer_der = open(FIEL_CER, 'rb').read()
        key_der = open(FIEL_KEY, 'rb').read()


        fiel = Fiel(cer_der, key_der, FIEL_PAS)

        descarga = DescargaMasiva(fiel)

        # token = self._get_token(cer_der, key_der, file_pass)
        token = file_globals['token']
        if not token:
           token = self._get_token(cer_der, key_der, file_pass) 

        result = descarga.descargar_paquete(token, rfc_solicitante, id_paquete)
        resultado_final = {}
        for ky in result.keys():
            resultado_final.update({
                ky: result[ky] if result[ky] else False,
                })
        return resultado_final
        #return {'token': '69/3==imposible'}


    def verificar_descarga(self, file_globals,  rfc_solicitante, id_solicitud):
        

        result = {}

        file_cer_path = file_globals['file_cer_path']
        file_key_path = file_globals['file_key_path']
        file_pass = file_globals['file_pass']
        
        FIEL_KEY = str(file_key_path)
        FIEL_CER = str(file_cer_path)
        FIEL_PAS = str(file_pass)
        cer_der = open(FIEL_CER, 'rb').read()
        key_der = open(FIEL_KEY, 'rb').read()


        fiel = Fiel(cer_der, key_der, FIEL_PAS)

        #token = self._get_token(cer_der, key_der, file_pass)
        token = file_globals['token']
        if not token:
           token = self._get_token(cer_der, key_der, file_pass) 

        descarga = VerificaSolicitudDescarga(fiel)

        result = descarga.verificar_descarga(token, rfc_solicitante, id_solicitud)

        resultado_final = {}
        for ky in result.keys():
            resultado_final.update({
                ky: result[ky] if result[ky] else False,
                })
        return resultado_final
        #return {'token': '69/3==imposible'}



        
#Creamos el servidor indicando que utilizaremos el puerto 5123
server = SimpleXMLRPCServer(("",8066))

### Registramos la clase y sus funciones ###
server.register_instance(DescargaCFDIFunctions())

# #Registramos las funciónes
# server.register_function(hola_mundo)
#Iniciamos el servidor
server.serve_forever()

### Consumirlo 
# import xmlrpc.client

# cliente = xmlrpc.client.ServerProxy('http://localhost:8066')

# client.hola_mundo()