import json
from pathlib import Path

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


def test_compara_pdf_y_ocr_de_pagina_5_654391() -> None:
    bytes_pdf = (ROOT / "pdfs" / "654391.pdf").read_bytes()
    pagina_pdf = LectorTextoPyMuPdf().leer_paginas(bytes_pdf)[4]
    pdf_data = ExtractorPaginaTecnicaRaloeCrono().extraer(pagina_pdf)
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(bytes_pdf, numero_pagina=5, dpi=200)
    ocr_debug = json.loads(
        (ROOT / "docs" / "ocr_debug" / "654391_pagina_tecnica_page_5_ocr_tesseract.json").read_text(encoding="utf-8")
    )
    ocr_data = extraer_pagina_5_desde_ocr(ocr_debug, bytes_imagen=pagina_renderizada.bytes_imagen)

    comparacion = comparar_extracciones(pdf_data, ocr_data)

    assert comparacion["resumen"]["diferencias"] == 7
    assert comparacion["resumen"]["coincidencias"] == 67
    assert comparacion["coincidencias"]["Caracteristicas"]["Velocidad"] == "0.80"
    assert comparacion["coincidencias"]["Puertas_cabina_embarque_1"]["Barreras_Op1"] == "Si"
    assert comparacion["coincidencias"]["Puertas_cabina_embarque_1"]["Barreras_Op1_txt"] == "MINI-CC-36"
    assert comparacion["coincidencias"]["Caracteristicas"]["Mono"] == "Si"
    assert comparacion["diferencias"]["Traccion_electrica"]["Modelo"] == {
        "pdf": "FRN0018LM2A-7",
        "ocr": "FRNOO18LM2A-7",
    }
    assert comparacion["diferencias"]["Caracteristicas"]["Sin_cuarto_de_maquinas"] == {
        "pdf": "Si",
        "ocr": "No",
    }
    assert comparacion["diferencias"]["Traccion_electrica"]["Conectores"] == {
        "pdf": "Si",
        "ocr": "No",
    }

    assert comparacion["solo_pdf"]["Normas"]["Norma_81_1_A3"] == "No"
    assert comparacion["vacios_en_ambos"]["Traccion_electrica"] == [
        "Consola_VF_txt",
        "Freno_lento_apertura",
        "Freno_lento_mantenimiento",
    ]
    assert comparacion["vacios_en_ambos"]["Traccion_hidraulica"] == [
        "Fabricante_oleo",
        "Grupo_valvulas",
        "Potencia_oleo",
        "Tension_valvulas",
        "Tipo_arranque",
    ]


def test_compara_pdf_y_ocr_de_pagina_foso_opciones_654391() -> None:
    bytes_pdf = (ROOT / "pdfs" / "654391.pdf").read_bytes()
    pagina_pdf = LectorTextoPyMuPdf().leer_paginas(bytes_pdf)[5]
    pdf_data = ExtractorFosoHuidaOpcionesRaloeCrono().extraer(pagina_pdf)
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(bytes_pdf, numero_pagina=6, dpi=200)
    ocr_debug = json.loads(
        (ROOT / "docs" / "ocr_debug" / "654391_foso_opciones_page_6_ocr_tesseract.json").read_text(encoding="utf-8")
    )
    ocr_data = extraer_foso_opciones_desde_ocr(ocr_debug, bytes_imagen=pagina_renderizada.bytes_imagen)

    comparacion = comparar_extracciones(pdf_data, ocr_data)

    assert comparacion["resumen"]["diferencias"] == 0
    assert comparacion["resumen"]["coincidencias"] == 85
    assert comparacion["coincidencias"]["Opciones"]["Limitador_velocidad_cab"] == "Si"
    assert comparacion["coincidencias"]["Opciones"]["Limitador_velocidad_cab_txt"] == "SLC LM18CD"
    assert comparacion["coincidencias"]["Opciones"]["Distancia_pesacargas_maniobra"] == "5.000"
    assert comparacion["coincidencias"]["Opciones"]["Rosario"] == "Si"
    assert comparacion["coincidencias"]["Opciones"]["Rosario_txt"] == "TIRA LEDS"
    assert comparacion["coincidencias"]["Opciones"]["Apertura_anticipada"] == "No"
    assert comparacion["coincidencias"]["Opciones"]["Test_de_freno"] == "Si"
    assert comparacion["coincidencias"]["Opciones"]["Completo"] == "Si"
    assert comparacion["coincidencias"]["Opciones"]["Modulo_ARM"] == "Si"
