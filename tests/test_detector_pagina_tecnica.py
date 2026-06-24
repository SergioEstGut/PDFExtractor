from pathlib import Path

from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_raloe_crono import (
    DetectorPaginaTecnicaRaloeCrono,
)


ROOT = Path(__file__).resolve().parents[1]


def test_detecta_pagina_tecnica_5_en_654391() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "Raloe" / "654391.pdf").read_bytes())

    pagina_tecnica = DetectorPaginaTecnicaRaloeCrono().detectar(paginas)

    assert pagina_tecnica.numero == 5


def test_detecta_pagina_tecnica_4_en_654340() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "Raloe" / "654340.pdf").read_bytes())

    pagina_tecnica = DetectorPaginaTecnicaRaloeCrono().detectar(paginas)

    assert pagina_tecnica.numero == 4








