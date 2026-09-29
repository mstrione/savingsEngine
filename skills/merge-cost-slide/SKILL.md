---
name: merge-cost-slide
description: Inyecta la única slide de "Estructura de costos e índices" (con gráficos nativos de PowerPoint, no imágenes) dentro del one-pager PPTX final de una categoría, preservando 100% del formato y los gráficos — replicando el procedimiento OOXML manual de TAIL CUTTER (`playbooks/03_merge_slide_costos_onepager.md`). Úsalo cuando el usuario pida "mergea la slide de costos en el one-pager de [categoría]", "agrega la slide de cost drivers al perfil de [categoría]", o "pega los gráficos de estructura de costos en el one-pager". No confundir con `category-onepager` (ese genera el one-pager desde cero; este skill agrega una slide ya existente a un one-pager ya existente). Tercera y última etapa del pipeline TAIL CUTTER — requiere que ya exista el one-pager de la Etapa 2.
---

# Merge Cost Slide

Tercer y último paso posible del pipeline TAIL CUTTER (ver `00_INDEX.md`): toma la slide de
"Estructura de costos e índices" de una categoría (1 slide, 2 gráficos nativos de PowerPoint) y la
agrega como slide adicional al one-pager final de esa misma categoría.

Este skill **es** la traducción a código de `playbooks/03_merge_slide_costos_onepager.md` —
esa es la fuente de verdad sobre el procedimiento; este SKILL.md solo resume cuándo y cómo invocar
el script. Si `contracts_root` tiene su propia copia de ese playbook, priorizala sobre este SKILL.md
si difieren en algún detalle.

## 0. Regla de activación (no negociable)

Igual que las otras dos etapas: esta operación **solo empieza si el usuario lo pide explícitamente**
en esta conversación — nunca dispara sola porque la Etapa 2 (one-pager) recién terminó. Si el
usuario solo pregunta sobre un merge ya hecho (ej. "¿la slide de costos ya está en el one-pager de
Transporte de Personal?"), respondé consultando el `.pptx` existente (contar slides con
`python-pptx`) — no dispara un merge nuevo ni modifica el archivo. Ante la duda de si conviene
sobrescribir el one-pager final de una categoría, preguntar antes de reemplazar.

## 1. Por qué esto no es un "copiar slide" genérico

`python-pptx` no soporta copiar slides con gráficos nativos (`c:chart`) entre presentaciones
distintas — pierde los charts o rompe relaciones. LibreOffice/UNO tampoco es confiable para fidelidad
exacta de charts y estilos entre plantillas distintas. Por eso el playbook (y este skill) manipulan
el paquete OOXML directamente: copian la cadena completa de dependencias
(`slide → slideLayout → slideMaster → theme`, y `slide → chart → workbook embebido`) al paquete
destino, renumerando IDs para no colisionar con las partes que ya existen ahí.

Esto es más frágil que una operación de copiado normal — el propio playbook lo marca como el paso
que requiere más cuidado de los tres. Tratá cada corrida como algo que necesita la doble validación
del paso 3, no como un script de "correr y listo".

## 2. Correr el merge

Necesitás dos archivos ya existentes:
- **Origen** — el pptx de 1 sola slide con los gráficos (típicamente en una carpeta
  `Estructura de costos e índices/` dentro de la categoría).
- **Destino** — el one-pager de esa misma categoría (el que generó `category-onepager`, Etapa 2).

