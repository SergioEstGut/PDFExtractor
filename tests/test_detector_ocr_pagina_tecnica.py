import pytest

from tests.ocr_debug_helpers import cargar_o_generar_ocr_debug_raloe
from extractor_pdf.infrastructure.selection.detector_ocr_raloe_crono import (
    DetectorPaginaTecnicaOcrRaloeCrono,
)

pytestmark = pytest.mark.ocr


def test_detecta_pagina_tecnica_desde_ocr_sin_numero_fijo() -> None:
    pagina_tecnica = cargar_o_generar_ocr_debug_raloe(
        "654391_pagina_tecnica_page_5_ocr_tesseract.json", numero_pagina=5, dpi=200
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
