---
name: contract-ingest
description: Lee contratos y adendas de proveedores (carpetas por categoría/proveedor: PDFs de contrato, adendas, órdenes de compra, formularios, dossiers) y produce un JSON consolidado por categoría (esquema v3, con trazabilidad fuente/confianza) más un Excel espejo y un resumen HTML (KPIs, vencimientos próximos, tabla filtrable, botón de descarga del Excel). Dos modos: "iniciar" (Modo A, desde cero) y "refrescar" (Modo B, incremental por mtime/tamaño). Paso inicial y repetible del Savings Engine — úsalo cuando pidan "clasificar contratos", "analizar los contratos", "extraer los contratos", "ingestar contratos nuevos", "leer la carpeta de contratos", "refrescar el análisis de contratos", "actualizar los contratos que cambiaron", o "ver si hay contratos nuevos". Usa subagentes en paralelo (uno por proveedor) y consolida en un único archivo versionado. El atajo "/inicio"/"/init" vive en el skill `menu`, que muestra las 6 opciones y delega en Modo A de este skill.
---

# Contract Ingest

Primer paso del pipeline de Savings Engine: convierte carpetas de contratos (PDF/DOCX/XLSX/PPTX)
en un JSON consolidado por categoría (+ Excel espejo), listo para que `discount-finder` busque
palancas de descuento. Implementa el esquema v3 de `references/schema.md`, que en la práctica es un
mirror del proceso real "TAIL CUTTER" que Mauro ya corre manualmente sobre estas mismas carpetas.

Tiene dos modos independientes, ambos documentados en este mismo archivo:

| | Modo A — Iniciar (§1-5) | Modo B — Refrescar (§6) |
|---|---|---|
| Cuándo | Primera vez para esa carpeta, o el usuario pide explícitamente reprocesar todo desde cero | Ya corrió Modo A al menos una vez; el usuario quiere detectar y reprocesar solo lo que cambió |
| Alcance | Todos los proveedores de `contracts_root` | Solo los proveedores con archivos nuevos/modificados (via `.savings-engine/manifest.json`) |
| Disparado por | `menu` (`/inicio`/`/init`) o pedido directo ("clasificá los contratos") | Pedido directo ("refrescá el análisis de contratos") o desde `menu` |

## 0. Regla de activación (no negociable)

Igual que el playbook real en el que se basa este esquema: una corrida nueva de extracción (inicial,
re-extracción completa, o un refresh incremental) **solo empieza si el usuario lo pide
explícitamente** en esta conversación. Si el usuario solo pregunta sobre una extracción ya hecha
(ej. "¿qué RUT tiene el proveedor X?"), respondé consultando el JSON ya generado — no dispares una
re-extracción ni sobrescribas archivos. Ante la duda, preguntar antes de generar o sobrescribir.

Si el usuario llega acá vía el skill `menu` (`/inicio`/`/init`), la elección de modo ya está resuelta
por lo que haya elegido ahí — no vuelvas a preguntar "modo A o B".

## 1. Primer uso: definir la carpeta de contratos y detectar playbooks propios

Este skill está pensado para instalarse **una sola vez** (como plugin de Cowork) y usarse después en
cualquier carpeta de contratos que el usuario conecte — nunca asumas que `contracts_root` es la
carpeta donde vive este mismo skill (una vez instalado como plugin, `skills/` queda montado en una
ruta de solo lectura, separada de la carpeta de trabajo del usuario). Todo el estado de esta
skill — config y outputs — vive **dentro de `contracts_root`**, nunca al lado de `skills/`.

- **Valor por defecto de `contracts_root`:** la carpeta que el usuario tiene conectada en esta
  sesión de Cowork. Si su contenido de primer nivel ya tiene pinta de `Categoría/Proveedor/archivos`,
  usala directo sin preguntar nada.
- **Antes de preguntar nada, revisá si ya existe** `<contracts_root>/.savings-engine/config.json`
  (probá primero con `contracts_root` = la carpeta conectada). Si existe y tiene `contracts_root`,
  usalo directo — pero confirmá con el usuario si quiere apuntar a otra carpeta antes de correr (por
  si está re-procesando una carpeta distinta a la de la última vez).
- **Si no existe, o la carpeta conectada no tiene pinta de carpeta de contratos:** preguntale al
  usuario la ruta absoluta de la carpeta raíz donde están sus contratos, organizada como
  `Categoría/Proveedor/archivos`. Guardala en `<contracts_root>/.savings-engine/config.json` con
  esta forma:

  ```json
  {
    "contracts_root": "/ruta/absoluta/de/la/carpeta/de/contratos",
    "output_root": "/ruta/absoluta/de/la/carpeta/de/contratos/output"
  }
  ```

  Este archivo queda **dentro de la carpeta de contratos del usuario**, no en el repo/plugin — así
  cada carpeta de contratos que el usuario conecte tiene su propio estado, y no depende de en qué
  máquina ni con qué cuenta se instaló el plugin.