El script se invoca con ruta relativa a la **carpeta propia de este skill** ("Base directory for
this skill" en tu contexto), no a `contracts_root`:

```bash
python3 scripts/merge_cost_slide.py \
    --src "<ruta al Cost_Driver_Development_<Categoria>.pptx>" \
    --dest "<ruta al one-pager de la categoría>"
```

El script (requiere `python-pptx` instalado, solo para su propia validación estructural final):

- copia la cadena theme → slideMaster (recortado a un solo `slideLayout`, no los ~99 de la
  plantilla completa) → slideLayout, con `.rels` propios;
- copia la slide, eliminando el marcador oculto de thinkcell (`p:graphicFrame` con
  `name="think-cell data - do not delete"`) y cualquier `<p:custDataLst>` (metadata de tags, sin
  impacto visual);
- copia cada chart nativo referenciado + su workbook embebido (`.xlsb`/`.xlsx`) + sus partes de
  color/estilo si existen, registrando todo en `[Content_Types].xml`;
- registra la nueva slide y su slideMaster en `presentation.xml`/`presentation.xml.rels`;
- **nunca sobrescribe el destino** — escribe siempre a un archivo nuevo, versionado
  automáticamente como `<destino>_merged_v<N>.pptx` si no pasás `--out`;
- corre una validación estructural propia con `python-pptx` (conteo de slides, conteo de charts en
  la slide nueva) e imprime cualquier `⚠️`/`❌` para relaciones o tipos que no supo manejar
  explícitamente — **no ignores esas advertencias**, son la señal de que algo en ese pptx en
  particular no calza con el caso típico (2 charts, sin relaciones exóticas) y necesita revisión
  manual antes de seguir.

## 3. QA obligatoria antes de reemplazar el original (doble, siempre)

El script deja esto explícito en su propio output — no es opcional:

1. **Estructural** (ya la corre el script, pero conviene confirmar vos también): slides del
   resultado = slides del destino original + 1; la slide nueva tiene los charts esperados.
2. **Visual:** convertí el resultado a PDF con LibreOffice headless
   (`scripts/office/soffice.py --headless --convert-to pdf` del skill `pptx`, mismo wrapper que usan
   `bcg-slide-generator`/`category-onepager` — bare `soffice` puede colgarse en este entorno) y
   rasterizá con `pdftoppm`. Mirá específicamente: que ambos gráficos rendericen con datos y estilos
   reales (no placeholders en blanco ni mensajes de archivo dañado), que no haya overlap ni texto
   cortado, y que las slides preexistentes del one-pager (sobre todo la primera) no se hayan alterado.

Recién después de esta doble QA, reemplazá el one-pager original de la categoría por el resultado
(paso 7 del playbook) y actualizá la fila de la categoría en `playbooks/TRACKER.md` (columna Merge
Slide Costos + fecha), si ese archivo existe.

## 4. Trampas conocidas (heredadas del playbook — no las repitas)

- No asumas que un archivo con el mismo nombre (ej. `slideLayout30.xml`) es idéntico entre origen y
  destino — pueden compartir número de archivo sin ser la misma plantilla. El script ya maneja esto
  copiando y renumerando desde cero, nunca reutilizando un archivo del destino solo porque el nombre
  coincide.
- El marcador de thinkcell oculto no es el gráfico visible — es un objeto OLE de bookkeeping, seguro
  de eliminar (el script ya lo hace).
- Si el pptx origen tiene más de 1 slide, el script aborta explícitamente — este skill asume el
  patrón real de "Estructura de costos e índices" (siempre 1 slide). Si aparece un caso con más de
  una, es una variante nueva que hay que evaluar a mano, no forzar por el script.
- Si `mcp__cowork__present_files` falla con "not accessible" al entregar el resultado, no es
  bloqueante — confirmá igual vía la validación estructural/visual y avisale al usuario por texto que
  el archivo quedó guardado correctamente.

## Ver también

- `playbooks/03_merge_slide_costos_onepager.md` — playbook fuente de verdad, con el detalle
  completo de cada paso OOXML y el checklist rápido.
- `scripts/merge_cost_slide.py` — implementación; corré `--help` para ver todas las opciones
  (`--out`, `--work-dir`).
- `../category-onepager/SKILL.md` — Etapa 2, genera el one-pager que este skill usa como destino.
- Skill `pptx` (instalado aparte) — de ahí sale el wrapper `scripts/office/soffice.py` usado en la
  QA visual.
