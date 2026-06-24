from pathlib import Path

from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_raloe_crono import (
    DetectorPaginaPremontadaArmarioBotonerasRaloeCrono,
)


ROOT = Path(__file__).resolve().parents[1]


def test_detecta_pagina_premontada_armario_botoneras_7_en_654391() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654391.pdf").read_bytes())

    pagina = DetectorPaginaPremontadaArmarioBotonerasRaloeCrono().detectar(paginas)

    assert pagina.numero == 7


def test_detecta_pagina_premontada_armario_botoneras_6_en_654340() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654340.pdf").read_bytes())

    pagina = DetectorPaginaPremontadaArmarioBotonerasRaloeCrono().detectar(paginas)

    assert pagina.numero == 6








