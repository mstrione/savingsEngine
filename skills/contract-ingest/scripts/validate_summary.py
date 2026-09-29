#!/usr/bin/env python3
"""
validate_summary.py — Validación liviana (sin dependencias externas) de un
JSON de extracción de categoría contra el esquema v3 (references/schema.json /
schema.md). No es un validador JSON Schema completo: chequea estructura
mínima, trazabilidad (fuente/confianza) en los campos clave, formato de
monto_total, y corre validate_rut.py sobre cada RUT — suficiente para
detectar errores comunes de un subagente (campo faltante, monto como texto
libre en vez de lista, RUT mal formado) antes de dárselo por bueno al
usuario.

Uso:
    python3 validate_summary.py --file Extracciones/categoria_contratos_v3.json
    python3 validate_summary.py --dir Extracciones   # valida todos los *_contratos_v*.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REQUIRED_METADATA_FIELDS = ["categoria", "fecha_extraccion", "version", "total_contratos"]

REQUIRED_CONTRATO_FIELDS = [
    "numero_contrato",
    "proveedor",
    "rut_run_proveedor",
    "vigencia",
    "monto_total",
    "documentos_fuente",
]

CAMPOS_CON_TRAZABILIDAD_ESPERADA = [
    "metodo_pago",
    "niveles_servicio",
    "clausula_incentivo_desempeno",
    "clausula_multa_penalizacion",
    "mecanismo_reajuste_indexacion",
]

CONFIANZA_VALIDA = {"alta", "media", "baja", None}


def _validate_rut(rut_valor: str) -> dict | None:
    """Corre validate_rut.py como subproceso para no duplicar la lógica del módulo 11."""
    script = Path(__file__).parent / "validate_rut.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script), rut_valor],
            capture_output=True, text=True, timeout=5,
        )
        return json.loads(result.stdout)
    except Exception:
        return None


def _check_trazabilidad(campo: dict, nombre: str, label: str, errors: list, warnings: list):
    if not isinstance(campo, dict):
        return
    confianza = campo.get("confianza")
    if "confianza" in campo and confianza not in CONFIANZA_VALIDA:
        errors.append(f"[{label}] '{nombre}.confianza' inválida: {confianza!r} (debe ser alta/media/baja/null)")
    if "valor" in campo and campo.get("valor") not in (None, "No especificado en el contrato") \
            and "fuente" not in campo:
        warnings.append(f"[{label}] '{nombre}' tiene valor pero no declara 'fuente' — revisar trazabilidad")


def _check_monto_total(monto_total, label: str, errors: list):
    lista = monto_total.get("valor") if isinstance(monto_total, dict) else monto_total
    if not isinstance(lista, list):
        errors.append(f"[{label}] 'monto_total' debe resolver a una lista de {{moneda,valor,periodo}} (regla 4.8), no texto libre")
        return
    for i, entry in enumerate(lista):
        if not isinstance(entry, dict) or not {"moneda", "valor", "periodo"} <= entry.keys():
            errors.append(f"[{label}] monto_total[{i}] mal formado — requiere moneda, valor y periodo")


def validate_contrato(contrato: dict, label: str) -> tuple[list, list]:
    errors, warnings = [], []

    for field in REQUIRED_CONTRATO_FIELDS:
        if field not in contrato:
            errors.append(f"[{label}] falta el campo obligatorio '{field}'")

    rut = contrato.get("rut_run_proveedor")
    if isinstance(rut, dict) and rut.get("valor"):
        chequeo = _validate_rut(rut["valor"])
        if chequeo and chequeo.get("valido") is False:
            if rut.get("confianza") != "baja":
                warnings.append(
                    f"[{label}] RUT '{rut['valor']}' no valida contra dígito verificador "
                    f"(declarado {chequeo.get('dv_declarado')}, calculado {chequeo.get('dv_calculado')}) "
                    f"— debería tener confianza:baja y nota de inconsistencia (regla 4.7), no corregirse"
                )

    if "monto_total" in contrato:
        _check_monto_total(contrato["monto_total"], label, errors)

    for campo_nombre in CAMPOS_CON_TRAZABILIDAD_ESPERADA:
        if campo_nombre in contrato:
            _check_trazabilidad(contrato[campo_nombre], campo_nombre, label, errors, warnings)

    if not contrato.get("notas"):
        warnings.append(f"[{label}] 'notas' vacío — confirmar que realmente no hubo hallazgos/alertas que registrar")

    return errors, warnings


def validate_file(data: dict, label: str) -> tuple[list, list]:
    errors, warnings = [], []

    if "metadata" not in data or "contratos" not in data:
        errors.append(f"[{label}] el archivo debe tener 'metadata' y 'contratos' a nivel raíz (esquema v3 por categoría, no por proveedor)")
        return errors, warnings

    metadata = data.get("metadata", {})
    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata:
            errors.append(f"[{label}] falta 'metadata.{field}'")

    contratos = data.get("contratos", [])
    if metadata.get("total_contratos") not in (None, len(contratos)):
        warnings.append(
            f"[{label}] metadata.total_contratos ({metadata.get('total_contratos')}) "
            f"no coincide con len(contratos) ({len(contratos)})"
        )

    for i, contrato in enumerate(contratos):
        c_label = f"{label} :: contratos[{i}] ({contrato.get('numero_contrato', '?')})"
        c_errors, c_warnings = validate_contrato(contrato, c_label)
        errors.extend(c_errors)
        warnings.extend(c_warnings)

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Ruta a un único JSON de extracción de categoría")
    group.add_argument("--dir", help="Carpeta con JSONs de extracción (recursivo, ignora archivos que no matcheen *contratos*.json)")
    args = parser.parse_args()

    if args.file:
        files = [Path(args.file)]
    else:
        files = sorted(p for p in Path(args.dir).rglob("*.json") if "contrato" in p.name.lower())

    total_errors, total_warnings = [], []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            total_errors.append(f"[{f}] JSON inválido: {e}")
            continue
        e, w = validate_file(data, str(f))
        total_errors.extend(e)
        total_warnings.extend(w)

    if total_warnings:
        print(f"⚠️  {len(total_warnings)} advertencia(s):")
        for w in total_warnings:
            print(f"  - {w}")

    if total_errors:
        print(f"❌ {len(total_errors)} error(es) en {len(files)} archivo(s):")
        for e in total_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"✅ {len(files)} archivo(s) OK (estructura)" + (f", {len(total_warnings)} advertencia(s) a revisar" if total_warnings else ""))


if __name__ == "__main__":
    main()
