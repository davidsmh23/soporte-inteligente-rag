---
id_ticket: #2271
tecnologia: Git, Control de Versiones, Desarrollo
autor: David_Admin
---
# Problema: Desarrollador no puede hacer merge de su rama por conflictos en múltiples archivos
Un desarrollador junior lleva bloqueado 2 horas intentando hacer `git merge main` en su rama de feature. Git le muestra conflictos en 5 archivos y no sabe cómo resolverlos sin perder su trabajo.

# Solución Exitosa:
Los conflictos de merge son normales cuando dos personas editan la misma parte de un archivo. Se resuelven manualmente o con una herramienta visual.
1. Ejecuta `git status` para ver todos los archivos en conflicto (marcados como `both modified`).
2. Abre cada archivo conflictivo. Busca los marcadores de conflicto: `<<<<<<< HEAD` (tu código), `=======` (separador), `>>>>>>> main` (código de main).
3. Edita el archivo dejando únicamente el código correcto (puede ser tuyo, el de main, o una combinación). Elimina todos los marcadores `<<<<`, `====`, `>>>>`.
4. Una vez resuelto cada archivo, añádelo al staging: `git add <archivo>`.
5. Cuando todos estén resueltos, completa el merge: `git commit`. Para conflictos complejos, usa una herramienta visual: `git mergetool` (configurable con VSCode, IntelliJ, etc.).
