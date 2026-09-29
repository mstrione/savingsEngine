---
name: discount-finder
description: Analiza el/los JSON consolidados de contract-ingest (uno por categoría, con nombre de archivo tipo "NOMBRE_CATEGORIA_contratos_vN.json") para detectar oportunidades de solicitud de descuento o renegociación, evaluando cada contrato contra una taxonomía de palancas (volumen, vencimiento, benchmark de mercado, términos de pago, tail spend, indexación, oportunidad ya cuantificada por SavingsRadar, etc.). Actúa como coordinador que solo reporta una palanca cuando su condición se cumple con evidencia verificable en el JSON. Úsalo cuando el usuario pida "buscar posibilidades de descuento", "qué proveedores podemos renegociar", "analizar palancas de negociación", "oportunidades de ahorro para [proveedor/categoría]", o "qué contratos están por vencer". Requiere haber corrido contract-ingest al menos una vez para la(s) categoría(s) en alcance.
---

# Discount Finder

Segundo paso del pipeline: convierte los JSON de `contract-ingest` en una lista de oportunidades
de descuento concretas, trazables y sin cifras inventadas.

## Prerrequisito

El output real de `contract-ingest` es **un JSON consolidado por categoría**
(`<categoria>_contratos_v<N>.json`, típicamente en una carpeta `Extracciones/` dentro de la
categoría — ver `../contract-ingest/SKILL.md` paso 4.2) — no un índice global ni un JSON por
proveedor. Si para la categoría en alcance no existe ningún `_contratos_v<N>.json`, avisale al
usuario que primero hay que correr `contract-ingest` (o corré ese paso vos mismo si el usuario ya
te dio la carpeta de contratos y solo faltó ese paso).

## 1. Alcance de la corrida

Preguntá o confirmá el alcance si no es obvio por el pedido del usuario:
- ¿Todas las categorías, o una puntual? Si son varias, cada una tiene su propio
  `_contratos_v<N>.json` — no asumas que existe un archivo combinado.
- ¿Usar la taxonomía genérica de `references/palancas.md`, o el usuario ya tiene su propia
  metodología (por ejemplo el Excel "Tail Cutter" u otro criterio interno)? Si la tiene,
  priorizala sobre la taxonomía genérica y pedile que te la resuma o comparta.

## 2. Rol de coordinador

Actuá como coordinador, no como generador de texto libre:

1. Para cada categoría en el alcance, identificá la versión más reciente de
   `<categoria>_contratos_v<N>.json` y cargala completa (necesaria para palancas que comparan
   entre contratos de la misma categoría, como consolidación de volumen o tail spend — el array
   `contratos[]` de ese único archivo ya contiene todos los proveedores de la categoría).
2. Para cada contrato en el alcance, evaluá **cada palanca** de `references/palancas.md` contra la
   condición de aplicabilidad descrita ahí, usando los campos reales del esquema v3 (ver
   `../contract-ingest/references/schema.md`): `vigencia.*`, `monto_total.valor[]`,
   `mecanismo_reajuste_indexacion.valor`, `metodo_pago.valor`, `niveles_servicio.valor`,
   `clausula_multa_penalizacion`, `clausula_incentivo_desempeno`, `dossier_savingsradar`, etc.
3. Una palanca solo se reporta como oportunidad si la condición se cumple explícitamente contra
   campos del JSON — nunca por intuición general ("este rubro suele tener descuento").
4. Si podés lanzar subagentes en paralelo (uno por categoría, o uno por lote de contratos dentro
   de una categoría grande) para acelerar el análisis, hacelo — cada subagente evalúa las mismas
   palancas sobre su lote y devuelve una lista de oportunidades en el formato de abajo.

## 3. Formato de salida

Por cada oportunidad detectada, generá un objeto:

```json
{
  "categoria": "Transporte de Personal",
  "proveedor": "COMERCIAL SERPAN LTDA",
  "numero_contrato": "4643004264",
  "lever": "proximidad_a_vencimiento",
  "rationale": "Explicación breve, en lenguaje de negocio, de por qué aplica.",
  "supporting_evidence": ["vigencia.fecha_fin.valor=2026-11-15", "vigencia.renovacion_automatica_tacita.valor=Sí"],
  "estimated_savings_range": null,
  "estimated_savings_source": null,
  "confidence": "alta"
}
```

- `proveedor` / `numero_contrato` identifican el contrato — el esquema v3 no tiene un
  `provider_id` numérico separado; si hace falta un identificador único, usá
  `rut_run_proveedor.valor` del registro.
- `estimated_savings_range` solo se completa si hay una base verificable para estimarlo. Dos
  fuentes legítimas, nunca un número "razonable" inventado:
  1. Una cifra explícita en el contrato (ej. un valor total y un % de descuento objetivo
     mencionado en algún documento).
  2. **`dossier_savingsradar`** del contrato, si `existe: true` (ver
     `../contract-ingest/references/schema.md`): los porcentajes/montos de `mdo_pct`/`target_pct`/
     `laa_pct` son una cifra ya cuantificada por la herramienta SavingsRadar de BCG, no una
     invención del coordinador — citarlos es válido siempre que `estimated_savings_source` deje
     explícito de dónde salen (ver palanca 11 en `references/palancas.md`).
  Si ninguna de las dos aplica, `null`.
- `estimated_savings_source`: `"contrato"` si sale de una cláusula/documento del contrato,
  `"dossier_savingsradar"` si sale del dossier SavingsRadar, `null` si `estimated_savings_range`
  es `null`.
- `confidence`: `alta` si la evidencia es directa y única; `media` si requiere alguna inferencia
  razonable; `baja` si es una señal débil que vale la pena validar manualmente.

Guardá el resultado consolidado en
`<contracts_root>/output/discount-opportunities/<YYYY-MM-DD>.json` (nunca en una carpeta `output/`
al lado de `skills/`) como una
lista de estos objetos, más un pequeño resumen (`total_contratos_analizados`,
`total_opportunities`, `by_lever` con conteo por palanca, `by_categoria` con conteo por categoría).

## 4. Resumen al usuario

Cerrá con un resumen corto en el chat (no hace falta repetir el JSON completo): cuántas
oportunidades se encontraron, top 3-5 por relevancia, y si alguna palanca quedó "a validar" por
falta de dato externo (ej. compromiso de volumen vs. consumo real). Sugerí correr
`savings-report` para verlo como reporte, o `discount-email` para armar el borrador de un
proveedor puntual.

## Ver también

- `references/palancas.md` — taxonomía de palancas y condición de aplicabilidad de cada una.
- `../contract-ingest/references/schema.md` — campos disponibles en el JSON de entrada, incluido
  `dossier_savingsradar`.
- `../contract-ingest/SKILL.md` — dónde y cómo se genera/versiona el JSON de entrada.
