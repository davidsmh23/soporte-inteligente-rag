---
id_ticket: #2319
tecnologia: macOS, Time Machine, Backup
autor: Carlos_Soporte
---
# Problema: Time Machine lleva 3 días sin completar ningún backup en MacBook Pro
Una usuaria reporta que Time Machine muestra "La última copia de seguridad no se pudo completar" con la descripción `Error de copia de seguridad (error 45)`. El disco de backup externo tiene espacio disponible.

# Solución Exitosa:
El error 45 de Time Machine indica que el snapshot local está corrupto o que hay un bloqueo en el proceso de backup.
1. Abre Terminal y detén Time Machine: `sudo tmutil disable`
2. Elimina los snapshots locales que puedan estar corruptos: `tmutil listlocalsnapshots / | xargs -I {} tmutil deletelocalsnapshots {}`
3. Vuelve a habilitar Time Machine: `sudo tmutil enable`
4. Si persiste, desmonta y vuelve a montar el disco de backup. En Finder > Menú Ir > Utilidades > Utilidad de Discos: selecciona el disco de Time Machine y ejecuta "Primeros Auxilios" para reparar el sistema de archivos.
5. Inicia un backup manual: `sudo tmutil startbackup`
