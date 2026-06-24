import json
from pathlib import Path
from typing import Any

from extractor_pdf.infrastructure.ocr.extractor_visual_tesseract import ExtractorVisualTesseract
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf


ROOT = Path(__file__).resolve().parents[1]


def cargar_o_generar_ocr_debug_raloe(nombre_archivo: str, numero_pagina: int, dpi: int) -> dict[str, Any]:
    ruta_debug = ROOT / "docs" / "ocr_debug" / nombre_archivo
    if ruta_debug.is_file():
        return json.loads(ruta_debug.read_text(encoding="utf-8"))

    pdf = ROOT / "pdfs" / "Raloe" / "654391.pdf"
    render = RenderizadorPaginaPyMuPdf().renderizar_pagina(
        pdf.read_bytes(),
        numero_pagina=numero_pagina,
        dpi=dpi,
    )
    ocr_debug = ExtractorVisualTesseract().extraer(render, cliente_id="cliente_base")
    ocr_debug.update(
        {
            "pdf": str(pdf),
            "page_number": numero_pagina,
            "dpi": dpi,
            "image": {"width": render.ancho, "height": render.alto},
        }
    )
    return ocr_debug
