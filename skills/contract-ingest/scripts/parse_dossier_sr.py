#!/usr/bin/env python3
"""
parse_dossier_sr.py — Deriva mecánicamente la parte anclada/numérica de `dossier_savingsradar`
(ver `skills/contract-ingest/references/schema.md`) a partir del `.pptx` "Dossier SR"
(`<Proveedor>_Negotiation_Dossier.pptx`) que suele acompañar a cada carpeta de proveedor bajo
`Dossier SR/`. "SR" = SavingsRadar — se confirmó vía el pie de página del propio PPTX
("Source: ... SavingsRadar Tool"), no "Solicitud de Renegociación" como se asumió al principio.

Qué deriva mecánicamente (sin juicio de Claude), leyendo la slide "Key facts & information:
Overview of Supplier, opportunity & tactics" (confirmado con el mismo layout/frases ancla en 2
proveedores reales de Transporte de Personal — FLEX SERVICIOS Y LOGISTICA LIMITADA y COMERCIAL
SERPAN LTDA — solo cambian los números y el nombre del proveedor):
- `negociacion_oportunidad_pct` / `negociacion_oportunidad_monto_musd` — línea "Negotiation
  Opportunity: X M$ (Y%)".
- `spend_musd` — línea "Spend: X M$".
- `supplier_name_en_dossier` — línea "Supplier Name: ...", para cruzar contra `proveedor` del
  registro y detectar si el dossier corresponde al proveedor equivocado.
- `power_balance_resumen` — la frase completa que sigue a "Power balance evaluation" (cita
  textual, no síntesis — es mecánico en el sentido de que es un extracto literal, no un juicio).
- `power_balance_score_overall` — el número solo bajo "Overall" antes de "Supplier margins".
- `mdo_pct` / `mdo_addressable_spend_musd` / `mdo_monto_musd` — bloque "Most desired outcome (MDO)".
- `target_pct` / `target_addressable_spend_musd` / `target_monto_musd` — bloque "Target for
  Supplier".
- `laa_pct` / `laa_addressable_spend_musd` / `laa_monto_musd` — bloque "Least acceptable
  agreement (LAA)".

Qué NO deriva (deliberado — requiere lectura y juicio de Claude en el chat, leyendo las slides de
SWOT / Negotiation Strategy / Argumentation Map del mismo dossier):
- `resumen_estrategia_negociacion`: síntesis del "so-what" de negociación para este proveedor
  (objetivos, palancas, argumentos) — no es una cifra a copiar, es juicio analítico igual que
  `hallazgo_principal_fila` en `derive_audit_hints.py`.

Ese campo queda como `"TODO"` en el output — el subagente de `contract-ingest` que procesa este
proveedor debe completarlo leyendo el resto del dossier antes de devolver el registro final. No
inventar ese resumen ni dejarlo en `"TODO"` en la entrega.

La moneda de las cifras (`M$`) no viene explícita en el dossier — no asumir USD ni CLP; el campo
`moneda_no_especificada` queda en `true` y el subagente debe anotar en `notas` si logra
determinarla por otra vía (ej. cruzando contra `monto_total` del contrato).

Uso:
    python3 parse_dossier_sr.py --pptx "<ruta>/<Proveedor>_Negotiation_Dossier.pptx" [--out hints.json]

Requiere `markitdown` disponible en PATH (mismo que usa el resto del pipeline para leer .pptx).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SLIDE_HEADER_MARKER = "Key facts & information: Overview of Supplier, opportunity & tactics"
SLIDE_BOUNDARY_RE = re.compile(r"<!--\s*Slide number:\s*\d+\s*-->")

NUM = r"[\d.,]+"


def run_markitdown(pptx_path: Path) -> str:
    try:
        result = subprocess.run(
            ["markitdown", str(pptx_path)],
            capture_output=True, text=True, timeout=60, check=True,
        )
    except FileNotFoundError:
        print("❌ markitdown no está disponible en PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ markitdown falló sobre {pptx_path}: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def extract_key_facts_slide(full_text: str) -> str | None:
    """Aísla el contenido de la slide 'Key facts & information...' entre su marcador de slide y
    el siguiente — no asume que siempre es la slide 7 (el número de slide puede variar según cuán
    largo sea el dossier de cada proveedor), solo busca el encabezado ancla."""
    idx = full_text.find(SLIDE_HEADER_MARKER)
    if idx == -1:
        return None
    # Retroceder hasta el marcador "<!-- Slide number: N -->" que abre esta slide.
    start = full_text.rfind("<!-- Slide number:", 0, idx)
    if start == -1:
        start = idx
    m = SLIDE_BOUNDARY_RE.search(full_text, idx)
    end = m.start() if m else len(full_text)
    return full_text[start:end]


def to_float(s: str | None):
    if s is None:
        return None
    return float(s.replace(",", "."))


def find1(pattern: str, text: str, flags=0):
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None


def find_group(pattern: str, text: str, n: int, flags=0):
    m = re.search(pattern, text, flags)
    if not m:
        return [None] * n
    return [m.group(i) for i in range(1, n + 1)]


def parse_slide(slide_text: str) -> dict:
    warnings = []

    def warn_if_missing(label, *vals):
        if all(v is None for v in vals):
            warnings.append(f"⚠️ no encontrado, revisar a mano: {label}")

    opp_monto, opp_pct = find_group(
        r"Negotiation Opportunity:\s*(" + NUM + r")M\$\s*\((" + NUM + r")%\)", slide_text, 2)
    warn_if_missing("negociacion_oportunidad", opp_pct, opp_monto)

    spend = find1(r"Spend:\s*(" + NUM + r")M\$", slide_text)
    warn_if_missing("spend", spend)

    supplier_name = find1(r"Supplier Name:\s*(.+)", slide_text)
    warn_if_missing("supplier_name_en_dossier", supplier_name)

    power_balance_resumen = find1(
        r"Power balance evaluation\d*\s*\n(.+?)\n", slide_text, flags=re.DOTALL)
    warn_if_missing("power_balance_resumen", power_balance_resumen)

    power_score = find1(r"Overall\s*\n+\s*(\d+)\s*\n+Supplier margins", slide_text)
    warn_if_missing("power_balance_score_overall", power_score)

    dash = r"[-–—]"  # hyphen, en dash, em dash — el pptx usa en dash (–)

    mdo_pct, mdo_addr, mdo_monto = find_group(
        r"Most desired outcome \(MDO\)\s*\n(" + NUM + r")% of \$(" + NUM + r")M addressable spend\s*"
        + dash + r"\s*(" + NUM + r")M\$",
        slide_text, 3)
    warn_if_missing("mdo", mdo_pct, mdo_addr, mdo_monto)

    target_pct, target_addr, target_monto = find_group(
        r"Target for Supplier\s*\n(" + NUM + r")% of \$(" + NUM + r")M addressable spend\s*"
        + dash + r"\s*(" + NUM + r")M\$",
        slide_text, 3)
    warn_if_missing("target", target_pct, target_addr, target_monto)

    laa_pct, laa_addr, laa_monto = find_group(
        r"Least acceptable agreement \(LAA\)\s*\n(" + NUM + r")% of \$(" + NUM + r")M addressable spend\s*"
        + dash + r"\s*(" + NUM + r")M\$",
        slide_text, 3)
    warn_if_missing("laa", laa_pct, laa_addr, laa_monto)

    return {
        "negociacion_oportunidad_pct": to_float(opp_pct),
        "negociacion_oportunidad_monto_musd": to_float(opp_monto),
        "spend_musd": to_float(spend),
        "supplier_name_en_dossier": supplier_name.strip() if supplier_name else None,
        "power_balance_resumen": power_balance_resumen.strip() if power_balance_resumen else None,
        "power_balance_score_overall": int(power_score) if power_score else None,
        "mdo_pct": to_float(mdo_pct),
        "mdo_addressable_spend_musd": to_float(mdo_addr),
        "mdo_monto_musd": to_float(mdo_monto),
        "target_pct": to_float(target_pct),
        "target_addressable_spend_musd": to_float(target_addr),
        "target_monto_musd": to_float(target_monto),
        "laa_pct": to_float(laa_pct),
        "laa_addressable_spend_musd": to_float(laa_addr),
        "laa_monto_musd": to_float(laa_monto),
        "moneda_no_especificada": True,
        "resumen_estrategia_negociacion": "TODO",
        "_warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pptx", required=True, help="Ruta al <Proveedor>_Negotiation_Dossier.pptx")
    ap.add_argument("--out", default=None, help="Ruta de salida (default: imprime a stdout)")
    args = ap.parse_args()

    pptx_path = Path(args.pptx)
    if not pptx_path.exists():
        print(f"❌ No existe el archivo: {pptx_path}", file=sys.stderr)
        sys.exit(1)

    full_text = run_markitdown(pptx_path)
    slide_text = extract_key_facts_slide(full_text)
    if slide_text is None:
        print("❌ No se encontró la slide 'Key facts & information: Overview of Supplier, "
              "opportunity & tactics' en este dossier — el template puede haber cambiado. "
              "No se derivó nada; completá dossier_savingsradar a mano leyendo el PPTX.",
              file=sys.stderr)
        result = {
            "archivo": str(pptx_path),
            "existe": True,
            "_template_no_reconocido": True,
            "resumen_estrategia_negociacion": "TODO",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    hints = parse_slide(slide_text)
    warnings = hints.pop("_warnings")

    result = {"archivo": str(pptx_path), "existe": True, **hints}

    print(f"✅ Campos mecánicos derivados de {pptx_path.name}.", file=sys.stderr)
    if warnings:
        print(f"⚠️  {len(warnings)} campo(s) no se pudieron derivar (template distinto al "
              f"esperado, o dossier incompleto) — revisar a mano:", file=sys.stderr)
        for w in warnings:
            print(f"    - {w}", file=sys.stderr)
    print("⚠️  'resumen_estrategia_negociacion' queda en 'TODO' — leé las slides de SWOT / "
          "Negotiation Strategy / Argumentation Map del mismo dossier y completalo con juicio "
          "propio antes de devolver el registro. No lo dejes en 'TODO' en la entrega final.",
          file=sys.stderr)
    print("⚠️  La moneda de estas cifras (M$) no viene explícita en el dossier — no asumas USD "
          "ni CLP; anotá en 'notas' si la determinaste cruzando contra 'monto_total' del "
          "contrato.", file=sys.stderr)

    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")
        print(f"✅ Escrito en: {args.out}", file=sys.stderr)
    else:
        print(out_json)


if __name__ == "__main__":
    main()
