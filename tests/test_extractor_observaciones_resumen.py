import json
from pathlib import Path

from extractor_pdf.infrastructure.extraction.client_base.extractor_observaciones_resumen import (
    ExtractorObservacionesResumenRaloeCrono,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf


ROOT = Path(__file__).resolve().parents[1]


def test_extrae_observaciones_de_resumen_654391() -> None:
    pagina_1 = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654391.pdf").read_bytes())[0]
    esperado = json.loads(
        (ROOT / "tests" / "fixtures" / "expected" / "654391_page_1.json").read_text(
            encoding="utf-8"
        )
    )

    resultado = ExtractorObservacionesResumenRaloeCrono().extraer(pagina_1)

    assert resultado == esperado


def test_devuelve_observaciones_null_si_resumen_no_tiene_observacion() -> None:
    pagina_1 = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654340.pdf").read_bytes())[0]
    esperado = json.loads(
        (ROOT / "tests" / "fixtures" / "expected" / "654340_page_1.json").read_text(
            encoding="utf-8"
        )
    )

    resultado = ExtractorObservacionesResumenRaloeCrono().extraer(pagina_1)

    assert resultado == esperado


def test_extrae_observaciones_continuadas_antes_de_detalle_precios() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654144.pdf").read_bytes())

    resultado = ExtractorObservacionesResumenRaloeCrono().extraer_paginas(paginas)

    assert "Añadir toma de tierra extra" in resultado["Observaciones"]
    assert "VENTILADOR EN CABINA ACTIVADO" in resultado["Observaciones"]
    assert "DETALLE DE ETIQUETAS DE PRECIO" not in resultado["Observaciones"]








