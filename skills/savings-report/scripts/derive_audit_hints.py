#!/usr/bin/env python3
"""
derive_audit_hints.py — Deriva mecánicamente la parte no-curada de
`auditoria_contratos.filas[]` (ver `skills/savings-report/references/microsite_data_schema.md`)
a partir del JSON consolidado de `contract-ingest` (esquema real v3,
`skills/contract-ingest/references/schema.md`).

Qué deriva mecánicamente (sin juicio de Claude):
- `contrato_numero`, `proveedor`: copia directa de `numero_contrato` / `proveedor` del contrato.
- `duracion`: a partir de `vigencia.fecha_inicio.valor` / `vigencia.fecha_fin.valor` (ISO).
- `modalidad_pago`: copia directa de `metodo_pago.valor` ("No especificado" si viene vacío) —
  es texto libre, no un enum Sí/No, así que no pasa por `normalize_si_no()`.
- `incentivos`, `penalidades`, `reajuste_indexacion`: a partir de
  `clausula_incentivo_desempeno.valor`, `clausula_multa_penalizacion.valor`,
  `mecanismo_reajuste_indexacion.valor`. El esquema v3 ya los define como enum "Sí"/"No", así que
  normalmente es una lectura directa — el fallback case/tilde-insensitive de `normalize_si_no()`
  solo cubre JSONs más viejos o no estrictamente conformes donde ese campo vino como texto libre
  ("Sí, según cláusula 8...") en vez del enum limpio.

Qué NO deriva (deliberado — requiere lectura y juicio de Claude en el chat, ver el esquema):
- `compromiso_volumen_sla`: síntesis de `niveles_servicio.valor` — no es una cifra a copiar, es un
  resumen de qué compromete el proveedor.
- `hallazgo_principal_fila`: juicio analítico, típicamente basado en `notas` del contrato + cruce
  con `auditoria_contratos.hallazgo_principal` general.

Ambos quedan como `"TODO"` en el output — reemplazalos en el chat antes de armar el
`microsite_data.json` final para `build_microsite.py`. No los dejes en `"TODO"` en la entrega.

Uso:
    python3 derive_audit_hints.py --json <categoria>_contratos_v<N>.json [--out filas_hint.json]
"""
import argparse
import json
import sys
import unicodedata
from datetime import date
from pathlib import Path


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalize_si_no(raw) -> str:
    """Normaliza un valor de cláusula a 'Sí' / 'No' / 'No especificado'.
    Lectura directa si ya es el enum esperado; fallback a prefijo de texto libre
    case/tilde-insensitive solo para JSONs no estrictamente v3."""
    if raw is None:
        return "No especificado"
    if isinstance(raw, str):
        s = strip_accents(raw.strip().lower())
        if "no especificado" in s or "no especifica" in s:
            return "No especificado"
        if s == "si" or s.startswith("si,") or s.startswith("si "):
            return "Sí"
        if s == "no" or s.startswith("no,") or s.startswith("no "):
            return "No"
    return "No especificado"


def parse_iso_date(s):
    if not s or not isinstance(s, str):
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def format_duracion(fecha_inicio: str, fecha_fin: str) -> str:
    d1, d2 = parse_iso_date(fecha_inicio), parse_iso_date(fecha_fin)
    if not d1 or not d2:
        return "No especificado en el contrato"
    if d2 < d1:
        return f"⚠️ fecha_fin ({fecha_fin}) anterior a fecha_inicio ({fecha_inicio}) — revisar a mano"
    total_months = (d2.year - d1.year) * 12 + (d2.month - d1.month)
    if d2.day < d1.day:
        total_months -= 1
    years, months = divmod(max(total_months, 0), 12)
    parts = []
    if years:
        parts.append(f"{years} año{'s' if years != 1 else ''}")
    if months:
        parts.append(f"{months} mes{'es' if months != 1 else ''}")
    if not parts:
        parts.append("< 1 mes")
    return " ".join(parts)


def derive_row(contrato: dict) -> dict:
    vigencia = contrato.get("vigencia") or {}
    fecha_inicio = (vigencia.get("fecha_inicio") or {}).get("valor")
    fecha_fin = (vigencia.get("fecha_fin") or {}).get("valor")

    incentivo = (contrato.get("clausula_incentivo_desempeno") or {}).get("valor")
    multa = (contrato.get("clausula_multa_penalizacion") or {}).get("valor")
    reajuste = (contrato.get("mecanismo_reajuste_indexacion") or {}).get("valor")
    metodo_pago = (contrato.get("metodo_pago") or {}).get("valor")

    return {
        "contrato_numero": contrato.get("numero_contrato", "No especificado"),
        "proveedor": contrato.get("proveedor", "No especificado"),
        "duracion": format_duracion(fecha_inicio, fecha_fin),
        "modalidad_pago": metodo_pago if metodo_pago else "No especificado",
        "incentivos": normalize_si_no(incentivo),
        "penalidades": normalize_si_no(multa),
        "reajuste_indexacion": normalize_si_no(reajuste),
        "compromiso_volumen_sla": "TODO",
        "hallazgo_principal_fila": "TODO",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", required=True, help="Ruta al JSON consolidado de contract-ingest")
    ap.add_argument("--out", default=None, help="Ruta de salida (default: imprime a stdout)")
    args = ap.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"❌ No existe el archivo: {json_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    contratos = data.get("contratos", [])
    if not contratos:
        print("❌ El JSON no tiene una lista 'contratos' o está vacía.", file=sys.stderr)
        sys.exit(1)

    filas = [derive_row(c) for c in contratos]

    n_todo_sla = sum(1 for f in filas if f["compromiso_volumen_sla"] == "TODO")
    n_todo_hallazgo = sum(1 for f in filas if f["hallazgo_principal_fila"] == "TODO")
    n_no_especificado = sum(
        1 for f in filas
        if "No especificado" in f["duracion"]
        or f["incentivos"] == "No especificado"
        or f["penalidades"] == "No especificado"
        or f["reajuste_indexacion"] == "No especificado"
    )

    print(f"✅ {len(filas)} filas derivadas mecánicamente ({json_path.name}).", file=sys.stderr)
    print(f"⚠️  {n_todo_sla} filas con 'compromiso_volumen_sla' pendiente de completar en el chat "
          f"(leyendo niveles_servicio.valor de cada contrato).", file=sys.stderr)
    print(f"⚠️  {n_todo_hallazgo} filas con 'hallazgo_principal_fila' pendiente de completar en el "
          f"chat (juicio analítico + cruce con notas del contrato).", file=sys.stderr)
    if n_no_especificado:
        print(f"⚠️  {n_no_especificado} filas con al menos un campo mecánico 'No especificado' — "
              f"el contrato de origen no tenía el dato explícito; no lo inventes al completar el "
              f"resto de la fila.", file=sys.stderr)

    out_json = json.dumps({"filas": filas}, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")
        print(f"✅ Escrito en: {args.out}", file=sys.stderr)
    else:
        print(out_json)


if __name__ == "__main__":
    main()