- **Detectá si `contracts_root` tiene un `playbooks/01_extraccion_contratos.md` como hermano de
  las carpetas de categoría.** Si existe, es la fuente de verdad — leelo completo y seguí sus
  reglas literalmente, incluso si difieren en detalle de `references/schema.md` (que es el
  fallback genérico de este skill). Si además existe un `TRACKER.md` en esa misma carpeta
  `playbooks/`, leelo para saber si la categoría ya fue corrida antes y con qué versión, antes de
  asumir que esta es una corrida inicial.

Los scripts de este skill (paso 2 en adelante) se invocan con rutas relativas a la **carpeta propia
de este skill** (la que ves como "Base directory for this skill" en tu contexto), nunca relativas a
`contracts_root` ni a ninguna carpeta de trabajo — eso es lo que permite que el mismo plugin
funcione sin cambios en la carpeta de contratos de cualquier usuario.

## 2. Escanear la estructura

Corré el script bundleado para listar categorías, proveedores y archivos sin tener que leer
carpeta por carpeta manualmente:

```bash
python3 scripts/scan_providers.py --root "<contracts_root>"
```

Esto te da, por categoría, la lista de carpetas de proveedor con sus archivos. Usalo para:
- Decidir cuántos subagentes lanzar (uno por proveedor).
- Detectar `loose_files` (archivos sueltos en la categoría, no asociados a un proveedor) y
  preguntarle al usuario qué hacer con ellos en vez de ignorarlos silenciosamente.

## 3. Procesar en paralelo, un subagente por proveedor

Para cada proveedor detectado, lanzá un subagente (Task/Agent) con instrucciones autocontenidas:

- Rutas absolutas de todos los archivos de esa carpeta de proveedor.
- El contenido de `references/schema.md` (o del playbook real si existe, ver paso 1) para que
  sepa exactamente qué campos producir y con qué estructura de trazabilidad (`fuente`/`confianza`).
- Las reglas no negociables: no fabricar valores (campo no explícito → `null`), validar el RUT con
  `scripts/validate_rut.py`, estructurar montos siempre como `[{moneda, valor, periodo}]`, y
  chequear la reconciliación aritmética `cantidad × costo_unitario` vs. `monto_total`.
- Que devuelva **un registro de contrato consolidado** (base + modificaciones + anexos + ODC en un
  solo objeto, no un objeto por documento) — el subagente no escribe el archivo final directamente,
  devuelve el registro para que el coordinador lo junte con los demás.

Lanzá los subagentes de a lotes razonables (5-8 en paralelo) en vez de todos a la vez si hay
muchos proveedores, para no saturar el contexto ni perder trazabilidad de errores.

Cada subagente debe leer **todos** los documentos de su proveedor (contrato original +
modificaciones/adendas + ODC + formularios + dossier de negociación si existe) antes de devolver
el registro — el objetivo es capturar el historial completo, no solo el contrato inicial.

Si la carpeta del proveedor tiene un `Dossier SR/<Proveedor>_Negotiation_Dossier.pptx` ("SR" =
SavingsRadar, no "Solicitud de Renegociación"), el subagente debe llenar `dossier_savingsradar`
(ver `references/schema.md`) en dos partes: corré primero
`python3 scripts/parse_dossier_sr.py --pptx "<ruta al pptx>"` para los
campos mecánicos (cifras de Negotiation Opportunity, Spend, MDO/Target/LAA, power balance), y
completá vos mismo `resumen_estrategia_negociacion` leyendo las slides de SWOT / Negotiation
Strategy / Argumentation Map del mismo dossier — el script deliberadamente no lo deriva, no lo
dejes en `"TODO"` en el registro final.

## 4. Consolidar en un único JSON de categoría (versionado)

Los subagentes corren en paralelo por velocidad, pero el resultado final es **un solo archivo por
categoría**, nunca JSONs sueltos por proveedor:

1. Juntá los registros devueltos por todos los subagentes en un único objeto
   `{ metadata, contratos: [...] }` (ver `references/schema.md`). Si distintos subagentes usaron
   convenciones de nombres de campo levemente distintas, normalizalas a las claves canónicas del
   esquema y dejá constancia de qué se normalizó en `metadata.nota_normalizacion` — no reinterpretes
   ni cambies los valores extraídos, solo las claves.
2. Antes de guardar, revisá la carpeta de salida de la categoría (`Extracciones/` si existe ese
   patrón dentro de `contracts_root`, o `<contracts_root>/output/` por defecto — nunca una carpeta
   `output/` al lado de `skills/`) y determiná la próxima versión = versión más alta existente + 1.
   **Nunca sobrescribas ni borres versiones anteriores.**
