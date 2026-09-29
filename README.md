# Savings Engine — plugin de Cowork

Plugin de Cowork para analizar contratos de proveedores y detectar oportunidades de descuento /
renegociación, con validación humana antes de cualquier envío de correo.

## Pipeline (7 skills)

```
0.  menu              → punto de entrada: "/inicio"/"/init" o "qué opciones tengo" → muestra las 6 opciones de abajo
1.  contract-ingest   → Modo A "iniciar" (desde cero) y Modo B "refrescar" (incremental por mtime/tamaño)
2.  discount-finder   → cruza el JSON contra una taxonomía de palancas → oportunidades detectadas
2b. category-onepager → (opcional, paralelo) one-pager PPTX por categoría
2c. merge-cost-slide  → (opcional) agrega slide de costos al one-pager
3.  savings-report    → Modo A: reporte HTML de oportunidades · Modo B: microsite interactivo por categoría
4.  discount-email    → redacta un borrador de correo por proveedor → queda en Outlook (Draft) — HITL
```

Cada paso es un skill independiente en `skills/`. Se disparan por lenguaje natural en el chat de
Cowork (no son comandos de shell), o eligiendo una opción del menú — ver "Las 6 opciones del menú"
más abajo.

## Requisitos antes de arrancar

1. **Plugin instalado en Cowork** — ver "Cómo instalar el plugin" abajo. Se instala **una sola
   vez**; después funciona en cualquier carpeta que conectes, no solo en este repo.
2. **Conector de Outlook** conectado en la sesión (lo necesita `discount-email` para crear el
   borrador). Sin esto, ese último paso no puede dejar el draft creado.
3. **Una carpeta de contratos**: no va dentro de este repo ni dentro del plugin. Conectala en
   Cowork (o decile al plugin su ruta absoluta cuando te la pida en la primera corrida — ver
   abajo). Puede ser cualquier carpeta de tu máquina, organizada como:
   ```
   <tu carpeta de contratos>/
     <Categoría 1>/
       <ID proveedor> - <Nombre proveedor>/
         contrato.pdf
         modificacion_001.pdf
         odc_1.pdf
         ...
     <Categoría 2>/
       ...
   ```

## Cómo instalar el plugin en Cowork

Este repo **es** el código fuente del plugin: una carpeta `.claude-plugin/plugin.json` (manifest)
junto a `skills/` (7 skills: `menu`, `contract-ingest`, `discount-finder`, `category-onepager`,
`merge-cost-slide`, `savings-report`, `discount-email`).

1. Empaquetá `.claude-plugin/` y `skills/` en un `.zip` (sin `INPUT/`, `config/`, `output/`,
   `_tmp_qa/`, `.git/` — eso es material de desarrollo del repo, no del plugin en sí).
2. En Cowork: pestaña **Customize** → subí el `.zip`. Requisitos de la plataforma: menos de 200MB
   y un `.zip` válido.
3. Listo — el plugin queda instalado en tu cuenta y disponible en **cualquier carpeta** que
   conectes en sesiones futuras, no solo en esta.

Si tu organización usa un marketplace interno de plugins (como en BCG), el mismo `.zip` sirve como
fuente para ese registro — consultá con el equipo de GenAI Workspace de BCG el paso administrativo
de publicarlo ahí (visibilidad Auto-install / Available / Not-available).

## Primera corrida — conectá tu carpeta de contratos y arrancá

No hace falta editar nada a mano ni clonar este repo en tu máquina.

1. En Cowork, conectá la carpeta que tiene (o va a tener) tus contratos.
2. Escribí **"/inicio"** en el chat — te muestra el menú de las 6 opciones (skill `menu`). También
   podés pedir directamente lo que quieras en lenguaje natural, sin pasar por el menú (ej.
   "clasificá los contratos").
