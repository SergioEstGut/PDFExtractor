import json
from pathlib import Path

from extractor_pdf.infrastructure.extraction.client_base.extractor_pagina_tecnica import (
    ExtractorPaginaTecnicaRaloeCrono,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf


PDF_PATH = Path(__file__).resolve().parents[1] / "pdfs" / "Raloe" / "654391.pdf"
ESPERADO_PATH = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "expected" / "654391_page_5.json"
)
PDF_654340_PATH = Path(__file__).resolve().parents[1] / "pdfs" / "Raloe" / "654340.pdf"
ESPERADO_654340_PATH = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "expected" / "654340_page_4.json"
)


def test_extrae_campos_esperados_de_pagina_tecnica_654391() -> None:
    pagina_5 = LectorTextoPyMuPdf().leer_paginas(PDF_PATH.read_bytes())[4]

    resultado = ExtractorPaginaTecnicaRaloeCrono().extraer(pagina_5)

    esperado = json.loads(ESPERADO_PATH.read_text(encoding="utf-8"))

    assert resultado == esperado


def test_extrae_campos_esperados_de_pagina_tecnica_654340() -> None:
    pagina_4 = LectorTextoPyMuPdf().leer_paginas(PDF_654340_PATH.read_bytes())[3]

    resultado = ExtractorPaginaTecnicaRaloeCrono().extraer(pagina_4)

    esperado = json.loads(ESPERADO_654340_PATH.read_text(encoding="utf-8"))

    assert resultado == esperado


def test_extrae_checks_reales_de_pagina_tecnica_654824() -> None:
    pagina_4 = LectorTextoPyMuPdf().leer_paginas(
        (Path(__file__).resolve().parents[1] / "pdfs" / "Raloe" / "654824.pdf").read_bytes()
    )[3]

    resultado = ExtractorPaginaTecnicaRaloeCrono().extraer(pagina_4)

    assert resultado["Normas"]["Norma_81_20_50"] == "Si"
    assert resultado["Normas"]["Norma_81_70"] == "Si"
    assert resultado["Caracteristicas"]["Maniobra"] == "SELECTIVA SUB/BAJ"
    assert resultado["Caracteristicas"]["Tipo"] == "DUPLEX"
    assert resultado["Caracteristicas"]["Consola_maniobra"] == "Si"
    assert resultado["Caracteristicas"]["Tension_linea"] == "400"
    assert resultado["Caracteristicas"]["Tension_motor"] == "350"
    assert resultado["Caracteristicas"]["Mono"] == "No"
    assert resultado["Caracteristicas"]["Tri"] == "Si"
    assert resultado["Caracteristicas"]["Velocidad"] == "1.00"
    assert resultado["Caracteristicas"]["Paradas"] == "3"
    assert resultado["Caracteristicas"]["Frecuencia_50_Hz"] == "Si"
    assert resultado["Caracteristicas"]["Frecuencia_60_Hz"] == "No"
    assert resultado["Caracteristicas"]["Neutro"] == "Si"


def test_debug_pdf_pagina_tecnica_marca_campos_pendientes_como_zona_vacia() -> None:
    pagina_5 = LectorTextoPyMuPdf().leer_paginas(PDF_PATH.read_bytes())[4]

    resultado = ExtractorPaginaTecnicaRaloeCrono().extraer_con_debug(pagina_5)
    debug = resultado["debug_pdf"]

    assert debug["Traccion_electrica"]["Freno_lento_apertura"]["fuente"] == "zona_vacia"
    assert debug["Traccion_hidraulica"]["Fabricante_oleo"]["fuente"] == "zona_vacia"
    assert debug["Caracteristicas"]["Velocidad"]["fuente"] == "valor_leido"
    assert debug["Caracteristicas"]["Mono"]["fuente"] == "check_zona"








