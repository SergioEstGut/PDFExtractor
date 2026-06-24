import json
from pathlib import Path

import pytest

from extractor_pdf.infrastructure.selection.detector_ocr_raloe_crono import (
    DetectorPaginaTecnicaOcrRaloeCrono,
)


ROOT = Path(__file__).resolve().parents[1]


def test_detecta_pagina_tecnica_desde_ocr_sin_numero_fijo() -> None:
    pagina_tecnica = json.loads(
        (ROOT / "docs" / "ocr_debug" / "654391_pagina_tecnica_page_5_ocr_tesseract.json").read_text(encoding="utf-8")
    )
    paginas = [
        _pagina_ocr(1, "Pedido Compra Ref.Cliente Observaciones"),
        _pagina_ocr(2, "DETALLE DE ETIQUETAS DE PRECIO"),
        {**pagina_tecnica, "page_number": 9},
        _pagina_ocr(10, "Gestión foso / huida reducida Limitador velocidad Cab"),
    ]

    detectada = DetectorPaginaTecnicaOcrRaloeCrono().detectar(paginas)

    assert detectada.numero_pagina == 9
    assert detectada.puntuacion >= 20
    assert "traccion_electrica" in detectada.senales
    assert "tension_linea_motor" in detectada.senales


def test_detector_ocr_falla_si_no_hay_senales_tecnicas() -> None:
    with pytest.raises(ValueError, match="pagina tecnica"):
        DetectorPaginaTecnicaOcrRaloeCrono().detectar(
            [
                _pagina_ocr(1, "Pedido Compra"),
                _pagina_ocr(2, "Observaciones cliente"),
            ]
        )


def _pagina_ocr(numero: int, texto: str) -> dict:
    return {
        "page_number": numero,
        "ocr": {
            "engine": "fake",
            "language": "spa",
            "text": texto,
            "words": [],
            "lines": [],
        },
    }
