---
id_ticket: #2356
tecnologia: MySQL, Base de Datos, Rendimiento
autor: Maria_Gomez
---
# Problema: Las consultas a la base de datos tardan más de 30 segundos en producción
El equipo de backend reporta que desde ayer las consultas a la tabla `orders` (con ~8 millones de registros) están tardando entre 30 y 60 segundos. El mismo query en staging (con pocos datos) tarda menos de 1 segundo.

# Solución Exitosa:
La tabla `orders` no tenía índice en la columna `status` que se usaba en el `WHERE` del query más frecuente, provocando un full table scan.
1. Activa el slow query log para confirmar cuáles queries son el problema: edita `/etc/mysql/mysql.conf.d/mysqld.cnf` y añade `slow_query_log = 1` y `long_query_time = 5`.
2. Analiza el query con `EXPLAIN SELECT * FROM orders WHERE status = 'pending' AND created_at > '2024-01-01';`
3. Si el tipo es `ALL` (full scan), crea un índice compuesto: `CREATE INDEX idx_status_created ON orders (status, created_at);`
4. Vuelve a ejecutar el `EXPLAIN` para verificar que ahora usa el índice (`type: ref`).
