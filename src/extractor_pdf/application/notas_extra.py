from typing import Any

from extractor_pdf.domain.entidades import PaginaPdf, PalabraTexto


SECCION_NOTAS_EXTRA = "Notas_extra"
COLOR_NEGRO = 0
MARCA_CHECK = "\x14"


def detectar_notas_extra(
    paginas: list[PaginaPdf],
    secciones_por_pagina: dict[int, list[str]] | None = None,
) -> list[dict[str, Any]]:
    secciones_por_pagina = secciones_por_pagina or {}
    notas: list[dict[str, Any]] = []

    for pagina in paginas:
        palabras_color = [
            palabra
            for palabra in pagina.palabras
            if not _es_texto_negro_o_gris(palabra.color) and palabra.texto != MARCA_CHECK
        ]
        for linea in _agrupar_por_linea(palabras_color):
            valor = " ".join(palabra.texto for palabra in linea).strip()
            if not valor:
                continue
            notas.append(
                {
                    "valor": valor,
                    "pagina": pagina.numero,
                    "seccion": _inferir_seccion(pagina.numero, linea, secciones_por_pagina),
                }
            )

    return notas


def _agrupar_por_linea(palabras: list[PalabraTexto]) -> list[list[PalabraTexto]]:
    lineas: list[list[PalabraTexto]] = []
    for palabra in sorted(palabras, key=lambda item: (item.y0, item.x0)):
        if not lineas or abs(lineas[-1][0].y0 - palabra.y0) > 4:
            lineas.append([palabra])
        else:
            lineas[-1].append(palabra)
    return lineas


def _inferir_seccion(
    numero_pagina: int,
    linea: list[PalabraTexto],
    secciones_por_pagina: dict[int, list[str]],
) -> str:
    secciones = secciones_por_pagina.get(numero_pagina, [])
    if not secciones:
        return ""
    if len(secciones) == 1:
        return secciones[0]

    y = min(palabra.y0 for palabra in linea)
    x = min(palabra.x0 for palabra in linea)

    if "Opciones" in secciones:
        return "Opciones"

    if {"Premontada", "Armario", "Botonera_Exterior", "Botonera_Cabina"}.issubset(set(secciones)):
        if y < 370:
            return "Premontada"
        if x < 270:
            return "Premontada" if y < 600 else "Botonera_Exterior"
        return "Armario" if y < 520 else "Botonera_Cabina"

    return secciones[-1]


def _es_texto_negro_o_gris(color: int | None) -> bool:
    if color is None:
        return True
    if color == COLOR_NEGRO:
        return True

    rojo = (color >> 16) & 255
    verde = (color >> 8) & 255
    azul = color & 255

    canal_max = max(rojo, verde, azul)
    canal_min = min(rojo, verde, azul)
    return canal_max <= 90 and canal_max - canal_min <= 20
