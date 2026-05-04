---
id_ticket: #2378
tecnologia: Redis, Caché, Backend
autor: David_Admin
---
# Problema: Aplicación lanza errores OOM al intentar guardar datos en caché
Los logs de la aplicación muestran `redis.exceptions.ResponseError: OOM command not allowed when used memory > 'maxmemory'`. El servicio de sesiones de usuario ha caído.

# Solución Exitosa:
Redis alcanzó su límite de memoria configurado (512MB) porque no tenía política de evicción activa, bloqueando nuevas escrituras en lugar de liberar claves antiguas.
1. Conéctate a Redis: `redis-cli`
2. Verifica el uso actual: `INFO memory` (busca `used_memory_human` y `maxmemory_human`).
3. Configura una política de evicción para liberar las claves menos usadas recientemente: `CONFIG SET maxmemory-policy allkeys-lru`
4. Si la memoria sigue siendo insuficiente, aumenta el límite temporalmente: `CONFIG SET maxmemory 1gb`
5. Para que sea permanente, edita `/etc/redis/redis.conf`: líneas `maxmemory 1gb` y `maxmemory-policy allkeys-lru`, luego `sudo systemctl restart redis`.
