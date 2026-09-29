#!/usr/bin/env python3
"""
diff_manifest.py — Compara el estado actual de la carpeta raíz de contratos
contra el último manifest guardado por build_manifest.py, y agrupa los
archivos nuevos/modificados/eliminados por categoría → proveedor, para que el
coordinador de "refrescar análisis de contratos" sepa exactamente qué
proveedores hay que reprocesar (sin tocar los que no cambiaron).

Uso:
    python3 diff_manifest.py --root "/ruta/a/Contratos" \
        [--manifest "/ruta/a/Contratos/.savings-engine/manifest.json"]

Requiere que build_manifest.py ya se haya corrido al menos una vez sobre esa
carpeta (es decir, que ya haya pasado un "iniciar análisis de contratos"). Si
no existe el manifest, termina con error explícito — no hay línea de base
contra la cual comparar.

No modifica nada en disco: solo reporta. El coordinador decide qué hacer con
el resultado (lanzar subagentes, actualizar el JSON de categoría, y volver a
correr build_manifest.py al final para fijar el nuevo estado).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_manifest import scan_root


def compare_files(old_files: dict, new_files: dict):
    """Devuelve (nuevos, modificados, eliminados) para un dict {relpath: {mtime,size}}."""
    nuevos, modificados, eliminados = [], [], []

    for relpath, stat in new_files.items():
        if relpath not in old_files:
            nuevos.append(relpath)
        else:
            old = old_files[relpath]
            if old.get("mtime") != stat.get("mtime") or old.get("size") != stat.get("size"):
                modificados.append(relpath)

    for relpath in old_files:
        if relpath not in new_files:
            eliminados.append(relpath)

    return sorted(nuevos), sorted(modificados), sorted(eliminados)


def diff(root: Path, manifest: dict) -> dict:
    current = scan_root(root)
    old_categories = manifest.get("categories", {})

    affected_providers = []
    new_categories = []
    loose_file_changes = []
    all_new, all_modified, all_deleted = [], [], []

    all_category_names = sorted(set(current.keys()) | set(old_categories.keys()))

    for cat_name in all_category_names:
        cur_cat = current.get(cat_name, {"providers": {}, "loose_files": {}})
        old_cat = old_categories.get(cat_name, {"providers": {}, "loose_files": {}})

        if cat_name not in old_categories:
            new_categories.append(cat_name)

        cur_providers = cur_cat.get("providers", {})
        old_providers = old_cat.get("providers", {})
        all_provider_folders = sorted(set(cur_providers.keys()) | set(old_providers.keys()))

        for provider_folder in all_provider_folders:
            cur_p = cur_providers.get(provider_folder)
            old_p = old_providers.get(provider_folder)

            cur_files = cur_p["files"] if cur_p else {}
            old_files = old_p["files"] if old_p else {}

            nuevos, modificados, eliminados = compare_files(old_files, cur_files)
            if not (nuevos or modificados or eliminados):
                continue

            all_new.extend(nuevos)
            all_modified.extend(modificados)
            all_deleted.extend(eliminados)

            ref = cur_p or old_p
            reasons = []
            if nuevos:
                reasons.append(f"{len(nuevos)} archivo(s) nuevo(s)")
            if modificados:
                reasons.append(f"{len(modificados)} archivo(s) modificado(s)")
            if eliminados:
                reasons.append(f"{len(eliminados)} archivo(s) eliminado(s) (no descargados/movidos)")

            affected_providers.append(
                {
                    "category": cat_name,
                    "provider_folder": provider_folder,
                    "provider_id": ref["provider_id"],
                    "provider_name": ref["provider_name"],
                    "reason": ", ".join(reasons),
                    "new_files": nuevos,
                    "modified_files": modificados,
                    "deleted_files": eliminados,
                    "is_new_provider": old_p is None,
                    "provider_removed": cur_p is None,
                }
            )

        cur_loose = cur_cat.get("loose_files", {})
        old_loose = old_cat.get("loose_files", {})
        nuevos, modificados, eliminados = compare_files(old_loose, cur_loose)
        if nuevos or modificados or eliminados:
            all_new.extend(nuevos)
            all_modified.extend(modificados)
            all_deleted.extend(eliminados)
            loose_file_changes.append(
                {
                    "category": cat_name,
                    "new_files": nuevos,
                    "modified_files": modificados,
                    "deleted_files": eliminados,
                }
            )

    return {
        "manifest_generated_at": manifest.get("generated_at"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "has_changes": bool(affected_providers or loose_file_changes or new_categories),
        "new_categories": new_categories,
        "affected_providers": affected_providers,
        "loose_file_changes": loose_file_changes,
        "summary": {
            "files_new": len(all_new),
            "files_modified": len(all_modified),
            "files_deleted": len(all_deleted),
            "providers_affected": len(affected_providers),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, help="Carpeta raíz de contratos (contracts_root)")
    parser.add_argument(
        "--manifest",
        default=None,
        help="Ruta al manifest previo (default: <root>/.savings-engine/manifest.json)",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser() if args.manifest else root / ".savings-engine" / "manifest.json"

    if not manifest_path.exists():
        print(
            json.dumps(
                {
                    "error": (
                        f"No existe manifest previo en {manifest_path}. "
                        "Corré 'iniciar análisis de contratos' al menos una vez antes de refrescar."
                    )
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Manifest corrupto en {manifest_path}: {e}"}), file=sys.stderr)
        sys.exit(1)

    try:
        result = diff(root, manifest)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
