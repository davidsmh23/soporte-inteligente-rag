---
id_ticket: #2388
tecnologia: Docker, Contenedores, DevOps
autor: David_Admin
---
# Problema: Contenedor de Docker sale inmediatamente con código de error 1
Al ejecutar `docker compose up` el contenedor de la aplicación aparece como `Exited (1)` a los pocos segundos. Los otros contenedores del stack (base de datos, caché) arrancan correctamente.

# Solución Exitosa:
El contenedor salía porque no encontraba la variable de entorno `DATABASE_URL` al momento de arranque.
1. Lee los logs del contenedor fallido: `docker logs <nombre_contenedor>`
2. El error indicaba `KeyError: 'DATABASE_URL'`, lo que confirma la variable faltante.
3. Verifica el archivo `.env` en la raíz del proyecto y asegúrate de que `DATABASE_URL` esté definida.
4. Si usas `docker compose`, comprueba que el servicio tenga `env_file: .env` o la variable bajo `environment:` en el `docker-compose.yml`.
5. Vuelve a levantar: `docker compose up --build`
