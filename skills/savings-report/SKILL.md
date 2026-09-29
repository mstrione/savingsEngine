---
name: savings-report
description: Genera reportes HTML sobre contratos de una categoría, en dos modos. Modo A — reporte de oportunidades de descuento detectadas por discount-finder (KPIs, tabla filtrable por proveedor/categoría/palanca, detalle de evidencia): úsalo cuando el usuario pida "armar el reporte de ahorros", "generar el HTML de oportunidades", "ver el dashboard de descuentos". Modo B — Microsite Buscador de contratos (catálogo interactivo, buscador de productos/servicios cruzando contratos, vista one-pager con auditoría de cláusulas): úsalo cuando el usuario pida "el buscador de contratos de [categoría]", "el microsite de [categoría]", o "algo interactivo para explorar los contratos, no solo el PPTX". No confundir con `category-onepager` (ese solo genera el slide PPTX). Modo A requiere `discount-finder`; Modo B requiere `contract-ingest`.
---

# Savings Report

Dos modos independientes, ambos parten de JSON ya generado por otro skill — este skill nunca
extrae datos de contratos por sí mismo.

## 0. Regla de activación (no negociable, ambos modos)

Igual que el resto del pipeline: un reporte nuevo (o una regeneración) **solo empieza si el
usuario lo pide explícitamente** — nunca dispara solo porque `discount-finder` o `contract-ingest`
recién terminaron. Si el usuario solo pregunta sobre un reporte ya generado, respondé mirando el
HTML/JSON existente, no dispares una regeneración.

## ¿Modo A o Modo B?

| | Modo A — Reporte de ahorros | Modo B — Microsite Buscador |
|---|---|---|
| Entrada | `<contracts_root>/output/discount-opportunities/<fecha>.json` (`discount-finder`) | JSON de `contract-ingest` + curación en el chat |
| Pregunta que responde | "¿Dónde hay oportunidades de descuento?" | "¿Qué dice cada contrato de esta categoría? ¿Qué productos tiene cada proveedor?" |
| Formato | 1 HTML (KPIs + tabla de oportunidades) | 1 HTML fijo (`index.html`) + 1 archivo de datos versionado (`datos_vN.js`) |
| Se re-corre | Cada vez que corre `discount-finder` de nuevo | Cada vez que hay una nueva versión del JSON de `contract-ingest`, o se refina la curación |

Si el usuario pide algo ambiguo ("hazme un reporte de la categoría X"), preguntá cuál de los dos
quiere antes de arrancar — no son intercambiables ni comparten output.

---

## Modo A — Reporte de oportunidades de descuento

Convierte `<contracts_root>/output/discount-opportunities/<fecha>.json` en un reporte HTML legible
para compartir internamente.

### A.1 Elegí el formato de salida

- **Si el usuario ya compartió un ejemplo de reporte** (mencionó que lo iba a pasar): seguí ese
  formato/estilo en vez del template genérico de `assets/report_template.html`, y actualizá ese
  archivo con la versión definitiva para las próximas corridas.
- **Si tenés disponible la herramienta de Artifact de Cowork** y el reporte es algo que el
  usuario va a querer reabrir/actualizar seguido (es el caso típico acá — esto es un tracker que
  se vuelve a correr): preferí publicarlo como artefacto persistido en vez de solo un archivo
  suelto.
- **Si no hay Artifact disponible o el usuario pidió explícitamente un archivo**: generá un HTML
  autocontenido (sin dependencias externas salvo Chart.js por CDN) en
  `<contracts_root>/output/reports/savings-report-<fecha>.html`, partiendo de
  `assets/report_template.html` (ruta relativa a la carpeta propia de este skill).

En cualquier caso, el reporte debe ser información 100% trazable al JSON de `discount-finder` —
no agregues números o afirmaciones que no estén en los datos de entrada.

### A.2 Contenido del reporte

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

### A.3 Marca / estilo

Este reporte es un entregable interno relacionado a un engagement de BCG. Antes de darlo por
terminado, aplicá (o sugerí aplicar) el skill `bcg-output-style` para alinear tipografía, colores
y tono al estándar de marca, si el usuario lo va a compartir con otros o dejarlo como entregable
formal.

---

## Modo B — Microsite Buscador de contratos

