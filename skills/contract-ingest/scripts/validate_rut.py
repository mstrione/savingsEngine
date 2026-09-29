#!/usr/bin/env python3
"""
validate_rut.py — Validación de RUT/RUN chileno contra el algoritmo de
dígito verificador módulo 11 (regla 4.7 de `playbooks/01_extraccion_contratos.md`,
si existe dentro de la carpeta de contratos del usuario).

No "corrige" un RUT que no valida: solo informa si el dígito verificador
declarado coincide con el calculado, para que ese campo se marque
`confianza: baja` y quede en la muestra de verificación obligatoria en vez
de aceptarse o corregirse a ciegas.

Uso:
    python3 validate_rut.py "77.225.200-5"
    python3 validate_rut.py "77225200-5" "12345678-9" ...   # varios de una
    echo "77.225.200-5" | python3 validate_rut.py -         # desde stdin, uno por línea

Salida: JSON por RUT con {rut_input, cuerpo, dv_declarado, dv_calculado, valido}.
"""
import json
import re
import sys


def _digito_verificador(cuerpo: str) -> str:
    """Calcula el dígito verificador módulo 11 para el cuerpo numérico del RUT (sin puntos/guion)."""
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = multiplicador + 1 if multiplicador < 7 else 2
    resto = suma % 11
    dv = 11 - resto
    if dv == 11:
        return "0"
    if dv == 10:
        return "K"
    return str(dv)


def validar_rut(rut_raw: str) -> dict:
    limpio = re.sub(r"[.\s]", "", rut_raw.strip()).upper()
    match = re.match(r"^(\d+)-?([\dK])$", limpio)
    if not match:
        return {
            "rut_input": rut_raw,
            "error": "Formato no reconocido — se esperaba <cuerpo numérico>[-<dv>], ej. 77225200-5",
            "valido": None,
        }
    cuerpo, dv_declarado = match.group(1), match.group(2)
    dv_calculado = _digito_verificador(cuerpo)
    return {
        "rut_input": rut_raw,
        "cuerpo": cuerpo,
        "dv_declarado": dv_declarado,
        "dv_calculado": dv_calculado,
        "valido": dv_declarado == dv_calculado,
    }


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    ruts = []
    if args == ["-"]:
        ruts = [line.strip() for line in sys.stdin if line.strip()]
    else:
        ruts = args

    resultados = [validar_rut(r) for r in ruts]
    output = resultados[0] if len(resultados) == 1 else resultados
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if any(r.get("valido") is False for r in resultados):
        sys.exit(2)  # código distinto para que un script llamador distinga "corrió pero hay RUT inválido"


if __name__ == "__main__":
    main()