3. Si elegís "iniciar análisis de contratos" (opción 1), el plugin usa la carpeta conectada como
   `contracts_root` por defecto si su estructura ya parece `Categoría/Proveedor/archivos`; si no, te
   pregunta la ruta absoluta. Esa decisión queda guardada dentro de tu propia carpeta de contratos,
   en `<tu carpeta de contratos>/.savings-engine/config.json` — **no en este repo ni en el plugin** —
   así corridas futuras en esa misma carpeta no vuelven a preguntar, y podés conectar varias
   carpetas de contratos distintas sin que se pisen entre sí.
4. A partir de ahí, pedí cada paso del pipeline en lenguaje natural o volviendo a escribir
   "/inicio" para ver el menú de nuevo (ver tabla abajo). Todo el output (JSON, Excel, PPTX, HTML,
   borradores) se genera dentro de tu carpeta de contratos, nunca dentro del plugin.

## Las 6 opciones del menú

Al escribir "/inicio" (o "/init"), el skill `menu` muestra estas 6 opciones numeradas:

| # | Opción | Qué hace | Skill |
|---|---|---|---|
| 1 | Iniciar análisis de contratos | Pide la carpeta, analiza y califica todos los contratos desde cero | `contract-ingest` (Modo A) |
| 2 | Refrescar análisis de contratos | Detecta archivos nuevos/modificados desde el último "iniciar" (fecha de modificación + tamaño) y reprocesa solo esos proveedores | `contract-ingest` (Modo B) |
| 3 | Crear one-pager por categoría | Perfil PPTX de una categoría (proveedores, montos, vencimientos) | `category-onepager` |
| 4 | Crear microsite por categoría | Catálogo interactivo HTML para explorar los contratos | `savings-report` (Modo B) |
| 5 | Analizar en busca de descuentos | Evalúa palancas de negociación sobre los contratos ya ingeridos | `discount-finder` |
| 6 | Crear correo en borrador para solicitar descuento | Arma el borrador en Outlook — nunca lo envía (HITL) | `discount-email` |

La opción 2 necesita que la opción 1 haya corrido al menos una vez sobre esa carpeta (guarda una
línea de base en `<contracts_root>/.savings-engine/manifest.json`).

Quedan fuera del menú, pero siguen existiendo como pasos independientes: `savings-report` Modo A
(reporte HTML de oportunidades, paso natural después de la opción 5) y `merge-cost-slide` (agrega
una slide de costos a un one-pager ya generado, paso natural después de la opción 3).

## Frases para arrancar cada paso

No son comandos de terminal — son pedidos en el chat de Cowork. Ejemplos:

| Paso | Ejemplos de frase disparadora |
|---|---|
| Menú | "/inicio", "/init", "qué opciones tengo", "menú principal" |
| 1. Ingesta (iniciar) | "Clasificá los contratos", "Analizá los contratos nuevos de la carpeta X", "Corré la ingesta de contratos" |
| 1. Ingesta (refrescar) | "Refrescá el análisis de contratos", "Fijate si hay contratos nuevos o modificados", "Actualizá lo que cambió" |
| 2. Descuentos | "Buscá posibilidades de descuento", "Qué contratos podemos renegociar", "Analizá palancas para [proveedor/categoría]" |
| 3. Reporte | "Armá el reporte de ahorros", "Generá el HTML de oportunidades" |
| 4. Email | "Preparame el email de descuento para [proveedor]", "Armá el borrador de negociación con..." |

Los pasos principales (1→2→3→4) son secuenciales (2 necesita el output de 1, etc.); 2b/2c son
opcionales y corren en paralelo a partir del output de 1/2. Podés repetir el paso 1 en modo "iniciar"
(reprocesa todo) o "refrescar" (solo lo que cambió) sin tener que rehacer todo el pipeline.

## Estructura del repo

Esto es el **código del plugin** — nunca contiene datos de contratos ni de un cliente puntual:

