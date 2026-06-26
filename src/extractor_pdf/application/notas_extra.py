from typing import Any

from extractor_pdf.domain.entidades import PaginaPdf, PalabraTexto


SECCION_NOTAS_EXTRA = "Notas_extra"
COLOR_NEGRO = 0
MARCA_CHECK = "\x14"


def detectar_notas_extra(
    paginas: list[PaginaPdf],
    secciones_por_pagina: dict[int, list[str]] | None = None,
    ignorar_tonos_azules: bool = False,
    ignorar_tonos_grises_claros: bool = False,
    detectar_marcas_visuales: bool = False,
) -> list[dict[str, Any]]:
    secciones_por_pagina = secciones_por_pagina or {}
    notas: list[dict[str, Any]] = []

    for pagina in paginas:
        if detectar_marcas_visuales:
            for marca in pagina.marcas_visuales:
                valor = _descripcion_marca_visual(marca.tipo, pagina.numero)
                if not valor:
                    continue
                notas.append(
                    {
                        "valor": valor,
                        "pagina": pagina.numero,
                        "seccion": _inferir_seccion(pagina.numero, [marca], secciones_por_pagina),
                    }
                )

        palabras_color = [
            palabra
            for palabra in pagina.palabras
            if not _es_texto_normal(
                palabra.color,
                ignorar_tonos_azules,
                ignorar_tonos_grises_claros,
            )
            and palabra.texto != MARCA_CHECK
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
    linea: list[Any],
    secciones_por_pagina: dict[int, list[str]],
) -> str:
    secciones = secciones_por_pagina.get(numero_pagina, [])
    if not secciones:
        return ""
    if len(secciones) == 1:
        return secciones[0]

    y = min(palabra.y0 for palabra in linea)
    x = min(palabra.x0 for palabra in linea)

    if {"Datos_Generales", "Botoneras_Exteriores", "Datos_Premontada"}.issubset(set(secciones)):
        return _inferir_seccion_crono_principal(x, y)

    if "Opciones" in secciones:
        return "Opciones"

    if {"Premontada", "Armario", "Botonera_Exterior", "Botonera_Cabina"}.issubset(set(secciones)):
        if y < 370:
            return "Premontada"
        if x < 270:
            return "Premontada" if y < 600 else "Botonera_Exterior"
        return "Armario" if y < 520 else "Botonera_Cabina"

    return secciones[-1]


def _inferir_seccion_crono_principal(x: float, y: float) -> str:
    if x < 199:
        if y < 220:
            return "Normas"
        if y < 390:
            return "Datos_Generales"
        if y < 520:
            return "Datos_Motor"
        if y < 620:
            return "Opciones_Maniobra"
        return "Rescates"

    if x < 385:
        if y < 297:
            return "Datos_Cabina"
        if y < 438:
            return "Caja_Inspeccion"
        if y < 503:
            return "Pesacargas"
        if y < 621:
            return "Botonera_Cabina"
        return "Botoneras_Exteriores"

    if y < 282:
        return "Medidas_Premontada"
    if y < 390:
        return "Medidas_Entreplantas"
    if y < 612:
        return "Datos_Premontada"
    if y < 656:
        return "Opciones_Especiales"
    return "Parametros_Variador"


def _descripcion_marca_visual(tipo: str, numero_pagina: int) -> str:
    if tipo in {"fondo_coloreado", "fondo_amarillo"}:
        return f"Fondo coloreado en pagina {numero_pagina}"
    if tipo in {"linea_coloreada", "linea_roja"}:
        return f"Linea coloreada en pagina {numero_pagina}"
    return ""


def _es_texto_normal(
    color: int | None,
    ignorar_tonos_azules: bool,
    ignorar_tonos_grises_claros: bool,
) -> bool:
    if color is None:
        return True
    if color == COLOR_NEGRO:
        return True

    rojo = (color >> 16) & 255
    verde = (color >> 8) & 255
    azul = color & 255

    canal_max = max(rojo, verde, azul)
    canal_min = min(rojo, verde, azul)
    if canal_max <= 90 and canal_max - canal_min <= 20:
        return True

    if ignorar_tonos_grises_claros and canal_max - canal_min <= 20:
        return True

    if ignorar_tonos_azules and azul >= 120 and azul > rojo + 35 and azul > verde + 15:
        return True

    return False