3. Guardá `<categoria>_contratos_v<N>.json` y generá el Excel espejo a partir de ese JSON (nunca al
   revés):
   ```bash
   python3 scripts/build_excel_mirror.py --json <ruta_al_json_v<N>>
   ```
   Esto resalta automáticamente las celdas con `confianza: baja`.
4. Corré el validador liviano sobre el archivo consolidado:
   ```bash
   python3 scripts/validate_summary.py --file <ruta_al_json_v<N>>
   ```
   Los errores son bloqueantes (estructura rota); las advertencias (ej. trazabilidad floja, RUT
   que no valida) son señales para la revisión muestral del paso 5, no motivo automático de
   reprocesar.
5. **Solo si esta corrida cubrió `contracts_root` completo** (Modo A, no un refresh parcial de Modo
   B): guardá la línea de base para poder refrescar más adelante, corriendo
   ```bash
   python3 scripts/build_manifest.py --root "<contracts_root>"
   ```
   Esto pisa `<contracts_root>/.savings-engine/manifest.json` a propósito (es un snapshot vivo del
   estado de archivos, no un artefacto versionado — ver §6). Sin este paso, "refrescar análisis de
   contratos" no tiene línea de base contra la cual comparar.
6. Generá el resumen HTML de la corrida (KPIs, vencimientos próximos, tabla filtrable) con botón de
   descarga del Excel espejo del paso 3:
   ```bash
   python3 scripts/build_ingest_summary.py --json <ruta_al_json_v<N>> --excel <ruta_al_xlsx_v<N>>
   ```
   Esto genera `<categoria>_contratos_v<N>_resumen.html` junto al JSON y al Excel (mismo directorio
   de salida — el botón de descarga del HTML linkea al `.xlsx` por nombre de archivo relativo, así
   que los tres archivos tienen que quedar juntos). Igual que el Excel, este resumen se genera
   siempre a partir del JSON ya validado — no agrega ni reinterpreta datos, solo los agrega/filtra
   para lectura rápida. Compartí este HTML con el usuario como el resumen principal de la corrida
   (el Excel queda como el detalle completo con trazabilidad fuente/confianza).

## 5. Verificación antes de entregar

- Revisión muestral (idealmente con un subagente independiente) contra el texto original: **100%**
  de los contratos con algún campo `confianza: baja` o alerta de inconsistencia, más una muestra
  aleatoria de 20% del resto (o 3 contratos, lo que sea mayor).
- Confirmar que los "No especificado en el contrato" realmente no aparecen en el texto (evitar
  falsos negativos).
- Si existe `TRACKER.md` en `playbooks/`, actualizar la fila de la categoría (Extracción, versión,
  fecha, notas de hallazgos) al terminar — sin tocar las filas de otras categorías.
- Entregale al usuario el HTML de resumen generado en el paso 6 (además de un mensaje corto en el
  chat con lo mismo en texto plano: cuántos proveedores se procesaron, qué versión quedó, y qué
  hallazgos/alertas quedaron en `notas` para revisar) — no hace falta que redacte un resumen aparte,
  el HTML ya cubre esa necesidad con el detalle navegable y el link de descarga a Excel.

Este paso (Modo A) es repetible: si el usuario vuelve a pedir "clasificá los contratos" / "iniciá
desde cero" sobre una carpeta que ya tiene versiones previas, seguí siendo un reprocesamiento
completo — el archivo de salida sigue siendo uno por categoría y la corrida nueva genera `_v<N+1>`,
nunca reemplaza `_v<N>`. Si lo que quiere es reprocesar solo lo que cambió, eso es Modo B (§6), no
una re-corrida de Modo A.

## 6. Modo B — Refrescar análisis de contratos (incremental)

Convierte "¿hay algo nuevo o modificado en la carpeta de contratos?" en un reprocesamiento acotado
— solo los proveedores afectados, no la categoría entera.

### 6.0 Prerrequisito

Necesita que Modo A haya corrido al menos una vez sobre esta `contracts_root` (es decir, que exista
`<contracts_root>/.savings-engine/manifest.json`, generado en el paso 5 de Modo A). Si no existe,
avisale al usuario que no hay línea de base y que primero hay que correr "iniciar análisis de
contratos" (Modo A) sobre toda la carpeta.

### 6.1 Detectar qué cambió

```bash
python3 scripts/diff_manifest.py --root "<contracts_root>"
```

Esto compara mtime+tamaño de cada archivo contra el manifest guardado y devuelve, agrupado por
categoría → proveedor: `affected_providers` (con sus archivos nuevos/modificados/eliminados),
`new_categories` (carpetas de categoría que no existían antes), y `loose_file_changes` (cambios en
archivos sueltos de categoría, sin carpeta de proveedor). Si `has_changes` es `false`, decíselo al
usuario y no hagas nada más — no regeneres nada solo por haber corrido el diff.

