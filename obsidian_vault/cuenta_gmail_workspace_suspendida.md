---
id_ticket: #2413
tecnologia: Google Workspace, Gmail, Administración
autor: Laura_Infra
---
# Problema: Un empleado no puede acceder a su cuenta de Google Workspace, aparece "Cuenta suspendida"
El empleado `pedro.ruiz@empresa.com` no puede entrar a Gmail, Google Drive ni ningún servicio de Google Workspace desde esta mañana. Aparece el mensaje "Tu cuenta ha sido suspendida".

# Solución Exitosa:
La cuenta fue suspendida automáticamente por la política de seguridad de Google al detectar un inicio de sesión desde un país inusual (viaje de trabajo). El administrador puede restaurarla desde la consola.
1. Accede a la consola de administración de Google Workspace: `admin.google.com`.
2. Ve a Directorio > Usuarios y busca `pedro.ruiz@empresa.com`.
3. Haz clic en el usuario. Aparecerá el aviso de cuenta suspendida junto a un botón "Reactivar usuario".
4. Haz clic en "Reactivar usuario" y confirma.
5. Pide al empleado que cambie su contraseña inmediatamente y que active la verificación en dos pasos (2FA) para evitar suspensiones futuras. Revisa en el registro de auditoría la actividad inusual detectada.
