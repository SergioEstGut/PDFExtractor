from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from extractor_pdf.infrastructure.comparison.comparador_extracciones import comparar_extracciones
from extractor_pdf.infrastructure.extraction.client_base.extractor_foso_huida_opciones import (
    ExtractorFosoHuidaOpcionesRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_pagina_tecnica import (
    ExtractorPaginaTecnicaRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_premontada_armario_botoneras import (
    ExtractorPremontadaArmarioBotonerasRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import (
    aplicar_contrato_salida,
    check_asociado_a_txt,
    especificacion_campo,
)
from extractor_pdf.infrastructure.ocr.extractor_visual_tesseract import ExtractorVisualTesseract
from extractor_pdf.infrastructure.ocr_contract.pagina_5_raloe_crono import (
    extraer_pagina_5_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.ocr_contract.pagina_foso_opciones_raloe_crono import (
    extraer_foso_opciones_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.ocr_contract.pagina_premontada_armario_botoneras_raloe_crono import (
    extraer_premontada_armario_botoneras_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_raloe_crono import (
    DetectorPaginaFosoHuidaOpcionesRaloeCrono,
    DetectorPaginaPremontadaArmarioBotonerasRaloeCrono,
    DetectorPaginaTecnicaRaloeCrono,
)


def main() -> None:
    args = _parse_args()
    pdf_path = args.pdf.resolve()
    pedido = pdf_path.stem
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bytes_pdf = pdf_path.read_bytes()
    paginas = LectorTextoPyMuPdf().leer_paginas(bytes_pdf)
    renderizador = RenderizadorPaginaPyMuPdf()
    extractor_visual = ExtractorVisualTesseract()

    trabajos = [
        {
            "nombre": "pagina_tecnica",
            "detector": DetectorPaginaTecnicaRaloeCrono(),
            "extractor_pdf": ExtractorPaginaTecnicaRaloeCrono(),
            "extractor_ocr": extraer_pagina_5_desde_ocr_con_debug,
        },
        {
            "nombre": "foso_opciones",
            "detector": DetectorPaginaFosoHuidaOpcionesRaloeCrono(),
            "extractor_pdf": ExtractorFosoHuidaOpcionesRaloeCrono(),
            "extractor_ocr": extraer_foso_opciones_desde_ocr_con_debug,
        },
        {
            "nombre": "premontada_armario_botoneras",
            "detector": DetectorPaginaPremontadaArmarioBotonerasRaloeCrono(),
            "extractor_pdf": ExtractorPremontadaArmarioBotonerasRaloeCrono(),
            "extractor_ocr": extraer_premontada_armario_botoneras_desde_ocr_con_debug,
        },
    ]

    resultado: dict[str, Any] = {
        "pedido": pedido,
        "pdf": str(pdf_path),
        "paginas_detectadas": {},
        "resumen": {},
        "secciones": {},
    }
    resultado_fusionado: dict[str, dict[str, str]] = {}

    for trabajo in trabajos:
        pagina = trabajo["detector"].detectar(paginas)
        numero_pagina = pagina.numero
        resultado["paginas_detectadas"][trabajo["nombre"]] = numero_pagina

        pdf_debug = trabajo["extractor_pdf"].extraer_con_debug(pagina)
        pdf_data = aplicar_contrato_salida(pdf_debug["data"])

        render = renderizador.renderizar_pagina(bytes_pdf, numero_pagina=numero_pagina, dpi=args.dpi)
        ocr_debug = extractor_visual.extraer(render, cliente_id="cliente_base")
        ocr_debug.update(
            {
                "pdf": str(pdf_path),
                "page_number": numero_pagina,
                "dpi": args.dpi,
                "image": {
                    "width": render.ancho,
                    "height": render.alto,
                },
            }
        )
        ocr_resultado = trabajo["extractor_ocr"](ocr_debug, bytes_imagen=render.bytes_imagen)
        ocr_data = aplicar_contrato_salida(ocr_resultado["data"])
        vacios_ocr_clasificados = clasificar_vacios_ocr(
            ocr_data=ocr_data,
            ocr_debug_extractor=ocr_resultado.get("debug", {}),
            lineas_ocr=ocr_debug["ocr"]["lines"],
        )

        comparacion = comparar_extracciones(pdf_data, ocr_data)
        fusion = fusionar_comparacion(comparacion)
        vacios_clasificados = clasificar_vacios_en_ambos(comparacion, fusion)
        resumen = resumen_con_porcentajes(comparacion)
        resumen["vacios_accionables"] = _contar_vacios_clasificados(
            vacios_clasificados["accionables"]
        )
        resumen["vacios_dependientes_de_check_no_marcado"] = _contar_vacios_clasificados(
            vacios_clasificados["dependientes_de_check_no_marcado"]
        )

        prefijo = f"{pedido}_{trabajo['nombre']}_page_{numero_pagina}"
        escribir_json(output_dir / f"{prefijo}_pdf.json", pdf_data)
        escribir_json(output_dir / f"{prefijo}_ocr_tesseract.json", ocr_debug)
        escribir_json(output_dir / f"{prefijo}_ocr.json", ocr_data)
        escribir_json(output_dir / f"{prefijo}_comparacion.json", comparacion)
        escribir_json(output_dir / f"{prefijo}_fusion.json", fusion)
        for seccion, campos in fusion.items():
            resultado_fusionado.setdefault(seccion, {}).update(campos)

        resultado["resumen"][trabajo["nombre"]] = resumen
        resultado["secciones"][trabajo["nombre"]] = {
            "pdf": pdf_data,
            "ocr": ocr_data,
            "comparacion": comparacion,
            "vacios_clasificados": vacios_clasificados,
            "vacios_ocr_clasificados": vacios_ocr_clasificados,
            "fusion": fusion,
        }

    resultado["resumen_total"] = resumen_total(resultado["resumen"])
    resultado["resultado_fusionado"] = resultado_fusionado
    escribir_json(output_dir / f"{pedido}_resultado_fusionado_pdf_ocr.json", resultado_fusionado)
    escribir_json(output_dir / f"{pedido}_diagnostico_pdf_ocr.json", resultado)
    print(json.dumps(resultado["resumen_total"], ensure_ascii=False, indent=2))
    print(f"Diagnostico guardado en: {output_dir / f'{pedido}_diagnostico_pdf_ocr.json'}")


def fusionar_comparacion(comparacion: dict[str, Any]) -> dict[str, dict[str, str]]:
    fusion: dict[str, dict[str, str]] = {}
    for bloque in ("coincidencias", "solo_pdf", "solo_ocr"):
        for seccion, campos in comparacion.get(bloque, {}).items():
            fusion.setdefault(seccion, {}).update(campos)

    for seccion, campos in comparacion.get("diferencias", {}).items():
        for campo, valores in campos.items():
            fusion.setdefault(seccion, {})[campo] = valores.get("pdf", "")

    for seccion, campos in comparacion.get("vacios_en_ambos", {}).items():
        for campo in campos:
            fusion.setdefault(seccion, {})[campo] = ""
    return fusion


def clasificar_vacios_en_ambos(
    comparacion: dict[str, Any],
    fusion: dict[str, dict[str, str]],
) -> dict[str, dict[str, list[str]]]:
    accionables: dict[str, list[str]] = {}
    dependientes: dict[str, list[str]] = {}

    for seccion, campos in comparacion.get("vacios_en_ambos", {}).items():
        for campo in campos:
            check_asociado = _check_asociado_a_txt(seccion, campo)
            if check_asociado and fusion.get(seccion, {}).get(check_asociado) != "Si":
                dependientes.setdefault(seccion, []).append(campo)
            else:
                accionables.setdefault(seccion, []).append(campo)

    return {
        "accionables": accionables,
        "dependientes_de_check_no_marcado": dependientes,
    }


def clasificar_vacios_ocr(
    ocr_data: dict[str, dict[str, str]],
    ocr_debug_extractor: dict[str, dict[str, Any]],
    lineas_ocr: list[dict[str, Any]],
) -> dict[str, Any]:
    vistos_vacios: dict[str, dict[str, str]] = {}
    no_vistos: dict[str, list[str]] = {}
    texto_lineas = [linea.get("text", "") for linea in lineas_ocr]

    for seccion, campos in ocr_data.items():
        for campo, valor in campos.items():
            if valor:
                continue

            check_asociado = _check_asociado_a_txt(seccion, campo)
            if check_asociado and campos.get(check_asociado) == "No":
                vistos_vacios.setdefault(seccion, {})[campo] = f"check asociado {check_asociado}=No"
                continue

            if campo in ocr_debug_extractor.get(seccion, {}):
                vistos_vacios.setdefault(seccion, {})[campo] = "evidencia OCR con valor normalizado vacio"
                continue

            if _columna_tabla_premontada_vista(seccion, campo, texto_lineas):
                vistos_vacios.setdefault(seccion, {})[campo] = "columna de tabla vista sin valor"
                continue

            alias = _alias_visto(seccion, campo, texto_lineas)
            if alias:
                vistos_vacios.setdefault(seccion, {})[campo] = f"alias visto: {alias}"
            else:
                no_vistos.setdefault(seccion, []).append(campo)

    return {
        "vistos_vacios": vistos_vacios,
        "no_vistos": no_vistos,
        "resumen": {
            "vistos_vacios": sum(len(campos) for campos in vistos_vacios.values()),
            "no_vistos": sum(len(campos) for campos in no_vistos.values()),
        },
    }


def _check_asociado_a_txt(seccion: str, campo: str) -> str:
    return check_asociado_a_txt(seccion, campo)


def _alias_visto(seccion: str, campo: str, lineas: list[str]) -> str:
    especificacion = especificacion_campo(seccion, campo) or {}
    lineas_normalizadas = [_normalizar_texto(linea) for linea in lineas]
    for alias in especificacion.get("aliases", []):
        alias_normalizado = _normalizar_texto(alias)
        if len(alias_normalizado) < 3:
            continue
        if any(alias_normalizado in linea for linea in lineas_normalizadas):
            return alias
    return ""


def _columna_tabla_premontada_vista(seccion: str, campo: str, lineas: list[str]) -> bool:
    if seccion != "Premontada" or campo not in {"Orient_E1", "Orient_E2"}:
        return False
    lineas_normalizadas = [_normalizar_texto(linea) for linea in lineas]
    return any("orient" in linea and ("modelo" in linea or "v h" in linea) for linea in lineas_normalizadas)


def _normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def _contar_vacios_clasificados(vacios: dict[str, list[str]]) -> int:
    return sum(len(campos) for campos in vacios.values())


def resumen_con_porcentajes(comparacion: dict[str, Any]) -> dict[str, Any]:
    resumen = dict(comparacion["resumen"])
    total = sum(resumen.values())
    resumen["total_campos_comparados"] = total
    resumen["campos_con_valor"] = (
        resumen["coincidencias"]
        + resumen["solo_pdf"]
        + resumen["solo_ocr"]
        + resumen["diferencias"]
    )
    resumen["campos_fusion_con_valor_no_discrepante"] = (
        resumen["coincidencias"] + resumen["solo_pdf"] + resumen["solo_ocr"]
    )
    resumen["porcentaje_con_valor"] = porcentaje(resumen["campos_con_valor"], total)
    resumen["porcentaje_fusion_con_valor_no_discrepante"] = porcentaje(
        resumen["campos_fusion_con_valor_no_discrepante"], total
    )
    resumen["porcentaje_validado_ambas_fuentes"] = porcentaje(resumen["coincidencias"], total)
    return resumen


def resumen_total(resumenes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    claves = [
        "coincidencias",
        "diferencias",
        "solo_pdf",
        "solo_ocr",
        "vacios_en_ambos",
        "total_campos_comparados",
        "campos_con_valor",
        "campos_fusion_con_valor_no_discrepante",
        "vacios_accionables",
        "vacios_dependientes_de_check_no_marcado",
    ]
    total = {clave: sum(resumen.get(clave, 0) for resumen in resumenes.values()) for clave in claves}
    total["porcentaje_con_valor"] = porcentaje(total["campos_con_valor"], total["total_campos_comparados"])
    total["porcentaje_fusion_con_valor_no_discrepante"] = porcentaje(
        total["campos_fusion_con_valor_no_discrepante"], total["total_campos_comparados"]
    )
    total["porcentaje_validado_ambas_fuentes"] = porcentaje(
        total["coincidencias"], total["total_campos_comparados"]
    )
    return total


def porcentaje(valor: int, total: int) -> float:
    if not total:
        return 0.0
    return round((valor / total) * 100, 2)


def escribir_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/ocr_debug"))
    parser.add_argument("--dpi", type=int, default=200)
    return parser.parse_args()


if __name__ == "__main__":
    main()
