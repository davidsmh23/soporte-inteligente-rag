---
id_ticket: #2334
tecnologia: Microsoft Teams, Office 365, Audio, Windows
autor: Carlos_Soporte
---
# Problema: En reuniones de Teams no se escucha al usuario ni él escucha a nadie
Un empleado reporta que al unirse a reuniones de Teams su micrófono no funciona y tampoco escucha a los demás participantes. En otras aplicaciones (Zoom, llamadas del sistema) el audio funciona correctamente.

# Solución Exitosa:
Teams no tenía permiso de acceso al micrófono en Windows 11 y además tenía el dispositivo de audio equivocado seleccionado.
1. Ve a Configuración de Windows > Privacidad y seguridad > Micrófono > asegúrate de que "Microsoft Teams" esté habilitado en la lista de aplicaciones.
2. Dentro de Teams, haz clic en los tres puntos (...) > Configuración > Dispositivos.
3. Selecciona el micrófono y altavoz correctos (los del headset, no el micrófono integrado del portátil).
4. Usa el botón "Hacer una llamada de prueba" para verificar que el audio funciona antes de unirte a la próxima reunión.
