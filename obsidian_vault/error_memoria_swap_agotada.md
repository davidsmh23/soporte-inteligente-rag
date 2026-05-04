---
id_ticket: #2374
tecnologia: Linux, Memoria, Swap, Rendimiento
autor: Laura_Infra
---
# Problema: Servidor de aplicaciones muy lento y el sistema comienza a matar procesos (OOM Killer)
El servidor `worker-03` está extremadamente lento. En los logs del sistema (`/var/log/syslog`) aparecen entradas `oom-kill event` indicando que el kernel está terminando procesos por falta de memoria RAM y swap.

# Solución Exitosa:
El servidor no tenía swap configurada y un pico de carga agotó la RAM disponible. Se añadió swap como medida de emergencia y se investigó el proceso responsable.
1. Como solución inmediata, añade un archivo de swap de 4GB:
   ```
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```
2. Para hacerlo permanente, añade a `/etc/fstab`: `/swapfile none swap sw 0 0`
3. Investiga qué proceso consumió la RAM: `ps aux --sort=-%mem | head -10`
4. Revisa el historial del OOM Killer: `grep -i "oom_kill\|killed process" /var/log/syslog`
5. Coordina con el equipo de desarrollo para optimizar el consumo de memoria del proceso identificado o aumentar la RAM del servidor.
