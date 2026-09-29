# Esquema de extracción de contratos — v3

> **Estado:** alineado con el proceso real "TAIL CUTTER" que Mauro ya usa manualmente
> (`playbooks/01_extraccion_contratos.md`, v3, 2026-09-27), descubierto durante la
> re-arquitectura del 2026-09-28. Reemplaza el borrador v0 (JSON por proveedor, campos en inglés,
> sin trazabilidad por campo) — ver historial de git si hace falta consultar v0.
>
> **Fuente de verdad:** si la carpeta de contratos configurada (`contracts_root`) tiene un
> `playbooks/01_extraccion_contratos.md` como hermano de las carpetas de categoría (patrón
> `<root>/playbooks/01_extraccion_contratos.md` + `<root>/<Categoría>/...`), ese archivo manda por
> sobre este documento — leerlo completo antes de extraer y seguir sus reglas literalmente. Este
> `schema.md` es el esquema **por defecto** para cuando esa carpeta no existe (repo nuevo, cliente
> nuevo sin playbooks propios todavía), y debe mantenerse sincronizado con la versión del playbook
> real cada vez que esta cambie.

## Cambio de unidad de salida respecto a v0

v0 producía **un JSON por proveedor**. El proceso real produce **un único JSON por categoría**
(metadata + arreglo de contratos), con Excel como espejo humano generado a partir de ese JSON. Los
subagentes por proveedor (ver `SKILL.md`) siguen corriendo en paralelo por velocidad, pero sus
resultados se **consolidan en un solo archivo versionado** antes de entregar — nunca se dejan como
JSONs sueltos por proveedor.

## Estructura del archivo

```json
{
  "metadata": {
    "categoria": "string",
    "fecha_extraccion": "YYYY-MM-DD",
    "cliente": "string",
    "metodologia": "string (qué playbook/versión se siguió, y qué cambió vs. la corrida anterior)",
    "version": "vN",
    "version_anterior": "vN-1 (YYYY-MM-DD) | null si es la primera",
    "total_contratos": "number",
    "nota_normalizacion": "string | null — cómo se resolvieron variaciones de nombres de campo entre sub-agentes, si aplica"
  },
  "contratos": [ /* ver 'Registro de contrato' abajo */ ]
}
```

## Registro de contrato (uno por proveedor/contrato, consolidando base + modificaciones + anexos + ODC)

Cada contrato es **un único registro consolidado**, no un registro por documento (regla 4.4 del
playbook). Campos, en el orden en que deben aparecer:

