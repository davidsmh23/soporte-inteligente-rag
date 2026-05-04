---
id_ticket: #2415
tecnologia: SSL, TLS, Nginx, Seguridad
autor: Maria_Gomez
---
# Problema: Navegadores muestran "Tu conexión no es privada" en la web interna
Los usuarios reportan que al acceder al portal interno `intranet.empresa.com` el navegador bloquea la página con el error `NET::ERR_CERT_DATE_INVALID`. La web lleva caída funcional para todos los equipos desde esta mañana.

# Solución Exitosa:
El certificado SSL de Let's Encrypt venció porque el cron de renovación automática (`certbot renew`) falló silenciosamente hace 30 días.
1. Conéctate al servidor web por SSH.
2. Renueva el certificado manualmente: `sudo certbot renew --force-renewal`
3. Si hay un error de validación, verifica que el puerto 80 esté abierto en el firewall para el challenge HTTP de Let's Encrypt.
4. Recarga Nginx para que aplique el nuevo certificado: `sudo systemctl reload nginx`
5. Para evitar recurrencia, verifica que el cron exista: `sudo crontab -l | grep certbot`. Si falta, agrégalo: `0 3 * * * certbot renew --quiet`
