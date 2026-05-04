---
id_ticket: #2371
tecnologia: Firewall, Redes, Linux, iptables
autor: Laura_Infra
---
# Problema: El nuevo servicio en el puerto 8443 no es accesible desde la red de la oficina
Se desplegó un nuevo servicio de reporting en el servidor `report-01` escuchando en el puerto `8443`. El servicio responde correctamente desde el propio servidor (`curl localhost:8443`) pero es inaccesible desde cualquier otro equipo de la red.

# Solución Exitosa:
El firewall de `ufw` (Uncomplicated Firewall) del servidor tenía una política restrictiva y no tenía una regla que permitiera el puerto 8443.
1. Verifica el estado del firewall: `sudo ufw status verbose`
2. Si el puerto 8443 no aparece en las reglas permitidas, añádelo: `sudo ufw allow 8443/tcp`
3. Recarga el firewall: `sudo ufw reload`
4. Verifica desde otro equipo: `curl -k https://IP-del-servidor:8443`
5. Si el servidor usa `iptables` directamente en lugar de `ufw`, añade la regla: `sudo iptables -A INPUT -p tcp --dport 8443 -j ACCEPT` y guárdala con `sudo iptables-save > /etc/iptables/rules.v4`.