Genera un HTML navegable de 3 pestañas ("Vista one-pager", "Catálogo de contratos", "Buscador de
productos/servicios") para explorar los contratos de una categoría — el 4° artefacto del proceso
TAIL CUTTER, fuera de las 3 etapas oficiales de `playbooks/00_INDEX.md`, pero que ya se
venía haciendo a mano para Transporte de Personal antes de que existiera este skill.

**Separación estricta dato/presentación**: `index.html` (de `assets/microsite/index_template.html`)
es 100% genérico y no cambia entre categorías. Todo el contenido específico de una categoría vive
en `datos.js`, que asigna `window.MICROSITE_DATA`. Si en algún momento parece necesario editar el
HTML para una categoría puntual, es señal de que falta un campo en el esquema — ver
`references/microsite_data_schema.md` — no de que haya que bifurcar el template.

### B.1 Prerrequisito

Confirmá que existe el JSON consolidado de `contract-ingest` para esa categoría
(`<categoria>_contratos_v<N>.json`). Si no existe, avisale al usuario que hay que correrlo primero.

Si ya existe un `onepager_spec.json` de `category-onepager` para la misma categoría (Etapa 2 del
pipeline), **leelo y reusá literalmente** `left_items`, el headline/`callout`, y el
footnote/fuente — ver la regla de reutilización en `references/microsite_data_schema.md`. No le
pidas al usuario que redacte dos veces la misma narrativa de negocio.

### B.2 Derivar lo mecánico

Rutas de script relativas a la carpeta propia de este skill:

```bash
python3 scripts/derive_audit_hints.py \
    --json <ruta al JSON de contract-ingest> \
    --out filas_hint.json
```

Esto calcula `duracion` y los tres campos Sí/No de `auditoria_contratos.filas[]` a partir de
`vigencia`/`clausula_*` del JSON crudo, y deja `compromiso_volumen_sla` y
`hallazgo_principal_fila` como `"TODO"` — esos dos **no son mecánicos**, requieren que leas
`niveles_servicio` y `notas` de cada contrato y redactes el hallazgo. No los dejes en `"TODO"` en
la entrega final; el script imprime un conteo de cuántas filas quedan pendientes de completar.

### B.3 Redactar `microsite_data.json`

Con el esquema completo de `references/microsite_data_schema.md`, armá el JSON de especificación:
`categoria`, `cliente`, `total_contratos`, `fecha_extraccion` (las 4 claves del header — si falta
alguna, el header muestra literalmente "undefined", no hay fallback en el template), `contratos[]`
(cada contrato con su `productos_servicios[]` **anidado**, no como lista aparte — el campo `tipo`
de cada producto **no es derivable mecánicamente**, proponé la taxonomía en el chat si es la
primera vez que se procesa esta categoría), `auditoria_contratos` (usando el resultado del paso
B.2, con los `TODO` ya completados), y `onepager_resumen` (reusando contenido de
`category-onepager` si corresponde, per B.1).

Guardá este JSON junto a los demás artefactos de la categoría, versionado igual que el resto del
pipeline.

### B.4 Generar el microsite

```bash
python3 scripts/build_microsite.py \
    --json microsite_data.json \
    --out-dir "<Categoría>/Outputs/Microsite Buscador"
```

El script:
- valida que el JSON tenga las 5 claves de primer nivel obligatorias y avisa si quedan campos
  `"TODO"` sin completar (no lo ignores sin revisar);
- empaqueta el contenido en `datos_v<N>.js` (versionado, **nunca sobrescribe** — misma regla que
  el resto del pipeline, sirve de historial/rollback);
- copia `index_template.html` como `index.html` **una sola vez** (si ya existe, no lo toca —
  el HTML no depende de la versión de datos; usá `--force-html` solo si el template genérico
  cambió y hay que propagar la actualización);
- escribe también `datos.js` (sin versión en el nombre) con el mismo contenido — **esta es la
  única excepción deliberada a la regla de "nunca sobrescribir"**: `index.html` carga
  `<script src="datos.js">` con nombre fijo por diseño (para no tener que tocar el HTML por
  versión), así que `datos.js` es un archivo vivo que siempre refleja la última `datos_vN.js`,
  no una versión de entrega en sí misma.

### B.5 QA obligatoria antes de entregar (doble)

1. **Estructural**: corré el script — sus propios `❌`/`⚠️` ya cubren claves faltantes y `TODO`
   sin completar.
2. **Visual**: abrí `index.html` (con `datos.js` al lado) y recorré las 3 pestañas a mano —
   catálogo de contratos con los filtros, buscador de productos cruzando contratos, y la vista
   one-pager con el gráfico, la tabla de vencimientos y la auditoría. Prestá atención a: que los
   `left_items` no se vean truncados, que los chips de filtro (proveedor/moneda/tipo) tengan
   opciones reales y no vacías, y que ninguna fila de `auditoria_contratos` haya quedado con
   `"TODO"` visible. Un subagente con acceso a browser es la forma más confiable de hacer esta
   verificación de forma independiente al propio script de build.

Recién después de esta doble QA, entregá los archivos. Si existe `playbooks/TRACKER.md`, actualizá
la fila de la categoría (versión de microsite, fecha) al terminar.

## Ver también

- `assets/report_template.html` — template HTML de Modo A.
- `assets/microsite/index_template.html` — template HTML genérico de Modo B (no editar por
  categoría).
- `references/microsite_data_schema.md` — esquema completo de `window.MICROSITE_DATA` (Modo B).
- `scripts/derive_audit_hints.py` / `scripts/build_microsite.py` — scripts de Modo B.
- `../discount-finder/SKILL.md` — formato del JSON de entrada de Modo A.
- `../contract-ingest/SKILL.md` — formato del JSON de entrada de Modo B.
- `../category-onepager/SKILL.md` — genera el PPTX equivalente a la pestaña one-pager de Modo B;
  comparten contenido curado, no lo dupliques.
