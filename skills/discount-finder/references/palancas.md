# Taxonomía de palancas de descuento — v0 (DRAFT)

> **Estado:** taxonomía genérica de procurement, punto de partida. Cuando Mauro pase ejemplos
> reales de palancas usadas en el engagement, reemplazar/ampliar esta lista y subir a `v1`.
> El objetivo de este archivo es que el coordinador (skill `discount-finder`) tenga, para cada
> palanca, una condición de aplicabilidad verificable contra el JSON de `contract-ingest` — nunca
> aplicar una palanca "porque suena razonable"; solo si la condición se cumple con evidencia.

Cada palanca se evalúa **por proveedor/contrato**, usando los campos del JSON generado por
`contract-ingest` (ver `schema.md`). El coordinador debe registrar, para cada oportunidad
detectada, qué campo(s) del JSON dispararon la palanca (`supporting_evidence`).

| # | Palanca | Condición de aplicabilidad (chequear en el JSON) | Evidencia a citar |
|---|---|---|---|
| 1 | **Proximidad a vencimiento / renovación** | `expiration_date` dentro de los próximos 6-9 meses, o flag `vence_en_menos_de_6_meses` | `expiration_date`, `renewal_type`, `notice_period_days` |
| 2 | **Consolidación de volumen** | 2+ proveedores activos en la misma `category` con alcance/servicio similar (detectable comparando `summary`/`key_clauses` entre proveedores de la misma categoría) | lista de `provider_id` involucrados |
| 3 | **Benchmark de precio de mercado** | `pricing_model` = `fijo` o `variable` y no hay evidencia de revisión de precio en las últimas 2 modificaciones (`modifications`) | `modifications`, `pricing_model` |
| 4 | **Revisión de cláusula de indexación/reajuste** | `key_clauses` incluye una cláusula de reajuste/indexación automática sin tope, o el flag `sin_clausula_de_reajuste` favorable al proveedor | `key_clauses` |
| 5 | **Términos de pago** | `payment_terms_days` < 45 y no hay cláusula de pronto pago/descuento por pago anticipado en `key_clauses` | `payment_terms_days`, `key_clauses` |
| 6 | **Consolidación de tail spend** | Proveedor con bajo valor relativo (`total_value_estimate` bajo o desconocido) dentro de una categoría con muchos proveedores pequeños | `category`, conteo de proveedores en `index.json` |
| 7 | **Compromiso de volumen no alcanzado** | `volume_commitment` explícito y evidencia en el resumen de que el consumo real es menor (requiere dato externo de consumo; si no está disponible, marcar como oportunidad a validar, no confirmada) | `volume_commitment` |
| 8 | **Múltiples modificaciones de precio al alza** | `modifications` con 2+ entradas cuyo `summary` mencione aumento de precio/tarifa, sin contraparte de reducción | `modifications` |
| 9 | **Historial de incumplimiento de SLA** | `key_clauses` o `summary` mencionan SLA definidos y hay evidencia (en dossier de negociación, si existe como documento) de incumplimientos | `documents` (tipo `dossier_negociacion`), `key_clauses` |
| 10 | **Bundling / multi-año** | Contrato de `term_months` corto (renovaciones anuales repetidas) sin descuento por plazo más largo mencionado en `key_clauses` | `term_months`, `modifications`, `key_clauses` |

## Reglas para el coordinador

1. **Nunca inventar cifras de ahorro.** Si el contrato no tiene `total_value_estimate`, reportar
   la oportunidad en términos cualitativos (ej. "potencial de negociación", sin rango de USD/CLP).
2. **Una palanca solo se reporta si su condición se cumple explícitamente** contra el JSON — no
   por intuición general del sector.
3. Para palancas que requieren comparar entre proveedores (2, 6), el coordinador debe leer
   `output/contract-summaries/index.json` completo antes de decidir, no solo el JSON de un
   proveedor aislado.
4. Cada oportunidad debe incluir un campo `confidence` (`alta`/`media`/`baja`) según qué tan
   directa es la evidencia.
5. Si el usuario ya definió su propia metodología de palancas (Excel "Tail Cutter" u otro), esa
   metodología tiene prioridad sobre esta lista genérica — preguntar antes de asumir.
