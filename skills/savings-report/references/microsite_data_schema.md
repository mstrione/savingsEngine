# Esquema del objeto `window.MICROSITE_DATA` (`datos.js`)

Este JSON/objeto JS es el equivalente, para el Modo B (Microsite Buscador), de lo que
`onepager_spec.json` es para `category-onepager` (ver `../../category-onepager/references/onepager_spec.md`):
el **puente curado** entre el JSON crudo de `contract-ingest` y el artefacto final — en este caso
`index.html` + `datos_vN.js`, no un PPTX.

No es un mirror 1:1 del JSON de `contract-ingest`. Es el resultado de aplicar la misma metodología
ya acordada con el usuario para el one-pager (moneda, multi-contrato, atípicos, estimaciones) más
un nivel de curación propio del microsite: la auditoría de contratos (`auditoria_contratos`) y la
taxonomía `tipo` de productos/servicios no existen como tales en el JSON de `contract-ingest` — son
lectura y clasificación que hace Claude en el chat.

`index_template.html` (`assets/microsite/index_template.html`) es 100% genérico y no cambia entre
categorías — lee todo de `window.MICROSITE_DATA`. Si en algún momento parece necesario tocar el HTML
para una categoría puntual, es señal de que falta un campo en este esquema, no de que haya que
tocar el template.

## Regla de reutilización (no negociable)

`left_items`, el `headline`/`titulo` del one-pager, `callout`, `chart_categories`/`chart_values`
(acá `monto_por_proveedor_clp_mm`) y `footnote`/`fuente_texto` **deben ser los mismos** que los que
ya se redactaron para `onepager_spec.json` de `category-onepager`, si ese archivo ya existe para la
categoría — no los reescribas desde cero. Es la misma narrativa de negocio, servida en dos
formatos. Si `category-onepager` corrió primero, copiá esos campos literalmente; si el microsite
corre primero, guardá esos mismos campos para reusarlos después en `onepager_spec.json`.

## Estructura completa

```
window.MICROSITE_DATA = {
  categoria: string,              // ej. "Transporte de Personal" — usado en document.title
  contratos: [ {...} ],           // catálogo de contratos, ver abajo
  productos_servicios: [ {...} ], // catálogo de productos/servicios aplanado, ver abajo
  auditoria_contratos: {...},     // ver abajo
  onepager_resumen: {...}         // ver abajo — reusa contenido de onepager_spec.json
}
```

### `contratos[]` — un elemento por contrato

Campos flat, ya como strings de display (no wrapped en `{valor,fuente,confianza}` — esa
traceabilidad vive en el JSON de `contract-ingest`, no acá; ver nota al final sobre por qué).

| Campo | Tipo | Descripción |
|---|---|---|
| `numero` | string | N° de contrato |
| `proveedor` | string | Razón social del proveedor |
| `moneda` | string | Moneda de facturación (para el chip-filter de moneda) |
| `tipo` | string | Tipo de contrato (para el chip-filter de tipo) — categoría curada, no siempre 1:1 con un campo del JSON crudo |
| `monto_total_display` | string | Monto ya formateado y convertido, listo para mostrar (ej. "CLP 30.504 MM") |
| `vigencia_inicio` / `vigencia_fin` | string (YYYY-MM-DD) | Fechas de vigencia — usadas también por `derive_audit_hints.py` para calcular `duracion` |
| `alerta_vencimiento` | string \| null | Texto de alerta si vence pronto (ej. "Vence en 37 días") — recalculable, no hardcodear una fecha relativa que quede vieja |
| `resumen` | string | 1-2 líneas de resumen del contrato para la vista de catálogo |

### `productos_servicios[]` — catálogo aplanado, cruza contratos

| Campo | Tipo | Descripción |
|---|---|---|
| `contrato_numero` | string | FK a `contratos[].numero` |
| `descripcion` | string | Descripción del producto/servicio |
| `tipo` | string | **Curado a mano** — no se puede derivar mecánicamente del JSON v3 real (confirmado en `datos_v2.js`: el header comment de esa versión ya marcaba este gap explícitamente). Cada categoría nueva requiere que Claude proponga la taxonomía de tipos en el chat. |
| `cantidad` | string | Cantidad/volumen, tal como aparece en el contrato |
| `costo_unitario_display` | string | Costo unitario ya formateado |

