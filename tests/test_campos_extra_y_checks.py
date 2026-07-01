from extractor_pdf.application.campos_extra import detectar_campos_extra
from extractor_pdf.domain.entidades import BloqueTexto, PaginaPdf, PalabraTexto
from extractor_pdf.infrastructure.extraction.client_base.extraccion_declarativa_pdf import (
    extraer_por_reglas_pdf,
)


def test_no_detecta_lineas_rojas_como_campos_extra() -> None:
    pagina = PaginaPdf(
        numero=1,
        texto="NS: M240100477 que",
        palabras=[
            _palabra("NS:", 10, 10, 25, 20, color=0xFF0000),
            _palabra("M240100477", 30, 10, 100, 20, color=0xFF0000),
            _palabra("que", 105, 10, 130, 20, color=0xFF0000),
        ],
        metodo_extraccion="test",
    )

    assert detectar_campos_extra([pagina], {}) == {}


def test_no_detecta_campos_extra_antes_de_detalle_en_pagina_tecnica() -> None:
    pagina = PaginaPdf(
        numero=4,
        texto="Leva eléctrica: 220\nDETALLE DE MATERIAL\nSerie: CRONO",
        bloques=[
            BloqueTexto(texto="Leva eléctrica: 220", x0=150, y0=70, x1=300, y1=80),
            BloqueTexto(texto="DETALLE DE MATERIAL", x0=250, y0=95, x1=360, y1=105),
            BloqueTexto(texto="Serie: CRONO", x0=30, y0=130, x1=100, y1=140),
        ],
        metodo_extraccion="test",
    )

    assert detectar_campos_extra(
        [pagina],
        {"general": {"Serie": "CRONO"}},
        secciones_por_pagina={4: ["general"]},
    ) == {}


def test_no_detecta_alias_contractual_generico_como_campo_extra() -> None:
    pagina = PaginaPdf(
        numero=4,
        texto="DETALLE DE MATERIAL\nLeva eléctrica: 220",
        bloques=[
            BloqueTexto(texto="DETALLE DE MATERIAL", x0=250, y0=95, x1=360, y1=105),
            BloqueTexto(texto="Leva eléctrica: 220", x0=44, y0=783, x1=140, y1=795),
        ],
        metodo_extraccion="test",
    )

    assert detectar_campos_extra(
        [pagina],
        {"Puertas_cabina_embarque_1": {"Leva_electrica_op1": "Si"}},
        secciones_por_pagina={4: ["general", "Puertas_cabina_embarque_1"]},
    ) == {}


def test_check_antes_de_alias_acepta_marca_textual() -> None:
    pagina = PaginaPdf(
        numero=1,
        texto="",
        palabras=[
            _palabra("\u2714", 184, 259, 191, 267),
            _palabra("81-", 195, 258, 209, 269),
            _palabra("20/50", 212, 258, 237, 269),
        ],
        metodo_extraccion="test",
    )
    especificaciones = {
        "Norma_81_20_50": {
            "nombre": "Norma_81_20_50",
            "tipo": "check_simple",
            "reglas": {
                "valor_marcado": "Si",
                "valor_no_marcado": "No",
                "extraccion_pdf": {
                    "modo": "check_antes_de_alias",
                    "aliases": ["81- 20/50"],
                    "distancia_maxima": 55,
                    "tolerancia_y": 8,
                    "si_no_hay_check": "No",
                },
            },
        }
    }

    assert extraer_por_reglas_pdf(
        pagina,
        "Normas",
        especificaciones_param=especificaciones,
        configuracion_pdf_param={},
    ) == {"Norma_81_20_50": "Si"}


def test_ignora_texto_rojo_al_leer_respuesta_de_campo() -> None:
    pagina = PaginaPdf(
        numero=5,
        texto="Pos.Caja Cuñas: ARRIBA techo de",
        palabras=[
            _palabra("Pos.Caja", 10, 10, 50, 20),
            _palabra("Cuñas:", 55, 10, 90, 20),
            _palabra("ARRIBA", 95, 10, 135, 20),
            _palabra("techo", 140, 10, 175, 20, color=0xFF0000),
            _palabra("de", 180, 10, 195, 20, color=0xFF0000),
        ],
        metodo_extraccion="test",
    )
    especificaciones = {
        "Pos_caja_cunas": {
            "nombre": "Pos_caja_cunas",
            "tipo": "texto",
            "aliases": ["Pos.Caja Cuñas"],
            "reglas": {
                "extraccion_pdf": {
                    "modo": "texto_derecha_alias",
                    "tokens": 3,
                }
            },
        }
    }

    assert extraer_por_reglas_pdf(
        pagina,
        "Opciones",
        especificaciones_param=especificaciones,
        configuracion_pdf_param={},
    ) == {"Pos_caja_cunas": "ARRIBA"}


