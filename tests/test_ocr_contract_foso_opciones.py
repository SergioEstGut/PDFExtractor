import json
from pathlib import Path

import pytest
from tests.ocr_debug_helpers import cargar_o_generar_ocr_debug_raloe
from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import check_asociado_a_txt
from extractor_pdf.infrastructure.ocr_contract.pagina_foso_opciones_raloe_crono import (
    extraer_foso_opciones_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf

pytestmark = pytest.mark.ocr


def test_extrae_foso_opciones_desde_ocr_debug_sin_inventar_valores() -> None:
    ocr_debug = cargar_o_generar_ocr_debug_raloe(
        "654391_foso_opciones_page_6_ocr_tesseract.json", numero_pagina=6, dpi=200
    )
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(
        Path("pdfs/Raloe/654391.pdf").read_bytes(), numero_pagina=6, dpi=200
    )

    resultado = extraer_foso_opciones_desde_ocr_con_debug(
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
                or (campo == "Idioma_voz_1" and "Idioma_voz" in evidencias.get(seccion, {}))
            )

    assert data["Opciones"]["Accionamiento_a_dist_limitador"] == "Si"
    assert data["Opciones"]["Accionamiento_a_dist_limitador_txt"] == "190"
    assert data["Opciones"]["Pesacargas_fabricante"] == "EMESA"
    assert data["Opciones"]["Tipo_pesacargas"] == "MECANICO"
    assert data["Opciones"]["Modelo_pesacargas"] == "PSQ 2 CONTACTOS"
    assert data["Opciones"]["Distancia_pesacargas_maniobra"] == "5.000"
    assert data["Opciones"]["Luz_emergencia_cabina"] == "PLAFON"
    assert data["Opciones"]["Pos_caja_cunas"] == "ABAJO"
    assert data["Opciones"]["Completo"] == "Si"
    assert data["Opciones"]["Luz_en_armario"] == "Si"

    assert data["Gestion_foso_huida_reducida"]["Foso_tope_cant"] == ""
    assert data["Gestion_foso_huida_reducida"]["Huida_barandilla_cant"] == ""
    assert data["Opciones"]["Qt"] == ""
    assert data["Opciones"]["Suministrar_mandos_MCH_cant_txt"] == ""
