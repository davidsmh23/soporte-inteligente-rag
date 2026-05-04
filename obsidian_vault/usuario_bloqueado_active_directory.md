---
id_ticket: #2298
tecnologia: Active Directory, Windows Server, Seguridad
autor: Carlos_Soporte
---
# Problema: Empleado no puede iniciar sesión, cuenta bloqueada en AD
La usuaria `ana.lopez@empresa.com` no puede entrar a su equipo Windows ni a ningún servicio corporativo. El sistema muestra el mensaje "Tu cuenta ha sido bloqueada. Contacta a tu administrador".

# Solución Exitosa:
La cuenta se bloqueó por múltiples intentos fallidos de contraseña, probablemente originados por un dispositivo móvil con las credenciales antiguas guardadas.
1. En el servidor de Active Directory, abre `Usuarios y equipos de Active Directory` (ADUC).
2. Busca la cuenta `ana.lopez`, haz clic derecho > Propiedades > pestaña Cuenta.
3. Desmarca la casilla "La cuenta está bloqueada" y haz clic en Aceptar.
4. Pide a la usuaria que cambie su contraseña inmediatamente.
5. Indica al usuario que actualice las credenciales en todos los dispositivos móviles para evitar nuevos bloqueos.
