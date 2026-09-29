#!/usr/bin/env python3
"""
merge_cost_slide.py — Inyecta la única slide de "Estructura de costos e
índices" (gráficos nativos de PowerPoint) dentro del PPTX "one-pager" de una
categoría, implementando en código el procedimiento OOXML manual descrito en
`playbooks/03_merge_slide_costos_onepager.md` (si existe dentro de la carpeta de contratos
del usuario).

Ese playbook es la fuente de verdad — este script es su traducción mecánica,
no un reemplazo de la doble validación (estructural + visual) que exige.
python-pptx/LibreOffice no pueden copiar slides con gráficos nativos (c:chart)
entre presentaciones sin romper relaciones — por eso esto se hace a mano sobre
el ZIP/XML del paquete, copiando la cadena completa de dependencias
(slide -> slideLayout -> slideMaster -> theme, slide -> chart -> workbook
embebido) y renumerando IDs para no colisionar con las partes ya existentes en
el destino.

Este script NUNCA sobreescribe el one-pager original: siempre escribe a un
archivo nuevo (versionado automáticamente si no se pasa --out). El paso 7 del
playbook ("reemplazar el archivo final") es una decisión humana posterior a la
doble QA, no algo que este script haga por su cuenta.

Uso:
    python3 merge_cost_slide.py --src Cost_Driver_Development_X.pptx \
        --dest X_LongTail_OnePager.pptx
        (sin --out: versiona automáticamente <dest>_merged_v<N>.pptx)

Requiere python-pptx (solo para la validación estructural final — el merge en
sí no lo usa, ver playbook sección "Por qué no usar herramientas estándar").
"""
import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

TYPE_SLIDE_LAYOUT = f"{NS_R}/slideLayout"
TYPE_SLIDE_MASTER = f"{NS_R}/slideMaster"
TYPE_THEME = f"{NS_R}/theme"
TYPE_CHART = f"{NS_R}/chart"
TYPE_PACKAGE = f"{NS_R}/package"
TYPE_IMAGE = f"{NS_R}/image"
TYPE_CHART_COLOR_STYLE = "http://schemas.microsoft.com/office/2011/relationships/chartColorStyle"
TYPE_CHART_STYLE = "http://schemas.microsoft.com/office/2011/relationships/chartStyle"

KNOWN_MEDIA_TYPES = {TYPE_IMAGE}


# --------------------------------------------------------------------------
# Utilidades XML (texto/regex, no DOM) — ver pptx skill: round-tripar OOXML
# por ElementTree reescribe prefijos de namespace y corrompe el archivo. Para
# las partes "de contenido" (slide/layout/master/chart) hacemos cirugía de
# texto quirúrgica; para los archivos de bookkeeping pequeños (.rels,
# presentation.xml, [Content_Types].xml) también, por consistencia y para no
# depender de un parser XML adicional.
# --------------------------------------------------------------------------

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_rels(rels_path: Path) -> dict:
    """Devuelve {Id: {'type':..., 'target':...}} de un archivo .rels."""
    if not rels_path.exists():
        return {}
    text = read(rels_path)
    rels = {}
    for m in re.finditer(
        r'<Relationship\s+([^>]*?)/?>', text
    ):
        attrs_text = m.group(1)
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', attrs_text))
        if "Id" in attrs:
            rels[attrs["Id"]] = {"type": attrs.get("Type", ""), "target": attrs.get("Target", "")}
    return rels


def resolve_target(base_dir: Path, target: str) -> Path:
    """Resuelve un Target relativo de .rels (ej. '../charts/chart1.xml')
    respecto del directorio *padre* de la parte que contiene el .rels
    (ej. ppt/slides/_rels/slide1.xml.rels -> base_dir=ppt/slides/)."""
    return (base_dir / target).resolve()


def next_free_number(dir_path: Path, prefix: str, ext: str) -> int:
    if not dir_path.exists():
        return 1
    pattern = re.compile(re.escape(prefix) + r"(\d+)" + re.escape(ext) + r"$")
    max_n = 0
    for f in dir_path.iterdir():
        m = pattern.match(f.name)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def unique_filename(dir_path: Path, filename: str) -> str:
    """Si filename ya existe en dir_path, le agrega _mergeN antes de la
    extensión hasta encontrar uno libre."""
    if not (dir_path / filename).exists():
        return filename
    stem, dot, ext = filename.rpartition(".")
    if not dot:
        stem, ext = filename, ""
    n = 1
    while True:
        candidate = f"{stem}_merge{n}.{ext}" if ext else f"{stem}_merge{n}"
        if not (dir_path / candidate).exists():
            return candidate
        n += 1


