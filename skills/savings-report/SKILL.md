---
name: savings-report
description: Genera un reporte HTML con las oportunidades de descuento detectadas por discount-finder — KPIs generales, tabla por proveedor/categoría/palanca, y detalle de evidencia. Úsalo cuando el usuario pida "armar el reporte de ahorros", "generar el HTML de oportunidades", "ver el dashboard de descuentos", "mostrame un resumen visual de las oportunidades", o después de correr discount-finder si el usuario quiere ver los resultados de forma visual en vez de en JSON crudo. Requiere haber corrido discount-finder al menos una vez.
---

# Savings Report

Tercer paso del pipeline: convierte `output/discount-opportunities/<fecha>.json` en un reporte
HTML legible para compartir internamente.

## 1. Elegí el formato de salida

- **Si el usuario ya compartió un ejemplo de reporte** (mencionó que lo iba a pasar): seguí ese
  formato/estilo en vez del template genérico de `assets/report_template.html`, y actualizá ese
  archivo con la versión definitiva para las próximas corridas.
- **Si tenés disponible la herramienta de Artifact de Cowork** y el reporte es algo que el
  usuario va a querer reabrir/actualizar seguido (es el caso típico acá — esto es un tracker que
  se vuelve a correr): preferí publicarlo como artefacto persistido en vez de solo un archivo
  suelto.
- **Si no hay Artifact disponible o el usuario pidió explícitamente un archivo**: generá un HTML
  autocontenido (sin dependencias externas salvas Chart.js por CDN) en
  `output/reports/savings-report-<fecha>.html`, partiendo de `assets/report_template.html`.

En cualquier caso, el reporte debe ser información 100% trazable al JSON de `discount-finder` —
no agregues números o afirmaciones que no estén en los datos de entrada.

## 2. Contenido del reporte

Estructura mínima (ver `assets/report_template.html` para el esqueleto real):

1. **KPIs generales**: proveedores analizados, oportunidades totales, distribución por
   `confidence` (alta/media/baja), distribución por categoría.
2. **Tabla de oportunidades**: proveedor, categoría, palanca, confianza, evidencia (resumida),
   con filtro/orden por categoría y por palanca si el formato lo permite (JS simple, sin
   frameworks pesados).
3. **Detalle por palanca**: cuántas oportunidades cayeron en cada palanca de
   `../discount-finder/references/palancas.md`, útil para que el usuario priorice por tipo de
   acción antes que por proveedor.
4. Nota al pie aclarando que los montos de ahorro estimado, cuando existen, provienen
   directamente de los contratos (no son proyecciones del modelo).

## 3. Marca / estilo

Este reporte es un entregable interno relacionado a un engagement de BCG. Antes de darlo por
terminado, aplicá (o sugerí aplicar) el skill `bcg-output-style` para alinear tipografía, colores
y tono al estándar de marca, si el usuario lo va a compartir con otros o dejarlo como entregable
formal.

## Ver también

- `assets/report_template.html` — template HTML de partida (placeholder hasta que el usuario
  pase su propio ejemplo).
- `../discount-finder/SKILL.md` — formato del JSON de entrada.
