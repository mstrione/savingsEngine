#!/usr/bin/env python3
"""
build_manifest.py — Toma una "foto" de todos los archivos de la carpeta raíz de
contratos (mtime + tamaño), agrupada por categoría/proveedor, y la guarda en
un archivo de estado separado (no versionado) para que `diff_manifest.py`
pueda comparar corridas futuras y detectar qué cambió.

Se corre al final de una ingesta completa ("iniciar análisis de contratos"),
nunca como paso independiente: es la línea de base contra la que se comparará
el próximo "refrescar análisis de contratos".

Uso:
    python3 build_manifest.py --root "/ruta/a/Contratos" \
        [--out "/ruta/a/Contratos/.savings-engine/manifest.json"]

Convenciones (comparten las de scan_providers.py del mismo skill):
- Nivel 1 dentro de --root: carpetas de categoría.
- Nivel 2: carpetas de proveedor, idealmente "<id> - <NOMBRE>".
- Se ignoran archivos ocultos, .DS_Store, temporales de Office (~$...), y
  cualquier cosa dentro de `output/` o `.savings-engine/` (son artefactos del
  propio pipeline, no contratos).

Excepción deliberada a "nunca sobrescribir" (misma lógica que `datos.js` en el
skill savings-report): este archivo es un snapshot vivo del estado actual de
la carpeta, no un artefacto de entrega versionado — cada corrida de
build_manifest.py pisa el anterior a propósito.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROVIDER_PATTERN = re.compile(r"^\s*(?P<id>[\w.\-]+)\s*-\s*(?P<name>.+?)\s*$")
IGNORED_FILE_PREFIXES = ("~$", ".")
IGNORED_FILENAMES = {".DS_Store"}
IGNORED_DIR_NAMES = {"output", ".savings-engine", ".git"}


def is_ignored_file(path: Path) -> bool:
    if path.name in IGNORED_FILENAMES:
        return True
    if path.name.startswith(IGNORED_FILE_PREFIXES):
        return True
    return False


def is_ignored_dir(path: Path) -> bool:
    return path.name in IGNORED_DIR_NAMES


def file_stat(path: Path) -> dict:
    st = path.stat()
    return {"mtime": st.st_mtime, "size": st.st_size}


def scan_root(root: Path) -> dict:
    """Misma estructura de recorrido que scan_providers.py, pero devuelve
    mtime+size por archivo en vez de solo listar rutas."""
    if not root.exists():
        raise FileNotFoundError(f"No existe la carpeta raíz: {root}")

    categories = {}

    for category_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if is_ignored_file(category_dir) or is_ignored_dir(category_dir):
            continue

        providers = {}
        for provider_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            if is_ignored_file(provider_dir) or is_ignored_dir(provider_dir):
                continue

            files = {}
            for f in provider_dir.rglob("*"):
                if not f.is_file() or is_ignored_file(f):
                    continue
                files[str(f.relative_to(root))] = file_stat(f)

            if not files:
                continue

            match = PROVIDER_PATTERN.match(provider_dir.name)
            if match:
                provider_id = match.group("id")
                provider_name = match.group("name")
            else:
                provider_id = provider_dir.name
                provider_name = provider_dir.name

            providers[str(provider_dir.relative_to(root))] = {
                "provider_id": provider_id,
                "provider_name": provider_name,
                "files": files,
            }

        loose_files = {}
        for f in category_dir.glob("*"):
            if not f.is_file() or is_ignored_file(f):
                continue
            loose_files[str(f.relative_to(root))] = file_stat(f)

        categories[category_dir.name] = {
            "providers": providers,
            "loose_files": loose_files,
        }

    return categories


def build_manifest(root: Path) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "categories": scan_root(root),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, help="Carpeta raíz de contratos (contracts_root)")
    parser.add_argument(
        "--out",
        default=None,
        help="Ruta de salida del manifest (default: <root>/.savings-engine/manifest.json)",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    try:
        manifest = build_manifest(root)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out).expanduser() if args.out else root / ".savings-engine" / "manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    total_files = sum(
        len(p["files"])
        for cat in manifest["categories"].values()
        for p in cat["providers"].values()
    ) + sum(len(cat["loose_files"]) for cat in manifest["categories"].values())

    print(
        json.dumps(
            {
                "ok": True,
                "manifest_path": str(out_path),
                "categories": len(manifest["categories"]),
                "files_tracked": total_files,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
