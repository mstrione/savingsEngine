#!/usr/bin/env python3
"""
validate_summary.py — Validación liviana (sin dependencias externas) de un
JSON de resumen de contrato contra el esquema v0 (references/schema.json /
schema.md). No es un validador JSON Schema completo: chequea campos
obligatorios, tipos básicos y valores de enum, que es suficiente para
detectar errores comunes de un subagente (campo faltante, tipo equivocado,
enum inventado).

Uso:
    python3 validate_summary.py --file output/contract-summaries/TI/4643003769.json
    python3 validate_summary.py --dir output/contract-summaries   # valida todos los .json
"""
import argparse
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "schema_version",
    "provider_id",
    "provider_name",
    "category",
    "documents",
    "summary",
    "source_folder",
    "processed_at",
]

ENUMS = {
    "renewal_type": {"automatica", "manual", "desconocida", None},
    "pricing_model": {"fijo", "variable", "por_consumo", "mixto", "desconocido", None},
}

DOC_TYPES = {"contrato", "modificacion", "odc", "formulario_admin", "dossier_negociacion", "otro"}


def validate_one(data: dict, label: str) -> list[str]:
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"[{label}] falta el campo obligatorio '{field}'")

    for field, allowed in ENUMS.items():
        if field in data and data[field] not in allowed:
            errors.append(f"[{label}] valor inválido en '{field}': {data[field]!r}")

    if "documents" in data:
        if not isinstance(data["documents"], list):
            errors.append(f"[{label}] 'documents' debe ser una lista")
        else:
            for i, doc in enumerate(data["documents"]):
                if not isinstance(doc, dict) or "file_name" not in doc or "doc_type" not in doc:
                    errors.append(f"[{label}] documents[{i}] mal formado (requiere file_name y doc_type)")
                elif doc.get("doc_type") not in DOC_TYPES:
                    errors.append(f"[{label}] documents[{i}].doc_type inválido: {doc.get('doc_type')!r}")

    if "total_value_estimate" in data and data["total_value_estimate"] is not None:
        if not isinstance(data["total_value_estimate"], (int, float)):
            errors.append(f"[{label}] 'total_value_estimate' debe ser numérico o null")

    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Ruta a un único JSON de resumen")
    group.add_argument("--dir", help="Carpeta con JSONs de resumen (recursivo)")
    args = parser.parse_args()

    files = []
    if args.file:
        files = [Path(args.file)]
    else:
        files = sorted(Path(args.dir).rglob("*.json"))

    total_errors = []
    for f in files:
        if f.name == "index.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            total_errors.append(f"[{f}] JSON inválido: {e}")
            continue
        total_errors.extend(validate_one(data, str(f)))

    if total_errors:
        print(f"❌ {len(total_errors)} error(es) en {len(files)} archivo(s):")
        for e in total_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"✅ {len(files)} archivo(s) OK")


if __name__ == "__main__":
    main()