### `auditoria_contratos` — sección "op-audit", curada

```
auditoria_contratos: {
  titulo: string,        // ej. "Auditoría de cláusulas por contrato"
  nota_rol: string,      // 1 línea de contexto sobre qué mira esta tabla — curada
  hallazgo_principal: string, // el "so-what" de la auditoría — curada, análoga al headline del one-pager
  filas: [
    {
      contrato_numero: string,       // FK a contratos[].numero
      duracion: string,              // MECÁNICO — derivable de vigencia_inicio/vigencia_fin (derive_audit_hints.py)
      incentivos: "Sí" | "No",       // MECÁNICO — derivable si el texto de cláusula empieza con "sí"/"no" (case/tilde-insensitive)
      penalidades: "Sí" | "No",      // ídem
      reajuste_indexacion: "Sí" | "No", // ídem
      compromiso_volumen_sla: string, // CURADO — síntesis, no mecánico
      hallazgo_principal_fila: string // CURADO — juicio analítico por contrato
    }
  ]
}
```

La distinción mecánico/curado no es cosmética: `derive_audit_hints.py` completa `duracion` y los
tres campos Sí/No a partir del JSON de `contract-ingest` (ver script), dejando
`compromiso_volumen_sla` y `hallazgo_principal_fila` como placeholders `"TODO"` que Claude debe
completar en el chat leyendo las cláusulas reales — nunca inventarlos ni dejarlos en `"TODO"` en la
entrega final.

### `onepager_resumen` — reusa contenido de `category-onepager`

```
onepager_resumen: {
  titulo: string,                 // = headline de onepager_spec.json, si existe
  left_heading: string,           // opcional, default "Productos y servicios de la categoría"
  left_items: [ {icon, title, desc} ],  // = left_items de onepager_spec.json, literal
  chart_heading: string,          // opcional, = chart_heading de onepager_spec.json
  monto_por_proveedor_clp_mm: [ {proveedor, valor, pct} ], // = chart_categories/chart_values combinados
  vencimientos: [ {vencimiento, proveedores, contratos, alerta} ], // = table_rows de onepager_spec.json
  callout: string,                // = callout de onepager_spec.json, literal
  fuente_texto: string,           // = footnote de onepager_spec.json, literal (fuente + tipo de cambio + método de estimación)
  nota_metodologica: string       // opcional, ampliación de fuente_texto si hace falta más detalle en el microsite que en el pptx
}
```

`left_items[].icon` se conserva en el esquema por paridad con `onepager_spec.json`, pero
`index_template.html` lo ignora al renderizar (usa solo un punto de color, no el ícono) — no hace
falta que el ícono exista en `assets/icons/` de `bcg-slide-generator` para que el microsite
funcione, solo para el PPTX.

## Por qué esto no está wrapped en `{valor, fuente, confianza}`

El JSON "ideal" de `contract-ingest` (`../../contract-ingest/references/schema.md`) envuelve casi
todo en objetos de trazabilidad. Este esquema no lo hace, por la misma razón que `datos_v2.js` real
tampoco lo hacía: el microsite es una vista de **display**, no el registro de trazabilidad — la
trazabilidad vive en el JSON de `contract-ingest` (fuente de verdad) y en el `footnote` del
one-pager, no en cada campo del microsite. Envolver cada campo acá sería redundante y complicaría
el template sin aportar valor al usuario final del buscador.

## Ver también

- `../../category-onepager/references/onepager_spec.md` — esquema del spec del one-pager PPTX;
  varios campos de `onepager_resumen` se copian literal de ahí.
- `../assets/microsite/index_template.html` — el HTML genérico que consume este objeto.
- `../scripts/derive_audit_hints.py` — deriva los campos mecánicos de `auditoria_contratos.filas[]`.
- `../scripts/build_microsite.py` — empaqueta un `microsite_data.json` autorado en `datos_vN.js`.
