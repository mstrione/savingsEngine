---
name: menu
description: Punto de entrada explícito del pipeline Savings Engine — muestra las 6 opciones disponibles (iniciar análisis de contratos, refrescar análisis de contratos, crear one-pager por categoría, crear microsite por categoría, analizar en busca de descuentos, crear correo en borrador para solicitar descuento) y dirige al skill correspondiente según lo que elija el usuario. Úsalo cuando el usuario escriba literalmente "/inicio" o "/init", o pida "qué opciones tengo", "menú principal", "qué puedo hacer con savings engine", "mostrame el menú", "empezar", "arrancar el pipeline". Si el usuario ya pide una acción puntual y específica (ej. "buscá descuentos para Transporte de Personal"), no hace falta pasar por acá — dejá que el skill correspondiente se dispare directo.
---

# Menu

Router del pipeline: no analiza contratos ni genera nada por sí mismo, solo presenta las 6 opciones
y delega en el skill que corresponda.

## 0. Cuándo mostrar el menú vs. cuándo no

- El menú es para cuando el usuario no especifica qué quiere (`/inicio`, "qué opciones tengo") o
  quiere ver el panorama completo antes de elegir.
- Si el usuario ya pidió algo puntual en el mismo mensaje (ej. "quiero refrescar Transporte de
  Personal", "armame el one-pager de TI"), saltá el menú y andá directo al skill correspondiente —
  no le hagas re-elegir de una lista algo que ya pidió explícitamente.

## 1. Las 6 opciones (orden fijo, por etapa del pipeline — no alfabético)

1. **Iniciar análisis de contratos** — pide la carpeta de contratos, analiza y califica todo desde
   cero. → `../contract-ingest/SKILL.md`, Modo A (§1-5).
2. **Refrescar análisis de contratos** — detecta archivos nuevos/modificados desde el último
   "iniciar" (por fecha de modificación y tamaño de archivo) y reprocesa solo esos proveedores, sin
   tocar el resto. → `../contract-ingest/SKILL.md`, Modo B (§6). Requiere haber corrido la opción 1
   al menos una vez sobre esa carpeta.
3. **Crear one-pager por categoría** — perfil PPTX de una categoría (proveedores, montos,
   vencimientos, hallazgo "so-what"). → `../category-onepager/SKILL.md`.
4. **Crear microsite por categoría** — catálogo interactivo HTML para explorar los contratos de una
   categoría (no confundir con el one-pager PPTX). → `../savings-report/SKILL.md`, Modo B.
5. **Analizar en busca de descuentos** — evalúa palancas de negociación sobre los contratos ya
   ingeridos y arma la lista de oportunidades. → `../discount-finder/SKILL.md`.
6. **Crear correo en borrador para solicitar descuento a un proveedor** — arma el borrador de
   negociación en Outlook (HITL, nunca lo envía). → `../discount-email/SKILL.md`.

Deliberadamente fuera del menú (siguen existiendo, pero son pasos secundarios/menos frecuentes que
no ameritan ocupar un lugar en las 6 opciones principales): `savings-report` Modo A (reporte HTML de
oportunidades — ofrecelo como paso siguiente natural después de la opción 5, no como opción aparte
del menú) y `merge-cost-slide` (agregar la slide de costos a un one-pager ya existente — ofrecelo
después de la opción 3 si el usuario tiene esa slide ya generada aparte).

## 2. Cómo presentarlas

- Listalas numeradas en el chat, con una línea de qué hace cada una — no repitas el detalle interno
  de cada skill acá, ese detalle vive en el SKILL.md de destino.
- **El paso 1 (opción 1) es un prerrequisito obligatorio para las opciones 2 a 6** — ninguna de esas
  cinco puede hacer nada real sin que exista primero el JSON consolidado de `contract-ingest` para
  la categoría en cuestión (opción 2 además necesita puntualmente `manifest.json`, ver
  `../contract-ingest/SKILL.md` §6.0). Si no existe `.savings-engine/manifest.json` ni ningún
  `<categoria>_contratos_v<N>.json` en la carpeta de contratos conectada, marcá **las opciones 2 a
  6** como "(necesita haber corrido la opción 1 primero)" en vez de ocultarlas, y si el usuario elige
  una de ellas igual, recomendale explícitamente correr la opción 1 antes — no la dejes elegir una
  opción imposible sin avisarle.
- Esperá a que el usuario elija (por número o por nombre) antes de hacer cualquier otra cosa — este
  skill no ejecuta nada por sí mismo.

## 3. Al recibir la elección

- Andá directo a las instrucciones del skill correspondiente (mapeo del paso 1) y seguilas
  literalmente — no dupliques ni resumas esa lógica en este archivo.
- Si la elección requiere info que el propio skill destino ya sabe pedir (`contracts_root`, alcance
  de categorías, qué oportunidad usar en el correo, etc.), dejá que la pida ese skill — este router
  no adivina esos datos ni los precarga.
- Las reglas de activación de cada skill destino (confirmación antes de sobrescribir, HITL en
  `discount-email`, doble QA antes de entregar, etc.) siguen aplicando sin excepción — el menú no es
  un atajo para saltárselas.

## Ver también

- Los 6 skills listados en el paso 1, más `savings-report` Modo A y `merge-cost-slide` (fuera del
  menú, pero ofrecidos como paso siguiente natural — ver nota en el paso 1).
- `../contract-ingest/SKILL.md` — documenta ahí mismo (§6.0) por qué la opción 2 (refrescar) necesita
  que la opción 1 (iniciar) haya corrido antes sobre esa misma carpeta.
