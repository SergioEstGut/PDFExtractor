from pathlib import Path

from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_raloe_crono import (
    DetectorPaginaFosoHuidaOpcionesRaloeCrono,
)


ROOT = Path(__file__).resolve().parents[1]


def test_detecta_pagina_foso_huida_opciones_6_en_654391() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "Raloe" / "654391.pdf").read_bytes())

    pagina = DetectorPaginaFosoHuidaOpcionesRaloeCrono().detectar(paginas)

    assert pagina.numero == 6


def test_detecta_pagina_foso_huida_opciones_5_en_654340() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "Raloe" / "654340.pdf").read_bytes())

    pagina = DetectorPaginaFosoHuidaOpcionesRaloeCrono().detectar(paginas)

    assert pagina.numero == 5