| Campo | Forma | Descripción |
|---|---|---|
| `numero_contrato` | string | Número de contrato tal como aparece en carpeta/documento. |
| `proveedor` | string | Razón social. Si hay discrepancias de nombre entre documentos fuente, dejarlo anotado acá mismo, no ocultarlo. |
| `rut_run_proveedor` | objeto con trazabilidad | `{ valor, validacion_digito_verificador: {resultado, detalle}, fuente, confianza }`. Ver regla de validación abajo. |
| `vigencia` | objeto anidado | `{ fecha_inicio: {valor, fuente, confianza}, fecha_fin: {valor, detalle_historial?, fuente, confianza}, renovacion_automatica_tacita: {valor: "Sí"\|"No", detalle, fuente, confianza}, termino_anticipado: {valor: "Sí"\|"No", detalle, fuente, confianza} }`. |
| `monto_total` | objeto | `{ valor: [ {moneda, valor, periodo} , ... ], nota, fuente, confianza }` — **siempre lista**, nunca texto libre, aunque solo haya una moneda/cifra (regla 4.8). Incluir tantas entradas como cifras distintas aparezcan en los documentos (tarifa recurrente, inferencias, cifras de ODC, etc.), cada una con su `periodo` explicando a qué corresponde. |
| `tipo_cambio` | objeto | `{ valor, detalle, fuente, confianza }`. `valor: null` si no está explícito — nunca calcular uno. |
| `productos_servicios_costo_unitario` | objeto | `{ descripcion_cantidad: [ {descripcion, cantidad, fuente, confianza} ], costo_unitario: [ {aplica_a, valor: [{moneda, valor, periodo}], fuente, confianza} ] }`. Nunca inferir cantidad a partir de frecuencia de facturación. |
| `metodo_pago` | objeto | `{ valor, fuente, confianza }`. |
| `niveles_servicio` | objeto | `{ valor, fuente, confianza }` — KPIs/SLAs comprometidos. |
| `clausula_incentivo_desempeno` | objeto | `{ valor: "Sí"\|"No", detalle, fuente, confianza }`. Ver distinción incentivo/multa/bono laboral (regla 4.3) — no reportar bono laboral obligatorio del proveedor hacia sus propios trabajadores como incentivo del cliente. |
| `clausula_multa_penalizacion` | objeto | `{ valor: "Sí"\|"No", detalle: [ {tipo, gatillante, monto, fuente} ], fuente, confianza }`. |
| `mecanismo_reajuste_indexacion` | objeto | `{ valor: "Sí"\|"No", detalle, fuente, confianza }`. No confundir con `tipo_cambio` (conversión entre monedas vs. indexación de precio en el tiempo). |
| `documentos_fuente` | array de strings | Todos los documentos leídos para armar este registro (contrato base, modificaciones, ODC, anexos), con fecha/nota breve de qué aporta cada uno. |
| `dossier_savingsradar` | objeto \| null | Ver subsección propia abajo. `null` si la carpeta del proveedor no tiene `Dossier SR/`. |
| `notas` | string | Hallazgos, alertas de inconsistencia (vigencia vs. monto, aritmética cruzada, RUT inválido), ambigüedades para revisión humana. Este es el campo donde vive el trabajo de auditoría — no lo dejes vacío si hubo algo raro. |
| `metadata_extraccion` | objeto \| null | Metadata propia del sub-agente que generó el registro (esquema usado, timestamp), si se conserva. |

### `dossier_savingsradar` — contenido del PPTX "Dossier SR", si existe

Muchas carpetas de proveedor (confirmado en Transporte de Personal) traen un
`Dossier SR/<Proveedor>_Negotiation_Dossier.pptx`. "SR" = **SavingsRadar** (confirmado por el pie
de página del propio PPTX: "Source: ... SavingsRadar Tool"), no "Solicitud de Renegociación". Es
un deck generado por una herramienta de BCG con cifras de oportunidad de negociación ya
cuantificadas para ese proveedor — no hay que inventarlas ni recalcularlas, solo extraerlas y
citarlas.

Igual que `auditoria_contratos.filas[]` en el esquema del microsite (ver
`../../savings-report/references/microsite_data_schema.md`), este objeto tiene una parte mecánica
y una curada:

```
dossier_savingsradar: {
  existe: boolean,                        // false si no hay carpeta "Dossier SR/" para este proveedor
  archivo: string | null,
  // --- MECÁNICO — derivable con scripts/parse_dossier_sr.py, leyendo la slide
  //     "Key facts & information: Overview of Supplier, opportunity & tactics" ---
  negociacion_oportunidad_pct: number | null,
  negociacion_oportunidad_monto_musd: number | null,
  spend_musd: number | null,
  supplier_name_en_dossier: string | null,  // para cruzar contra `proveedor` — si no coincide, alerta en `notas`
  power_balance_resumen: string | null,     // cita textual del dossier, no síntesis propia
  power_balance_score_overall: number | null,
  mdo_pct: number | null, mdo_addressable_spend_musd: number | null, mdo_monto_musd: number | null,
  target_pct: number | null, target_addressable_spend_musd: number | null, target_monto_musd: number | null,
  laa_pct: number | null, laa_addressable_spend_musd: number | null, laa_monto_musd: number | null,
  moneda_no_especificada: boolean,          // true por defecto — el dossier no dice si M$ es USD o CLP
  // --- CURADO — requiere que el subagente lea SWOT / Negotiation Strategy / Argumentation Map
  //     del mismo dossier y sintetice, igual que `hallazgo_principal_fila` en el microsite ---
  resumen_estrategia_negociacion: string,
  fuente: string,                          // ej. "Dossier SR (SavingsRadar Tool)"
  confianza: "alta" | "media" | "baja"
}
```

