---
id_ticket: #2358
tecnologia: Java, JVM, Backend, Rendimiento
autor: David_Admin
---
# Problema: La aplicación Java se cae con OutOfMemoryError en producción
El servicio `facturacion-service` (Java 17, Spring Boot) se cae varias veces al día con el error en los logs: `java.lang.OutOfMemoryError: Java heap space`. El servidor tiene 16 GB de RAM pero la JVM solo usa 512 MB antes de caerse.

# Solución Exitosa:
La JVM estaba arrancando con los valores por defecto de heap, que son muy conservadores. Al aumentar el heap máximo el problema desapareció.
1. Verifica los parámetros actuales de la JVM: busca en el script de arranque del servicio las flags `-Xms` (heap inicial) y `-Xmx` (heap máximo). Si no existen, la JVM usa los defaults (normalmente 256MB-512MB).
2. Edita el archivo de configuración del servicio (o el `systemd unit file`) y añade/modifica las flags:
   `-Xms1g -Xmx4g`
3. También activa el GC log para monitorear a largo plazo: `-Xlog:gc*:file=/var/log/app/gc.log:time:filecount=5,filesize=20m`
4. Reinicia el servicio: `sudo systemctl restart facturacion-service`
5. Monitorea con `jcmd <PID> VM.native_memory` o con un APM para detectar posibles fugas de memoria si el problema persiste.
