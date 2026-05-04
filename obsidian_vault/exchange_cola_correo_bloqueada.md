---
id_ticket: #2397
tecnologia: Exchange Server, Email, Windows Server
autor: Maria_Gomez
---
# Problema: Los correos salientes están atascados en la cola de Exchange y no se entregan
El equipo de ventas reporta que los correos enviados desde esta mañana no están llegando a los destinatarios externos. En la consola de Exchange, la cola de transporte muestra 847 mensajes pendientes con el estado `Ready`.

# Solución Exitosa:
El conector de envío de Exchange tenía la IP del servidor de relay SMTP del proveedor desactualizada tras un cambio de infraestructura del ISP la noche anterior.
1. Abre el `Exchange Admin Center` o `Exchange Management Shell`.
2. Ve a Flujo de correo > Conectores de envío y edita el conector de salida hacia Internet.
3. En la sección "Espacios de direcciones" o "Smart host", actualiza la IP o FQDN del servidor de relay con el nuevo valor proporcionado por el ISP.
4. Reinicia el servicio de transporte de Exchange: `Restart-Service MSExchangeTransport`
5. En el Exchange Management Shell, libera los mensajes de la cola: `Get-Queue | Resume-Queue`. Monitorea la cola con `Get-Queue | Select-Object Identity,MessageCount,Status` hasta que se vacíe.
