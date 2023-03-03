# auditoria_descarga_sat

Estos modulos estan hechos para la version 12 de Odoo (Rama Master)

 <p>
    Este modulo agrega una nueva funcionalidad con el boton Leer y Auditar Zip, lo que hace es utilizar el ZIP descargado por el SAT leer sus atributos relacionarlo en la pesta&ntilde;a correspondiente:
    <ul>
      <li>
        Ingresos
      </li>
      <li>
        Egresos
      </li>
      <li>
        Traslados
      </li>
      <li>
        Nomina
      </li>
      <li>
        Pago
      </li>
      <li>
        Otros
      </li>
    </ul>
  </p>

Dependencias:
 * Libreria cfdiclient
 * Modulo account_cfdi_audit_zipfile

Como este paquete de modulos trabaja con llaves privadas(Key - RSA) tenemos problemas para la desencriptarla, entonces para solucionarlo se creo un Web Service Local con  XMLRPCServer, el cual ejecuta los siguientes metodos:
<ul>
  <li>_get_token</li>
  <li>get_token_as_var</li>
  <li>solicita_descarga</li>
  <li>descargar_paquete</li>
  <li>verificar_descarga</li>
</ul>
El Archivo tiene por nombre Web_Service_Descarga_SAT.py el cual debemos ejecutar con el Script start_web_service.sh, la accion manual seria ejecutarlo manualmente, pero se genero el servicio sat-service.service el cual se administra con el gestor de Servicios de Linux.

Primero Creamos el Script

sudo nano /etc/systemd/system/sat-service.service

Actualizamos los Servicios Disponibles:

systemctl daemon-reload

Iniciamos:

systemctl start sat-service

Habilitamos con el Reinicio:

systemctl enable sat-service

Las Dependencias necesarias son:
<ul>
  <li>
  cfdiclient
  </li>
  <li>
  xmlrpc
  </li>
</ul>


