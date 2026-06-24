from __future__ import annotations

import re
import unicodedata

from extractor_pdf.domain.entidades import PaginaPdf


ANCLAS_POR_ROL = {
    "principal": {
        "formulario maniobras crono": 3,
        "normas": 2,
        "datos generales": 2,
        "datos motor": 2,
        "datos cabina": 2,
        "medidas premontada": 2,
    },
    "botoneras_rellano": {
        "datos instalacion": 3,
        "botoneras de rellano": 3,
        "placa para botoneras de rellano": 3,
        "neo 1t": 1,
        "neo 2tt": 1,
        "neo 3ktt": 1,
    },
}

PUNTUACION_MINIMA = {
    "principal": 7,
    "botoneras_rellano": 7,
}


def detectar_plantilla_felesa_crono(paginas: list[PaginaPdf]) -> str:
    texto = _normalizar("\n".join(pagina.texto for pagina in paginas[:2]))
    if (
        "formulario maniobra crono hidraulicas" in texto
        or "datos central" in texto
        or "hidraulico" in texto
    ):
        return "felesa_crono_hidraulico"
    return "felesa_crono_electrico"


def detectar_paginas_felesa_crono(paginas: list[PaginaPdf]) -> dict[str, int]:
    resultado: dict[str, int] = {}
    for rol, anclas in ANCLAS_POR_ROL.items():
        pagina, puntuacion = _mejor_pagina(paginas, anclas)
        if pagina is not None and puntuacion >= PUNTUACION_MINIMA[rol]:
            resultado[rol] = pagina
    return resultado


def _mejor_pagina(paginas: list[PaginaPdf], anclas: dict[str, int]) -> tuple[int | None, int]:
    mejor_pagina: int | None = None
    mejor_puntuacion = 0
    for pagina in paginas:
        texto = _normalizar(pagina.texto)
        puntuacion = sum(peso for ancla, peso in anclas.items() if ancla in texto)
        if puntuacion > mejor_puntuacion:
            mejor_pagina = pagina.numero
            mejor_puntuacion = puntuacion
    return mejor_pagina, mejor_puntuacion


def _normalizar(texto: str) -> str:
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"[^a-zA-Z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip().casefold()
