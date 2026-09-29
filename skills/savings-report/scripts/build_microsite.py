#!/usr/bin/env python3
"""
build_microsite.py — Empaqueta un `microsite_data.json` autorado (ver
skills/savings-report/references/microsite_data_schema.md) en un `datos_vN.js` versionado, y
copia el template genérico `index_template.html` a la carpeta de salida como `index.html` (una
sola vez — el HTML nunca cambia entre corridas de la misma categoría).

Este script es al Modo B (Microsite Buscador) lo que `build_onepager.py` es a `category-onepager`:
solo renderiza/empaqueta lo que ya se decidió y redactó en el chat. No inventa contenido, no
corre `derive_audit_hints.py` por vos (corré eso antes, a mano, y pegá el resultado en
`microsite_data.json` completando los campos "TODO" con juicio propio).

Uso:
    python3 build_microsite.py --json microsite_data.json --out-dir "<carpeta Microsite Buscador>"

El JSON de entrada debe tener la forma exacta de `window.MICROSITE_DATA` (ver el esquema) —
este script solo valida presencia de las claves de primer nivel y escribe, nunca reinterpreta
ni completa contenido faltante.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REQUIRED_TOP_LEVEL = [
    "categoria",
    "cliente",
    "total_contratos",
    "fecha_extraccion",
    "contratos",
    "auditoria_contratos",
    "onepager_resumen",
]

TEMPLATE_REL_PATH = Path(__file__).resolve().parent.parent / "assets" / "microsite" / "index_template.html"


def find_todos(obj, path=""):
    """Recorre el JSON buscando strings 'TODO' sueltos, para avisar antes de empaquetar —
    típicamente compromiso_volumen_sla / hallazgo_principal_fila que quedaron sin completar
    después de derive_audit_hints.py."""
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(find_todos(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_todos(v, f"{path}[{i}]"))
    elif isinstance(obj, str) and obj.strip().upper() == "TODO":
        hits.append(path)
    return hits


def next_version_path(out_dir: Path, base_name: str = "datos") -> Path:
    """Nunca sobrescribe: busca datos_v<N>.js existentes en out_dir y devuelve la ruta para
    _v<N+1>.js — misma regla de versionado que build_onepager.py / merge_cost_slide.py."""
    pattern = re.compile(re.escape(base_name) + r"_v(\d+)\.js$")
    max_v = 0
    if out_dir.exists():
        for f in out_dir.iterdir():
            m = pattern.match(f.name)
            if m:
                max_v = max(max_v, int(m.group(1)))
    return out_dir / f"{base_name}_v{max_v + 1}.js"


def build_datos_js(spec: dict, version_label: str) -> str:
    header = (
        f"// datos.js — generado por build_microsite.py — {version_label}\n"
        f"// Categoría: {spec.get('categoria', 'No especificado')}\n"
        f"// No editar a mano: este archivo se reconstruye a partir de microsite_data.json.\n"
        f"// El HTML (index.html) es 100% genérico y no depende de esta versión — nunca hace\n"
        f"// falta tocarlo al actualizar los datos.\n"
    )
    body = "window.MICROSITE_DATA = " + json.dumps(spec, ensure_ascii=False, indent=2) + ";\n"
    return header + body


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", required=True, help="Ruta al microsite_data.json ya redactado")
    ap.add_argument("--out-dir", required=True, help="Carpeta de salida (ej. '<Categoría>/Outputs/Microsite Buscador')")
    ap.add_argument("--template", default=str(TEMPLATE_REL_PATH), help="Ruta al index_template.html (default: el bundleado en este skill)")
    ap.add_argument("--force-html", action="store_true", help="Sobrescribir index.html aunque ya exista (normalmente innecesario: el HTML no cambia entre versiones)")
    args = ap.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"❌ No existe el archivo: {json_path}", file=sys.stderr)
        sys.exit(1)
    spec = json.loads(json_path.read_text(encoding="utf-8"))

    missing = [k for k in REQUIRED_TOP_LEVEL if k not in spec]
    if missing:
        print(f"❌ Faltan claves obligatorias de primer nivel en el JSON: {missing}", file=sys.stderr)
        sys.exit(1)

    todos = find_todos(spec)
    if todos:
        print("⚠️  ADVERTENCIA: el JSON todavía tiene campos 'TODO' sin completar (revisión/juicio "
              "pendiente en el chat, no los dejes así en la entrega):", file=sys.stderr)
        for path in todos:
            print(f"    - {path}", file=sys.stderr)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    datos_path = next_version_path(out_dir)
    version_label = datos_path.stem  # ej. "datos_v3"
    datos_path.write_text(build_datos_js(spec, version_label), encoding="utf-8")
    print(f"✅ Datos empaquetados: {datos_path}")

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"❌ No existe el template: {template_path}", file=sys.stderr)
        sys.exit(1)

    index_path = out_dir / "index.html"
    if index_path.exists() and not args.force_html:
        print(f"ℹ️  index.html ya existe en {out_dir} — no se sobrescribe (usá --force-html si "
              f"cambió el template genérico y hay que actualizarlo). El HTML no depende de la "
              f"versión de datos, así que normalmente no hace falta tocarlo.")
    else:
        shutil.copy(template_path, index_path)
        print(f"✅ index.html copiado: {index_path}")

    # index_template.html carga los datos con un <script src="datos.js"> fijo (por diseño: así
    # el HTML nunca necesita tocarse por versión). Eso significa que "datos.js" en sí NO seguía
    # la regla general de "nunca sobrescribir" del resto del pipeline — es la única excepción
    # deliberada: es un archivo "vivo" (el que el navegador realmente carga), no una versión de
    # entrega. El historial real de versiones vive en datos_vN.js (ese sí nunca se sobrescribe,
    # sirve de auditoría/rollback) y datos.js siempre es una copia idéntica de la vN más reciente.
    live_path = out_dir / "datos.js"
    live_path.write_text(build_datos_js(spec, version_label + " (copia viva de datos.js)"), encoding="utf-8")
    print(f"✅ datos.js (vivo, sobrescrito por diseño) actualizado desde {datos_path.name}")

    print("\nSiguiente paso: QA obligatoria (ver SKILL.md, Modo B, sección de QA) antes de "
          "entregar — abrir index.html y validar visualmente las 3 pestañas, no solo confiar en "
          "esta validación estructural.")


if __name__ == "__main__":
    main()
