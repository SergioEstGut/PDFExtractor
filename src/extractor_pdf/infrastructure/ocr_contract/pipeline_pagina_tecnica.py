from __future__ import annotations

from typing import Any

from extractor_pdf.domain.puertos import ExtractorVisualPagina
from extractor_pdf.infrastructure.ocr_contract.pagina_5_raloe_crono import (
    extraer_pagina_5_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf
from extractor_pdf.infrastructure.selection.detector_ocr_raloe_crono import (
    DetectorPaginaTecnicaOcrRaloeCrono,
)


def extraer_pagina_tecnica_ocr_desde_pdf(
    bytes_pdf: bytes,
    extractor_visual: ExtractorVisualPagina,
    renderizador: RenderizadorPaginaPyMuPdf | None = None,
    dpi: int = 200,
) -> dict[str, Any]:
    renderizador = renderizador or RenderizadorPaginaPyMuPdf()
    paginas_ocr = []
    for numero_pagina in range(1, renderizador.contar_paginas(bytes_pdf) + 1):
        renderizada = renderizador.renderizar_pagina(bytes_pdf, numero_pagina=numero_pagina, dpi=dpi)
        pagina_ocr = extractor_visual.extraer(renderizada, cliente_id="cliente_base")
        pagina_ocr["page_number"] = numero_pagina
        paginas_ocr.append(pagina_ocr)

    detectada = DetectorPaginaTecnicaOcrRaloeCrono().detectar(paginas_ocr)
    resultado = extraer_pagina_5_desde_ocr_con_debug(detectada.ocr)
    resultado["metadata"] = {
        "technical_page": detectada.numero_pagina,
        "score": detectada.puntuacion,
        "signals": detectada.senales,
        "dpi": dpi,
    }
    return resultado
