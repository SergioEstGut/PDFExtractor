import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from extractor_pdf.domain.entidades import PaginaPdf
from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import (
    especificaciones_seccion,
)


SECCION_CAMPOS_EXTRA = "Campos_extra"
MARCA_CHECK = "\x14"


def detectar_campos_extra(
    paginas: list[PaginaPdf],
    datos_conocidos: dict[str, Any],
    secciones_por_pagina: dict[int, list[str]] | None = None,
) -> dict[str, Any]:
    claves_conocidas = _claves_conocidas(datos_conocidos)
    campos_extra: dict[str, Any] = {}
    secciones_por_pagina = secciones_por_pagina or {}

    for pagina in paginas:
        secciones_pagina = secciones_por_pagina.get(pagina.numero, [])
        for linea in pagina.texto.splitlines():
            candidato = _leer_par_clave_valor_en_linea(linea)
            if candidato is None:
                continue

            clave_original, valor = candidato
            clave_segura = a_clave_segura(clave_original)
            if _clave_normalizada(clave_segura) in claves_conocidas:
                continue

            campos_extra.setdefault(
                clave_segura,
                {
                    "nombre_campo": clave_segura,
                    "valor": valor,
                    "pagina": pagina.numero,
                    "seccion": secciones_pagina[0] if secciones_pagina else "",
                },
            )

        _detectar_campos_conocidos_fuera_de_seccion(pagina, secciones_pagina, campos_extra)

    return campos_extra


def a_clave_segura(clave_original: str) -> str:
    texto = _quitar_acentos(clave_original).replace("º", "o").replace("ª", "a")
    texto = re.sub(r"[^A-Za-z0-9_]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")

    if not texto:
        return "Campo_extra"
    if texto[0].isdigit():
        return f"Campo_{texto}"
    return texto


def _leer_par_clave_valor_en_linea(linea: str) -> tuple[str, str] | None:
    texto = linea.strip()
    if texto.count(":") != 1:
        return None

    clave_original, valor = (parte.strip() for parte in texto.split(":", maxsplit=1))
    if not clave_original or not valor:
        return None
    if clave_original.isdigit():
        return None
    if clave_original.upper() == "PEDIDO CON OBSERVACIONES":
        return None
    if len(clave_original) > 80:
        return None
    if valor.endswith(":"):
        return None

    return clave_original, valor


def _claves_conocidas(datos: dict[str, Any]) -> set[str]:
    claves: set[str] = {_clave_normalizada(SECCION_CAMPOS_EXTRA)}

    def visitar(valor: Any) -> None:
        if not isinstance(valor, dict):
            return

        for clave, hijo in valor.items():
            claves.add(_clave_normalizada(clave))
            visitar(hijo)

    visitar(datos)
    return claves


def _clave_normalizada(clave: str) -> str:
    return a_clave_segura(clave).casefold()


def _quitar_acentos(texto: str) -> str:
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )


def _detectar_campos_conocidos_fuera_de_seccion(
    pagina: PaginaPdf,
    secciones_pagina: list[str],
    campos_extra: dict[str, Any],
) -> None:
    if not secciones_pagina:
        return

    filas = _filas(pagina)
    for seccion_esperada, nombre_campo, especificacion in _campos_contractuales_con_aliases():
        if seccion_esperada in secciones_pagina:
            continue

        coincidencia = _buscar_alias(filas, especificacion.get("aliases", []))
        if coincidencia is None:
            continue

        fila, indice, alias = coincidencia
        valor = _leer_valor_extra(pagina, fila, indice, alias, especificacion)
        if not valor:
            continue

        seccion_detectada = secciones_pagina[-1]
        clave_extra = f"{seccion_detectada}.{nombre_campo}"
        campos_extra.setdefault(
            clave_extra,
            {
                "nombre_campo": nombre_campo,
                "valor": valor,
                "pagina": pagina.numero,
                "seccion": seccion_detectada,
            },
        )


