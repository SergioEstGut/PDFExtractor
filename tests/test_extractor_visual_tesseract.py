from pathlib import Path
import shutil

import pytest

from extractor_pdf.infrastructure.ocr.extractor_visual_tesseract import (
    ErrorTesseractNoDisponible,
    ExtractorVisualTesseract,
)
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf


PDF_PATH = Path(__file__).resolve().parents[1] / "pdfs" / "654391.pdf"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract no esta instalado en PATH")
def test_tesseract_lee_texto_de_pagina_5_renderizada() -> None:
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(PDF_PATH.read_bytes(), numero_pagina=5, dpi=200)

    resultado = ExtractorVisualTesseract().extraer(pagina_renderizada, cliente_id="cliente_base")

    assert resultado["ocr"]["engine"] == "tesseract"
    assert "MO/4473005" in resultado["ocr"]["text"]
    assert resultado["ocr"]["words"]
    assert resultado["ocr"]["lines"]
    assert resultado["ocr"]["line_count"] == len(resultado["ocr"]["lines"])


def test_tesseract_informa_si_falta_dependencia_o_binario() -> None:
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(PDF_PATH.read_bytes(), numero_pagina=5, dpi=100)

    try:
        resultado = ExtractorVisualTesseract(idioma="eng").extraer(
            pagina_renderizada,
            cliente_id="cliente_base",
        )
    except ErrorTesseractNoDisponible as exc:
        assert str(exc)
    else:
        assert resultado["ocr"]["engine"] == "tesseract"








