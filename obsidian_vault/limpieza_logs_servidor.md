---
id_ticket: #2310
tecnologia: Linux, Bash, Servidores
autor: David_Admin
---
# Problema: Disco lleno por acumulación de logs
El servidor de producción (AppServer-01) ha lanzado una alerta de disco al 99% de capacidad. Se verificó que la carpeta `/var/log/app` tiene archivos de hace más de 6 meses que no se han rotado.

# Solución Exitosa:
Se debe limpiar los logs antiguos y establecer una tarea cron para que no vuelva a pasar.
1. Para liberar espacio inmediato, ejecuta este comando para borrar logs de más de 30 días:
   `find /var/log/app/ -name "*.log" -type f -mtime +30 -exec rm -f {} \;`
2. Para evitar que se repita, se ha configurado el servicio `logrotate` en el servidor con la política estándar de retención de 15 días.
