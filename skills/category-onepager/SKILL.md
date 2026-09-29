---
name: category-onepager
description: Construye el one-pager PPTX de una categoría de contratos (gráfico de monto/participación por proveedor, calendario de vencimientos, hallazgo "so-what" en el título y callout) a partir del JSON consolidado de `contract-ingest`, replicando el método real de TAIL CUTTER (`playbooks/02_onepager_categoria.md`) sobre el motor del skill `bcg-slide-generator`. Úsalo cuando el usuario pida "el one-pager de [categoría]", "arma el perfil de categoría", "el slide de proveedores de [categoría]", o "necesito el resumen ejecutivo de contratos en PPTX". Requiere haber corrido `contract-ingest` al menos una vez para esa categoría. No confundir con `savings-report` (ese es el reporte HTML de oportunidades de descuento, no el one-pager de perfil de categoría).
---

# Category One-Pager

Segundo paso posible del pipeline (paralelo a `discount-finder`, no depende de él): convierte el
JSON de `contract-ingest` en el slide PPTX de perfil de categoría — el mismo formato que ya se usó
a mano para Transporte de Personal.

Este skill **envuelve** `bcg-slide-generator`, no lo reemplaza: usa su clase `BCGDeck` (plantilla
BCG, íconos, gráficos y tablas nativas) por debajo. Antes de usar este skill conviene tener leído
`bcg-slide-generator/SKILL.md` una vez, aunque no hace falta invocarlo aparte — `scripts/build_onepager.py`
ya hace el `import` directamente.

## 0. Regla de activación (no negociable)