def next_version_out_path(dest_pptx: Path) -> Path:
    base = dest_pptx.stem
    out_dir = dest_pptx.parent
    pattern = re.compile(re.escape(base) + r"_merged_v(\d+)\.pptx$")
    max_v = 0
    for f in out_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            max_v = max(max_v, int(m.group(1)))
    return out_dir / f"{base}_merged_v{max_v + 1}.pptx"


def strip_cust_data(xml_text: str) -> str:
    """Elimina <p:custDataLst>...</p:custDataLst> (referencias a tags/BCG
    metadata) — no tienen impacto visual, ver playbook 'Conceptos clave'."""
    return re.sub(r"<p:custDataLst>.*?</p:custDataLst>", "", xml_text, flags=re.DOTALL)


def strip_thinkcell_marker(xml_text: str) -> str:
    """Elimina el <p:graphicFrame> del marcador oculto de thinkcell
    (name='think-cell data - do not delete'), si existe. No es el gráfico
    visible — es un objeto OLE de bookkeeping, seguro de eliminar."""
    marker = "think-cell data - do not delete"
    idx = xml_text.find(marker)
    if idx == -1:
        return xml_text
    start = xml_text.rfind("<p:graphicFrame", 0, idx)
    end = xml_text.find("</p:graphicFrame>", idx)
    if start == -1 or end == -1:
        print("⚠️  ADVERTENCIA: se encontró el marcador de thinkcell pero no se pudo "
              "delimitar el <p:graphicFrame> completo — no se eliminó nada, revisá a mano.",
              file=sys.stderr)
        return xml_text
    end += len("</p:graphicFrame>")
    removed = xml_text[start:end]
    print(f"  - Marcador thinkcell oculto eliminado ({len(removed)} chars).")
    return xml_text[:start] + xml_text[end:]


def find_used_rids(xml_text: str) -> set:
    """Todos los r:id / r:embed que sigan presentes en el XML de la slide
    después de la limpieza — deberían ser, normalmente, solo los charts."""
    return set(re.findall(r'r:(?:id|embed)="([^"]+)"', xml_text))


def content_type_lookup(content_types_path: Path):
    """Lee [Content_Types].xml y devuelve (defaults, overrides):
    defaults: {extension: content_type}
    overrides: {partname: content_type}  (partname empieza con '/')"""
    text = read(content_types_path)
    defaults = dict(re.findall(r'<Default\s+Extension="([^"]+)"\s+ContentType="([^"]+)"\s*/>', text))
    overrides = dict(re.findall(r'<Override\s+PartName="([^"]+)"\s+ContentType="([^"]+)"\s*/>', text))
    return defaults, overrides


def content_type_for(defaults: dict, overrides: dict, partname: str) -> str:
    if partname in overrides:
        return overrides[partname]
    ext = partname.rsplit(".", 1)[-1]
    return defaults.get(ext, "")


def add_content_type_default(content_types_path: Path, ext: str, content_type: str):
    text = read(content_types_path)
    if re.search(rf'<Default\s+Extension="{re.escape(ext)}"', text):
        return
    # OJO: no usar text.index(">") a secas — matchea el '>' de cierre de
    # '<?xml ... ?>' (que también contiene '>'), no el de '<Types ...>', y
    # el insert queda ANTES de <Types>, corrompiendo el XML. Hay que anclar
    # específicamente al tag <Types ...> de apertura.
    m = re.search(r"<Types[^>]*>", text)
    if not m:
        print(f"❌ No se encontró el tag <Types> en {content_types_path} — no se pudo registrar "
              f"el Default Extension='{ext}'.", file=sys.stderr)
        return
    insert_at = m.end()
    new_entry = f'<Default Extension="{ext}" ContentType="{content_type}"/>'
    write(content_types_path, text[:insert_at] + new_entry + text[insert_at:])


def add_content_type_override(content_types_path: Path, partname: str, content_type: str):
    text = read(content_types_path)
    if f'PartName="{partname}"' in text:
        return
    new_entry = f'<Override PartName="{partname}" ContentType="{content_type}"/>'
    write(content_types_path, text.replace("</Types>", new_entry + "</Types>"))


