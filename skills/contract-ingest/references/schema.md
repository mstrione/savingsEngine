# Esquema de resumen de contrato — v0 (DRAFT)

> **Estado:** borrador inicial, inferido de la estructura de carpetas de ejemplo (categoría → proveedor → contrato/adendas/ODC/dossier).
> Cuando Mauro pase ejemplos reales de resúmenes esperados, actualizar este archivo y `schema.json` en consecuencia, y subir la versión a `v1`.

Cada corrida del skill `contract-ingest` produce **un JSON por proveedor**, guardado en
`output/contract-summaries/<categoria>/<provider_id>.json`, más un índice agregado en
`output/contract-summaries/index.json`.

## Campos

| Campo | Tipo | Descripción |
|---|---|---|
| `schema_version` | string | Versión del esquema usado (`"0.1-draft"`). |
| `provider_id` | string | Código de proveedor tal como aparece en el nombre de carpeta (ej. `"4643003769"`). |
| `provider_name` | string | Razón social del proveedor. |
| `category` | string | Categoría de gasto (nombre de la carpeta padre, ej. `"TI y Telecomunicaciones"`). |
| `contract_number` | string \| null | Número de contrato principal, si se identifica en el documento. |
| `effective_date` | string (ISO date) \| null | Fecha de inicio de vigencia. |
| `expiration_date` | string (ISO date) \| null | Fecha de término / próxima renovación. |
| `term_months` | number \| null | Duración del contrato en meses, si es identificable. |
| `renewal_type` | enum: `"automatica"`, `"manual"`, `"desconocida"` | Tipo de renovación. |
| `notice_period_days` | number \| null | Días de preaviso requeridos para no renovar / renegociar. |
| `currency` | string \| null | Moneda del contrato (ej. `"CLP"`, `"USD"`). |
| `pricing_model` | enum: `"fijo"`, `"variable"`, `"por_consumo"`, `"mixto"`, `"desconocido"` | Estructura de precio. |
| `total_value_estimate` | number \| null | Valor total estimado del contrato, **solo si figura explícitamente** en algún documento. Nunca calcular ni inventar. |
| `payment_terms_days` | number \| null | Plazo de pago (ej. 30, 60, 90 días). |
| `volume_commitment` | string \| null | Compromiso de volumen/consumo mínimo, en texto libre citando la cláusula. |
| `key_clauses` | array de objetos | Cláusulas relevantes para negociación. Cada objeto: `{ "clause_type": string, "description": string, "source_document": string }`. |
| `modifications` | array de objetos | Historial de adendas/modificaciones. Cada objeto: `{ "mod_number": string, "date": string, "document_file": string, "summary": string }`, ordenado cronológicamente. |
| `documents` | array de objetos | Todos los archivos leídos para este proveedor. Cada objeto: `{ "file_name": string, "doc_type": enum(\"contrato\",\"modificacion\",\"odc\",\"formulario_admin\",\"dossier_negociacion\",\"otro\"), "date": string \| null }`. |
| `contacts` | array de objetos | Nombres/roles de firmantes o contactos comerciales que aparezcan. **Dato personal — ver nota abajo.** Cada objeto: `{ "name": string, "role": string \| null }`. |
| `flags` | array de strings | Señales útiles para el paso de descuentos, ej. `"vence_en_menos_de_6_meses"`, `"sin_clausula_de_reajuste"`, `"multiples_modificaciones_de_precio"`. |
| `summary` | string | Resumen en lenguaje simple (3-5 líneas) del contrato y su estado actual. |
| `source_folder` | string | Ruta de la carpeta de proveedor procesada. |
| `processed_at` | string (ISO datetime) | Timestamp de la corrida. |

### Nota sobre datos personales

`contacts` puede incluir nombres de personas físicas (firmantes, contactos comerciales). Esto es
dato personal según la Sección 6 de BCG Claude Code Safeguards. Incluir solo nombre y rol —
**nunca** email, teléfono, RUT o firma en el JSON. Si el resumen no necesita esta información para
el análisis de descuentos, omitir el campo por completo.

### Principio de trazabilidad

Todo campo no trivial (`total_value_estimate`, `key_clauses`, `flags`, etc.) debe poder rastrearse
a un documento fuente concreto (`source_document` / `document_file`). Si un dato no está explícito
en los documentos, usar `null` — no inferir ni completar con supuestos.
