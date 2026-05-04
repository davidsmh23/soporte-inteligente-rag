---
id_ticket: #2302
tecnologia: Windows, Windows Update, Sistemas
autor: Carlos_Soporte
---
# Problema: Windows Update falla con código de error 0x80070005 en varios equipos
Múltiples equipos Windows 10 del departamento de contabilidad no pueden instalar las actualizaciones de seguridad mensuales. El proceso se inicia pero siempre falla al 100% con el código `0x80070005 (Acceso denegado)`.

# Solución Exitosa:
El error `0x80070005` indica que el servicio de Windows Update no tiene permisos sobre la carpeta de caché de actualizaciones, habitualmente por el software antivirus bloqueando el proceso o por permisos corruptos en la carpeta `SoftwareDistribution`.
1. Abre CMD como administrador.
2. Detén los servicios de actualización: `net stop wuauserv && net stop cryptSvc && net stop bits && net stop msiserver`
3. Renombra la carpeta de caché para que se regenere: `ren C:\Windows\SoftwareDistribution SoftwareDistribution.old`
4. Reinicia los servicios: `net start wuauserv && net start cryptSvc && net start bits && net start msiserver`
5. Ve a Configuración > Windows Update > Buscar actualizaciones. El proceso debería completarse ahora.
