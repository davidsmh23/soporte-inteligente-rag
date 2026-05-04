---
id_ticket: #2283
tecnologia: WiFi, Windows, Redes, Drivers
autor: Carlos_Soporte
---
# Problema: El portátil Windows no detecta ninguna red WiFi tras una actualización
Después de que Windows Update instalara actualizaciones el martes por la noche, el portátil de un usuario ya no muestra ninguna red WiFi disponible. El ícono de red muestra un globo con X roja.

# Solución Exitosa:
La actualización de Windows instaló una versión incompatible del driver del adaptador WiFi, desactivando el dispositivo.
1. Haz clic derecho en el botón de Inicio > Administrador de dispositivos.
2. Expande "Adaptadores de red". Busca el adaptador WiFi; si tiene un signo de exclamación amarillo, confirma el problema.
3. Haz clic derecho en el adaptador > Propiedades > pestaña Controlador > "Revertir controlador" para volver al driver anterior.
4. Si "Revertir" está desactivado, descarga el driver correcto desde la web del fabricante del portátil (HP, Dell, Lenovo, etc.) usando el número de modelo.
5. Instala el driver descargado y reinicia. El adaptador WiFi debería volver a funcionar correctamente.
