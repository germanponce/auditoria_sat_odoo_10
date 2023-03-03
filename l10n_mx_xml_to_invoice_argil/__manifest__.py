# -*- coding: utf-8 -*-
{
    'name': "Carga de facturas por XMLs",

    'summary': """
       Modulo que permite la carga y validacion de facturas 
       al importar un archivo .zip que contenga xml de facturas
       """,

    'description': """
       Modulo que permite la carga y validacion de facturas 
       al importar un archivo .zip que contenga xml de facturas (CFDIs)
    """,

    'author': "Argil Consulting",
    'website': "http://www.argil.mx",
    'category': 'Invoicing',
    'version': '1.0.2',

    'maintainer':"Israel Cruz Argil",

    # dependencias
    'depends': [
        'sale_management',
        'base_vat',
        'base_address_extended',
        #'base_address_city',
        'l10n_mx_einvoice',
        'l10n_mx',
        'stock',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/partner_views.xml',         
    ],
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
    'auto_install': False,
}