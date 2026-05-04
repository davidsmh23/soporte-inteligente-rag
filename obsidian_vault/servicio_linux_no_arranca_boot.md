---
id_ticket: #2341
tecnologia: Linux, Systemd, Servidores, DevOps
autor: Maria_Gomez
---
# Problema: El servicio de la aplicación no arranca automáticamente tras reiniciar el servidor
Cada vez que el servidor `backend-01` se reinicia por mantenimiento, el equipo de guardia debe conectarse manualmente y ejecutar `systemctl start app-service` para que la aplicación vuelva a estar disponible. El tiempo de inactividad promedio es de 15 minutos.

# Solución Exitosa:
El servicio de systemd de la aplicación no estaba habilitado para arranque automático (`enabled`), solo estaba configurado para poder iniciarse manualmente.
1. Verifica el estado actual del servicio: `sudo systemctl status app-service` (busca si dice `Loaded: loaded (/etc/systemd/system/app-service.service; disabled`).
2. Habilita el arranque automático: `sudo systemctl enable app-service`
3. Confirma que el cambio se aplicó: `sudo systemctl is-enabled app-service` (debe responder `enabled`).
4. Reinicia el servidor en un periodo de mantenimiento para verificar que el servicio arranca solo: `sudo reboot`
5. Tras el reinicio, comprueba que el servicio está activo sin intervención manual: `sudo systemctl status app-service`.