def write_rels_file(rels_path: Path, relationships: list):
    """relationships: lista de dicts {'id','type','target'} (target relativo,
    ya calculado por el caller)."""
    body = "".join(
        f'<Relationship Id="{r["id"]}" Type="{r["type"]}" Target="{r["target"]}"/>'
        for r in relationships
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{REL_NS}">{body}</Relationships>'
    )
    write(rels_path, xml)


# --------------------------------------------------------------------------
# Merge principal
# --------------------------------------------------------------------------

def merge(src_pptx: Path, dest_pptx: Path, work_dir: Path, visual_qa_hint: bool = True) -> Path:
    src_dir = work_dir / "src"
    dest_dir = work_dir / "dest"
    for d in (src_dir, dest_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    with zipfile.ZipFile(src_pptx) as z:
        z.extractall(src_dir)
    with zipfile.ZipFile(dest_pptx) as z:
        z.extractall(dest_dir)

    src_pres = read(src_dir / "ppt" / "presentation.xml")
    n_src_slides = len(re.findall(r"<p:sldId ", src_pres))
    if n_src_slides != 1:
        print(f"❌ El pptx origen tiene {n_src_slides} slides — este script asume exactamente "
              f"1 (la slide de 'Estructura de costos e índices'). Abortando: revisá a mano.",
              file=sys.stderr)
        sys.exit(1)

    src_defaults, src_overrides = content_type_lookup(src_dir / "[Content_Types].xml")

    # ---- 1. Cadena slide -> slideLayout -> slideMaster -> theme ----
    src_slide_rels = parse_rels(src_dir / "ppt" / "slides" / "_rels" / "slide1.xml.rels")
    layout_rel = next((r for r in src_slide_rels.values() if r["type"] == TYPE_SLIDE_LAYOUT), None)
    if not layout_rel:
        print("❌ La slide origen no tiene relación a un slideLayout. Abortando.", file=sys.stderr)
        sys.exit(1)
    src_layout_path = resolve_target(src_dir / "ppt" / "slides", layout_rel["target"])
    src_layout_num_m = re.search(r"slideLayout(\d+)\.xml$", src_layout_path.name)
    src_layout_rels = parse_rels(src_layout_path.parent / "_rels" / (src_layout_path.name + ".rels"))

    master_rel_in_layout = next((r for r in src_layout_rels.values() if r["type"] == TYPE_SLIDE_MASTER), None)
    if not master_rel_in_layout:
        print("❌ El slideLayout origen no tiene relación a un slideMaster. Abortando.", file=sys.stderr)
        sys.exit(1)
    src_master_path = resolve_target(src_layout_path.parent, master_rel_in_layout["target"])
    src_master_rels = parse_rels(src_master_path.parent / "_rels" / (src_master_path.name + ".rels"))

    theme_rid_in_master = next((rid for rid, r in src_master_rels.items() if r["type"] == TYPE_THEME), None)
    if not theme_rid_in_master:
        print("❌ El slideMaster origen no tiene relación a un theme. Abortando.", file=sys.stderr)
        sys.exit(1)
    src_theme_path = resolve_target(src_master_path.parent, src_master_rels[theme_rid_in_master]["target"])

    # rId del layout DENTRO del master (el que hay que preservar en sldLayoutIdLst)
    layout_rid_in_master = next(
        rid for rid, r in src_master_rels.items()
        if r["type"] == TYPE_SLIDE_LAYOUT and resolve_target(src_master_path.parent, r["target"]) == src_layout_path
    )

    print(f"Cadena de dependencias detectada: slide1.xml -> {src_layout_path.name} -> "
          f"{src_master_path.name} -> {src_theme_path.name}")

    # ---- Números libres en destino ----
    dest_themes = dest_dir / "ppt" / "theme"
    dest_masters = dest_dir / "ppt" / "slideMasters"
    dest_layouts = dest_dir / "ppt" / "slideLayouts"
    dest_slides = dest_dir / "ppt" / "slides"
    dest_charts = dest_dir / "ppt" / "charts"
    dest_embeddings = dest_dir / "ppt" / "embeddings"
    dest_media = dest_dir / "ppt" / "media"

    new_theme_n = next_free_number(dest_themes, "theme", ".xml")
    new_master_n = next_free_number(dest_masters, "slideMaster", ".xml")
    new_layout_n = next_free_number(dest_layouts, "slideLayout", ".xml")
    new_slide_n = next_free_number(dest_slides, "slide", ".xml")

    new_theme_file = f"theme{new_theme_n}.xml"
    new_master_file = f"slideMaster{new_master_n}.xml"
    new_layout_file = f"slideLayout{new_layout_n}.xml"
    new_slide_file = f"slide{new_slide_n}.xml"

    # ---- Copiar theme ----
    shutil.copy(src_theme_path, dest_themes / new_theme_file)
    add_content_type_override(
        dest_dir / "[Content_Types].xml", f"/ppt/theme/{new_theme_file}",
        content_type_for(src_defaults, src_overrides, f"/ppt/theme/{src_theme_path.name}"),
    )

    # ---- Copiar slideMaster (recortado a 1 solo layout) ----
    master_xml = read(src_master_path)
    master_xml = strip_cust_data(master_xml)
    layout_id_entries = re.findall(r'<p:sldLayoutId[^/]*/>', master_xml)
    kept_entries = [e for e in layout_id_entries if f'r:id="{layout_rid_in_master}"' in e]
    if len(kept_entries) != 1:
        print(f"⚠️  ADVERTENCIA: se esperaba 1 <p:sldLayoutId> con r:id={layout_rid_in_master} "
              f"en el master, se encontraron {len(kept_entries)}. Revisá el resultado a mano.",
              file=sys.stderr)
    list_block_m = re.search(r"<p:sldLayoutIdLst>.*?</p:sldLayoutIdLst>", master_xml, flags=re.DOTALL)
    if list_block_m and kept_entries:
        new_list_block = "<p:sldLayoutIdLst>" + "".join(kept_entries) + "</p:sldLayoutIdLst>"
        master_xml = master_xml[:list_block_m.start()] + new_list_block + master_xml[list_block_m.end():]
        print(f"  - slideMaster recortado: {len(layout_id_entries)} layouts -> 1 "
              f"(se evita copiar los ~{len(layout_id_entries)} layouts completos de la plantilla).")
    write(dest_masters / new_master_file, master_xml)

    write_rels_file(
        dest_masters / "_rels" / (new_master_file + ".rels"),
        [
            {"id": layout_rid_in_master, "type": TYPE_SLIDE_LAYOUT, "target": f"../slideLayouts/{new_layout_file}"},
            {"id": theme_rid_in_master, "type": TYPE_THEME, "target": f"../theme/{new_theme_file}"},
        ],
    )
    add_content_type_override(
        dest_dir / "[Content_Types].xml", f"/ppt/slideMasters/{new_master_file}",
        content_type_for(src_defaults, src_overrides, f"/ppt/slideMasters/{src_master_path.name}"),
    )

    # ---- Copiar slideLayout ----
    layout_xml = strip_cust_data(read(src_layout_path))
    write(dest_layouts / new_layout_file, layout_xml)

    layout_new_rels = [{"id": layout_rid_in_master, "type": TYPE_SLIDE_MASTER, "target": f"../slideMasters/{new_master_file}"}]
    for rid, r in src_layout_rels.items():
        if r["type"] in KNOWN_MEDIA_TYPES:
            media_src = resolve_target(src_layout_path.parent, r["target"])
            new_name = unique_filename(dest_media, media_src.name)
            dest_media.mkdir(parents=True, exist_ok=True)
            shutil.copy(media_src, dest_media / new_name)
            layout_new_rels.append({"id": rid, "type": r["type"], "target": f"../media/{new_name}"})
        elif r["type"] == TYPE_SLIDE_MASTER:
            continue  # ya agregado arriba con el rId correcto
        else:
            print(f"⚠️  ADVERTENCIA: relación no manejada explícitamente en slideLayout "
                  f"(rId={rid}, type={r['type']}). No se copió — revisá visualmente si falta algo.",
                  file=sys.stderr)
    write_rels_file(dest_layouts / "_rels" / (new_layout_file + ".rels"), layout_new_rels)
    add_content_type_override(
        dest_dir / "[Content_Types].xml", f"/ppt/slideLayouts/{new_layout_file}",
        content_type_for(src_defaults, src_overrides, f"/ppt/slideLayouts/{src_layout_path.name}"),
    )

    # ---- Copiar slide + charts + workbooks embebidos ----
    slide_xml = read(src_dir / "ppt" / "slides" / "slide1.xml")
    slide_xml = strip_thinkcell_marker(slide_xml)
    slide_xml = strip_cust_data(slide_xml)
    used_rids = find_used_rids(slide_xml)
    write(dest_slides / new_slide_file, slide_xml)

    slide_new_rels = [{"id": "rIdLayout", "type": TYPE_SLIDE_LAYOUT, "target": f"../slideLayouts/{new_layout_file}"}]
    n_charts_copied = 0
    for rid in used_rids:
        r = src_slide_rels.get(rid)
        if not r:
            print(f"⚠️  ADVERTENCIA: la slide referencia r:id={rid} que no está en su .rels de "
                  f"origen. Ignorado.", file=sys.stderr)
            continue
        if r["type"] != TYPE_CHART:
            print(f"⚠️  ADVERTENCIA: relación r:id={rid} usada en la slide no es de tipo chart "
                  f"({r['type']}) — no manejada explícitamente, revisá visualmente.", file=sys.stderr)
            continue
        chart_src_path = resolve_target(src_dir / "ppt" / "slides", r["target"])
        new_chart_n = next_free_number(dest_charts, "chart", ".xml")
        new_chart_file = f"chart{new_chart_n}.xml"
        dest_charts.mkdir(parents=True, exist_ok=True)
        shutil.copy(chart_src_path, dest_charts / new_chart_file)
        add_content_type_override(
            dest_dir / "[Content_Types].xml", f"/ppt/charts/{new_chart_file}",
            content_type_for(src_defaults, src_overrides, f"/ppt/charts/{chart_src_path.name}"),
        )
        slide_new_rels.append({"id": rid, "type": TYPE_CHART, "target": f"../charts/{new_chart_file}"})

        chart_src_rels_path = chart_src_path.parent / "_rels" / (chart_src_path.name + ".rels")
        chart_src_rels = parse_rels(chart_src_rels_path)
        chart_new_rels = []
        for crid, cr in chart_src_rels.items():
            ctarget_src = resolve_target(chart_src_path.parent, cr["target"])
            if cr["type"] == TYPE_PACKAGE:
                dest_embeddings.mkdir(parents=True, exist_ok=True)
                new_name = unique_filename(dest_embeddings, ctarget_src.name)
                shutil.copy(ctarget_src, dest_embeddings / new_name)
                ext = new_name.rsplit(".", 1)[-1]
                default_ct = src_defaults.get(ext, "")
                if default_ct:
                    add_content_type_default(dest_dir / "[Content_Types].xml", ext, default_ct)
                chart_new_rels.append({"id": crid, "type": cr["type"], "target": f"../embeddings/{new_name}"})
            elif cr["type"] in (TYPE_CHART_COLOR_STYLE, TYPE_CHART_STYLE):
                prefix = "colors" if cr["type"] == TYPE_CHART_COLOR_STYLE else "style"
                new_n = next_free_number(dest_charts, prefix, ".xml")
                new_name = f"{prefix}{new_n}.xml"
                shutil.copy(ctarget_src, dest_charts / new_name)
                add_content_type_override(
                    dest_dir / "[Content_Types].xml", f"/ppt/charts/{new_name}",
                    content_type_for(src_defaults, src_overrides, f"/ppt/charts/{ctarget_src.name}"),
                )
                chart_new_rels.append({"id": crid, "type": cr["type"], "target": f"{new_name}"})
            else:
                print(f"⚠️  ADVERTENCIA: relación no manejada en chart {chart_src_path.name} "
                      f"(rId={crid}, type={cr['type']}). No se copió.", file=sys.stderr)
        write_rels_file(dest_charts / "_rels" / (new_chart_file + ".rels"), chart_new_rels)
        n_charts_copied += 1

    write_rels_file(dest_slides / "_rels" / (new_slide_file + ".rels"), slide_new_rels)
    add_content_type_override(
        dest_dir / "[Content_Types].xml", f"/ppt/slides/{new_slide_file}",
        content_type_for(src_defaults, src_overrides, f"/ppt/slides/slide1.xml"),
    )
    print(f"  - {n_charts_copied} chart(s) nativo(s) copiado(s) con sus workbooks embebidos.")

    # ---- Registrar slide + slideMaster en presentation.xml / .rels ----
    pres_rels_path = dest_dir / "ppt" / "_rels" / "presentation.xml.rels"
    pres_rels_text = read(pres_rels_path)
    existing_rids = [int(n) for n in re.findall(r'Id="rId(\d+)"', pres_rels_text)]
    max_rid = max(existing_rids) if existing_rids else 0
    rid_master = f"rId{max_rid + 1}"
    rid_slide = f"rId{max_rid + 2}"
    new_pres_rels_entries = (
        f'<Relationship Id="{rid_master}" Type="{TYPE_SLIDE_MASTER}" '
        f'Target="slideMasters/{new_master_file}"/>'
        f'<Relationship Id="{rid_slide}" Type="{NS_R}/slide" Target="slides/{new_slide_file}"/>'
    )
    write(pres_rels_path, pres_rels_text.replace("</Relationships>", new_pres_rels_entries + "</Relationships>"))

    pres_path = dest_dir / "ppt" / "presentation.xml"
    pres_text = read(pres_path)
    existing_ids = [int(n) for n in re.findall(r'<p:sld(?:MasterId|Id)\s+id="(\d+)"', pres_text)]
    max_id = max(existing_ids) if existing_ids else 2147483647
    new_master_id = max_id + 1
    new_slide_id = max_id + 2
    pres_text = re.sub(
        r"</p:sldMasterIdLst>",
        f'<p:sldMasterId id="{new_master_id}" r:id="{rid_master}"/></p:sldMasterIdLst>',
        pres_text, count=1,
    )
    pres_text = re.sub(
        r"</p:sldIdLst>",
        f'<p:sldId id="{new_slide_id}" r:id="{rid_slide}"/></p:sldIdLst>',
        pres_text, count=1,
    )
    write(pres_path, pres_text)
    print(f"  - Registrado en presentation.xml: sldMasterId={new_master_id} ({rid_master}), "
          f"sldId={new_slide_id} ({rid_slide}).")

    # ---- Empaquetar ----
    out_path = next_version_out_path(dest_pptx)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in dest_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(dest_dir))

    return out_path