def _leer_valor_extra(
    pagina: PaginaPdf,
    fila: list[Any],
    indice_alias: int,
    alias: str,
    especificacion: dict[str, Any],
) -> str:
    tipo = especificacion.get("tipo", "")
    if tipo == "check_simple":
        return "Si" if _hay_check_antes_de_alias(pagina, fila[indice_alias]) else ""
    if tipo in {"check_con_valor", "int", "double", "texto"} and _alias_es_especifico(alias):
        return _texto_derecha(fila, indice_alias)
    return ""


def _alias_es_especifico(alias: str) -> bool:
    tokens = _tokens(alias)
    return len(tokens) >= 2 and len(_normalizar_alias(alias)) >= 10


def _hay_check_antes_de_alias(pagina: PaginaPdf, palabra_alias: Any) -> bool:
    return any(
        marca.x1 <= palabra_alias.x0
        and palabra_alias.x0 - marca.x1 <= 45
        and abs(marca.y0 - palabra_alias.y0) <= 8
        for marca in pagina.marcas_check
    )


def _texto_derecha(fila: list[Any], indice_alias: int) -> str:
    x_fin = fila[indice_alias].x1
    valores = [
        palabra.texto
        for palabra in fila
        if palabra.x0 > x_fin and palabra.texto not in {MARCA_CHECK, "V", "m", "mm"}
    ]
    return " ".join(valores).strip()


def _filas(pagina: PaginaPdf) -> list[list[Any]]:
    filas: list[list[Any]] = []
    palabras = [palabra for palabra in pagina.palabras if palabra.texto != MARCA_CHECK]
    for palabra in sorted(palabras, key=lambda item: (item.y0, item.x0)):
        if not filas or abs(filas[-1][0].y0 - palabra.y0) > 4:
            filas.append([palabra])
        else:
            filas[-1].append(palabra)
    return filas


def _buscar_alias(filas: list[list[Any]], aliases: list[str]) -> tuple[list[Any], int, str] | None:
    for fila in filas:
        for alias in aliases:
            indice = _indice_alias(fila, alias)
            if indice is not None:
                return fila, indice, alias
    return None


def _indice_alias(fila: list[Any], alias: str) -> int | None:
    textos = [_normalizar_alias(palabra.texto) for palabra in fila]
    objetivo = [_normalizar_alias(token) for token in _tokens(alias)]
    if not objetivo:
        return None
    for indice in range(0, len(textos) - len(objetivo) + 1):
        if textos[indice : indice + len(objetivo)] == objetivo:
            return indice
    return None


def _tokens(texto: str) -> list[str]:
    return [token for token in re.split(r"\s+", texto.strip()) if token]


def _normalizar_alias(texto: str) -> str:
    texto = _reparar_mojibake(texto).rstrip(":")
    texto = _quitar_acentos(texto)
    texto = re.sub(r"[^A-Za-z0-9]+", "", texto)
    return texto.casefold()


def _reparar_mojibake(texto: str) -> str:
    try:
        return texto.encode("latin1").decode("utf-8")
    except UnicodeError:
        return texto


@lru_cache(maxsize=1)
def _campos_contractuales_con_aliases() -> tuple[tuple[str, str, dict[str, Any]], ...]:
    return tuple(
        (seccion, nombre, especificacion)
        for seccion in _secciones_contrato()
        for nombre, especificacion in especificaciones_seccion(seccion).items()
        if especificacion.get("aliases")
    )


@lru_cache(maxsize=1)
def _secciones_contrato() -> tuple[str, ...]:
    secciones: list[str] = []
    for ruta in _directorio_secciones_contrato().glob("*.json"):
        contenido = json.loads(ruta.read_text(encoding="utf-8-sig"))
        secciones.append(contenido["seccion"])
    return tuple(secciones)


def _directorio_secciones_contrato() -> Path:
    for base in Path(__file__).resolve().parents:
        candidato = base / "docs" / "contrato_raloe_crono" / "secciones"
        if candidato.is_dir():
            return candidato
    raise FileNotFoundError("No se encontro docs/contrato_raloe_crono/secciones")
