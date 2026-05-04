---
id_ticket: #2289
tecnologia: Python, pip, SSL, Linux
autor: Carlos_Soporte
---
# Problema: pip install falla con error de verificación SSL en servidor corporativo
Al intentar instalar dependencias con `pip install -r requirements.txt` en el servidor de CI, el proceso falla con `SSL: CERTIFICATE_VERIFY_FAILED`. En el equipo local del desarrollador funciona correctamente.

# Solución Exitosa:
El servidor de CI está detrás de un proxy corporativo que realiza inspección SSL (SSL Interception), sustituyendo el certificado original por el del proxy. pip no confía en ese certificado.
1. Exporta el certificado raíz del proxy corporativo en formato PEM. Pídelo al equipo de redes.
2. Localiza el bundle de certificados de pip: `python -c "import certifi; print(certifi.where())"`
3. Añade el certificado corporativo al final del archivo `cacert.pem` de certifi: `cat corporativo.pem >> /ruta/del/cacert.pem`
4. Alternatively, configura la variable de entorno: `export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt` (asegúrate de que el cert corporativo esté ahí).
5. Vuelve a ejecutar `pip install`.
