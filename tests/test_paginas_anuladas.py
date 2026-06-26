from extractor_pdf.application import paginas_anuladas
from extractor_pdf.application.paginas_anuladas import (
    _texto_indica_anulacion,
    es_pagina_anulada_raloe,
    filtrar_paginas_anuladas_raloe,
)
from extractor_pdf.domain.entidades import MarcaVisual, PaginaPdf


def test_detecta_sello_visual_nulo_raloe() -> None:
    pagina = _pagina(
        8,
        [
            MarcaVisual(tipo="linea_coloreada", x0=190, y0=45, x1=335, y1=118),
            MarcaVisual(tipo="fondo_coloreado", x0=205, y0=67, x1=235, y1=102),
            MarcaVisual(tipo="fondo_coloreado", x0=237, y0=67, x1=265, y1=103),
            MarcaVisual(tipo="fondo_coloreado", x0=265, y0=67, x1=285, y1=102),
            MarcaVisual(tipo="fondo_coloreado", x0=287, y0=66, x1=316, y1=103),
        ],
    )

    assert es_pagina_anulada_raloe(pagina)


def test_detecta_sello_visual_nulo_raloe_escalado() -> None:
    pagina = _pagina(
        9,
        [
            MarcaVisual(tipo="linea_coloreada", x0=237, y0=64, x1=327, y1=108),
            MarcaVisual(tipo="fondo_coloreado", x0=247, y0=77, x1=265, y1=98),
            MarcaVisual(tipo="fondo_coloreado", x0=267, y0=77, x1=284, y1=99),
            MarcaVisual(tipo="fondo_coloreado", x0=284, y0=77, x1=296, y1=98),
            MarcaVisual(tipo="fondo_coloreado", x0=298, y0=77, x1=316, y1=99),
        ],
    )

    assert es_pagina_anulada_raloe(pagina)


def test_detecta_sello_visual_nulo_raloe_en_cualquier_posicion() -> None:
    pagina = _pagina(
        9,
        [
            MarcaVisual(tipo="linea_coloreada", x0=390, y0=620, x1=535, y1=693),
            MarcaVisual(tipo="fondo_coloreado", x0=405, y0=642, x1=435, y1=677),
            MarcaVisual(tipo="fondo_coloreado", x0=437, y0=642, x1=465, y1=678),
            MarcaVisual(tipo="fondo_coloreado", x0=465, y0=642, x1=485, y1=677),
            MarcaVisual(tipo="fondo_coloreado", x0=487, y0=641, x1=516, y1=678),
        ],
    )

    assert es_pagina_anulada_raloe(pagina)


def test_filtra_paginas_anuladas_sin_descartar_notas_coloreadas_normales() -> None:
    normal = _pagina(
        1,
        [
            MarcaVisual(tipo="linea_coloreada", x0=110, y0=500, x1=400, y1=501),
            MarcaVisual(tipo="fondo_coloreado", x0=100, y0=300, x1=200, y1=320),
        ],
    )
    anulada = _pagina(
        8,
        [
            MarcaVisual(tipo="linea_coloreada", x0=190, y0=45, x1=335, y1=118),
            MarcaVisual(tipo="fondo_coloreado", x0=205, y0=67, x1=235, y1=102),
            MarcaVisual(tipo="fondo_coloreado", x0=237, y0=67, x1=265, y1=103),
            MarcaVisual(tipo="fondo_coloreado", x0=265, y0=67, x1=285, y1=102),
        ],
    )

    assert filtrar_paginas_anuladas_raloe([normal, anulada]) == [normal]


def test_texto_sello_confirma_solo_anulacion() -> None:
    assert _texto_indica_anulacion("NULO")
    assert _texto_indica_anulacion("nula")
    assert _texto_indica_anulacion("ANULADO")
    assert _texto_indica_anulacion("Anulada")
    assert _texto_indica_anulacion("Muto")
    assert not _texto_indica_anulacion("HOLA")


def test_sello_visual_requiere_texto_de_anulacion_si_hay_pdf(monkeypatch) -> None:
    pagina = _pagina(
        1,
        [
            MarcaVisual(tipo="linea_coloreada", x0=390, y0=620, x1=535, y1=693),
            MarcaVisual(tipo="fondo_coloreado", x0=405, y0=642, x1=435, y1=677),
            MarcaVisual(tipo="fondo_coloreado", x0=437, y0=642, x1=465, y1=678),
            MarcaVisual(tipo="fondo_coloreado", x0=465, y0=642, x1=485, y1=677),
        ],
    )
    monkeypatch.setattr(paginas_anuladas, "_leer_texto_sello", lambda *_: "HOLA")

    assert not es_pagina_anulada_raloe(pagina, bytes_pdf=b"%PDF")

    monkeypatch.setattr(paginas_anuladas, "_leer_texto_sello", lambda *_: "NULA")

    assert es_pagina_anulada_raloe(pagina, bytes_pdf=b"%PDF")


def _pagina(numero: int, marcas: list[MarcaVisual]) -> PaginaPdf:
    return PaginaPdf(
        numero=numero,
        texto="",
        bloques=[],
        palabras=[],
        marcas_check=[],
        marcas_visuales=marcas,
        metodo_extraccion="embedded_text",
    )
