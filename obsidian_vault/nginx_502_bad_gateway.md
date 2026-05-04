---
id_ticket: #2367
tecnologia: Nginx, Backend, Redes
autor: Laura_Infra
---
# Problema: La API devuelve 502 Bad Gateway de forma intermitente
El equipo de producto reporta que aproximadamente el 30% de las peticiones a la API REST en producción devuelven `502 Bad Gateway`. El problema empezó tras un despliegue de hoy a las 14:00.

# Solución Exitosa:
Nginx no podía conectar con el proceso de la aplicación porque el despliegue había cambiado el puerto interno de 3000 a 8080, pero la configuración de Nginx no se actualizó.
1. Revisa los logs de error de Nginx: `sudo tail -f /var/log/nginx/error.log`
2. Busca líneas con `connect() failed (111: Connection refused)` para confirmar el puerto incorrecto.
3. Edita el bloque `upstream` en la config de Nginx: `sudo nano /etc/nginx/sites-available/api.conf`
4. Actualiza `proxy_pass http://localhost:3000;` a `proxy_pass http://localhost:8080;`
5. Valida la sintaxis y recarga: `sudo nginx -t && sudo systemctl reload nginx`
