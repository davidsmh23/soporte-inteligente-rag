---
id_ticket: #2393
tecnologia: CORS, Backend, API, Navegadores
autor: Maria_Gomez
---
# Problema: La nueva versión del frontend lanza errores CORS al llamar a la API
Tras desplegar el nuevo frontend en `app.empresa.com`, la consola del navegador muestra `Access to XMLHttpRequest at 'api.empresa.com/v2/data' from origin 'app.empresa.com' has been blocked by CORS policy`. La versión anterior funcionaba.

# Solución Exitosa:
La API v2 no tenía configurado el nuevo dominio `app.empresa.com` en su lista de orígenes permitidos (antes era `old-app.empresa.com`).
1. Localiza la configuración CORS en el backend. En Express.js sería el middleware `cors()`; en Django, el setting `CORS_ALLOWED_ORIGINS`; en Spring Boot, la anotación `@CrossOrigin`.
2. Añade `https://app.empresa.com` a la lista de orígenes permitidos.
3. Si se usan cookies o cabeceras de autenticación, asegúrate de que `credentials: true` (o el equivalente del framework) también esté activo.
4. Redespliega el backend y verifica en el navegador que la cabecera de respuesta `Access-Control-Allow-Origin: https://app.empresa.com` ya aparece en las peticiones.
