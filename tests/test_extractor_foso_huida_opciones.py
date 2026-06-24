import json
from pathlib import Path
from typing import Any

from extractor_pdf.infrastructure.extraction.client_base.extractor_foso_huida_opciones import (
    ExtractorFosoHuidaOpcionesRaloeCrono,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf


ROOT = Path(__file__).resolve().parents[1]
ESPERADO = ROOT / "tests" / "fixtures" / "expected"


def test_extrae_foso_huida_opciones_de_654391_pagina_6() -> None:
    pagina_6 = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654391.pdf").read_bytes())[5]

    resultado = ExtractorFosoHuidaOpcionesRaloeCrono().extraer(pagina_6)

    assert resultado == _load_esperado("654391_page_6.json")


def test_extrae_foso_huida_opciones_de_654340_pagina_5() -> None:
    pagina_5 = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654340.pdf").read_bytes())[4]

    resultado = ExtractorFosoHuidaOpcionesRaloeCrono().extraer(pagina_5)

    assert resultado == _load_esperado("654340_page_5.json")


def test_debug_pdf_foso_opciones_marca_campos_pendientes_como_zona_vacia() -> None:
    pagina_6 = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654391.pdf").read_bytes())[5]

    resultado = ExtractorFosoHuidaOpcionesRaloeCrono().extraer_con_debug(pagina_6)
    debug = resultado["debug_pdf"]

    assert debug["Gestion_foso_huida_reducida"]["Foso_tope_cant"]["fuente"] == "zona_vacia"
    assert debug["Gestion_foso_huida_reducida"]["Huida_barandilla_cant"]["fuente"] == "zona_vacia"
    assert debug["Opciones"]["Qt"]["fuente"] == "zona_vacia"
    assert debug["Opciones"]["Distancia_a_maniobra"]["fuente"] == "zona_vacia"
    assert debug["Opciones"]["Limitador_velocidad_cab"]["fuente"] == "valor_leido"
    assert debug["Opciones"]["Completo"]["fuente"] == "check_zona"


def _load_esperado(nombre_archivo: str) -> dict[str, Any]:
    return json.loads((ESPERADO / nombre_archivo).read_text(encoding="utf-8"))








