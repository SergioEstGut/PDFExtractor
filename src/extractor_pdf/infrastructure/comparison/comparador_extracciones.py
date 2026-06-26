from __future__ import annotations

from typing import Any

from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import normalizar_valor_campo


SECCIONES_NO_COMPARABLES = {"Campos_extra", "Notas_extra", "warning"}


def comparar_extracciones(
    pdf_data: dict[str, Any],
    ocr_data: dict[str, Any],
) -> dict[str, Any]:
    coincidencias: dict[str, dict[str, str]] = {}
    diferencias: dict[str, dict[str, dict[str, str]]] = {}
    solo_pdf: dict[str, dict[str, str]] = {}
    solo_ocr: dict[str, dict[str, str]] = {}
    vacios_en_ambos: dict[str, list[str]] = {}

    secciones_pdf = _secciones_comparables(pdf_data)
    secciones_ocr = _secciones_comparables(ocr_data)

    for seccion in sorted(set(secciones_pdf) | set(secciones_ocr)):
        campos_pdf = secciones_pdf.get(seccion, {})
        campos_ocr = secciones_ocr.get(seccion, {})
        for campo in sorted(set(campos_pdf) | set(campos_ocr)):
            valor_pdf = _normalizar_para_comparar(seccion, campo, campos_pdf.get(campo, ""))
            valor_ocr = _normalizar_para_comparar(seccion, campo, campos_ocr.get(campo, ""))

            if valor_pdf and valor_ocr and valor_pdf == valor_ocr:
                _poner(coincidencias, seccion, campo, valor_pdf)
            elif valor_pdf and valor_ocr:
                _poner(diferencias, seccion, campo, {"pdf": valor_pdf, "ocr": valor_ocr})
            elif valor_pdf:
                _poner(solo_pdf, seccion, campo, valor_pdf)
            elif valor_ocr:
                _poner(solo_ocr, seccion, campo, valor_ocr)
            else:
                vacios_en_ambos.setdefault(seccion, []).append(campo)

    return {
        "resumen": {
            "coincidencias": _contar_campos(coincidencias),
            "diferencias": _contar_campos(diferencias),
            "solo_pdf": _contar_campos(solo_pdf),
            "solo_ocr": _contar_campos(solo_ocr),
            "vacios_en_ambos": sum(len(campos) for campos in vacios_en_ambos.values()),
        },
        "coincidencias": coincidencias,
        "diferencias": diferencias,
        "solo_pdf": solo_pdf,
        "solo_ocr": solo_ocr,
        "vacios_en_ambos": vacios_en_ambos,
    }


def _secciones_comparables(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        seccion: campos
        for seccion, campos in data.items()
        if seccion not in SECCIONES_NO_COMPARABLES and isinstance(campos, dict)
    }


def _poner(destino: dict[str, dict[str, Any]], seccion: str, campo: str, valor: Any) -> None:
    destino.setdefault(seccion, {})[campo] = valor


def _normalizar_para_comparar(seccion: str, campo: str, valor: str) -> str:
    if valor == "":
        return ""
    return normalizar_valor_campo(seccion, campo, valor)


def _contar_campos(secciones: dict[str, dict[str, Any]]) -> int:
    return sum(len(campos) for campos in secciones.values())
