import json
from pathlib import Path

import pytest
from tests.ocr_debug_helpers import cargar_o_generar_ocr_debug_raloe
from extractor_pdf.infrastructure.comparison.comparador_extracciones import comparar_extracciones
from extractor_pdf.infrastructure.extraction.client_base.extractor_pagina_tecnica import (
    ExtractorPaginaTecnicaRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_foso_huida_opciones import (
    ExtractorFosoHuidaOpcionesRaloeCrono,
)
from extractor_pdf.infrastructure.ocr_contract.pagina_foso_opciones_raloe_crono import (
    extraer_foso_opciones_desde_ocr,
)
from extractor_pdf.infrastructure.ocr_contract.pagina_5_raloe_crono import (
    extraer_pagina_5_desde_ocr,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf


ROOT = Path(__file__).resolve().parents[1]


def test_comparador_normaliza_valores_leidos_antes_de_comparar() -> None:
    comparacion = comparar_extracciones(
        {"Caracteristicas": {"Tension_linea": "16"}},
        {"Caracteristicas": {"Tension_linea": "16 V"}},
    )

    assert comparacion["resumen"]["diferencias"] == 0
    assert comparacion["resumen"]["coincidencias"] == 1
    assert comparacion["coincidencias"]["Caracteristicas"]["Tension_linea"] == "16"


def test_comparador_no_aplica_default_a_campos_no_leidos() -> None:
    comparacion = comparar_extracciones(
        {"Caracteristicas": {"Mono": ""}},
        {"Caracteristicas": {"Mono": ""}},
    )

    assert comparacion["resumen"]["vacios_en_ambos"] == 1
    assert comparacion["vacios_en_ambos"]["Caracteristicas"] == ["Mono"]


def test_comparador_ignora_bloques_auxiliares_no_comparables() -> None:
    comparacion = comparar_extracciones(
        {
            "Caracteristicas": {"Maniobra": "SELECTIVA BAJADA"},
            "warning": [{"campo": "Caracteristicas.Maniobra"}],
            "Notas_extra": [{"texto": "nota"}],
        },
        {
            "Caracteristicas": {"Maniobra": "SELECTIVA BAJADA"},
            "warning": [],
            "Campos_extra": {"Campo": "valor"},
        },
    )

    assert comparacion["resumen"]["coincidencias"] == 1
    assert comparacion["resumen"]["diferencias"] == 0
    assert comparacion["coincidencias"]["Caracteristicas"]["Maniobra"] == "SELECTIVA BAJADA"


@pytest.mark.ocr
def test_compara_pdf_y_ocr_de_pagina_5_654391() -> None:
    bytes_pdf = (ROOT / "pdfs" / "Raloe" / "654391.pdf").read_bytes()
    pagina_pdf = LectorTextoPyMuPdf().leer_paginas(bytes_pdf)[4]
    pdf_data = ExtractorPaginaTecnicaRaloeCrono().extraer(pagina_pdf)
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(bytes_pdf, numero_pagina=5, dpi=200)
    ocr_debug = cargar_o_generar_ocr_debug_raloe(
        "654391_pagina_tecnica_page_5_ocr_tesseract.json", numero_pagina=5, dpi=200
    )
    ocr_data = extraer_pagina_5_desde_ocr(ocr_debug, bytes_imagen=pagina_renderizada.bytes_imagen)

    comparacion = comparar_extracciones(pdf_data, ocr_data)

    assert comparacion["resumen"]["diferencias"] > 0
    assert comparacion["resumen"]["coincidencias"] > 0
    assert comparacion["coincidencias"]["Caracteristicas"]["Maniobra"] == "SELECTIVA BAJADA"
    assert comparacion["coincidencias"]["Traccion_electrica"]["Longitud_cable_potencia"] == "20.000"
    assert comparacion["diferencias"]["Traccion_electrica"]["Modelo"] == {
        "pdf": "FRN0018LM2A-7",
        "ocr": "FRNOO18LM2A-7",
    }
    assert comparacion["solo_pdf"]["Normas"]["Norma_81_73"] == "No"
    assert comparacion["coincidencias"]["Normas"]["Norma_81_20_50"] == "Si"
    assert "Freno_lento_apertura" in comparacion["vacios_en_ambos"]["Traccion_electrica"]


@pytest.mark.ocr
def test_compara_pdf_y_ocr_de_pagina_foso_opciones_654391() -> None:
    bytes_pdf = (ROOT / "pdfs" / "Raloe" / "654391.pdf").read_bytes()
    pagina_pdf = LectorTextoPyMuPdf().leer_paginas(bytes_pdf)[5]
    pdf_data = ExtractorFosoHuidaOpcionesRaloeCrono().extraer(pagina_pdf)
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(bytes_pdf, numero_pagina=6, dpi=200)
    ocr_debug = cargar_o_generar_ocr_debug_raloe(
        "654391_foso_opciones_page_6_ocr_tesseract.json", numero_pagina=6, dpi=200
    )
    ocr_data = extraer_foso_opciones_desde_ocr(ocr_debug, bytes_imagen=pagina_renderizada.bytes_imagen)

    comparacion = comparar_extracciones(pdf_data, ocr_data)

    assert comparacion["resumen"]["diferencias"] == 0
    assert comparacion["resumen"]["coincidencias"] > 0
    assert comparacion["coincidencias"]["Opciones"]["Distancia_pesacargas_maniobra"] == "5.000"
    assert comparacion["coincidencias"]["Opciones"]["Pesacargas_fabricante"] == "EMESA"
    assert comparacion["coincidencias"]["Opciones"]["Accionamiento_a_dist_limitador"] == "Si"
    assert comparacion["coincidencias"]["Opciones"]["Completo"] == "Si"
    assert comparacion["coincidencias"]["Opciones"]["Modulo_ARM"] == "Si"
