import re

from extractor_pdf.domain.entidades import MarcaVisual, PaginaPdf


def filtrar_paginas_anuladas_raloe(
    paginas: list[PaginaPdf], bytes_pdf: bytes | None = None
) -> list[PaginaPdf]:
    """Descarta copias anuladas con sello confirmado por texto."""
    return [
        pagina
        for pagina in paginas
        if not es_pagina_anulada_raloe(pagina, bytes_pdf=bytes_pdf)
    ]


def es_pagina_anulada_raloe(pagina: PaginaPdf, bytes_pdf: bytes | None = None) -> bool:
    sellos = candidatos_sello_anulacion_raloe(pagina)
    if not sellos:
        return False
    if bytes_pdf is None:
        return True
    return any(_sello_confirma_anulacion(bytes_pdf, pagina.numero, sello) for sello in sellos)


def candidatos_sello_anulacion_raloe(pagina: PaginaPdf) -> list[MarcaVisual]:
    sellos = [
        marca
        for marca in pagina.marcas_visuales
        if marca.tipo == "linea_coloreada"
        and 80 <= _ancho(marca) <= 180
        and 35 <= _alto(marca) <= 95
    ]

    return [sello for sello in sellos if _contiene_letras_de_sello(pagina, sello)]


def _contiene_letras_de_sello(pagina: PaginaPdf, sello: MarcaVisual) -> bool:
    margen_x = 20
    margen_y = 10
    fondos_letras = [
        marca
        for marca in pagina.marcas_visuales
        if marca.tipo == "fondo_coloreado"
        and sello.x0 - margen_x <= marca.x0 <= sello.x1 + margen_x
        and sello.y0 - margen_y <= marca.y0 <= sello.y1 + margen_y
        and 8 <= _ancho(marca) <= 45
        and 18 <= _alto(marca) <= 50
    ]
    return len(fondos_letras) >= 3


def _sello_confirma_anulacion(bytes_pdf: bytes, numero_pagina: int, sello: MarcaVisual) -> bool:
    texto = _leer_texto_sello(bytes_pdf, numero_pagina, sello)
    return _texto_indica_anulacion(texto)


def _leer_texto_sello(bytes_pdf: bytes, numero_pagina: int, sello: MarcaVisual) -> str:
    try:
        import fitz
        import pytesseract
        from PIL import Image
        from io import BytesIO
    except Exception:
        return ""

    documento = fitz.open(stream=bytes_pdf, filetype="pdf")
    try:
        pagina = documento[numero_pagina - 1]
        clip = fitz.Rect(
            max(0, sello.x0 - 40),
            max(0, sello.y0 - 30),
            min(pagina.rect.width, sello.x1 + 40),
            min(pagina.rect.height, sello.y1 + 30),
        )
        pixmap = pagina.get_pixmap(clip=clip, dpi=300, alpha=False)
        imagen = Image.open(BytesIO(pixmap.tobytes("png")))
        textos = [
            pytesseract.image_to_string(imagen, lang="spa+eng", config=config)
            for config in ("--psm 7", "--psm 8", "--psm 6")
        ]
        return "\n".join(texto for texto in textos if texto)
    except Exception:
        return ""
    finally:
        documento.close()


def _texto_indica_anulacion(texto: str) -> bool:
    normalizado = _normalizar_texto_sello(texto)
    if re.search(r"\b(?:NULO|NULA|ANULADO|ANULADA)\b", normalizado):
        return True
    return any(_parece_palabra_anulacion(token) for token in normalizado.split())


def _parece_palabra_anulacion(token: str) -> bool:
    if token in {"MUTO"}:
        return True
    objetivos = ("NULO", "NULA", "ANULADO", "ANULADA")
    return any(
        abs(len(token) - len(objetivo)) <= 1
        and _distancia_levenshtein(token, objetivo) <= _distancia_maxima(objetivo)
        for objetivo in objetivos
    )


def _distancia_maxima(objetivo: str) -> int:
    return 1 if len(objetivo) <= 4 else 2


def _distancia_levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    anterior = list(range(len(b) + 1))
    for indice_a, char_a in enumerate(a, start=1):
        actual = [indice_a]
        for indice_b, char_b in enumerate(b, start=1):
            actual.append(
                min(
                    anterior[indice_b] + 1,
                    actual[indice_b - 1] + 1,
                    anterior[indice_b - 1] + (char_a != char_b),
                )
            )
        anterior = actual
    return anterior[-1]


def _normalizar_texto_sello(texto: str) -> str:
    texto = texto.upper().replace("0", "O")
    texto = re.sub(r"[^A-Z]+", " ", texto)
    return " ".join(texto.split())


def _ancho(marca: MarcaVisual) -> float:
    return abs(marca.x1 - marca.x0)


def _alto(marca: MarcaVisual) -> float:
    return abs(marca.y1 - marca.y0)
