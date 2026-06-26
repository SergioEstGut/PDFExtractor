from extractor_pdf.domain.entidades import PalabraTexto
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf


def test_normaliza_contenido_dentro_de_check_como_marca() -> None:
    palabras = [
        PalabraTexto(texto="4", x0=184, y0=259, x1=191, y1=267),
        PalabraTexto(texto="81-", x0=195, y0=258, x1=209, y1=269),
    ]
    marcas = [PalabraTexto(texto="\x14", x0=183, y0=258, x1=192, y1=267)]

    normalizadas = LectorTextoPyMuPdf._normalizar_contenido_checks(palabras, marcas)

    assert normalizadas[0].texto == "\x14"
    assert normalizadas[1].texto == "81-"


def test_no_normaliza_numero_fuera_de_check() -> None:
    palabras = [
        PalabraTexto(texto="4", x0=529, y0=330, x1=535, y1=344),
    ]
    marcas = [PalabraTexto(texto="\x14", x0=183, y0=258, x1=192, y1=267)]

    normalizadas = LectorTextoPyMuPdf._normalizar_contenido_checks(palabras, marcas)

    assert normalizadas[0].texto == "4"


def test_deduplica_palabras_superpuestas() -> None:
    palabras = [
        PalabraTexto(texto="ESTANDAR", x0=501.8, y0=576.9, x1=555.9, y1=586.0),
        PalabraTexto(texto="ESTANDAR", x0=501.8, y0=576.9, x1=555.9, y1=586.0),
        PalabraTexto(texto="OTRA", x0=560, y0=576.9, x1=590, y1=586.0),
    ]

    normalizadas = LectorTextoPyMuPdf._deduplicar_palabras(palabras)

    assert [palabra.texto for palabra in normalizadas] == ["ESTANDAR", "OTRA"]
