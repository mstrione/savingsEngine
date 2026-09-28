#!/usr/bin/env python3
"""
scan_providers.py — Escanea la carpeta raíz de contratos (estructura
Categoria/Proveedor/archivos) y devuelve un JSON con la lista de proveedores
a procesar, para que el coordinador del skill contract-ingest pueda repartir
un subagente por proveedor.

Uso:
    python3 scan_providers.py --root "/ruta/a/Contratos" [--category "TI y Telecomunicaciones"]

Convenciones asumidas (ajustar si la estructura real difiere):
- Nivel 1 dentro de --root: carpetas de categoría (ej. "TI y Telecomunicaciones").
- Nivel 2: carpetas de proveedor, idealmente con formato "<id> - <NOMBRE>"
  (ej. "4643003769 - LOS NAVEGANTES S.A"). Si no matchea ese patrón, se usa
  el nombre completo de la carpeta como provider_id y provider_name.
- Se ignoran archivos ocultos, .DS_Store, temporales de Office (~$...) y
  carpetas que no contengan archivos.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PROVIDER_PATTERN = re.compile(r"^\s*(?P<id>[\w.\-]+)\s*-\s*(?P<name>.+?)\s*$")
IGNORED_FILE_PREFIXES = ("~$", ".")
IGNORED_FILENAMES = {".DS_Store"}


def is_ignored(path: Path) -> bool:
    if path.name in IGNORED_FILENAMES:
        return True
    if path.name.startswith(IGNORED_FILE_PREFIXES):
        return True
    return False


def scan(root: Path, only_category: str | None = None):
    result = []
    if not root.exists():
        raise FileNotFoundError(f"No existe la carpeta raíz: {root}")

    for category_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if is_ignored(category_dir):
            continue
        if only_category and category_dir.name != only_category:
            continue

        providers = []
        for provider_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            if is_ignored(provider_dir):
                continue

            files = [
                str(f.relative_to(root))
                for f in provider_dir.rglob("*")
                if f.is_file() and not is_ignored(f)
            ]
            if not files:
                continue

            match = PROVIDER_PATTERN.match(provider_dir.name)
            if match:
                provider_id = match.group("id")
                provider_name = match.group("name")
            else:
                provider_id = provider_dir.name
                provider_name = provider_dir.name

            providers.append(
                {
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "folder": str(provider_dir.relative_to(root)),
                    "file_count": len(files),
                    "files": files,
                }
            )

        # Categoría "plana" (archivos sueltos, sin subcarpeta de proveedor)
        loose_files = [
            str(f.relative_to(root))
            for f in category_dir.glob("*")
            if f.is_file() and not is_ignored(f)
        ]

        result.append(
            {
                "category": category_dir.name,
                "providers": providers,
                "loose_files": loose_files,
            }
        )

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Carpeta raíz de contratos")
    parser.add_argument("--category", default=None, help="Filtrar por una sola categoría")
    args = parser.parse_args()

    try:
        data = scan(Path(args.root).expanduser(), args.category)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
