# Savings Engine — plugin de Cowork

Plugin de Cowork para analizar contratos de proveedores y detectar oportunidades de descuento /
renegociación, con validación humana antes de cualquier envío de correo.

## Pipeline (4 pasos)

```
1. contract-ingest   → lee contratos/adendas por proveedor → JSON estructurado (paralelo, repetible)
2. discount-finder    → cruza el JSON contra una taxonomía de palancas → oportunidades detectadas
3. savings-report     → arma un reporte HTML con las oportunidades
4. discount-email     → redacta un borrador de correo por proveedor → queda en Outlook (Draft) — HITL
```

Cada paso es un skill independiente en `skills/`. Se disparan por lenguaje natural en el chat de
Cowork (no son comandos de shell) — ver "Frases para arrancar cada paso" más abajo.

## Requisitos antes de arrancar

1. **Carpeta conectada en Cowork**: esta carpeta (`savingsEngine`) tiene que ser la carpeta
   seleccionada/conectada en tu sesión de Cowork, para que los skills puedan leer/escribir en
   `config/`, `output/` y `skills/`.
2. **Conector de Outlook** conectado en la sesión (lo necesita `discount-email` para crear el
   borrador). Sin esto, ese último paso no puede dejar el draft creado.
3. **Contratos**: no van dentro de este repo. Vos le decís al plugin, en la primera corrida,
   dónde están — ver abajo. Podés usar cualquier carpeta de tu máquina, organizada como:
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
   (mismo patrón que viste en `INPUT/` — esa carpeta es solo de referencia para mí, no la toco y
   la vas a borrar vos.)

## Cómo instalar los skills en Cowork

Este repo no es un `.pptx`/`.xlsx` con instalador; son 4 carpetas de skill (`SKILL.md` +
recursos). Dos formas de usarlo:

- **Opción simple**: cloná este repo como tu carpeta de trabajo de Cowork (o poné el repo dentro
  de la carpeta que ya usás) y, al empezar la sesión, decile a Claude algo como "leé
  `skills/contract-ingest/SKILL.md` antes de arrancar" si no se dispara solo por el pedido.
- **Opción empaquetada**: pedile a Claude (en una sesión con el skill `skill-creator` disponible)
  que empaquete cada carpeta de `skills/` con `scripts/package_skill.py` para generar un archivo
  `.skill` instalable individualmente desde el botón "Save skill". Útil si querés instalarlos en
  otra cuenta/perfil sin clonar el repo entero.

Si tu organización usa un mecanismo formal de marketplace de plugins (como los plugins internos
de BCG), consultá con el equipo de GenAI Workspace de BCG el paso de registro — este repo te deja
listos los skills, pero el registro en un marketplace corporativo es un paso administrativo aparte.

## Primera corrida — configurar la carpeta de contratos

No hace falta editar nada a mano. La primera vez que le pidas al plugin que analice contratos
(ver frases abajo), te va a preguntar la ruta absoluta de tu carpeta de contratos y la va a guardar
en `config/config.json` (que **no se sube al repo** — está en `.gitignore`, es específico de tu
máquina). Corridas futuras la reutilizan; si querés apuntar a otra carpeta, avisale y la actualiza.

Si preferís configurarlo vos mismo antes de arrancar: copiá `config/config.example.json` a
`config/config.json` y completá `contracts_root`.

## Frases para arrancar cada paso

No son comandos de terminal — son pedidos en el chat de Cowork. Ejemplos:

| Paso | Ejemplos de frase disparadora |
|---|---|
| 1. Ingesta | "Clasificá los contratos", "Analizá los contratos nuevos de la carpeta X", "Corré la ingesta de contratos" |
| 2. Descuentos | "Buscá posibilidades de descuento", "Qué contratos podemos renegociar", "Analizá palancas para [proveedor/categoría]" |
| 3. Reporte | "Armá el reporte de ahorros", "Generá el HTML de oportunidades" |
| 4. Email | "Preparame el email de descuento para [proveedor]", "Armá el borrador de negociación con..." |

Los 4 pasos son secuenciales (2 necesita el output de 1, etc.) pero podés repetir el paso 1 solo
cuando agregues contratos nuevos, sin tener que rehacer todo el pipeline.

## Estructura del repo

```
savingsEngine/
├── README.md                     ← este archivo
├── config/
│   ├── config.example.json       ← template (versionado)
│   └── config.json               ← tu config real (gitignored, no versionado)
├── skills/
│   ├── contract-ingest/          ← paso 1
│   ├── discount-finder/          ← paso 2
│   ├── savings-report/           ← paso 3
│   └── discount-email/           ← paso 4
├── output/                       ← generado en cada corrida (gitignored)
│   ├── contract-summaries/
│   ├── discount-opportunities/
│   └── reports/
└── docs/
    └── ARQUITECTURA.md
```

## Estado actual / qué falta

Este plugin arrancó con esquemas **v0 / borrador**, inferidos de la estructura de carpetas de
`INPUT/` (categoría → proveedor → contrato/adendas/ODC/dossier) sin haber visto todavía ejemplos
reales de:

- El JSON de resumen de contrato esperado (`skills/contract-ingest/references/schema.md`).
- La taxonomía real de palancas de descuento (`skills/discount-finder/references/palancas.md`).
- El formato del reporte HTML (`skills/savings-report/assets/report_template.html`).

Cuando pases esos ejemplos, decile al plugin (o pedímelo a mí) que actualice esos tres archivos a
`v1` — el resto del pipeline no debería necesitar cambios estructurales.

## Datos y seguridad

- Los contratos y todo output generado (JSON, reportes, borradores de correo) **nunca se suben al
  repo** — quedan en tu máquina, excluidos vía `.gitignore`. El repo versiona solo el código del
  plugin.
- `discount-email` nunca envía correos automáticamente: siempre deja un borrador en Outlook para
  que lo revises y envíes vos.
- Cualquier dato personal (nombres de firmantes, contactos) que aparezca en los JSON de contrato
  debe tratarse según las políticas de datos personales de BCG — ver
  `skills/contract-ingest/references/schema.md`, sección "Nota sobre datos personales".
