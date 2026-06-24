from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PaginaOcrDetectada:
    numero_pagina: int
    puntuacion: int
    senales: list[str]
    ocr: dict[str, Any]


class DetectorPaginaTecnicaOcrRaloeCrono:
    def detectar(self, paginas_ocr: list[dict[str, Any]]) -> PaginaOcrDetectada:
        candidatas = [self._puntuar(pagina_ocr) for pagina_ocr in paginas_ocr]
        candidatas = [candidata for candidata in candidatas if candidata.puntuacion > 0]

        if not candidatas:
            raise ValueError("No se encontro la pagina tecnica por OCR.")

        return max(candidatas, key=lambda candidata: candidata.puntuacion)

    def _puntuar(self, pagina_ocr: dict[str, Any]) -> PaginaOcrDetectada:
        texto = _normalizar_texto(pagina_ocr.get("ocr", {}).get("text", ""))
        puntuacion = 0
        senales_encontradas: list[str] = []

        for senal, variantes, peso in _SENALES_TECNICAS:
            if any(variante in texto for variante in variantes):
                puntuacion += peso
                senales_encontradas.append(senal)

        return PaginaOcrDetectada(
            numero_pagina=_numero_pagina(pagina_ocr),
            puntuacion=puntuacion,
            senales=senales_encontradas,
            ocr=pagina_ocr,
        )


_SENALES_TECNICAS = [
    ("detalle_material", ("detalle de material",), 5),
    ("maniobra_carlos_silva", ("maniobra carlos silva",), 4),
    ("serie", ("serie:",), 3),
    ("normas", ("normas:",), 3),
    ("caracteristicas", ("caracteristicas:",), 4),
    ("traccion_electrica", ("traccion electrica:",), 5),
    ("puertas_cabina", ("puertas de cabina embarque",), 4),
    ("tension_linea_motor", ("tension linea / motor:", "tension linea motor:"), 3),
    ("modelo_motor", ("modelo motor:",), 2),
    ("fabricante_motor", ("fabricante:",), 1),
]


def _normalizar_texto(texto: str) -> str:
    texto = _reparar_mojibake(texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return " ".join(texto.lower().split())


def _reparar_mojibake(texto: str) -> str:
    if "Ã" not in texto and "Â" not in texto:
        return texto
    try:
        return texto.encode("latin1").decode("utf-8")
    except UnicodeError:
        return texto


def _numero_pagina(pagina_ocr: dict[str, Any]) -> int:
    numero = pagina_ocr.get("page_number", pagina_ocr.get("numero_pagina", 0))
    return int(numero)
