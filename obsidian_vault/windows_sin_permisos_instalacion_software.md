---
id_ticket: #2256
tecnologia: Windows, GPO, Active Directory, Permisos
autor: Carlos_Soporte
---
# Problema: Los usuarios no pueden instalar ningún software, reciben "Acceso denegado"
El departamento de diseño reporta que tras una actualización de la política de grupo (GPO) del viernes, ningún usuario puede instalar ni actualizar aplicaciones. Aparece "Necesitas permiso de administrador para realizar cambios en este equipo".

# Solución Exitosa:
La GPO `Restricción de instalación de software` fue aplicada accidentalmente a la OU de diseño cuando debía aplicarse solo a la OU de administración.
1. En el servidor de Active Directory, abre `Administración de directivas de grupo` (GPMC).
2. Navega a la OU `Diseño` y revisa las GPO vinculadas.
3. Identifica la GPO de restricción (en este caso `Software_Install_Block`) y deslínkala de la OU de diseño haciendo clic derecho > "Eliminar vínculo".
4. En los equipos afectados, fuerza la actualización de directiva: `gpupdate /force` en CMD como administrador.
5. Verifica que los usuarios ya puedan instalar software. Coordina con el equipo de seguridad para aplicar la GPO correctamente solo a las OUs requeridas.
