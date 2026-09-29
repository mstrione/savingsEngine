# Taxonomía de palancas de descuento — v1

> **Estado:** reconciliada contra el esquema real v3 de `contract-ingest`
> (`../../contract-ingest/references/schema.md`) el 2026-09-28 — reemplaza la v0 (DRAFT), que
> usaba nombres de campo en inglés (`expiration_date`, `pricing_model`, `key_clauses`, etc.) que no
> existen en el JSON real. Si el usuario ya definió su propia metodología de palancas (Excel "Tail
> Cutter" u otro), esa metodología tiene prioridad sobre esta lista genérica — preguntar antes de
> asumir.
>
> El objetivo de este archivo es que el coordinador (skill `discount-finder`) tenga, para cada
> palanca, una condición de aplicabilidad verificable contra el JSON de `contract-ingest` — nunca
> aplicar una palanca "porque suena razonable"; solo si la condición se cumple con evidencia.

Cada palanca se evalúa **por contrato**, usando los campos del registro de contrato del JSON
generado por `contract-ingest` (ver `schema.md`). El coordinador debe registrar, para cada
oportunidad detectada, qué campo(s) del JSON dispararon la palanca (`supporting_evidence`), citando
la ruta completa del campo (ej. `vigencia.fecha_fin.valor`, no solo `vigencia`).

| # | Palanca | Condición de aplicabilidad (chequear en el JSON) | Evidencia a citar |
|---|---|---|---|
| 1 | **Proximidad a vencimiento / renovación** | `vigencia.fecha_fin.valor` dentro de los próximos 6-9 meses, y/o `vigencia.renovacion_automatica_tacita.valor = "Sí"` | `vigencia.fecha_fin.valor`, `vigencia.renovacion_automatica_tacita.valor` |
| 2 | **Consolidación de volumen** | 2+ contratos activos en la misma categoría (mismo `_contratos_v<N>.json`) con alcance/servicio similar (comparar `productos_servicios_costo_unitario.descripcion_cantidad[].descripcion` y `notas` entre contratos) | `numero_contrato` de los contratos involucrados |
| 3 | **Benchmark de precio de mercado** | `monto_total.valor[]` no tiene ninguna entrada reciente con `periodo` que indique revisión de precio, y no hay mención de renegociación de tarifa en `notas` | `monto_total.valor[]`, `notas` |
| 4 | **Revisión de cláusula de indexación/reajuste** | `mecanismo_reajuste_indexacion.valor = "Sí"` con `detalle` que indique reajuste automático sin tope favorable al proveedor, o `= "No"` en un contrato de plazo largo (sin protección para el cliente tampoco) | `mecanismo_reajuste_indexacion.valor`, `mecanismo_reajuste_indexacion.detalle` |
| 5 | **Términos de pago** | `metodo_pago.valor` indica plazo corto (ej. contra factura/anticipado) sin mención de descuento por pronto pago en `notas` | `metodo_pago.valor`, `notas` |
| 6 | **Consolidación de tail spend** | Contrato con `monto_total.valor[]` bajo en relación al resto de contratos de la misma categoría (comparar contra el resto del array `contratos[]` del mismo JSON) | `monto_total.valor[]`, conteo de contratos de la categoría |
| 7 | **Compromiso de volumen no alcanzado** | `productos_servicios_costo_unitario.descripcion_cantidad[]` muestra un compromiso de cantidad explícito y hay evidencia en `notas` de que el consumo real es menor (requiere dato externo de consumo; si no está disponible, marcar como oportunidad a validar, no confirmada) | `productos_servicios_costo_unitario.descripcion_cantidad[]`, `notas` |
| 8 | **Múltiples modificaciones de precio al alza** | El historial de `monto_total.valor[]` (varias entradas con distinto `periodo`) muestra 2+ subas de tarifa sin contraparte de reducción, y/o `notas` documenta modificaciones de precio al alza | `monto_total.valor[]`, `notas` |
| 9 | **Incumplimiento o brecha de SLA** | `niveles_servicio.valor` define KPIs/SLAs y `notas` o `dossier_savingsradar.power_balance_resumen` documentan incumplimientos u operación por debajo de benchmark | `niveles_servicio.valor`, `notas`, `dossier_savingsradar.power_balance_resumen` |
| 10 | **Bundling / multi-año** | Contrato con `vigencia.fecha_inicio.valor`/`vigencia.fecha_fin.valor` de plazo corto (renovaciones repetidas, ver `vigencia.fecha_fin.detalle_historial`) sin mención de descuento por plazo más largo en `notas` | `vigencia.fecha_inicio.valor`, `vigencia.fecha_fin.valor`, `vigencia.fecha_fin.detalle_historial`, `notas` |
| 11 | **Oportunidad ya cuantificada por SavingsRadar (Dossier SR)** | `dossier_savingsradar.existe = true` para este contrato | `dossier_savingsradar.negociacion_oportunidad_pct`, `dossier_savingsradar.mdo_pct`/`target_pct`/`laa_pct`, `dossier_savingsradar.spend_musd` |

### Nota sobre la palanca 11

A diferencia de las palancas 1-10 (que el coordinador deriva por su cuenta comparando campos del
contrato), la palanca 11 es distinta: la oportunidad **ya viene cuantificada** por la herramienta
SavingsRadar de BCG dentro del PPTX "Dossier SR" de ese proveedor (ver
`../../contract-ingest/references/schema.md`, sección `dossier_savingsradar`). El coordinador no
recalcula nada acá — solo verifica que `existe = true`, cita los porcentajes/montos tal cual están
en el dossier, y puede usarlos como fuente legítima (no inventada) de `estimated_savings_range` en
el formato de salida de `SKILL.md` (con `estimated_savings_source: "dossier_savingsradar"`). Si el
dossier no coincide en nombre de proveedor (`supplier_name_en_dossier` distinto de `proveedor`),
marcar `confidence: baja` y anotarlo como alerta antes de reportar la oportunidad.

## Reglas para el coordinador

1. **Nunca inventar cifras de ahorro.** Si el contrato no tiene una cifra de descuento explícita
   en `notas`/documentos y tampoco existe `dossier_savingsradar` para ese proveedor, reportar la
   oportunidad en términos cualitativos (ej. "potencial de negociación", sin rango de USD/CLP) —
   ver la excepción explícita de la palanca 11 arriba, que sí es una fuente válida de cifra.
2. **Una palanca solo se reporta si su condición se cumple explícitamente** contra el JSON — no
   por intuición general del sector.
3. Para palancas que requieren comparar entre contratos (2, 6, 8), el coordinador debe leer el
   array `contratos[]` completo del `<categoria>_contratos_v<N>.json` de esa categoría antes de
   decidir, no solo el registro de un contrato aislado.
4. Cada oportunidad debe incluir un campo `confidence` (`alta`/`media`/`baja`) según qué tan
   directa es la evidencia.
5. Si el usuario ya definió su propia metodología de palancas (Excel "Tail Cutter" u otro), esa
   metodología tiene prioridad sobre esta lista genérica — preguntar antes de asumir.
