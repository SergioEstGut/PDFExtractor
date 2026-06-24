import json
from pathlib import Path

from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import check_asociado_a_txt
from extractor_pdf.infrastructure.ocr_contract.pagina_foso_opciones_raloe_crono import (
    extraer_foso_opciones_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf


def test_extrae_foso_opciones_desde_ocr_debug_sin_inventar_valores() -> None:
    ocr_debug = json.loads(
        Path("docs/ocr_debug/654391_foso_opciones_page_6_ocr_tesseract.json").read_text(encoding="utf-8")
    )
    pagina_renderizada = RenderizadorPaginaPyMuPdf().renderizar_pagina(
        Path("pdfs/654391.pdf").read_bytes(), numero_pagina=6, dpi=200
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

    assert data["Opciones"]["Limitador_velocidad_cab"] == "Si"
    assert data["Opciones"]["Limitador_velocidad_cab_txt"] == "SLC LM18CD"
    assert data["Opciones"]["Limitador_posicion"] == "ABAJO"
    assert data["Opciones"]["Limitador_ubicacion"] == "EN CHASIS"
    assert data["Opciones"]["Accionamiento_a_dist_limitador"] == "Si"
    assert data["Opciones"]["Accionamiento_a_dist_limitador_txt"] == "190"
    assert data["Opciones"]["Pesacargas_fabricante"] == "EMESA"
    assert data["Opciones"]["Tipo_pesacargas"] == "MECANICO"
    assert data["Opciones"]["Modelo_pesacargas"] == "PSQ 2 CONTACTOS"
    assert data["Opciones"]["Distancia_pesacargas_maniobra"] == "5.000"
    assert data["Opciones"]["Luz_emergencia_cabina"] == "PLAFON"
    assert data["Opciones"]["Rescate"] == "AUTO. MOTOR"
    assert data["Opciones"]["Pos_caja_cunas"] == "ABAJO"
    assert data["Opciones"]["Comunicacion_suministro"] == "Si"
    assert data["Opciones"]["Comunicacion_suministro_txt"] == "MANIOBRA"
    assert data["Opciones"]["Modelo_comunicacion"] == "MK-852"
    assert data["Opciones"]["Sintesis_voz"] == "Si"
    assert data["Opciones"]["Sintesis_voz_txt"] == "INCLUIDO EN COMUNICACION"
    assert data["Opciones"]["Idioma_voz_1"] == "ESPAÑOL"
    assert data["Opciones"]["Interfono_suministro"] == "Si"
    assert data["Opciones"]["Interfono_suministro_txt"] == "MANIOBRA"
    assert data["Opciones"]["Enchufes"] == "Si"
    assert data["Opciones"]["Enchufes_txt"] == "SCHUKO"
    assert data["Opciones"]["Rosario"] == "Si"
    assert data["Opciones"]["Rosario_txt"] == "TIRA LEDS"
    assert data["Opciones"]["Cant_rosario"] == "1"
    assert data["Opciones"]["Posicionamiento"] == "IMANES"
    assert data["Opciones"]["Completo"] == "Si"
    assert data["Opciones"]["Luz_en_armario"] == "Si"
    assert data["Opciones"]["Socorro_electrico_en_maniobra"] == "Si"
    assert data["Opciones"]["Magnetotermicos_y_diferenciales"] == "Si"
    assert data["Opciones"]["Modulo_ARM"] == "Si"
    assert data["Opciones"]["Modulo_DCI"] == "Si"

    assert data["Gestion_foso_huida_reducida"]["Foso_tope_cant"] == ""
    assert data["Gestion_foso_huida_reducida"]["Huida_barandilla_cant"] == ""
    assert data["Opciones"]["Qt"] == ""
    assert data["Opciones"]["Suministrar_mandos_MCH_cant_txt"] == ""
