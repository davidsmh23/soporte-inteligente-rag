---
id_ticket: #2432
tecnologia: SSL, Let's Encrypt, DNS, Linux
autor: Maria_Gomez
---
# Problema: Certbot falla al renovar el certificado con error de validación DNS
El script de renovación automática de Let's Encrypt falla con el error: `DNS problem: NXDOMAIN looking up A for api.empresa.com - check that a DNS record exists for this domain`. El certificado caduca en 5 días.

# Solución Exitosa:
El registro DNS tipo A para `api.empresa.com` fue eliminado accidentalmente durante una limpieza de registros DNS el día anterior.
1. Verifica que el dominio no resuelve: `dig A api.empresa.com` (si devuelve `NXDOMAIN`, el registro no existe).
2. Accede al panel de gestión DNS del proveedor (Cloudflare, Route53, GoDaddy, etc.).
3. Crea de nuevo el registro A: `api.empresa.com → IP_del_servidor` con TTL de 300 segundos.
4. Espera a que el DNS se propague (puede tardar entre 5 y 30 minutos): `watch -n 10 "dig A api.empresa.com +short"`
5. Una vez que el dominio resuelve correctamente, fuerza la renovación del certificado: `sudo certbot renew --force-renewal -d api.empresa.com`
