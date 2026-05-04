---
id_ticket: #2277
tecnologia: VMware, Virtualización, Sistemas
autor: David_Admin
---
# Problema: Máquina virtual de VMware no arranca y muestra error de archivo bloqueado
Al intentar encender la VM `dev-env-win11` en VMware Workstation, aparece el error: `Failed to lock the file` y `Cannot open the disk 'dev-env-win11.vmdk' or one of the snapshot disks it depends on`.

# Solución Exitosa:
Los archivos `.lck` (lock files) de VMware no se eliminaron correctamente tras un cierre brusco del sistema anfitrión.
1. Asegúrate de que la VM esté completamente apagada y no en estado suspendido.
2. Navega a la carpeta donde está almacenada la VM en el sistema de archivos del host.
3. Busca y elimina todas las carpetas con extensión `.lck` (por ejemplo `dev-env-win11.vmdk.lck`).
4. También elimina cualquier archivo `.vmem` si existe (son archivos de memoria de la última sesión).
5. Intenta encender la VM de nuevo desde VMware. Debería arrancar sin errores.