Un archivo "eliminado" (`deleted_files`) es una señal para que el usuario revise manualmente — no
implica borrar nada del JSON consolidado ni sacar al proveedor; usalo solo para avisar.

### 6.2 Mostrar el alcance antes de reprocesar

Antes de lanzar subagentes, mostrale al usuario la lista de proveedores afectados (categoría +
nombre + motivo, viene armado en `affected_providers[].reason`) — es información nueva que el
usuario no pidió explícitamente ver, y como esto puede tocar varias categorías a la vez conviene que
confirme el alcance antes de que el coordinador dispare trabajo.

### 6.3 Reprocesar solo los proveedores afectados

Igual que el paso 3 de Modo A (subagente por proveedor, mismas reglas no negociables de
trazabilidad/RUT/reconciliación aritmética y el mismo tratamiento de `dossier_savingsradar`), pero
**solo para los proveedores en `affected_providers`** — no relances subagentes para proveedores sin
cambios, esa es justamente la ganancia de Modo B sobre repetir Modo A.

### 6.4 Fusionar en una nueva versión del JSON de categoría

Por cada categoría con proveedores afectados:

1. Cargá el `<categoria>_contratos_v<N>.json` más reciente completo.
2. Reemplazá, dentro de `contratos[]`, únicamente los registros de los proveedores reprocesados
   (match por `numero_contrato`/`rut_run_proveedor.valor`, según cómo identifique cada registro el
   esquema — ver `references/schema.md`); dejá el resto de los registros exactamente como estaban,
   sin re-normalizar ni retocar.
3. Si `new_categories` o un proveedor nuevo aparece dentro de una categoría existente, agregalo como
   registro nuevo en vez de "reemplazar" nada.
4. Guardá como `_v<N+1>` (nunca pisa `_v<N>` — misma regla que Modo A), regenerá el Excel espejo
   (`build_excel_mirror.py`) y corré `validate_summary.py` sobre el archivo nuevo completo.
5. Regenerá también el resumen HTML de esa categoría con `build_ingest_summary.py` (mismo comando
   que el paso 6 de Modo A, apuntando al `_v<N+1>.json` y `.xlsx` nuevos) — el resumen tiene que
   reflejar siempre la última versión, no la de antes del refresh.

### 6.5 Cerrar el ciclo

1. Volvé a correr `build_manifest.py --root "<contracts_root>"` para que el snapshot quede al día
   (si no hacés esto, el próximo refresh va a volver a detectar como "cambiados" los mismos archivos
   que ya procesaste ahora).
2. Verificación muestral: acá sí conviene **100%** de los proveedores reprocesados (no una muestra
   parcial, ya que el volumen de un refresh suele ser chico) — mismo criterio de "confianza baja"
   que en el paso 5 de Modo A.
3. Si existe `TRACKER.md`, actualizá solo las filas de las categorías tocadas.
4. Entregale al usuario el/los HTML de resumen regenerados en el paso 6.4.5 (uno por categoría
   tocada), más un mensaje corto en el chat: qué proveedores se reprocesaron y por qué (nuevo
   archivo / modificado), qué versión quedó por categoría, y qué quedó para revisión manual (ej.
   archivos eliminados).

## Ver también

- `references/schema.md` — descripción completa de cada campo del JSON de salida, y la regla de
  que un `playbooks/01_extraccion_contratos.md` real (si existe en `contracts_root`) manda por
  sobre este esquema.
- `references/schema.json` — mismo esquema en formato JSON Schema (usado por `validate_summary.py`).
- `scripts/validate_rut.py` — validador de dígito verificador chileno (módulo 11).
- `scripts/build_excel_mirror.py` — genera el Excel espejo desde el JSON, resaltando `confianza: baja`.
- `scripts/build_ingest_summary.py` — genera el resumen HTML (Modo A paso 6, Modo B paso 6.4.5) a
  partir del JSON + el Excel ya generado, usando `assets/ingest_summary_template.html`.
- `assets/ingest_summary_template.html` — template genérico del resumen HTML (no editar por
  categoría — la data se inyecta vía `build_ingest_summary.py`, mismo patrón que
  `../savings-report/assets/report_template.html`).
- `scripts/parse_dossier_sr.py` — deriva los campos mecánicos de `dossier_savingsradar` desde el
  PPTX "Dossier SR" de cada proveedor.
- `scripts/build_manifest.py` — snapshot de mtime+tamaño por archivo (Modo A, paso 5). Único archivo
  de este skill pensado para sobrescribirse siempre, igual que `datos.js` en `savings-report`.
- `scripts/diff_manifest.py` — compara el snapshot actual contra el manifest guardado (Modo B, §6.1).
- `../menu/SKILL.md` — dueño del atajo literal `/inicio`/`/init`; delega en Modo A de este skill.
