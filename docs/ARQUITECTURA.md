# Arquitectura — Savings Engine

## Decisiones de diseño

- **7 skills separados, no uno solo**: cada paso (`menu`, `contract-ingest`, `discount-finder`,
  `category-onepager`, `merge-cost-slide`, `savings-report`, `discount-email`) tiene un disparador
  de lenguaje natural distinto y se invoca en momentos distintos del trabajo (la ingesta es inicial
  y repetible; el resto se corre bajo demanda). Separarlos evita que un pedido de "generá el
  reporte" dispare sin querer toda la ingesta de nuevo.
- **`menu` como router explícito, dueño de `/inicio`/`/init`**: antes, `/inicio` disparaba
  directamente la ingesta completa (Modo A). Al agregar un segundo modo de ingesta ("refrescar") más
  4 acciones bajo demanda, dejar `/inicio` atado a un solo skill dejaba de alcanzar — se necesitaba
  un punto de entrada que muestre las 6 opciones y delegue, sin que cada skill tenga que saber de la
  existencia de los otros 5. `menu` no procesa nada por sí mismo: es pura navegación/delegación, así
  que agregar una séptima opción el día de mañana no toca la lógica de ningún skill existente.
- **`contract-ingest` con dos modos (iniciar / refrescar) en vez de dos skills separados**: a
  diferencia de `menu` vs. el resto, acá sí conviene un solo skill — ambos modos comparten el mismo
  esquema v3, los mismos scripts de validación/Excel, y el mismo criterio de "un subagente por
  proveedor afectado". Separarlos en dos skills hubiera duplicado esa lógica compartida sin necesidad
  (mismo criterio que `savings-report` Modo A/B, que también conviven en un solo skill).
- **Paralelismo por proveedor en `contract-ingest`**: cada carpeta de proveedor es independiente
  entre sí (no comparte estado), por lo que un subagente por proveedor es seguro y acelera
  significativamente el procesamiento cuando hay muchas carpetas.
- **`discount-finder` como coordinador, no generador libre**: las palancas se evalúan contra
  condiciones explícitas sobre el JSON (ver `palancas.md`), no por criterio subjetivo del modelo
  en el momento. Esto es clave para evitar oportunidades "alucinadas" — cada oportunidad debe
  poder rastrearse a un campo concreto del JSON de `contract-ingest`.
- **`discount-email` nunca envía**: por diseño (decisión explícita de Mauro), el paso de envío de
  correo queda siempre como una acción manual del usuario en Outlook. El plugin arma y deja el
  borrador; el HITL es el envío en sí, no una confirmación intermedia dentro del chat.
- **Config dentro de la carpeta de contratos, no en el repo/plugin**: `contracts_root` depende de
  la máquina/usuario y potencialmente de datos de cliente (rutas que revelan nombre de
  cliente/engagement). Además, una vez instalado como plugin de Cowork, `skills/` queda montado en
  modo solo lectura — el plugin no puede escribir su propio estado al lado de sí mismo. Por eso
  `contracts_root`/`output_root` viven en `<contracts_root>/.savings-engine/config.json`, dentro de
  la carpeta de contratos del propio usuario, y se piden (o se infieren de la carpeta conectada en
  Cowork) interactivamente en la primera corrida (`/inicio`).

## Refrescar análisis de contratos: manifest separado + reprocesamiento parcial

- **`manifest.json` en archivo separado, no dentro de `config.json`**: `config.json` guarda
  configuración estable (rutas) que casi no cambia; el manifest es un snapshot potencialmente grande
  (mtime+tamaño de cada archivo de cada proveedor) que se reescribe completo en cada "iniciar" o
  "refrescar". Mezclarlos hubiera hecho que cualquier lectura/escritura de configuración tuviera que
  lidiar con un archivo mucho más pesado y con un ritmo de cambio distinto.
- **`manifest.json` es la única excepción a "nunca sobrescribir" dentro de `contract-ingest`**
  (mismo patrón que `datos.js` en `savings-report`): no es un artefacto de entrega versionado, es
  estado interno del pipeline — por eso `build_manifest.py` lo pisa a propósito en cada corrida de
  Modo A, y `diff_manifest.py` nunca lo modifica (solo lee y compara).
- **Refrescar reprocesa solo el proveedor afectado, no toda la categoría**: la alternativa (reprocesar
  la categoría completa ante cualquier cambio) es más simple pero desperdicia trabajo — si 1 de 9
  proveedores de una categoría tiene una adenda nueva, no hay razón para volver a leer los 8 restantes
  ni para relanzar 9 subagentes. El costo es que la fusión en `contract-ingest/SKILL.md` §6.4 tiene
  que reemplazar registros puntuales dentro del `contratos[]` existente en vez de regenerar el array
  entero — más frágil que "regenerar todo", por eso ese paso deja explícito el criterio de match
  (`numero_contrato`/RUT) y la regla de no retocar los registros no afectados.
- **Un archivo "eliminado" en el diff no dispara ninguna acción automática**: borrar o mover un
  archivo fuente no debería hacer desaparecer un proveedor ya analizado del JSON consolidado (podría
  ser un archivo que se reorganizó, no que el contrato dejó de existir) — se reporta para revisión
  humana, nunca se actúa solo.

## Extensiones futuras posibles (no implementadas)

- Reporte HTML como artefacto vivo de Cowork (con refresh de datos) en vez de archivo estático,
  si el volumen de corridas lo justifica.
- Métricas de ahorro consolidado a nivel de portafolio completo (hoy el análisis es por
  proveedor/contrato).