def test_texto_debajo_hasta_unidad_corta_unidad_con_texto_pegado() -> None:
    pagina = PaginaPdf(
        numero=1,
        texto="Maquina\nminiACT170 240mm 2:1 630Kg(7x6,5)",
        palabras=[
            _palabra("Maquina", 10, 10, 55, 20),
            _palabra("miniACT170", 10, 30, 70, 40),
            _palabra("240mm", 75, 30, 115, 40),
            _palabra("2:1", 120, 30, 145, 40),
            _palabra("630Kg(7x6,5)", 150, 30, 220, 40),
        ],
        metodo_extraccion="test",
    )
    especificaciones = {
        "Maquina": {
            "nombre": "Maquina",
            "tipo": "texto",
            "aliases": ["Maquina"],
            "reglas": {
                "extraccion_pdf": {
                    "modo": "texto_debajo_hasta_unidad",
                    "aliases": ["Maquina"],
                    "filas_debajo": 1,
                    "limite_x_derecha": 240,
                    "unidad": "kg",
                }
            },
        }
    }

    assert extraer_por_reglas_pdf(
        pagina,
        "Datos_Generales",
        especificaciones_param=especificaciones,
        configuracion_pdf_param={},
    ) == {"Maquina": "miniACT170 240mm 2:1"}


def test_tipo_llavin_placa_acepta_texto_en_borde_inferior_de_zona() -> None:
    pagina = PaginaPdf(
        numero=2,
        texto="C/retorno C/registro",
        palabras=[
            _palabra("C/retorno", 268.7, 333.6, 302.1, 342.6),
            _palabra("C/registro", 304.3, 333.6, 339.1, 342.6),
            _palabra("1", 300.6, 345.4, 307.3, 358.8),
        ],
        metodo_extraccion="test",
    )
    especificaciones = {
        "NEO_1K_tipo_llavin": {
            "nombre": "NEO_1K_tipo_llavin",
            "tipo": "texto",
            "aliases": ["NEO_1K tipo llavin"],
            "reglas": {
                "extraccion_pdf": {
                    "modo": "texto_en_zona",
                    "x_min": 260,
                    "x_max": 350,
                    "y_min": 328,
                    "y_max": 344,
                    "ignorar_valores": ["---"],
                }
            },
        }
    }

    assert extraer_por_reglas_pdf(
        pagina,
        "Placas_Botoneras_Rellano",
        especificaciones_param=especificaciones,
        configuracion_pdf_param={},
    ) == {"NEO_1K_tipo_llavin": "C/retorno C/registro"}


def test_texto_derecha_alias_puede_conservar_v_si_la_regla_lo_permite() -> None:
    pagina = PaginaPdf(
        numero=1,
        texto="Tipo Display DISPLAY TFT 7 ESSENTIAL V",
        palabras=[
            _palabra("Tipo", 10, 10, 30, 20),
            _palabra("Display", 35, 10, 70, 20),
            _palabra("DISPLAY", 80, 10, 125, 20),
            _palabra("TFT", 130, 10, 150, 20),
            _palabra("7", 155, 10, 160, 20),
            _palabra("ESSENTIAL", 165, 10, 220, 20),
            _palabra("V", 225, 10, 232, 20),
        ],
        metodo_extraccion="test",
    )
    especificaciones = {
        "Tipo_display": {
            "nombre": "Tipo_display",
            "tipo": "texto",
            "aliases": ["Tipo Display"],
            "reglas": {
                "extraccion_pdf": {
                    "modo": "texto_derecha_alias",
                    "aliases": ["Tipo Display"],
                    "limite_x_derecha": 240,
                    "permitir_valores_ruido": ["V"],
                }
            },
        }
    }

    assert extraer_por_reglas_pdf(
        pagina,
        "Botonera_Cabina",
        especificaciones_param=especificaciones,
        configuracion_pdf_param={},
    ) == {"Tipo_display": "DISPLAY TFT 7 ESSENTIAL V"}


def _palabra(texto: str, x0: float, y0: float, x1: float, y1: float, color: int = 0) -> PalabraTexto:
    return PalabraTexto(texto=texto, x0=x0, y0=y0, x1=x1, y1=y1, color=color)
