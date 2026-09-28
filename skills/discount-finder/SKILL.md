---
name: discount-finder
description: Analiza los resúmenes de contrato en JSON (generados por contract-ingest) para detectar oportunidades de solicitud de descuento o renegociación, evaluando cada proveedor/contrato contra una taxonomía de palancas (volumen, vencimiento, benchmark de mercado, términos de pago, tail spend, indexación, etc.). Actúa como coordinador que solo reporta una palanca cuando su condición se cumple con evidencia verificable en el JSON. Úsalo cuando el usuario pida "buscar posibilidades de descuento", "qué proveedores podemos renegociar", "analizar palancas de negociación", "oportunidades de ahorro para [proveedor/categoría]", o "qué contratos están por vencer". Requiere haber corrido contract-ingest al menos una vez.
---

# Discount Finder

Segundo paso del pipeline: convierte los JSON de `contract-ingest` en una lista de oportunidades
de descuento concretas, trazables y sin cifras inventadas.

## Prerrequisito

Si `output/contract-summaries/index.json` no existe, avisale al usuario que primero hay que
correr el skill `contract-ingest` (o corré el paso vos mismo si el usuario ya te dio la carpeta de
contratos y solo faltó ese paso).

## 1. Alcance de la corrida

Preguntá o confirmá el alcance si no es obvio por el pedido del usuario:
- ¿Todos los proveedores/categorías, o uno puntual (por nombre de proveedor o categoría)?
- ¿Usar la taxonomía genérica de `references/palancas.md`, o el usuario ya tiene su propia
  metodología (por ejemplo el Excel "Tail Cutter" u otro criterio interno)? Si la tiene,
  priorizala sobre la taxonomía genérica y pedile que te la resuma o comparta.

## 2. Rol de coordinador

Actuá como coordinador, no como generador de texto libre:

1. Cargá `output/contract-summaries/index.json` completo (necesario para palancas que comparan
   entre proveedores, como consolidación de volumen o tail spend).
2. Para cada proveedor en el alcance, abrí su JSON individual y evaluá **cada palanca** de
   `references/palancas.md` contra la condición de aplicabilidad descrita ahí.
3. Una palanca solo se reporta como oportunidad si la condición se cumple explícitamente contra
   campos del JSON — nunca por intuición general ("este rubro suele tener descuento").
4. Si podés lanzar subagentes en paralelo (uno por proveedor o por categoría) para acelerar el
   análisis cuando hay muchos proveedores, hacelo — cada subagente evalúa las mismas palancas
   sobre su proveedor y devuelve una lista de oportunidades en el formato de abajo.

## 3. Formato de salida

Por cada oportunidad detectada, generá un objeto:

```json
{
  "provider_id": "4643003769",
  "provider_name": "LOS NAVEGANTES S.A",
  "category": "TI y Telecomunicaciones",
  "lever": "proximidad_a_vencimiento",
  "rationale": "Explicación breve, en lenguaje de negocio, de por qué aplica.",
  "supporting_evidence": ["expiration_date=2026-11-15", "renewal_type=automatica"],
  "estimated_savings_range": null,
  "confidence": "alta"
}
```

- `estimated_savings_range` solo se completa si hay una cifra explícita en el contrato que
  permita estimarlo (ej. un valor total y un % de descuento objetivo mencionado en algún
  documento). Si no, `null` — nunca calcular un número "razonable" sin base documental.
- `confidence`: `alta` si la evidencia es directa y única; `media` si requiere alguna inferencia
  razonable; `baja` si es una señal débil que vale la pena validar manualmente.

Guardá el resultado consolidado en `output/discount-opportunities/<YYYY-MM-DD>.json` como una
lista de estos objetos, más un pequeño resumen (`total_providers_analyzed`,
`total_opportunities`, `by_lever` con conteo por palanca).

## 4. Resumen al usuario

Cerrá con un resumen corto en el chat (no hace falta repetir el JSON completo): cuántas
oportunidades se encontraron, top 3-5 por relevancia, y si alguna palanca quedó "a validar" por
falta de dato externo (ej. compromiso de volumen vs. consumo real). Sugerí correr
`savings-report` para verlo como reporte, o `discount-email` para armar el borrador de un
proveedor puntual.

## Ver también

- `references/palancas.md` — taxonomía de palancas y condición de aplicabilidad de cada una.
- `../contract-ingest/references/schema.md` — campos disponibles en el JSON de entrada.