```
savingsEngine/
├── README.md                     ← este archivo
├── .claude-plugin/
│   └── plugin.json               ← manifest del plugin (name/version/description)
├── skills/
│   ├── menu/                     ← paso 0 (router de "/inicio" → las 6 opciones)
│   ├── contract-ingest/          ← paso 1 (Modo A iniciar / Modo B refrescar)
│   ├── discount-finder/          ← paso 2
│   ├── category-onepager/        ← paso 2b (paralelo, one-pager PPTX por categoría)
│   ├── merge-cost-slide/         ← paso 2c (agrega slide de costos al one-pager)
│   ├── savings-report/           ← paso 3 (Modo A reporte HTML / Modo B microsite)
│   └── discount-email/           ← paso 4
└── docs/
    └── ARQUITECTURA.md
```

La config (`contracts_root`) y todo output generado (JSON, Excel, PPTX, HTML, borradores) viven
**dentro de la carpeta de contratos del usuario**, en `<contracts_root>/.savings-engine/config.json`
y `<contracts_root>/output/...` respectivamente — nunca en este repo. Esto es así porque, una vez
instalado como plugin de Cowork, `skills/` queda montado en modo solo lectura: el plugin no puede
escribir su propio estado al lado de sí mismo, tiene que escribirlo en la carpeta de trabajo del
usuario. `config/config.example.json` sigue sirviendo como referencia del formato, pero ya no se
copia a una `config/config.json` local del repo.

## Estado actual / qué falta

Este plugin arrancó con esquemas **v0 / borrador**, inferidos de la estructura de carpetas antes
de haber visto todavía el proceso real "TAIL CUTTER". Eso ya se reconcilió:

- `skills/contract-ingest/references/schema.md` está en **v3**, alineado campo a campo con el
  playbook real (`playbooks/01_extraccion_contratos.md` dentro de la carpeta de contratos del
  usuario, si existe — incluye `dossier_savingsradar`, el contenido mecánicamente extraíble del
  PPTX "Dossier SR" que acompaña a varios proveedores).
- `skills/discount-finder/references/palancas.md` está en **v1**, reconciliado contra los nombres
  de campo reales del esquema v3 (ya no usa los nombres v0 en inglés).
- Sigue pendiente (no bloqueante, es una mejora futura): el formato del reporte HTML de Modo A de
  `savings-report` (`skills/savings-report/assets/report_template.html`) no se validó todavía
  contra un ejemplo real que el usuario haya compartido — sigue siendo el template genérico.
- La detección incremental de cambios (antes listada como mejora futura en
  `docs/ARQUITECTURA.md`) ya está implementada: es la opción 2 del menú ("refrescar análisis de
  contratos"), vía `skills/contract-ingest/scripts/build_manifest.py` +
  `scripts/diff_manifest.py` — ver `skills/contract-ingest/SKILL.md` §6.

Nota sobre la estructura de salida real: `contract-ingest` guarda **un JSON por categoría**
(`<categoria>_contratos_v<N>.json`), normalmente en una carpeta `Extracciones/` dentro de la
categoría — no siempre en `<contracts_root>/output/contract-summaries/`, que es solo la convención
por defecto de este skill. Si la carpeta de contratos real del usuario ya trae su propia estructura
de salida, esa manda (ver `skills/contract-ingest/SKILL.md` paso 1).

## Datos y seguridad

- Los contratos y todo output generado (JSON, reportes, borradores de correo) **nunca se suben al
  repo/plugin** — viven enteramente dentro de tu propia carpeta de contratos
  (`<contracts_root>/.savings-engine/` y `<contracts_root>/output/`), una carpeta de tu máquina que
  vos elegís y conectás en Cowork. Este repo (y el `.zip` que se instala como plugin) versiona solo
  el código: nunca contiene datos de un cliente puntual, así que no depende de `.gitignore` para
  mantenerlos separados.
- `discount-email` nunca envía correos automáticamente: siempre deja un borrador en Outlook para
  que lo revises y envíes vos.
- El esquema v3 de contract-ingest no captura un campo de contacto/contraparte explícito. Si algún
  documento fuente incluye nombres de firmantes u otros datos personales, tratalos según las
  políticas de datos personales de BCG antes de compartir cualquier output fuera del equipo.