Igual que en `contract-ingest`: una corrida nueva (o re-generación) del one-pager **solo empieza si
el usuario lo pide explícitamente**. Si solo pregunta algo sobre un one-pager ya generado (ej. "¿qué
proveedor tiene más participación?"), respondé mirando el PPTX/JSON existentes — no dispares una
regeneración.

## 1. Prerrequisito y detección de playbook propio

- Confirmá que existe el JSON de `contract-ingest` para esa categoría
  (`<categoria>_contratos_v<N>.json`). Si no existe, avisale al usuario que hay que correr
  `contract-ingest` primero.
- Si `contracts_root` tiene un `playbooks/02_onepager_categoria.md` real (mismo patrón que
  `contract-ingest` paso 1), es la fuente de verdad — leelo completo y priorizalo sobre las reglas
  resumidas en este SKILL.md. Revisá también `playbooks/TRACKER.md` para saber si esta categoría ya
  tiene una versión previa del one-pager y qué cambió entre versiones (para no repetir decisiones ya
  tomadas, ej. el tipo de cambio usado la vez anterior).

## 2. Refinamiento metodológico obligatorio (antes de tocar el PPTX)

**No construyas el spec ni el PPTX todavía.** El playbook real exige resolver primero, en el chat,
las decisiones que cambian los números que van a aparecer en el gráfico: consolidación de moneda,
tratamiento de proveedores multi-contrato, contratos atípicos, método de estimación de montos no
explícitos, y la distinción "flota no especificada" vs. inventar una cantidad.

Ver `references/methodology_questions.md` para las preguntas exactas — hacelas todas (agrupadas en
un mensaje) antes de seguir. Si el usuario ya las resolvió en una corrida anterior de esta misma
categoría (ver `TRACKER.md`), confirmá que siguen aplicando en vez de re-preguntar desde cero.

## 3. Redactar el JSON de especificación (`onepager_spec.json`)

Con la metodología acordada, construí el spec siguiendo `references/onepager_spec.md` (esquema
completo + ejemplo real). Puntos que no son opcionales:

- **Orden del gráfico:** proveedores de mayor a menor monto, con el `%` de participación en el
  label de cada barra.
- **Orden de la tabla de vencimientos:** fecha ascendente (el próximo vencimiento arriba).
- **Headline "so-what":** el título tiene que afirmar el hallazgo (concentración + vencimientos
  próximos), no ser un título genérico. Ejemplo real: *"Transporte de Personal: 7 proveedores
  concentran CLP 89.843 MM en 9 contratos; 2 vencen en 37 días"*.
- **Footnote:** fuente + tipo(s) de cambio usados (con fecha) + método de estimación de montos no
  explícitos (marcados con `*`) + el disclaimer "Precio/Renta Total Máximo Estimado" (techo
  referencial, no obligación de pago fija) cuando aplique.
- Los montos y textos del spec deben ser trazables 1:1 al JSON de `contract-ingest` — este paso
  traduce y redacta, no inventa cifras nuevas.

Guardá este JSON en la carpeta de salida de la categoría (ej. junto al PPTX anterior si existe),
versionado igual que los demás artefactos del pipeline.

## 4. Generar el PPTX

Los scripts de este skill se invocan con rutas relativas a la **carpeta propia de este skill** (tu
"Base directory for this skill"), no a `contracts_root` ni a ningún cwd asumido:

```bash
python3 scripts/build_onepager.py --json <ruta_al_spec.json>
```

El script:
- busca automáticamente dónde está montado `bcg-slide-generator` en esta sesión/instalación (su
  ruta cambia entre sesiones — nunca la hardcodees ni asumas la de una corrida anterior); si no lo
  encuentra, pasale `--skill-dir <ruta>` con la ruta real;
- copia (si no están ya) `bcg_template.py`/`pptx_utils.py`/`assets/` de ese skill a un directorio de
  trabajo local junto al `--json` (`_onepager_build/`), para no depender de imports entre plugins;
- arma el slide único con layout `d_title_only`: columna izquierda de íconos+texto (alto de cada
  fila estimado automáticamente para que no se superponga ni desborde), columna derecha con
  gráfico de barras horizontal + tabla de vencimientos, callout full-width, y footnotes en la zona
  exenta de QA (y≥6.60);
- **nunca sobrescribe una versión anterior** — si no pasás `--out`, calcula automáticamente
  `<categoria>_OnePager_v<N+1>.pptx` en el mismo directorio del spec.

Si el script imprime una advertencia de que la columna izquierda o la tabla se pasan del límite
vertical, no la ignores — reducí `left_items`/filas de tabla o acortá texto y volvé a correr antes
de pasar a la QA visual.

## 5. QA obligatoria antes de entregar (doble)

1. **QA de coherencia literal:** cada cifra y afirmación del PPTX (headline, callout, footnote,
   tabla) tiene que poder rastrearse al JSON de `contract-ingest` y a las decisiones metodológicas
   del paso 2. Si algo no cuadra, es un bug del spec, no del script de render.
2. **QA visual:** convertí a imagen y mirala (ver la sección "Converting to Images" / "Visual QA"
   de `bcg-slide-generator` y `pptx` — mismo procedimiento: `soffice.py --convert-to pdf` +
   `pdftoppm`). Prestá atención especial a: texto cortado en la columna izquierda (la estimación de
   alto es una aproximación, no una garantía), la tabla de vencimientos desbordando el límite
   y=6.05, y contraste del callout.

Recién después de esta doble QA, entregá el archivo. Si existe `playbooks/TRACKER.md`, actualizá la
fila de la categoría (versión de one-pager, fecha, metodología usada) al terminar.

## Ver también

- `references/methodology_questions.md` — preguntas obligatorias de refinamiento metodológico.
- `references/onepager_spec.md` — esquema completo del JSON de spec + ejemplo real.
- `playbooks/02_onepager_categoria.md` — playbook fuente (prioridad sobre este SKILL.md si
  existe una copia real en `contracts_root`).
- `../contract-ingest/SKILL.md` — de dónde sale el JSON de entrada.
- Skill `bcg-slide-generator` (instalado aparte, su ruta de mount varía por sesión) — motor de
  renderizado (BCGDeck); no hace falta invocarlo aparte, `scripts/build_onepager.py` ya lo importa
  directamente (ver auto-detección de `--skill-dir` arriba).
