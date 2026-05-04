---
id_ticket: #2311
tecnologia: Outlook, Office 365, Windows
autor: Laura_Infra
---
# Problema: Outlook no descarga correos nuevos desde hace 2 horas
Un usuario reporta que Outlook muestra "Conectado" en la barra de estado pero los correos nuevos no aparecen. Al enviar un correo de prueba desde otro cliente, este llega al servidor pero no se refleja en el Outlook del usuario.

# Solución Exitosa:
El archivo OST (caché local de Outlook) estaba corrupto, impidiendo la sincronización con Exchange Online.
1. Cierra Outlook completamente.
2. Ve a Panel de Control > Cuentas de Correo > pestaña Archivos de datos.
3. Anota la ruta del archivo `.ost` de la cuenta afectada.
4. Navega a esa ruta con el Explorador de archivos y renombra el archivo `.ost` a `.ost.bak`.
5. Vuelve a abrir Outlook. Creará un nuevo archivo OST y comenzará la resincronización completa desde el servidor. El proceso puede tardar varios minutos según el tamaño del buzón.
