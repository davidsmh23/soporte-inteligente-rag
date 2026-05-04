---
id_ticket: #2055
tecnologia: PostgreSQL, Base de Datos
autor: Maria_Gomez
---
# Problema: Error de conexiones máximas en la base de datos
El equipo de desarrollo reporta que la aplicación principal se cae y en los logs aparece el error: `FATAL: remaining connection slots are reserved for non-replication superuser connections`.

# Solución Exitosa:
El clúster de base de datos llegó a su límite de conexiones simultáneas. 
Para solucionarlo:
1. Conéctate al servidor de base de datos por SSH.
2. Abre el archivo de configuración: `sudo nano /etc/postgresql/14/main/postgresql.conf`
3. Busca el parámetro `max_connections` y súbelo de 100 a 200.
4. Reinicia el servicio: `sudo systemctl restart postgresql`
