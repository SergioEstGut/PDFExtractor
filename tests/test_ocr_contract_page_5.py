import json
from pathlib import Path

from extractor_pdf.infrastructure.ocr_contract.pagina_5_raloe_crono import (
    extraer_pagina_5_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf


def test_extrae_pagina_5_raloe_crono_desde_ocr_debug_sin_inventar_valores() -> None:
    ocr_debug = json.loads(
        Path("docs/ocr_debug/654391_pagina_tecnica_page_5_ocr_tesseract.json").read_text(encoding="utf-8")
    )
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(
        Path("pdfs/654391.pdf").read_bytes(), numero_pagina=5, dpi=200
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
            assert campo in evidencias.get(seccion, {})

    assert data["general"]["Serie"] == "CRONO"
    assert data["Caracteristicas"]["Tension_linea"] == "240"
    assert data["Traccion_electrica"]["Modelo"] == "FRNOO18LM2A-7"
    assert data["Puertas_cabina_embarque_1"]["Barreras_Op1"] == "Si"
    assert data["Puertas_cabina_embarque_1"]["Barreras_Op1_txt"] == "MINI-CC-36"
    assert data["Puertas_cabina_embarque_2"]["Barreras_op2"] == "Si"
    assert data["Puertas_cabina_embarque_2"]["Barreras_Op2_txt"] == "MINI-CC-36"
    assert data["Caracteristicas"]["Velocidad"] == "0.80"
    assert data["Caracteristicas"]["Mono"] == "Si"
    assert data["Caracteristicas"]["Sin_cuarto_de_maquinas"] == "No"
    assert data["Traccion_electrica"]["Conectores"] == "No"
    assert evidencias["Caracteristicas"]["Velocidad"]["valor_crudo"] == "0,80"
    assert evidencias["Caracteristicas"]["Velocidad"]["valor_normalizado"] == "0.80"

    assert data["Normas"]["Norma_81_1_A3"] == ""
    assert data["Traccion_hidraulica"]["Fabricante_oleo"] == ""
    assert data["Traccion_hidraulica"]["Grupo_valvulas"] == ""
