---
id_ticket: #2102
tecnologia: VPN, Redes, macOS
autor: Carlos_Soporte
---
# Problema: Empleados con Mac no pueden conectar a la VPN
Varios usuarios que acaban de actualizar sus ordenadores a macOS Sonoma reportan que el cliente Tunnelblick se queda conectando infinitamente y luego da "Timeout".

# Solución Exitosa:
Es un problema de compatibilidad conocido entre macOS Sonoma y el protocolo IPv6 en versiones antiguas del cliente.
Pasos para el usuario:
1. Actualizar Tunnelblick a la última versión estable (mínimo 3.8.8b).
2. Abrir Tunnelblick > Configuración de VPN > Avanzado.
3. Marcar la casilla que dice "Deshabilitar IPv6 al conectar".
4. Volver a conectar.
