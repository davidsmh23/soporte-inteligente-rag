---
id_ticket: #2362
tecnologia: Apache, Linux, Permisos, Web
autor: Laura_Infra
---
# Problema: Apache devuelve error 403 Forbidden en una nueva aplicación desplegada
Después de desplegar una nueva aplicación web en `/var/www/nueva-app`, Apache devuelve `403 Forbidden` en todos los recursos. Los archivos están en la ruta correcta y el VirtualHost está bien configurado.

# Solución Exitosa:
El usuario `www-data` (bajo el cual corre Apache) no tenía permisos de lectura sobre los archivos de la nueva aplicación porque se subieron con el usuario `root` y los permisos de los archivos eran `600`.
1. Verifica el error en los logs: `sudo tail -f /var/log/apache2/error.log` (busca `Permission denied`).
2. Comprueba los permisos actuales: `ls -la /var/www/nueva-app/`
3. Corrige los permisos de forma recursiva. Carpetas deben ser `755` y archivos `644`:
   ```
   sudo find /var/www/nueva-app -type d -exec chmod 755 {} \;
   sudo find /var/www/nueva-app -type f -exec chmod 644 {} \;
   ```
4. Asigna el propietario correcto: `sudo chown -R www-data:www-data /var/www/nueva-app`
5. Recarga Apache: `sudo systemctl reload apache2` y verifica la web.
