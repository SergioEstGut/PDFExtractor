from pathlib import Path

from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_felesa_crono import (
    detectar_paginas_felesa_crono,
)


ROOT = Path(__file__).resolve().parents[1]


def test_detecta_paginas_felesa_crono_por_roles() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas(
        (ROOT / "pdfs" / "Felesa" / "654277.pdf").read_bytes()
    )

    assert detectar_paginas_felesa_crono(paginas) == {
        "principal": 1,
        "botoneras_rellano": 2,
    }
