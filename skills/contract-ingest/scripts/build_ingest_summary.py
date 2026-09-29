#!/usr/bin/env python3
"""
Genera un resumen HTML de una corrida de contract-ingest (Modo A o Modo B) a partir del JSON
consolidado de la categoría, con un link de descarga al Excel espejo ya generado por
build_excel_mirror.py.

No extrae ni reinterpreta datos de los contratos: solo lee el JSON v3 ya validado y arma vistas
agregadas (KPIs, vencimientos próximos, tabla filtrable) para que el usuario tenga un panorama
rápido sin tener que abrir el Excel — el Excel sigue siendo la fuente completa con trazabilidad
fuente/confianza campo por campo.

Uso:
    python3 build_ingest_summary.py --json <ruta_v<N>.json> --excel <ruta_v<N>.xlsx>
    python3 build_ingest_summary.py --json <ruta_v<N>.json> --excel <ruta_v<N>.xlsx> --output <ruta.html>
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "assets", "ingest_summary_template.html"))
DATA_PLACEHOLDER = "__INGEST_SUMMARY_DATA_JSON__"

DIAS_ALERTA_VENCIMIENTO = 90

CONFIANZA_ORDEN = {"alta": 0, "media": 1, "baja": 2}


def _get(node, path, default=None):
    cur = node
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur if cur is not None else default


def _confianza_of(node):
    """Peor confianza encontrada recursivamente dentro de un nodo del contrato."""
    peor = {"valor": None}

    def walk(n):
        if isinstance(n, dict):
            c = n.get("confianza")
            if isinstance(c, str) and c in CONFIANZA_ORDEN:
                if peor["valor"] is None or CONFIANZA_ORDEN[c] > CONFIANZA_ORDEN[peor["valor"]]:
                    peor["valor"] = c
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for item in n:
                walk(item)

    walk(node)
    return peor["valor"] or "alta"


def _stringify_monto(monto_total):
    if not isinstance(monto_total, dict):
        return "No especificado"
    valores = monto_total.get("valor")
    if not isinstance(valores, list) or not valores:
        return "No especificado"
    partes = []
    for v in valores:
        if not isinstance(v, dict):
            continue
        moneda = v.get("moneda", "")
        valor = v.get("valor")
        periodo = v.get("periodo")
        if isinstance(valor, (int, float)):
            txt = f"{moneda} {valor:,.0f}".strip()
        else:
            txt = f"{moneda} {valor}".strip()
        if periodo:
            txt += f" ({periodo})"
        partes.append(txt)
    return "; ".join(partes) if partes else "No especificado"


def _parse_fecha(valor):
    if not valor or not isinstance(valor, str):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def build_summary(data, excel_filename):
    metadata = data.get("metadata", {}) or {}
    contratos = data.get("contratos", []) or []

    hoy = date.today()
    limite_alerta = hoy + timedelta(days=DIAS_ALERTA_VENCIMIENTO)

    filas = []
    conteo_confianza = {"alta": 0, "media": 0, "baja": 0}
    proveedores = set()
    vencimientos_proximos = []
    con_alertas = 0

    for c in contratos:
        proveedor = c.get("proveedor") or "No especificado"
        proveedores.add(proveedor)

        fecha_inicio_raw = _get(c, ["vigencia", "fecha_inicio", "valor"])
        fecha_fin_raw = _get(c, ["vigencia", "fecha_fin", "valor"])
        fecha_fin = _parse_fecha(fecha_fin_raw)

        confianza_contrato = _confianza_of(c)
        conteo_confianza[confianza_contrato] = conteo_confianza.get(confianza_contrato, 0) + 1

        notas = (c.get("notas") or "").strip()
        tiene_alerta = confianza_contrato == "baja" or bool(notas)
        if tiene_alerta:
            con_alertas += 1

        if fecha_fin and hoy <= fecha_fin <= limite_alerta:
            vencimientos_proximos.append({
                "proveedor": proveedor,
                "numero_contrato": c.get("numero_contrato") or "No especificado",
                "fecha_fin": fecha_fin_raw,
                "dias_restantes": (fecha_fin - hoy).days,
            })

        filas.append({
            "proveedor": proveedor,
            "numero_contrato": c.get("numero_contrato") or "No especificado",
            "rut": _get(c, ["rut_run_proveedor", "valor"], "No especificado"),
            "fecha_inicio": fecha_inicio_raw or "No especificado",
            "fecha_fin": fecha_fin_raw or "No especificado",
            "monto_total": _stringify_monto(c.get("monto_total")),
            "confianza": confianza_contrato,
            "notas": notas,
        })

    vencimientos_proximos.sort(key=lambda x: x["dias_restantes"])

    return {
        "categoria": metadata.get("categoria") or "No especificado",
        "cliente": metadata.get("cliente") or "No especificado",
        "fecha_extraccion": metadata.get("fecha_extraccion") or "No especificado",
        "version": metadata.get("version") or "No especificado",
        "version_anterior": metadata.get("version_anterior"),
        "total_contratos": len(contratos),
        "total_proveedores": len(proveedores),
        "con_alertas": con_alertas,
        "confianza": conteo_confianza,
        "vencimientos_proximos": vencimientos_proximos,
        "dias_alerta_vencimiento": DIAS_ALERTA_VENCIMIENTO,
        "contratos": filas,
        "excel_filename": excel_filename,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", required=True, help="Ruta al JSON consolidado _v<N>.json de la categoria")
    parser.add_argument("--excel", required=True,
                         help="Ruta al Excel espejo ya generado por build_excel_mirror.py (para linkear la descarga)")
    parser.add_argument("--output", help="Ruta de salida del HTML (default: <json>_resumen.html, junto al JSON)")
    args = parser.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not os.path.exists(args.excel):
        print(f"ADVERTENCIA: no se encontro el Excel espejo en {args.excel} -- el resumen se genera "
              f"igual, pero el boton de descarga va a quedar roto hasta que corras build_excel_mirror.py.",
              file=sys.stderr)

    excel_filename = os.path.basename(args.excel)
    summary = build_summary(data, excel_filename)

    output_path = args.output
    if not output_path:
        base, _ = os.path.splitext(args.json)
        output_path = f"{base}_resumen.html"

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    if DATA_PLACEHOLDER not in template:
        print(f"ERROR: el template {TEMPLATE_PATH} no tiene el placeholder {DATA_PLACEHOLDER} -- "
              f"no se puede inyectar la data. Revisa que no se haya editado el template a mano.",
              file=sys.stderr)
        sys.exit(1)

    data_json = json.dumps(summary, ensure_ascii=False, indent=2)
    html = template.replace(DATA_PLACEHOLDER, data_json)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Resumen generado: {output_path}")
    print(f"  Contratos: {summary['total_contratos']} | Proveedores: {summary['total_proveedores']} | "
          f"Con alertas: {summary['con_alertas']}")
    if summary["vencimientos_proximos"]:
        print(f"  {len(summary['vencimientos_proximos'])} contrato(s) vencen en los proximos "
              f"{DIAS_ALERTA_VENCIMIENTO} dias.")


if __name__ == "__main__":
    main()
