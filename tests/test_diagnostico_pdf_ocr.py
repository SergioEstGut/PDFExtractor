from scripts.diagnosticar_pdf_ocr_pedido import (
    clasificar_vacios_en_ambos,
    clasificar_vacios_ocr,
    fusionar_comparacion,
)


def test_fusion_prioriza_pdf_en_diferencias() -> None:
    fusion = fusionar_comparacion(
        {
            "coincidencias": {},
            "solo_pdf": {},
            "solo_ocr": {},
            "diferencias": {
                "Traccion_electrica": {
                    "Variador": {"pdf": "CONTROL TECHNIQUES", "ocr": "CONTROL"}
                }
            },
            "vacios_en_ambos": {},
        }
    )

    assert fusion["Traccion_electrica"]["Variador"] == "CONTROL TECHNIQUES"


def test_fusion_mantiene_vacio_si_no_lo_lee_ninguna_fuente() -> None:
    fusion = fusionar_comparacion(
        {
            "coincidencias": {},
            "solo_pdf": {},
            "solo_ocr": {},
            "diferencias": {},
            "vacios_en_ambos": {"Traccion_electrica": ["Modelo"]},
        }
    )

    assert fusion["Traccion_electrica"]["Modelo"] == ""


def test_clasifica_txt_vacio_como_dependiente_si_su_check_no_esta_marcado() -> None:
    clasificacion = clasificar_vacios_en_ambos(
        {"vacios_en_ambos": {"Opciones": ["GSM_txt", "Distancia_a_maniobra"]}},
        {"Opciones": {"GSM": "No"}},
    )

    assert clasificacion["dependientes_de_check_no_marcado"]["Opciones"] == ["GSM_txt"]
    assert clasificacion["accionables"]["Opciones"] == ["Distancia_a_maniobra"]


def test_clasifica_txt_vacio_como_accionable_si_su_check_esta_marcado() -> None:
    clasificacion = clasificar_vacios_en_ambos(
        {"vacios_en_ambos": {"Opciones": ["GSM_txt"]}},
        {"Opciones": {"GSM": "Si"}},
    )

    assert clasificacion["accionables"]["Opciones"] == ["GSM_txt"]
    assert clasificacion["dependientes_de_check_no_marcado"] == {}


def test_clasifica_orient_premontada_como_visto_vacio_si_ve_encabezado_tabla() -> None:
    clasificacion = clasificar_vacios_ocr(
        ocr_data={"Premontada": {"Orient_E1": "", "Orient_E2": ""}},
        ocr_debug_extractor={},
        lineas_ocr=[{"text": "Modelo Orient | Puertas Piso Precableadas"}],
    )

    assert clasificacion["vistos_vacios"]["Premontada"] == {
        "Orient_E1": "columna de tabla vista sin valor",
        "Orient_E2": "columna de tabla vista sin valor",
    }
    assert clasificacion["no_vistos"] == {}
