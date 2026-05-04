---
id_ticket: #2261
tecnologia: Impresoras, Redes, Windows
autor: Laura_Infra
---
# Problema: La impresora de red del piso 3 aparece como "Sin conexión" en todos los equipos
Los 20 usuarios del piso 3 no pueden imprimir. La impresora HP LaserJet Pro M404n aparece como "Sin conexión" en todos los equipos Windows, aunque el dispositivo físico tiene luz verde y parece encendida.

# Solución Exitosa:
La impresora había cambiado de IP por una renovación del DHCP del switch de planta, por lo que la cola de impresión apuntaba a una IP inexistente.
1. Imprime una página de configuración desde la impresora pulsando el botón de información (o desde el menú de la pantalla) para obtener su IP actual.
2. En un equipo Windows, ve a Panel de Control > Dispositivos e impresoras.
3. Haz clic derecho en la impresora > Propiedades de impresora > pestaña Puertos.
4. Selecciona el puerto TCP/IP actual y pulsa "Configurar puerto".
5. Actualiza el campo "Nombre o dirección IP de la impresora" con la nueva IP obtenida en el paso 1.
6. Para evitar que ocurra de nuevo, asigna una IP estática a la impresora desde el panel de administración web del dispositivo.
