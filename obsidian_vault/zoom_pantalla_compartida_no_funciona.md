---
id_ticket: #2328
tecnologia: Zoom, macOS, Permisos
autor: Carlos_Soporte
---
# Problema: Un empleado no puede compartir pantalla en Zoom desde su Mac
Durante presentaciones en Zoom, el usuario intenta compartir pantalla pero recibe el mensaje "Zoom no tiene permiso para grabar la pantalla. Habilítalo en Preferencias del Sistema" y el botón queda inactivo.

# Solución Exitosa:
macOS requiere permiso explícito de "Grabación de pantalla" para que las aplicaciones puedan compartir el escritorio, y Zoom no lo tenía concedido.
1. Ve a Preferencias del Sistema (o Configuración del Sistema en macOS Ventura+) > Privacidad y seguridad > Grabación de pantalla.
2. Busca "Zoom" en la lista. Si no aparece, puede que necesites añadirlo con el botón `+`.
3. Activa la casilla junto a Zoom.
4. Si el sistema pide cerrar y reabrir Zoom, acéptalo.
5. Vuelve a intentar compartir pantalla en Zoom. Si sigue sin funcionar, ve también a Accesibilidad en el mismo panel de Privacidad y asegúrate de que Zoom esté habilitado allí también.
