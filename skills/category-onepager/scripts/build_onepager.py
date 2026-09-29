#!/usr/bin/env python3
"""
build_onepager.py — Genera el one-pager PPTX de una categoría (playbook
`playbooks/02_onepager_categoria.md`, si existe dentro de la carpeta de contratos del
usuario) a partir de un JSON de especificación (no del JSON de contract-ingest
directamente — ver ../SKILL.md paso 2 sobre por qué hay un paso de traducción
intermedio) usando el motor real del skill bcg-slide-generator (clase BCGDeck).

Este script generaliza el enfoque de un one-pager de categoría hecho a mano
(columna izquierda de íconos, columna derecha con gráfico + tabla, callout
full-width, footnotes en la zona exenta de QA) para que sirva para cualquier
categoría, tomando el contenido de un archivo --json en vez de estar
hardcodeado, y estimando automáticamente el alto de cada fila de texto (antes
se ajustaba a mano fila por fila).

Uso:
    python3 build_onepager.py --json onepager_spec.json --out /ruta/salida.pptx
    python3 build_onepager.py --json onepager_spec.json
        (sin --out: versiona automáticamente en el directorio del --json)

Requiere que el skill bcg-slide-generator esté instalado en este entorno. Por defecto lo busca
automáticamente (ver find_default_skill_dir) porque su ruta de mount cambia entre sesiones e
instalaciones — nunca es la misma carpeta dos veces. Si la búsqueda automática no lo encuentra,
pasá `--skill-dir <ruta>` con la ruta real (Claude puede verla en su propio contexto como "Base
directory for this skill" apenas bcg-slide-generator se carga una vez).
"""
import argparse
import glob
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path


def find_default_skill_dir() -> str | None:
    """Busca bcg-slide-generator en ubicaciones típicas de mount de plugins, sin asumir un path
    fijo de sandbox/sesión (ese path incluye un slug aleatorio que cambia en cada sesión, y en una
    instalación distinta del plugin puede no existir /sessions/ en absoluto)."""
    candidates = []
    for pattern in (
        "/sessions/*/mnt/.claude/skills/bcg-slide-generator",
        "/sessions/*/mnt/*/skills/bcg-slide-generator",
        os.path.expanduser("~/.claude/skills/bcg-slide-generator"),
        "/var/folders/*/*/*/claude-hostloop-plugins/*/skills/bcg-slide-generator",
    ):
        candidates.extend(glob.glob(pattern))
    return candidates[0] if candidates else None


DEFAULT_SKILL_DIR = find_default_skill_dir()


def estimate_text_height(text: str, box_width_in: float, font_pt: float, line_height_factor: float = 1.3) -> float:
    """Estima el alto (in pulgadas) que ocupará `text` en un textbox de ancho
    `box_width_in` a tamaño `font_pt`, para poder apilar filas sin overlap ni
    tener que medir a mano (ver comentario original en build_slide_v2.py:
    'chars*pt*0.55/72 per line, pt/72*1.3 per line')."""
    avg_char_width_in = font_pt * 0.55 / 72
    chars_per_line = max(1, int(box_width_in / avg_char_width_in))
    n_lines = max(1, math.ceil(len(text) / chars_per_line))
    line_height_in = font_pt / 72 * line_height_factor
    return n_lines * line_height_in


def next_version_path(out_dir: Path, base_name: str) -> Path:
    """Nunca sobrescribe: busca versiones existentes <base_name>_v<N>.pptx en
    out_dir y devuelve la ruta para _v<N+1>. Regla no negociable del playbook."""
    pattern = re.compile(re.escape(base_name) + r"_v(\d+)\.pptx$")
    max_v = 0
    if out_dir.exists():
        for f in out_dir.iterdir():
            m = pattern.match(f.name)
            if m:
                max_v = max(max_v, int(m.group(1)))
    return out_dir / f"{base_name}_v{max_v + 1}.pptx"


def setup_engine(skill_dir: str, work_dir: Path):
    scripts_dir = work_dir / "scripts"
    assets_dir = work_dir / "assets"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("bcg_template.py", "pptx_utils.py"):
        dst = scripts_dir / fname
        if not dst.exists():
            shutil.copy(os.path.join(skill_dir, "scripts", fname), dst)
    if not assets_dir.exists():
        shutil.copytree(os.path.join(skill_dir, "assets"), assets_dir)
    sys.path.insert(0, str(scripts_dir))
    from bcg_template import BCGDeck, COLORS, DETAIL_CONTENT_START_Y, check_setup  # noqa: E402
    check_setup()
    return BCGDeck, COLORS, DETAIL_CONTENT_START_Y, assets_dir


