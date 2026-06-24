from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import (
    aplicar_contrato_salida,
    check_asociado_a_txt,
    normalizar_checks_con_texto_asociado,
    normalizar_valor_campo,
)


def test_normaliza_double_desde_especificacion_de_campo() -> None:
    assert normalizar_valor_campo("Caracteristicas", "Velocidad", "0,80 m/s") == "0.80"
    assert normalizar_valor_campo("Traccion_electrica", "Frec_motor", "19,47 hz") == "19.47"


def test_normaliza_int_desde_especificacion_de_campo() -> None:
    assert normalizar_valor_campo("Caracteristicas", "Paradas", "5 paradas") == "5"


def test_respeta_texto_desde_especificacion_de_campo() -> None:
    assert normalizar_valor_campo("Traccion_electrica", "Modelo", "FRN0018LM2A-7") == "FRN0018LM2A-7"


def test_preserva_no_en_check_simple_con_valor_no_marcado() -> None:
    assert normalizar_valor_campo("Puertas_cabina_embarque_1", "Leva_electrica_op1", "No") == "No"


def test_valor_asociado_infiere_check_marcado() -> None:
    salida = aplicar_contrato_salida(
        {
            "Puertas_cabina_embarque_1": {
                "Leva_electrica_op1": "No",
                "Leva_electrica_op1_txt": "120 mm",
            }
        }
    )

    assert salida["Puertas_cabina_embarque_1"]["Leva_electrica_op1"] == "Si"
    assert salida["Puertas_cabina_embarque_1"]["Leva_electrica_op1_txt"] == "120"


def test_valor_asociado_vacio_no_infiere_check_marcado() -> None:
    salida = aplicar_contrato_salida(
        {
            "Puertas_cabina_embarque_1": {
                "Leva_electrica_op1": "No",
                "Leva_electrica_op1_txt": "",
            }
        }
    )

    assert salida["Puertas_cabina_embarque_1"]["Leva_electrica_op1"] == "No"


def test_valor_asociado_infiere_check_aunque_no_venga_en_lectura() -> None:
    salida = aplicar_contrato_salida(
        {
            "Puertas_cabina_embarque_1": {
                "Leva_electrica_op1_txt": "120 mm",
            }
        }
    )

    assert salida["Puertas_cabina_embarque_1"]["Leva_electrica_op1"] == "Si"


def test_normaliza_check_con_texto_asociado_desde_valor_en_campo_check() -> None:
    salida = normalizar_checks_con_texto_asociado(
        {
            "Opciones": {
                "Interfono_suministro": "MANIOBRA",
                "Interfono_suministro_txt": "",
            }
        }
    )

    assert salida["Opciones"]["Interfono_suministro"] == "Si"
    assert salida["Opciones"]["Interfono_suministro_txt"] == "MANIOBRA"


def test_normaliza_check_con_texto_asociado_no_inventa_si_viene_vacio() -> None:
    salida = normalizar_checks_con_texto_asociado(
        {
            "Opciones": {
                "Interfono_suministro": "",
                "Interfono_suministro_txt": "",
            }
        }
    )

    assert salida["Opciones"]["Interfono_suministro"] == ""
    assert salida["Opciones"]["Interfono_suministro_txt"] == ""


def test_normaliza_check_con_texto_asociado_no_crea_txt_si_no_viene_leido() -> None:
    salida = normalizar_checks_con_texto_asociado(
        {
            "Normas": {
                "Norma_81_73": "No",
            }
        }
    )

    assert "Norma_81_73_txt" not in salida["Normas"]


def test_contrato_expone_check_asociado_a_txt() -> None:
    assert check_asociado_a_txt("Opciones", "Interfono_suministro_txt") == "Interfono_suministro"
