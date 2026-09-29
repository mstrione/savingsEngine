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

**Este documento describe exactamente los campos que `assets/microsite/index_template.html` lee
del objeto — no una versión idealizada o resumida.** Si en algún momento parece necesario tocar el
HTML para una categoría puntual, es señal de que falta un campo acá, no de que haya que bifurcar el
template. (Nota histórica: una versión anterior de este archivo documentaba un esquema más chico y
plano que nunca coincidió con lo que el template realmente consume — causó un bug real en el
microsite de "TI y Telecomunicaciones" el 2026-09-29: `undefined` en el header y un
`TypeError` al ordenar el catálogo. Esta versión se verificó campo por campo contra el `<script>`
de `index_template.html`.)

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
  categoria: string,          // ej. "TI y Telecomunicaciones" — título de página y <h1>
  cliente: string,            // nombre del cliente — línea "sub" del header
  total_contratos: number,    // cuenta de contratos — línea "sub" del header ("N contratos")
  fecha_extraccion: string,   // fecha de la extracción (YYYY-MM-DD o texto libre) — línea "sub"
  contratos: [ {...} ],       // catálogo de contratos, ver abajo
  auditoria_contratos: {...}, // ver abajo
  onepager_resumen: {...}     // ver abajo — reusa contenido de onepager_spec.json
}
```

`categoria`, `cliente`, `total_contratos` y `fecha_extraccion` son las 4 claves que arma la línea
del header (`D.cliente + ' · ' + D.total_contratos + ' contratos · extracción ' + D.fecha_extraccion`).
Si falta cualquiera de las 4, el header muestra literalmente `undefined` — no hay fallback en el
template. `build_microsite.py` las valida como obligatorias de primer nivel.

**No existe un `productos_servicios[]` de primer nivel.** El catálogo de productos/servicios va
anidado dentro de cada contrato (`contratos[].productos_servicios`, ver abajo) — el template arma
el buscador aplanado (`flattenProductos()`) leyendo `D.contratos.forEach(c => c.productos_servicios)`,
nunca `D.productos_servicios`.

### `contratos[]` — un elemento por contrato

```
{
  numero_contrato: string,
  proveedor: string,
  alerta: string | null,          // truthy → badge "⚠ Alerta" + caja de alerta en el detalle
  tiene_modificacion: boolean,    // true → badge "Con modificación"
  vigencia: {
    fecha_inicio: string,         // YYYY-MM-DD
    fecha_fin: string             // YYYY-MM-DD — usado para ordenar el catálogo y calcular días restantes
  },
  vigencia_nota: string,          // opcional — se agrega como " — <nota>" junto a la vigencia
  monto_total: {
    valor: string,                 // ya formateado/convertido, listo para mostrar (ej. "30.504 MM")
    moneda: string                 // usado también por el chip-filter de moneda (UF/CLP/USD)
  },
  rut_run_proveedor: string,
  rut_validacion: string,          // resultado de validate_rut.py, texto de display
  renovacion_automatica: string,
  termino_anticipado: string,
  tipo_cambio: string,
  metodo_pago: string,
  niveles_servicio: string,
  clausula_incentivo_desempeno: string,
  clausula_multa_penalizacion: string,
  mecanismo_reajuste_indexacion: string,
  documentos_fuente: [string],     // lista de nombres de archivo, se muestra con <br> entre cada uno
  notas: string,
  productos_servicios: [ {...} ]   // catálogo de productos de ESTE contrato, ver abajo — anidado, no top-level
}
```

Todos los campos de texto van ya como strings de display (no wrapped en `{valor,fuente,confianza}`
— esa trazabilidad vive en el JSON de `contract-ingest`, no acá; ver nota al final). Cualquier
campo sin dato disponible en el contrato de origen debe llevar `"-"` o `"No especificado"` como
string — nunca `null`/`undefined`, porque el template no tiene fallback y los imprime tal cual
(`${c.campo||'-'}` cubre algunos campos, pero no todos — mejor no depender de eso).

El filtro de moneda del catálogo lee `c.monto_total.moneda` (no hay un campo `moneda` separado a
nivel contrato). No hay tampoco un campo `tipo` a nivel contrato para el chip-filter de tipo — ese
filtro se arma a partir de los `tipo` de `productos_servicios[]` de cada contrato.

### `contratos[].productos_servicios[]` — catálogo de productos, anidado por contrato

```
{
  tipo: string,            // curado a mano — no derivable mecánicamente del JSON v3 real; cada
                            // categoría nueva requiere que Claude proponga la taxonomía en el chat
  descripcion: string,
  cantidad: string,        // tal como aparece en el contrato
  costo_unitario: string,  // ya formateado
  moneda: string           // opcional — se muestra entre paréntesis junto al costo unitario
}
```

El buscador de productos (`flattenProductos()`) le agrega automáticamente `proveedor`,
`numero_contrato` y `alerta` a cada producto aplanado — no hace falta repetirlos acá.

### `auditoria_contratos` — sección "op-audit", curada

```
auditoria_contratos: {
  titulo: string,        // ej. "Auditoría de cláusulas por contrato"
  nota_rol: string,      // 1 línea de contexto sobre qué mira esta tabla — curada
  hallazgo_principal: string, // el "so-what" de la auditoría — curada, análoga al headline del one-pager
  filas: [
    {
      contrato_numero: string,       // FK a contratos[].numero_contrato — MECÁNICO
      proveedor: string,             // MECÁNICO — copia directa de contratos[].proveedor
      duracion: string,              // MECÁNICO — derivable de vigencia.fecha_inicio/fecha_fin (derive_audit_hints.py)
      modalidad_pago: string,        // MECÁNICO — copia directa de metodo_pago.valor del JSON crudo
      incentivos: "Sí" | "No" | "No especificado",       // MECÁNICO
      penalidades: "Sí" | "No" | "No especificado",      // MECÁNICO
      reajuste_indexacion: "Sí" | "No" | "No especificado", // MECÁNICO
      compromiso_volumen_sla: string, // CURADO — síntesis de niveles_servicio, no mecánico
      hallazgo_principal_fila: string // CURADO — juicio analítico por contrato (ver nota abajo)
    }
  ]
}
```

`derive_audit_hints.py` completa `contrato_numero`, `proveedor`, `duracion`, `modalidad_pago` y los
tres campos Sí/No a partir del JSON de `contract-ingest`, dejando `compromiso_volumen_sla` y
`hallazgo_principal_fila` como placeholders `"TODO"` que Claude debe completar en el chat leyendo
las cláusulas reales — nunca inventarlos ni dejarlos en `"TODO"` en la entrega final.

**Nota conocida:** `index_template.html` no renderiza actualmente `hallazgo_principal_fila` en
ninguna celda de la tabla de auditoría (solo se usa `hallazgo_principal` a nivel de sección, no por
fila). El campo se sigue derivando/curando por paridad con el resto del esquema y por si se agrega
esa columna más adelante, pero hoy es un campo "vivo" sin efecto visual — no es un bug, es una
brecha de diseño pendiente (ver `docs/ARQUITECTURA.md`, extensiones futuras).

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

`vencimientos[].contratos` es un string tipo `"1234 / 5678"` (varios números separados por ` / `) —
el template toma el primero (`.split('/')[0].trim()`) para buscar ese contrato en `D.contratos` y
calcular los días restantes en vivo. Si el primer número no matchea exactamente un
`contratos[].numero_contrato`, esa fila muestra "-" en días restantes sin romper nada más.

`left_items[].icon` se conserva en el esquema por paridad con `onepager_spec.json`, pero
`index_template.html` lo ignora al renderizar (usa solo un punto de color, no el ícono) — no hace
falta que el ícono exista en `assets/icons/` de `bcg-slide-generator` para que el microsite
funcione, solo para el PPTX.

## Por qué esto no está wrapped en `{valor, fuente, confianza}`

El JSON "ideal" de `contract-ingest` (`../../contract-ingest/references/schema.md`) envuelve casi
todo en objetos de trazabilidad. Este esquema no lo hace: el microsite es una vista de **display**,
no el registro de trazabilidad — la trazabilidad vive en el JSON de `contract-ingest` (fuente de
verdad) y en el `footnote` del one-pager, no en cada campo del microsite. Envolver cada campo acá
sería redundante y complicaría el template sin aportar valor al usuario final del buscador.

## Ver también

- `../../category-onepager/references/onepager_spec.md` — esquema del spec del one-pager PPTX;
  varios campos de `onepager_resumen` se copian literal de ahí.
- `../assets/microsite/index_template.html` — el HTML genérico que consume este objeto; es la
  fuente de verdad de este documento — ante cualquier duda, lo que lee el `<script>` ahí manda.
- `../scripts/derive_audit_hints.py` — deriva los campos mecánicos de `auditoria_contratos.filas[]`.
- `../scripts/build_microsite.py` — empaqueta un `microsite_data.json` autorado en `datos_vN.js`;
  valida presencia de `categoria`, `cliente`, `total_contratos`, `fecha_extraccion`, `contratos`,
  `auditoria_contratos`, `onepager_resumen` como claves de primer nivel.
