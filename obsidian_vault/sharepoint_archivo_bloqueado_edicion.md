---
id_ticket: #2306
tecnologia: SharePoint, Office 365, Colaboración
autor: Carlos_Soporte
---
# Problema: Un documento de Word en SharePoint aparece bloqueado y no permite edición a nadie
El equipo de RRHH no puede editar el documento `Contratos_Q2_2025.docx` alojado en SharePoint. Al intentar abrirlo, aparece el mensaje "Este archivo está bloqueado para edición por [nombre de usuario que ya no está en la empresa]".

# Solución Exitosa:
El archivo tenía un bloqueo de edición (co-authoring lock) asociado a la cuenta del usuario que se dio de baja, y la sesión nunca se cerró correctamente.
1. Como administrador de SharePoint, navega a la biblioteca de documentos donde está el archivo.
2. Selecciona el archivo > Haz clic derecho o usa el menú "..." > "Detalles".
3. En el panel de información, busca la sección "Check-out realizado por" o "Editado por".
4. Si el archivo está en check-out, ve al panel de administración de SharePoint Online y usa PowerShell:
   `Set-PnPFileCheckedIn -Url "/sites/RRHH/Shared Documents/Contratos_Q2_2025.docx" -Comment "Liberación de bloqueo administrativo"`
5. Como alternativa más rápida: descarga el archivo, elimina el original del SharePoint y vuelve a subir la copia. Informa al equipo de que los metadatos del historial de versiones se perderán.
