---
id_ticket: #2401
tecnologia: Linux, SSH, Redes
autor: Carlos_Soporte
---
# Problema: SSH devuelve "Connection refused" al servidor de producción
El equipo de DevOps no puede conectarse por SSH al servidor `prod-app-02`. El comando `ssh usuario@prod-app-02` responde inmediatamente con `ssh: connect to host prod-app-02 port 22: Connection refused`.

# Solución Exitosa:
El servicio `sshd` se había detenido tras una actualización automática del sistema operativo.
1. Accede al servidor mediante la consola de emergencia del proveedor de nube (AWS EC2 Instance Connect, GCP Serial Console, etc.).
2. Verifica el estado del servicio: `sudo systemctl status sshd`
3. Si aparece como inactivo, inícialo: `sudo systemctl start sshd`
4. Habilítalo para que arranque automáticamente: `sudo systemctl enable sshd`
5. Confirma que escucha en el puerto 22: `sudo ss -tlnp | grep 22`