`scripts/parse_dossier_sr.py --pptx <ruta>` deriva todos los campos mecánicos (probado contra 2
dossiers reales de Transporte de Personal — FLEX y COMERCIAL SERPAN — mismo layout/frases ancla,
solo cambian los números). Deja `resumen_estrategia_negociacion` en `"TODO"`: el subagente que
procesa ese proveedor debe completarlo con juicio propio antes de devolver el registro final — no
dejarlo en `"TODO"` en la entrega, igual que con `hallazgo_principal_fila`/`compromiso_volumen_sla`
en `derive_audit_hints.py`.

`discount-finder` puede citar `mdo_pct`/`target_pct`/`laa_pct` como fuente legítima (no inventada)
de `estimated_savings_range` cuando este objeto existe — ver `../../discount-finder/references/palancas.md`.

### Regla de trazabilidad y confianza (obligatoria en todo campo no trivial)

Todo valor no trivial se envuelve como `{ valor, fuente, confianza }` (o variantes con `detalle`,
`existe`, etc. cuando el campo es más rico que un escalar). `confianza` es `alta`, `media` o
`baja`:
- `baja` automático si el dato viene de un documento OCR (PDF escaneado) o de un contrato con
  formato degradado/difícil de leer.
- Todo campo `confianza: baja` o con alerta de inconsistencia entra obligatoriamente en la muestra
  de verificación (ver sección de verificación en el playbook, cobertura 100% de esos casos + 20%
  o 3 contratos del resto, lo que sea mayor).

### Reglas no negociables (heredadas del playbook, resumidas — ver el original para el texto completo)

1. **No fabricar**: campo no explícito → `null` o `"No especificado en el contrato"`. Ninguna
   inferencia se presenta como dato directo.
2. **Inferencias permitidas, siempre etiquetadas** y citando la cláusula de origen.
3. **Incentivo ≠ multa ≠ bono laboral**: verificar el efecto económico real, no la palabra usada en
   el contrato.
4. **Consolidar base + modificaciones** en un solo registro; detectar y anotar inconsistencias
   vigencia-vs-monto cuando una modificación cambia alcance/plazo sin actualizar tarifa.
5. **Formato variable entre contratos**: buscar por tema/palabra clave (vigencia, precio, KPI,
   multa), no por número de cláusula fijo.
6. **OCR**: aplicar si el PDF no tiene texto nativo; verificar con grep de términos clave; marcar
   `confianza: baja`.
7. **RUT/RUN**: validar contra dígito verificador módulo 11 chileno (ver `scripts/validate_rut.py`
   en este skill). Si no valida, **no corregir adivinando** — registrar tal cual, `confianza: baja`,
   nota explícita.
8. **Montos multi-moneda**: siempre `[{moneda, valor, periodo}]`, nunca texto libre.
9. **Validación aritmética cruzada**: en todo contrato (no solo modificaciones), chequear si
   `cantidad × costo_unitario` reconcilia con `monto_total`. Si no reconcilia sin explicación
   documentada, es hallazgo/alerta en `notas` — no se fuerza a cuadrar.
10. **Normalización**: fechas siempre ISO (`AAAA-MM-DD`); números con punto decimal estándar.

## Formato de salida y versionado

- **JSON** (fuente primaria) + **Excel** (espejo, generado desde el JSON, nunca al revés; celdas
  `confianza: baja` resaltadas visualmente).
- **Versionado obligatorio**: antes de guardar, revisar la carpeta de salida de la categoría y usar
  versión = (versión más alta existente) + 1. Nunca sobrescribir ni borrar versiones anteriores.
  JSON y Excel de una misma corrida comparten número de versión.
- Actualizar la fila de la categoría en `TRACKER.md` (si existe, ver `playbooks/00_INDEX.md`)
  al terminar: columna Extracción, versión, fecha, y notas de hallazgos relevantes.

## Ver también

- `references/schema.json` — este mismo esquema en JSON Schema, usado por `validate_summary.py`.
- `scripts/validate_rut.py` — validador de dígito verificador chileno, reutilizable fuera de este
  skill.
- `playbooks/01_extraccion_contratos.md` (si existe en la carpeta de contratos del usuario)
  — texto completo y autoritativo de las reglas resumidas arriba.
