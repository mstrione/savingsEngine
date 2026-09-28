---
name: contract-ingest
description: Lee contratos y adendas de proveedores (organizados en carpetas por categoría y proveedor: PDFs de contrato, modificaciones/adendas, órdenes de compra, formularios administrativos, dossiers de negociación) y produce un resumen estructurado en JSON por proveedor. Es el paso inicial y repetible del Savings Engine — úsalo cuando el usuario pida "clasificar contratos", "analizar los contratos", "resumir los contratos", "ingestar contratos nuevos", "leer la carpeta de contratos", o cuando quiera arrancar o refrescar el análisis de ahorro antes de buscar descuentos. Usa subagentes en paralelo (uno por proveedor) para acelerar el procesamiento cuando hay múltiples carpetas.
---

# Contract Ingest

Primer paso del pipeline de Savings Engine: convierte carpetas de contratos (PDF/DOCX/XLSX/PPTX)
en JSON estructurado y trazable, listo para que `discount-finder` busque palancas de descuento.

## 0. Primer uso: definir la carpeta de contratos

Antes de procesar nada, revisá `config/config.json` (en la raíz del proyecto, junto a `skills/`).

- **Si no existe o no tiene `contracts_root`:** preguntale al usuario la ruta absoluta de la
  carpeta raíz donde están sus contratos, organizada como `Categoría/Proveedor/archivos`
  (igual al patrón de ejemplo que vio en `INPUT/`). Guardala en `config/config.json` con esta forma:

  ```json
  {
    "contracts_root": "/ruta/absoluta/que/te/dio/el/usuario",
    "output_root": "output"
  }
  ```

  `config/config.json` está en `.gitignore` — nunca lo subas al repo, es específico de cada
  máquina/usuario.

- **Si ya existe:** usala directamente, pero confirmá con el usuario si quiere apuntar a otra
  carpeta antes de correr (por si está re-procesando una carpeta distinta a la de la última vez).

## 1. Escanear la estructura

Corré el script bundleado para listar categorías, proveedores y archivos sin tener que leer
carpeta por carpeta manualmente:

```bash
python3 skills/contract-ingest/scripts/scan_providers.py --root "<contracts_root>"
```

Esto te da, por categoría, la lista de carpetas de proveedor con sus archivos. Usalo para:
- Decidir cuántos subagentes lanzar (uno por proveedor).
- Detectar `loose_files` (archivos sueltos en la categoría, no asociados a un proveedor) y
  preguntarle al usuario qué hacer con ellos en vez de ignorarlos silenciosamente.

## 2. Procesar en paralelo, un subagente por proveedor

Para cada proveedor detectado, lanzá un subagente (Task/Agent) con instrucciones autocontenidas:

- Rutas absolutas de todos los archivos de esa carpeta de proveedor.
- El contenido de `references/schema.md` (o un resumen fiel de sus campos) para que sepa
  exactamente qué JSON producir.
- La instrucción explícita de **no inventar valores**: todo campo que no esté explícito en los
  documentos va como `null`, y todo campo no trivial debe citar el documento fuente.
- Dónde guardar el resultado: `output/contract-summaries/<categoria>/<provider_id>.json`.

Lanzá los subagentes de a lotes razonables (5-8 en paralelo) en vez de todos a la vez si hay
muchos proveedores, para no saturar el contexto ni perder trazabilidad de errores.

Cada subagente debe leer **todos** los documentos de su proveedor (contrato original +
modificaciones/adendas + ODC + formularios + dossier de negociación si existe) antes de escribir
el JSON — el objetivo es capturar el historial completo, no solo el contrato inicial.

## 3. Validar y consolidar

Una vez que todos los subagentes terminaron:

1. Corré el validador liviano sobre toda la carpeta de salida:
   ```bash
   python3 skills/contract-ingest/scripts/validate_summary.py --dir output/contract-summaries
   ```
   Si hay errores, decidí si reprocesar ese proveedor puntual (no hace falta re-correr todo).

2. Armá `output/contract-summaries/index.json`: una lista plana de todos los proveedores
   procesados con `{provider_id, provider_name, category, expiration_date, flags, json_path}`,
   para que `discount-finder` y `savings-report` no tengan que abrir cada JSON individual para
   tener una vista general.

3. Contale al usuario, en un resumen corto (no en un archivo aparte): cuántos proveedores se
   procesaron, cuántos por categoría, y si hubo `loose_files` o errores de validación pendientes.

## Re-ejecución (idempotencia)

Este paso es repetible. Si el usuario agrega contratos nuevos o corrige algo y vuelve a pedir la
ingesta:
- Reprocesar solo las carpetas de proveedor que cambiaron es más rápido, pero solo hacelo si
  podés detectar cambios de forma confiable (fecha de modificación de archivos). Si no estás
  seguro, preferí reprocesar todo antes que dejar un JSON desactualizado.
- Sobrescribí el JSON del proveedor (no acumules versiones sueltas) y actualizá `index.json`.

## Ver también

- `references/schema.md` — descripción completa de cada campo del JSON de salida.
- `references/schema.json` — mismo esquema en formato JSON Schema (usado por `validate_summary.py`).
