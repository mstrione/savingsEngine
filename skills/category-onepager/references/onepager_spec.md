# Esquema del JSON de especificación (`onepager_spec.json`)

Este JSON es el **puente** entre el JSON de `contract-ingest` (datos crudos,
trazables campo por campo) y el PPTX final. No es un mirror 1:1 del JSON de
contratos — es el resultado de aplicar la metodología ya acordada con el
usuario (ver `methodology_questions.md`): agrupaciones, conversión de moneda,
redondeos para el gráfico, y el texto de negocio (headline, callout, items de
la columna izquierda) que un LLM redacta a partir de los datos, no que copia
literalmente del JSON.

Por eso este paso lo hace Claude en el chat (leyendo el JSON de
`contract-ingest` + las respuestas del usuario a las preguntas de
metodología), y el script `scripts/build_onepager.py` solo renderiza — nunca
al revés (misma regla de "el Excel se genera del JSON, nunca al revés" que ya
aplica en `contract-ingest`, extendida acá: el PPTX se genera del spec, nunca
se edita a mano y después se reconstruye el spec).

## Campos obligatorios

| Campo | Tipo | Descripción |
|---|---|---|
| `categoria` | string | Nombre de la categoría (usado para el nombre de archivo si no hay `output_base_name`) |
| `headline` | string | Título "so-what" del slide — debe afirmar el hallazgo clave (ej. "Transporte de Personal: 7 proveedores concentran CLP 89.843 MM en 9 contratos; 2 vencen en 37 días"), no un título genérico tipo "Resumen de categoría" |
| `left_heading` | string | Encabezado de la columna izquierda (default: "Productos y servicios de la categoría") |
| `left_items` | array de `{icon, title, desc}` | Filas de la columna izquierda. `icon` = nombre de ícono disponible en `assets/icons/` del skill bcg-slide-generator (listar con `ls` si no estás seguro; si el nombre no existe el render va a fallar visiblemente, no silenciosamente) |
| `chart_heading` | string | Subtítulo sobre el gráfico (ej. "Monto total y % de participación por proveedor (CLP MM)") |
| `chart_categories` | array de string | Una entrada por proveedor/barra, **orden descendente por monto** (regla del playbook), con el `%` de participación incluido en el label (ej. `"FLEX SERVICIOS Y LOGISTICA (34%)"`) |
| `chart_values` | array de number | Mismo orden que `chart_categories` |
| `table_header` | array de string | Encabezados de la tabla de vencimientos (típico: Vencimiento, Proveedor(es), N° Contrato(s), Alerta) |
| `table_rows` | array de array de string | Filas, **ordenadas por fecha de vencimiento ascendente** |
| `callout` | string | Frase de una línea con el hallazgo accionable (concentración, vencimientos próximos, etc.) |
| `footnote` | string | Fuente + tipo(s) de cambio + método de estimación de montos no explícitos + disclaimer "Precio/Renta Total Máximo Estimado" — ver regla no negociable en `methodology_questions.md` |

## Campos opcionales

- `table_col_widths`: array de number (pulgadas), debe sumar ~8.15. Si se omite, se
  reparte el ancho en partes iguales entre las columnas.
- `chart_h`: alto del gráfico en pulgadas (default 1.55). Subilo si hay pocas
  barras y sobra espacio vertical; bajalo si hay muchos proveedores.
- `output_base_name`: nombre base del archivo de salida (sin fecha ni versión —
  el script agrega `_v<N>` automáticamente). Default: `<categoria>_OnePager`.
- `table_font_sz`: tamaño de fuente de la tabla (default 11).

## Ejemplo real (Transporte de Personal, adaptado de `build_slide_v2.py`)

```json
{
  "categoria": "Transporte de Personal",
  "headline": "Transporte de Personal: 7 proveedores concentran CLP 89.843 MM en 9 contratos; 2 vencen en 37 días",
  "left_items": [
    {"icon": "LargeTruck", "title": "Camionetas y camiones",
     "desc": "Salfa Rent: 81 camionetas (contrato 212, Elqui) + 6 camiones de apoyo, contrato 693, Huasco"}
  ],
  "chart_categories": ["FLEX SERVICIOS Y LOGISTICA (34%)", "SOC. INVERSIONES LAS VEGAS (25%)"],
  "chart_values": [30504, 22532],
  "table_header": ["Vencimiento", "Proveedor(es)", "N° Contrato(s)", "Alerta"],
  "table_rows": [["31-oct-2026", "SALFA RENT (x2 contratos)", "4643003212 / 3693", "Vence en 37 días"]],
  "callout": "Flex + leasing Las Vegas concentran 59% del gasto de la categoría...",
  "footnote": "Fuente: Extracción de contratos v3. UF=$41.008,10 y USD/CLP=$942,89 al 24-sep-2026. *Salfa Rent: estimado a partir de..."
}
```

## Ver también

- `../SKILL.md` — flujo completo (incluye el paso de refinamiento metodológico y la QA obligatoria).
- `methodology_questions.md` — preguntas que hay que resolver con el usuario antes de armar este JSON.
