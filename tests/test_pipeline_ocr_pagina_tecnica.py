from pathlib import Path

import pytest
from tests.ocr_debug_helpers import cargar_o_generar_ocr_debug_raloe
from extractor_pdf.domain.entidades import PaginaRenderizada
from extractor_pdf.infrastructure.ocr_contract.pipeline_pagina_tecnica import (
    extraer_pagina_tecnica_ocr_desde_pdf,
)


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.ocr


def test_pipeline_ocr_detecta_pagina_tecnica_antes_de_extraer() -> None:
    ocr_tecnico = cargar_o_generar_ocr_debug_raloe(
        "654391_pagina_tecnica_page_5_ocr_tesseract.json", numero_pagina=5, dpi=200
    )
    extractor = ExtractorVisualFake({5: ocr_tecnico})

    resultado = extraer_pagina_tecnica_ocr_desde_pdf(
        (ROOT / "pdfs" / "Raloe" / "654391.pdf").read_bytes(),
        extractor_visual=extractor,
        renderizador=RenderizadorFake(total_paginas=7),
    )

    assert resultado["metadata"]["technical_page"] == 5
    assert resultado["metadata"]["score"] >= 20
    assert resultado["data"]["general"]["Serie"] == "CRONO"
    assert resultado["data"]["Traccion_electrica"]["Modelo"] == "FRNOO18LM2A-7"
    assert extractor.paginas_leidas == [1, 2, 3, 4, 5, 6, 7]


class RenderizadorFake:
    def __init__(self, total_paginas: int) -> None:
        self.total_paginas = total_paginas

    def contar_paginas(self, bytes_pdf: bytes) -> int:
        return self.total_paginas

    def renderizar_pagina(self, bytes_pdf: bytes, numero_pagina: int, dpi: int = 200) -> PaginaRenderizada:
        return PaginaRenderizada(
            numero_pagina=numero_pagina,
            bytes_imagen=b"",
            formato_imagen="png",
            ancho=1,
            alto=1,
            dpi=dpi,
        )


class ExtractorVisualFake:
    def __init__(self, paginas: dict[int, dict]) -> None:
        self.paginas = paginas
        self.paginas_leidas: list[int] = []

    def extraer(self, pagina_renderizada: PaginaRenderizada, cliente_id: str) -> dict:
        self.paginas_leidas.append(pagina_renderizada.numero_pagina)
        return self.paginas.get(
            pagina_renderizada.numero_pagina,
            {
                "ocr": {
                    "engine": "fake",
                    "language": "spa",
                    "text": "Pedido Compra",
                    "words": [],
                    "lines": [],
                }
            },
        )
