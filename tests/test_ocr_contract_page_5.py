import json
from pathlib import Path

import pytest
from tests.ocr_debug_helpers import cargar_o_generar_ocr_debug_raloe
from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import check_asociado_a_txt
from extractor_pdf.infrastructure.ocr_contract.pagina_5_raloe_crono import (
    extraer_pagina_5_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf

pytestmark = pytest.mark.ocr


def test_extrae_pagina_5_raloe_crono_desde_ocr_debug_sin_inventar_valores() -> None:
    ocr_debug = cargar_o_generar_ocr_debug_raloe(
        "654391_pagina_tecnica_page_5_ocr_tesseract.json", numero_pagina=5, dpi=200
    )
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(
        Path("pdfs/Raloe/654391.pdf").read_bytes(), numero_pagina=5, dpi=200
    )

    resultado = extraer_pagina_5_desde_ocr_con_debug(
        ocr_debug, bytes_imagen=pagina_renderizada.bytes_imagen
    )
    data = resultado["data"]
    evidencias = resultado["debug"]

    for seccion, campos in data.items():
        for campo, valor in campos.items():
            if not valor:
                continue
            assert (
                campo in evidencias.get(seccion, {})
                or check_asociado_a_txt(seccion, campo)
                or f"{campo}_txt" in evidencias.get(seccion, {})
            )

    assert data["general"]["Serie"] == "CRONO"
    assert data["Traccion_electrica"]["Modelo"] == "FRNOO18LM2A-7"
    assert data["Caracteristicas"]["Maniobra"] == "SELECTIVA BAJADA"
    assert data["Traccion_electrica"]["Longitud_cable_potencia"] == "20.000"
    assert data["Traccion_electrica"]["Micros"] == "OPTICO PNP"

    assert data["Normas"]["Norma_81_1_A3"] == ""
    assert data["Traccion_hidraulica"]["Fabricante_oleo"] == ""
    assert data["Traccion_hidraulica"]["Grupo_valvulas"] == ""
