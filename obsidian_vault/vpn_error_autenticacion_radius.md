---
id_ticket: #2349
tecnologia: VPN, RADIUS, Active Directory, Redes
autor: David_Admin
---
# Problema: Todos los empleados en remoto no pueden autenticarse en la VPN corporativa
Desde las 08:00 ningún empleado puede conectarse a la VPN. El cliente VPN devuelve "Credenciales inválidas" aunque las contraseñas son correctas. Los servicios internos están accesibles desde la oficina.

# Solución Exitosa:
El servidor RADIUS que autentica las conexiones VPN contra Active Directory tenía el servicio `Network Policy Server (NPS)` detenido tras una actualización automática del servidor Windows.
1. Conéctate al servidor RADIUS (en este caso el servidor de políticas de red Windows, `nps-01`) mediante una sesión de consola o escritorio remoto desde la red interna.
2. Abre `Servicios` (services.msc) y busca `Servidor de directivas de redes`.
3. El servicio estaba en estado "Detenido". Inícialo y cámbialo a inicio "Automático".
4. Verifica en los logs del NPS (`Visor de eventos > Vistas personalizadas > Roles de servidor > Directiva de redes y acceso`) que las autenticaciones vuelven a procesarse correctamente.
5. Notifica a los empleados que pueden volver a conectarse a la VPN.
