# Arquitectura — Savings Engine

## Decisiones de diseño

- **4 skills separados, no uno solo**: cada paso tiene un disparador de lenguaje natural distinto
  y se invoca en momentos distintos del trabajo (la ingesta es inicial y repetible; el resto se
  corre bajo demanda). Separarlos evita que un pedido de "generá el reporte" dispare sin querer
  toda la ingesta de nuevo.
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
- **Config local, no en el repo**: `contracts_root` depende de la máquina/usuario y potencialmente
  de datos de cliente (rutas que revelan nombre de cliente/engagement). Por eso vive en
  `config/config.json`, gitignored, y se pide interactivamente en la primera corrida.

## Extensiones futuras posibles (no implementadas)

- Detección de cambios incremental en `contract-ingest` (hash o mtime por archivo) para no
  reprocesar proveedores sin cambios.
- Reporte HTML como artefacto vivo de Cowork (con refresh de datos) en vez de archivo estático,
  si el volumen de corridas lo justifica.
- Métricas de ahorro consolidado a nivel de portafolio completo (hoy el análisis es por
  proveedor/contrato).