def validate_structural(out_path: Path, expected_slides: int):
    try:
        from pptx import Presentation
    except ImportError:
        print("⚠️  python-pptx no está instalado — no se pudo correr la validación estructural. "
              "Instalalo (pip install python-pptx) antes de dar esto por bueno.", file=sys.stderr)
        return False
    prs = Presentation(str(out_path))
    n = len(prs.slides)
    ok = n == expected_slides
    print(f"{'✅' if ok else '❌'} Validación estructural (python-pptx): {n} slides "
          f"(esperado: {expected_slides}).")
    last_slide = prs.slides[n - 1]
    texts = [sh.text_frame.text for sh in last_slide.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
    n_charts = sum(1 for sh in last_slide.shapes if sh.has_chart)
    print(f"   Última slide: {n_charts} chart(s) nativo(s) detectado(s) por python-pptx, "
          f"{len(texts)} cuadro(s) de texto no vacío(s).")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="PPTX origen (1 slide, 'Estructura de costos e índices')")
    ap.add_argument("--dest", required=True, help="PPTX destino (one-pager de la categoría)")
    ap.add_argument("--out", default=None, help="Ruta de salida (default: versiona automáticamente)")
    ap.add_argument("--work-dir", default=None, help="Directorio de trabajo temporal")
    args = ap.parse_args()

    src_pptx = Path(args.src)
    dest_pptx = Path(args.dest)
    if not src_pptx.exists():
        print(f"❌ No existe el archivo origen: {src_pptx}", file=sys.stderr)
        sys.exit(1)
    if not dest_pptx.exists():
        print(f"❌ No existe el archivo destino: {dest_pptx}", file=sys.stderr)
        sys.exit(1)

    with zipfile.ZipFile(dest_pptx) as z:
        dest_pres = z.read("ppt/presentation.xml").decode("utf-8")
    n_dest_slides_before = len(re.findall(r"<p:sldId ", dest_pres))

    work_dir = Path(args.work_dir) if args.work_dir else dest_pptx.parent / "_merge_cost_slide_build"

    out_path = merge(src_pptx, dest_pptx, work_dir)
    if args.out:
        custom_out = Path(args.out)
        shutil.move(out_path, custom_out)
        out_path = custom_out

    print(f"✅ Merge completado: {out_path}")
    validate_structural(out_path, n_dest_slides_before + 1)
    print(
        "\n⚠️  RECORDATORIO (no negociable, ver playbook 03 paso 6): esto NO reemplaza la QA "
        "visual. Convertí a PDF con LibreOffice headless y rasterizá con pdftoppm para mirar la "
        "slide nueva — chequeá que los gráficos rendericen con datos y estilos correctos, que no "
        "haya mensajes de archivo dañado, y que el resto de las slides no se haya alterado. Solo "
        "después de esa inspección visual reemplazá el one-pager original (paso 7)."
    )


if __name__ == "__main__":
    main()
