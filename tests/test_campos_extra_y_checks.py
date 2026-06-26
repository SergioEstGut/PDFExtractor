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


def _palabra(texto: str, x0: float, y0: float, x1: float, y1: float, color: int = 0) -> PalabraTexto:
    return PalabraTexto(texto=texto, x0=x0, y0=y0, x1=x1, y1=y1, color=color)
