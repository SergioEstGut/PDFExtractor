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
    directorio_contrato: Path | None = None,
    detectar_conocidos_fuera_de_seccion: bool = True,
    claves_ignoradas: set[str] | None = None,
    ignorar_lineas_desde_y: float | None = None,
    ignorar_lineas_antes_de_texto: dict[int, str] | None = None,
) -> dict[str, Any]:
    claves_conocidas = _claves_conocidas(datos_conocidos)
    claves_conocidas.update(
        _claves_aliases_contrato(str(directorio_contrato) if directorio_contrato else None)
    )
    claves_ignoradas_normalizadas = {
        _clave_normalizada(clave)
        for clave in (claves_ignoradas or set())
    }
    campos_extra: dict[str, Any] = {}
    secciones_por_pagina = secciones_por_pagina or {}
    ignorar_lineas_antes_de_texto = ignorar_lineas_antes_de_texto or {}

    for pagina in paginas:
        secciones_pagina = secciones_por_pagina.get(pagina.numero, [])
        lineas_rojas = _lineas_rojas_normalizadas(pagina)
        texto_inicio = ignorar_lineas_antes_de_texto.get(pagina.numero)
        if texto_inicio is None and "general" in secciones_pagina:
            texto_inicio = "DETALLE DE MATERIAL"
        for linea in _lineas_candidatas(pagina, ignorar_lineas_desde_y, texto_inicio):
            if _normalizar_linea(linea) in lineas_rojas:
                continue
            candidato = _leer_par_clave_valor_en_linea(linea)
            if candidato is None:
                continue

            clave_original, valor = candidato
            clave_segura = a_clave_segura(clave_original)
            if _clave_normalizada(clave_segura) in claves_ignoradas_normalizadas:
                continue
            if _clave_normalizada(clave_segura) in claves_conocidas:
                continue
            if _es_valor_relleno(valor):
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

        if detectar_conocidos_fuera_de_seccion:
            _detectar_campos_conocidos_fuera_de_seccion(
                pagina,
                secciones_pagina,
                campos_extra,
                directorio_contrato,
                y_min=_y_bloque_con_texto(pagina, texto_inicio),
            )

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

    indice_dos_puntos = texto.index(":")
    if (
        indice_dos_puntos > 0
        and indice_dos_puntos + 1 < len(texto)
        and texto[indice_dos_puntos - 1].isdigit()
        and texto[indice_dos_puntos + 1].isdigit()
    ):
        return None

    clave_original, valor = (parte.strip() for parte in texto.split(":", maxsplit=1))
    clave_original = re.sub(r"^\(?\d+\)?\s+", "", clave_original).strip()
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


def _es_valor_relleno(valor: str) -> bool:
    texto = valor.strip()
    if not texto:
        return True
    texto = texto.replace("Â", "")
    texto = re.sub(r"[.\u2026·_\-\sЕE]+", "", texto)
    texto = re.sub(r"\b(mm|cm|m|v|kw|cv)\b", "", texto, flags=re.IGNORECASE)
    return not texto.strip()


def _lineas_candidatas(
    pagina: PaginaPdf,
    ignorar_lineas_desde_y: float | None,
    ignorar_lineas_antes_de_texto: str | None = None,
) -> list[str]:
    y_inicio = _y_bloque_con_texto(pagina, ignorar_lineas_antes_de_texto)

    if ignorar_lineas_desde_y is None and y_inicio is None:
        return pagina.texto.splitlines()

    lineas: list[str] = []
    for bloque in pagina.bloques:
        if y_inicio is not None and bloque.y0 < y_inicio:
            continue
        if ignorar_lineas_desde_y is not None and bloque.y0 >= ignorar_lineas_desde_y:
            continue
        lineas.extend(bloque.texto.splitlines())
    return lineas


def _y_bloque_con_texto(pagina: PaginaPdf, texto: str | None) -> float | None:
    if not texto:
        return None
    objetivo = _normalizar_linea(texto)
    candidatos = [
        bloque.y0
        for bloque in pagina.bloques
        if objetivo in _normalizar_linea(bloque.texto)
    ]
    return min(candidatos) if candidatos else None


def _lineas_rojas_normalizadas(pagina: PaginaPdf) -> set[str]:
    lineas: list[list[Any]] = []
    palabras_rojas = [palabra for palabra in pagina.palabras if _es_rojo(palabra.color)]
    for palabra in sorted(palabras_rojas, key=lambda item: (item.y0, item.x0)):
        if not lineas or abs(lineas[-1][0].y0 - palabra.y0) > 4:
            lineas.append([palabra])
        else:
            lineas[-1].append(palabra)
    return {
        _normalizar_linea(" ".join(palabra.texto for palabra in linea))
        for linea in lineas
    }


def _es_rojo(color: int | None) -> bool:
    if color is None:
        return False
    rojo = (color >> 16) & 255
    verde = (color >> 8) & 255
    azul = color & 255
    return rojo >= 150 and rojo > verde + 50 and rojo > azul + 50


def _normalizar_linea(linea: str) -> str:
    texto = _quitar_acentos(_reparar_mojibake(linea))
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip().casefold()


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
    directorio_contrato: Path | None,
    y_min: float | None = None,
) -> None:
    if not secciones_pagina:
        return

    filas = _filas(pagina, y_min=y_min)
    for seccion_esperada, nombre_campo, especificacion in _campos_contractuales_con_aliases(
        str(directorio_contrato) if directorio_contrato else None
    ):
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


def _filas(pagina: PaginaPdf, y_min: float | None = None) -> list[list[Any]]:
    filas: list[list[Any]] = []
    palabras = [
        palabra
        for palabra in pagina.palabras
        if palabra.texto != MARCA_CHECK and (y_min is None or palabra.y0 >= y_min)
    ]
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


@lru_cache(maxsize=None)
def _campos_contractuales_con_aliases(
    directorio_contrato: str | None = None,
) -> tuple[tuple[str, str, dict[str, Any]], ...]:
    return tuple(
        (seccion, nombre, especificacion)
        for seccion, campos in _secciones_contrato(directorio_contrato)
        for nombre, especificacion in campos.items()
        if especificacion.get("aliases")
    )


@lru_cache(maxsize=None)
def _secciones_contrato(
    directorio_contrato: str | None = None,
) -> tuple[tuple[str, dict[str, Any]], ...]:
    if directorio_contrato is None:
        return tuple(
            (seccion, especificaciones_seccion(seccion))
            for seccion in _secciones_contrato_raloe()
        )

    secciones: list[tuple[str, dict[str, Any]]] = []
    for ruta in Path(directorio_contrato).glob("*.json"):
        contenido = json.loads(ruta.read_text(encoding="utf-8-sig"))
        campos = {
            campo["nombre"]: campo
            for campo in contenido.get("campos", [])
            if isinstance(campo, dict) and campo.get("nombre")
        }
        secciones.append((contenido["seccion"], campos))
    return tuple(secciones)


@lru_cache(maxsize=None)
def _claves_aliases_contrato(directorio_contrato: str | None) -> set[str]:
    claves: set[str] = set()
    for _seccion, campos in _secciones_contrato(directorio_contrato):
        for especificacion in campos.values():
            for alias in especificacion.get("aliases", []):
                claves.add(_clave_normalizada(alias))
            reglas_pdf = especificacion.get("reglas", {}).get("extraccion_pdf", {})
            for alias in reglas_pdf.get("aliases", []):
                claves.add(_clave_normalizada(alias))
    return claves


@lru_cache(maxsize=1)
def _secciones_contrato_raloe() -> tuple[str, ...]:
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
