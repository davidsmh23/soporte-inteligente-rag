---
id_ticket: #2385
tecnologia: Backup, Cron, Linux, Bash
autor: David_Admin
---
# Problema: El backup nocturno automatizado lleva una semana sin ejecutarse
El equipo de operaciones detectó que los backups diarios de la base de datos MySQL no se han generado desde hace 7 días. El cron job de backup estaba configurado y funcionaba correctamente el mes pasado.

# Solución Exitosa:
El script de backup fallaba porque la contraseña de la cuenta MySQL usada para el dump había sido rotada 8 días atrás sin actualizar el script.
1. Revisa los logs del cron: `grep CRON /var/log/syslog | tail -20` o revisa el output capturado en el archivo de log del script.
2. Ejecuta el script manualmente para ver el error en tiempo real: `bash /opt/scripts/backup_mysql.sh`
3. El error `mysqldump: Got error: 1045: Access denied for user 'backup_user'@'localhost'` confirma la causa.
4. Actualiza la contraseña en el script: `nano /opt/scripts/backup_mysql.sh` y modifica la variable `DB_PASSWORD`.
5. Protege el script de lecturas no autorizadas: `chmod 700 /opt/scripts/backup_mysql.sh`. Verifica que el cron sigue activo: `crontab -l`.
