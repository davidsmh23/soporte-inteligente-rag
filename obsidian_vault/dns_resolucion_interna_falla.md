---
id_ticket: #2345
tecnologia: DNS, Redes, Linux, Windows
autor: Maria_Gomez
---
# Problema: Equipos no resuelven dominios internos tras cambio de router
Después de sustituir el router principal de la oficina, varios equipos no pueden acceder a recursos internos como `intranet.empresa.local` o `fileserver.empresa.local`, aunque sí acceden a internet correctamente.

# Solución Exitosa:
El nuevo router asignaba por DHCP su propia IP como servidor DNS, ignorando el servidor DNS interno de la empresa donde están registrados los dominios `.empresa.local`.
1. Identifica la IP del servidor DNS interno (normalmente el servidor de Active Directory, por ejemplo `192.168.1.10`).
2. En el panel de administración del router, ve a la sección DHCP > Opciones avanzadas.
3. Cambia el campo "DNS primario" de la IP del router a la IP del servidor DNS interno (`192.168.1.10`).
4. Para los equipos ya conectados, pídeles que renueven su IP: en Windows `ipconfig /release && ipconfig /renew`; en Linux `sudo dhclient -r && sudo dhclient`.
5. Verifica la resolución: `nslookup intranet.empresa.local`.