def build(spec: dict, skill_dir: str, work_dir: Path):
    BCGDeck, COLORS, DETAIL_CONTENT_START_Y, assets_dir = setup_engine(skill_dir, work_dir)

    deck = BCGDeck(template_path=str(assets_dir / "BCG_Master_16-9_Default.pptx"))
    DARK = COLORS["DARK_TEXT"]
    GREEN = COLORS["BCG_GREEN"]

    slide = deck.add_content_slide(spec["headline"], source=None, layout="d_title_only", detail=True)

    CALLOUT_Y = 6.10
    CONTENT_BOTTOM = CALLOUT_Y - 0.05  # 6.05, igual que el script original

    deck.add_line(slide, 4.35, DETAIL_CONTENT_START_Y, 0, CONTENT_BOTTOM - DETAIL_CONTENT_START_Y,
                  color=GREEN, width=1.5)

    # ---------------- LEFT COLUMN ----------------
    LX, LW = 0.69, 3.51
    HEADING_H = 0.36
    deck.add_textbox(slide, spec.get("left_heading", "Productos y servicios de la categoría"),
                      LX, DETAIL_CONTENT_START_Y, LW, HEADING_H, sz=13, color=GREEN, bold=True)

    icon_size = 0.26
    title_desc_gap = 0.01
    row_y = DETAIL_CONTENT_START_Y + HEADING_H + 0.02
    text_x = LX + icon_size + 0.12
    text_w = LW - icon_size - 0.12

    for item in spec["left_items"]:
        title_h = estimate_text_height(item["title"], text_w, 11)
        desc_h = estimate_text_height(item["desc"], text_w, 10)
        deck.add_icon(slide, item.get("icon", "Global"), LX, row_y + 0.01, size=icon_size, color=GREEN)
        deck.add_textbox(slide, item["title"], text_x, row_y, text_w, title_h, sz=11, color=DARK, bold=True)
        deck.add_textbox(slide, item["desc"], text_x, row_y + title_h + title_desc_gap, text_w, desc_h,
                          sz=10, color=DARK)
        row_content_h = max(icon_size, title_h + title_desc_gap + desc_h)
        row_y += row_content_h

    if row_y > CONTENT_BOTTOM:
        print(f"⚠️  ADVERTENCIA: la columna izquierda termina en y={row_y:.2f}, "
              f"por debajo del límite y={CONTENT_BOTTOM:.2f} (zona del callout). "
              f"Reducí la cantidad de left_items o el largo de las descripciones "
              f"y volvé a correr — no ignores este warning sin revisar visualmente.",
              file=sys.stderr)

    # ---------------- RIGHT COLUMN ----------------
    RX, RW = 4.50, 8.15
    deck.add_textbox(slide, spec.get("chart_heading", "Monto total y % de participación por proveedor"),
                      RX, DETAIL_CONTENT_START_Y, RW, 0.26, sz=13, color=GREEN, bold=True)

    chart_y = DETAIL_CONTENT_START_Y + 0.30
    chart_h = spec.get("chart_h", 1.55)
    deck.add_chart(slide, "bar_horizontal",
                   categories=spec["chart_categories"],
                   series=[{"name": spec.get("chart_series_name", "Monto (CLP MM)"), "values": spec["chart_values"]}],
                   x=RX, y=chart_y, w=RW, h=chart_h,
                   data_labels=True, number_format="#,##0", colors=["29BA74"], legend=False)

    table_y = chart_y + chart_h + 0.15
    table_h = CONTENT_BOTTOM - table_y
    if table_h <= 0.3:
        print(f"⚠️  ADVERTENCIA: queda muy poco espacio para la tabla (h={table_h:.2f}). "
              f"Reducí chart_h o el número de filas de la tabla.", file=sys.stderr)

    table_header = spec["table_header"]
    table_data = [table_header] + spec["table_rows"]
    col_widths = spec.get("table_col_widths")
    if not col_widths:
        col_widths = [RW / len(table_header)] * len(table_header)

    deck.add_table(slide, table_data, x=RX, y=table_y, w=RW, h=table_h,
                    header=True, col_widths=col_widths, sz=spec.get("table_font_sz", 11), stripe=True)

    # ---------------- CALLOUT (full width) ----------------
    callout_h = 0.38
    deck.add_rounded_rectangle(slide, LX, CALLOUT_Y, 12.65 - LX, callout_h,
                                fill_color="FFFFFF", radius=16667, line_color=GREEN, line_width=1.25)
    deck.add_textbox(slide, spec["callout"], LX + 0.15, CALLOUT_Y, 12.65 - LX - 0.3, callout_h,
                      sz=12, color=GREEN, bold=True, valign="middle")

    # ---------------- FOOTNOTES (y>=6.60, zona exenta de QA) ----------------
    deck.add_textbox(slide, spec["footnote"], LX, 6.62, 12.65 - LX, 0.75, sz=8, color=COLORS["MED_GRAY"])

    return deck


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", required=True, help="Ruta al JSON de especificación del one-pager")
    ap.add_argument("--skill-dir", default=DEFAULT_SKILL_DIR,
                     help="Ruta al skill bcg-slide-generator (default: auto-detectada)")
    ap.add_argument("--work-dir", default=None, help="Directorio de trabajo temporal (default: junto al --json)")
    ap.add_argument("--out", default=None, help="Ruta de salida .pptx (default: versiona automáticamente)")
    args = ap.parse_args()

    if not args.skill_dir:
        print("❌ No se encontró bcg-slide-generator automáticamente. Pasá --skill-dir <ruta> con "
              "su ubicación real (aparece en el contexto de Claude como 'Base directory for this "
              "skill' apenas ese skill se carga una vez).", file=sys.stderr)
        sys.exit(1)

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"❌ No existe el archivo: {json_path}", file=sys.stderr)
        sys.exit(1)
    spec = json.loads(json_path.read_text(encoding="utf-8"))

    required = ["headline", "left_items", "chart_categories", "chart_values",
                "table_header", "table_rows", "callout", "footnote"]
    missing = [k for k in required if k not in spec]
    if missing:
        print(f"❌ Faltan campos obligatorios en el JSON de spec: {missing}", file=sys.stderr)
        sys.exit(1)

    work_dir = Path(args.work_dir) if args.work_dir else json_path.parent / "_onepager_build"

    if args.out:
        out_path = Path(args.out)
    else:
        base_name = spec.get("output_base_name") or (spec.get("categoria", "Categoria").replace(" ", "_") + "_OnePager")
        out_path = next_version_path(json_path.parent, base_name)

    deck = build(spec, args.skill_dir, work_dir)
    deck.save(str(out_path))
    print(f"✅ One-pager generado: {out_path}")
    print("SLIDE_COUNT:", deck.slide_count)


if __name__ == "__main__":
    main()
