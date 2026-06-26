from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import (
    aplicar_contrato_salida,
    check_asociado_a_txt,
    normalizar_checks_con_texto_asociado,
    normalizar_valor_campo,
    warnings_checks_con_texto_asociado,
)


def test_normaliza_double_desde_especificacion_de_campo() -> None:
    assert normalizar_valor_campo("Caracteristicas", "Velocidad", "0,80 m/s") == "0.80"
    assert normalizar_valor_campo("Traccion_electrica", "Frec_motor", "19,47 hz") == "19.47"


def test_normaliza_int_desde_especificacion_de_campo() -> None:
    assert normalizar_valor_campo("Caracteristicas", "Paradas", "5 paradas") == "5"


def test_respeta_texto_desde_especificacion_de_campo() -> None:
    assert normalizar_valor_campo("Traccion_electrica", "Modelo", "FRN0018LM2A-7") == "FRN0018LM2A-7"


def test_guion_es_vacio_en_campo_escalar() -> None:
    assert normalizar_valor_campo("Puertas_cabina_embarque_1", "Tipo_op1", "-") == ""


def test_guion_se_preserva_en_tablas_y_secuencias() -> None:
    salida = aplicar_contrato_salida(
        {
            "Premontada": {
                "Acceso_E1": "-3,-2,-,0",
                "Piso_E1": "A,A,-,A",
            }
        }
    )

    assert salida["Premontada"]["Acceso_E1"] == "-3,-2,-,0"
    assert salida["Premontada"]["Piso_E1"] == "A,A,-,A"


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
    assert salida["warning"] == [
        {
            "tipo": "check_no_marcado_con_valor_asociado",
            "campo_check": "Puertas_cabina_embarque_1.Leva_electrica_op1",
            "campo_valor": "Puertas_cabina_embarque_1.Leva_electrica_op1_txt",
            "valor_check": "No",
            "valor_asociado": "120",
        }
    ]


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


def test_warning_si_check_no_marcado_tiene_valor_asociado() -> None:
    warnings = warnings_checks_con_texto_asociado(
        {
            "Puertas_cabina_embarque_1": {
                "Barreras_Op1": "No",
                "Barreras_Op1_txt": "N",
            }
        }
    )

    assert warnings == [
        {
            "tipo": "check_no_marcado_con_valor_asociado",
            "campo_check": "Puertas_cabina_embarque_1.Barreras_Op1",
            "campo_valor": "Puertas_cabina_embarque_1.Barreras_Op1_txt",
            "valor_check": "No",
            "valor_asociado": "N",
        }
    ]


def test_warning_si_check_marcado_no_tiene_valor_asociado() -> None:
    warnings = warnings_checks_con_texto_asociado(
        {
            "Puertas_cabina_embarque_1": {
                "Barreras_Op1": "Si",
                "Barreras_Op1_txt": "",
            }
        }
    )

    assert warnings == [
        {
            "tipo": "check_marcado_sin_valor_asociado",
            "campo_check": "Puertas_cabina_embarque_1.Barreras_Op1",
            "campo_valor": "Puertas_cabina_embarque_1.Barreras_Op1_txt",
            "valor_check": "Si",
            "valor_asociado": "",
        }
    ]
