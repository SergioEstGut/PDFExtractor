from __future__ import annotations

import re
import unicodedata

from extractor_pdf.domain.entidades import PaginaPdf


ANCLAS_POR_ROL = {
    "principal": {
        "formulario maniobras aszende electricas": 4,
        "formulari crono": 3,
        "normas": 2,
        "datos generales": 2,
        "datos motor": 2,
        "datos cabina": 2,
        "medidas premontada": 2,
    },
}

PUNTUACION_MINIMA = {
    "principal": 7,
}


def detectar_plantilla_aszende_crono(paginas: list[PaginaPdf]) -> str:
    texto = _normalizar("\n".join(pagina.texto for pagina in paginas))
    if _parece_aszende_electrico(texto):
        return "aszende_crono_electrico"
    return "aszende_crono_desconocido"


def detectar_paginas_aszende_crono(paginas: list[PaginaPdf]) -> dict[str, int]:
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


def _parece_aszende_electrico(texto: str) -> bool:
    if "aszende" not in texto and "asc electricos" not in texto:
        return False
    return (
        "formulario maniobras aszende electricas" in texto
        or "formulari crono" in texto
        or "datos motor" in texto
        or "datos cabina" in texto
    )
