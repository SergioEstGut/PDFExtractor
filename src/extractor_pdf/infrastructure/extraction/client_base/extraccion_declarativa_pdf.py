from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from extractor_pdf.domain.entidades import PaginaPdf, PalabraTexto
from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import (
    configuracion_extraccion_pdf_seccion,
    especificaciones_seccion,
    normalizar_valor_campo,
)

MARCA_CHECK = "\x14"


@dataclass(frozen=True)
class CoincidenciaAlias:
    fila: list[PalabraTexto]
    indice: int
    fin_x: float
    alias: str


def extraer_por_reglas_pdf(
    pagina: PaginaPdf,
    seccion: str,
    especificaciones_param: dict[str, dict[str, Any]] | None = None,
    configuracion_pdf_param: dict[str, Any] | None = None,
    normalizador: Callable[[str, str, str], str] | None = None,
) -> dict[str, str]:
    resultado: dict[str, str] = {}
    especificaciones = especificaciones_param or especificaciones_seccion(seccion)
    configuracion_pdf = (
        configuracion_pdf_param
        if configuracion_pdf_param is not None
        else configuracion_extraccion_pdf_seccion(seccion)
    )
    normalizar = normalizador or normalizar_valor_campo
    filas = _filas(pagina)
    subsecciones = _resolver_subsecciones(
        filas, configuracion_pdf.get("subsecciones", {})
    )

    for campo, especificacion in especificaciones.items():
        reglas = especificacion.get("reglas", {}).get("extraccion_pdf")
        if not reglas:
            continue
        reglas_lista = reglas if isinstance(reglas, list) else [reglas]
        for regla in reglas_lista:
            filas_regla = subsecciones.get(regla.get("subseccion_pdf"), filas)
            valor = _aplicar_regla(pagina, filas_regla, especificacion, regla)
            if valor in set(regla.get("ignorar_valores", [])):
                valor = ""
            if valor == "":
                continue
            resultado[campo] = normalizar(seccion, campo, valor)
            break

    _aplicar_dependencias(resultado, especificaciones)
    return resultado


def _aplicar_dependencias(
    resultado: dict[str, str],
    especificaciones: dict[str, dict[str, Any]],
) -> None:
    for campo, especificacion in especificaciones.items():
        dependencia = especificacion.get("reglas", {}).get("depende_de")
        if not isinstance(dependencia, dict):
            continue
        campo_dependencia = dependencia.get("campo")
        if not campo_dependencia:
            continue
        valor_dependencia = str(resultado.get(campo_dependencia, ""))
        valores = dependencia.get("si_valores")
        if valores is None:
            valores = [dependencia.get("si_valor")]
        if valor_dependencia in {str(valor) for valor in valores}:
            resultado[campo] = str(dependencia.get("valor", ""))


def _resolver_subsecciones(
    filas: list[list[PalabraTexto]],
    definiciones: dict[str, dict[str, Any]],
) -> dict[str, list[list[PalabraTexto]]]:
    return {
        nombre: _filas_en_subseccion(filas, definicion)
        for nombre, definicion in definiciones.items()
    }


def _filas_en_subseccion(
    filas: list[list[PalabraTexto]],
    definicion: dict[str, Any],
) -> list[list[PalabraTexto]]:
    indice_inicio = _indice_fila_con_alias(filas, definicion.get("inicio", []), 0)
    if indice_inicio is None:
        return []

    indice_fin = _indice_fila_con_alias(filas, definicion.get("fin", []), indice_inicio + 1)
    if indice_fin is None:
        filas_subseccion = filas[indice_inicio:]
    else:
        filas_subseccion = filas[indice_inicio:indice_fin]

    x_min = definicion.get("x_min")
    x_max = definicion.get("x_max")
    y_min = definicion.get("y_min")
    y_max = definicion.get("y_max")
    if x_min is None and x_max is None and y_min is None and y_max is None:
        return filas_subseccion

    filtradas: list[list[PalabraTexto]] = []
    for fila in filas_subseccion:
        palabras = [
            palabra
            for palabra in fila
            if (x_min is None or palabra.x0 >= float(x_min))
            and (x_max is None or palabra.x0 <= float(x_max))
            and (y_min is None or palabra.y0 >= float(y_min))
            and (y_max is None or palabra.y0 <= float(y_max))
        ]
        if palabras:
            filtradas.append(palabras)
    return filtradas


def _indice_fila_con_alias(
    filas: list[list[PalabraTexto]],
    aliases: str | list[str],
    desde: int,
) -> int | None:
    if isinstance(aliases, str):
        aliases = [aliases]
    for indice in range(desde, len(filas)):
        if any(_indice_alias(filas[indice], alias) is not None for alias in aliases):
            return indice
    return None


def _aplicar_regla(
    pagina: PaginaPdf,
    filas: list[list[PalabraTexto]],
    especificacion: dict[str, Any],
    regla: dict[str, Any],
) -> str:
    modo = regla.get("modo", "")
    if modo == "check_x_en_zona":
        return _leer_check_x_en_zona(pagina, regla)
    if modo == "texto_en_zona":
        return _texto_en_zona(pagina, regla)
    if modo == "numero_en_zona":
        return _numero_en_texto(
            _texto_en_zona(pagina, regla),
            entero=regla.get("entero", False),
            indice=int(regla.get("indice_numero", 0)),
        )

    coincidencia = _buscar_alias(filas, especificacion, regla)
    if coincidencia is None:
        return ""

    if modo == "check_antes_de_alias":
        return _leer_check_antes_de_alias(pagina, coincidencia, regla)
    if modo == "check_x_derecha_alias":
        return _leer_check_x_derecha(coincidencia, regla)
    if modo == "check_x_derecha_cercana_alias":
        return _leer_check_x_derecha_cercana(pagina, coincidencia, regla)
    if modo == "texto_derecha_alias":
        return _texto_derecha(coincidencia, regla)
    if modo == "texto_derecha_token_despues_alias":
        return _texto_derecha_token_despues_alias(coincidencia, regla)
    if modo == "texto_derecha_cercana_alias":
        return _texto_derecha_cercana(pagina, coincidencia, regla)
    if modo == "texto_debajo_alias":
        return _texto_debajo(coincidencia, filas, regla)
    if modo == "numero_debajo_alias":
        return _numero_en_texto(
            _texto_debajo(coincidencia, filas, regla),
            entero=regla.get("entero", False),
            indice=int(regla.get("indice_numero", 0)),
        )
    if modo == "texto_debajo_hasta_unidad":
        return _texto_sin_tokens_con_unidad(_texto_debajo(coincidencia, filas, regla), regla)
    if modo == "numero_debajo_con_unidad":
        return _numero_con_unidad(_texto_debajo(coincidencia, filas, regla), regla)
    if modo == "numero_derecha_alias":
        return _numero_en_texto(
            _texto_derecha(coincidencia, regla),
            entero=regla.get("entero", False),
            indice=int(regla.get("indice_numero", 0)),
        )
    if modo == "numero_derecha_cercana_alias":
        return _numero_en_texto(
            _texto_derecha_cercana(pagina, coincidencia, regla),
            entero=regla.get("entero", False),
            indice=int(regla.get("indice_numero", 0)),
        )
    if modo == "valor_por_token_en_texto_derecha":
        return _valor_por_token_en_texto(_texto_derecha(coincidencia, regla), regla)
    if modo == "valor_por_token_en_texto_derecha_cercana":
        return _valor_por_token_en_texto(
            _texto_derecha_cercana(pagina, coincidencia, regla), regla
        )
    if modo == "texto_entre_aliases":
        return _texto_derecha(coincidencia, regla)
    return ""


def _buscar_alias(
    filas: list[list[PalabraTexto]],
    especificacion: dict[str, Any],
    regla: dict[str, Any],
) -> CoincidenciaAlias | None:
    aliases = regla.get("aliases") or especificacion.get("aliases", [])
    contexto = regla.get("despues_de")
    contexto_inicio_fila = regla.get("despues_de_inicio_fila")
    if regla.get("subseccion_pdf"):
        contexto = None
        contexto_inicio_fila = None
    contexto_visto = not contexto and not contexto_inicio_fila
    ocurrencia_objetivo = int(regla.get("ocurrencia_alias", 0))
    ocurrencia_actual = 0

    for fila in filas:
        if contexto_inicio_fila and _fila_empieza_por(fila, contexto_inicio_fila):
            contexto_visto = True
        elif contexto and _indice_alias(fila, contexto) is not None:
            contexto_visto = True

        if not contexto_visto:
            continue
        if regla.get("en_fila_con") and _indice_alias(fila, regla["en_fila_con"]) is None:
            continue

        for alias in aliases:
            for indice in _indices_alias(fila, alias):
                if ocurrencia_actual < ocurrencia_objetivo:
                    ocurrencia_actual += 1
                    continue
                return CoincidenciaAlias(
                    fila=fila,
                    indice=indice,
                    fin_x=fila[indice + len(_tokens(alias)) - 1].x1,
                    alias=alias,
                )
    return None


def _fila_empieza_por(fila: list[PalabraTexto], alias: str) -> bool:
    tokens = _tokens(alias)
    if len(fila) < len(tokens):
        return False
    return [_normalizar(palabra.texto) for palabra in fila[: len(tokens)]] == [
        _normalizar(token) for token in tokens
    ]


def _leer_check_antes_de_alias(
    pagina: PaginaPdf,
    coincidencia: CoincidenciaAlias,
    regla: dict[str, Any],
) -> str:
    palabra_alias = coincidencia.fila[coincidencia.indice]
    distancia_maxima = float(regla.get("distancia_maxima", 95))
    tolerancia_y = float(regla.get("tolerancia_y", 14))
    candidatos = [
        marca
        for marca in pagina.marcas_check
        if marca.x1 <= palabra_alias.x0
        and palabra_alias.x0 - marca.x1 <= distancia_maxima
        and abs(marca.y0 - palabra_alias.y0) <= tolerancia_y
    ] + [
        palabra
        for palabra in pagina.palabras
        if _es_marca_check_textual(palabra.texto)
        and palabra.x1 <= palabra_alias.x0
        and palabra_alias.x0 - palabra.x1 <= distancia_maxima
        and abs(palabra.y0 - palabra_alias.y0) <= tolerancia_y
    ]
    if candidatos:
        return regla.get("valor_marcado", "Si")
    if regla.get("si_no_hay_check") == "No":
        return regla.get("valor_no_marcado", "No")
    return ""


def _leer_check_x_derecha(coincidencia: CoincidenciaAlias, regla: dict[str, Any]) -> str:
    x_fin = coincidencia.fin_x
    x_stop = _x_stop(coincidencia.fila, regla.get("hasta_aliases", []), x_fin)
    distancia_maxima = regla.get("distancia_maxima_derecha", 60)
    limite_x_derecha = regla.get("limite_x_derecha")
    marcado = any(
        _es_marca_check_textual(palabra.texto)
        and palabra.x0 > x_fin
        and (x_stop is None or palabra.x0 < x_stop)
        and palabra.x0 - x_fin <= float(distancia_maxima)
        and (limite_x_derecha is None or palabra.x0 < float(limite_x_derecha))
        for palabra in coincidencia.fila
    )
    if marcado:
        return regla.get("valor_marcado", "Si")
    return regla.get("valor_no_marcado", "No")


def _leer_check_x_derecha_cercana(
    pagina: PaginaPdf,
    coincidencia: CoincidenciaAlias,
    regla: dict[str, Any],
) -> str:
    x_fin = coincidencia.fin_x
    x_stop = _x_stop(coincidencia.fila, regla.get("hasta_aliases", []), x_fin)
    distancia_maxima = regla.get("distancia_maxima_derecha", 60)
    limite_x_derecha = regla.get("limite_x_derecha")
    tolerancia_y = float(regla.get("tolerancia_y", 8))
    y_ref = coincidencia.fila[coincidencia.indice].y0
    marcado = any(
        _es_marca_check_textual(palabra.texto)
        and palabra.x0 > x_fin
        and abs(palabra.y0 - y_ref) <= tolerancia_y
        and (x_stop is None or palabra.x0 < x_stop)
        and palabra.x0 - x_fin <= float(distancia_maxima)
        and (limite_x_derecha is None or palabra.x0 < float(limite_x_derecha))
        for palabra in pagina.palabras
    )
    if marcado:
        return regla.get("valor_marcado", "Si")
    return regla.get("valor_no_marcado", "No")


def _leer_check_x_en_zona(pagina: PaginaPdf, regla: dict[str, Any]) -> str:
    marcado = any(_es_marca_check_textual(palabra.texto) for palabra in _palabras_en_zona(pagina, regla))
    if marcado:
        return regla.get("valor_marcado", "Si")
    return regla.get("valor_no_marcado", "No")


def _es_marca_check_textual(texto: str) -> bool:
    if texto.strip().upper() in {"X", "\u2713", "\u2714", "\u2611", "\u2612"}:
        return True
    return texto.strip().upper() in {"X", "✔", "✓", "☑", "☒"}


def _texto_en_zona(pagina: PaginaPdf, regla: dict[str, Any]) -> str:
    valores = [
        palabra.texto
        for palabra in sorted(_palabras_en_zona(pagina, regla), key=lambda item: (item.y0, item.x0))
        if not _es_ruido_valor(palabra.texto)
    ]
    return " ".join(valores).strip()


def _palabras_en_zona(pagina: PaginaPdf, regla: dict[str, Any]) -> list[PalabraTexto]:
    x_min = regla.get("x_min")
    x_max = regla.get("x_max")
    y_min = regla.get("y_min")
    y_max = regla.get("y_max")
    return [
        palabra
        for palabra in pagina.palabras
        if (x_min is None or palabra.x0 >= float(x_min))
        and (x_max is None or palabra.x1 <= float(x_max))
        and (y_min is None or palabra.y0 >= float(y_min))
        and (y_max is None or palabra.y1 <= float(y_max))
        and not _es_palabra_nota(palabra)
    ]


def _texto_derecha(coincidencia: CoincidenciaAlias, regla: dict[str, Any]) -> str:
    x_fin = coincidencia.fin_x
    x_stop = _x_stop(coincidencia.fila, regla.get("hasta_aliases", []), x_fin)
    distancia_maxima = regla.get("distancia_maxima_derecha")
    limite_x_derecha = regla.get("limite_x_derecha")
    valores = [
        palabra.texto
        for palabra in coincidencia.fila
        if palabra.x0 > x_fin
        and (x_stop is None or palabra.x0 < x_stop)
        and (distancia_maxima is None or palabra.x0 - x_fin <= float(distancia_maxima))
        and (limite_x_derecha is None or palabra.x0 < float(limite_x_derecha))
        and not _es_ruido_valor(palabra.texto)
    ]
    saltar = int(regla.get("saltar_tokens", 0))
    tomar = _tokens_a_tomar(regla)
    if saltar:
        valores = valores[saltar:]
    if tomar is not None:
        valores = valores[:tomar]
    separador = regla.get("separador_tokens", " ")
    return str(separador).join(valores).strip()


def _texto_derecha_token_despues_alias(coincidencia: CoincidenciaAlias, regla: dict[str, Any]) -> str:
    x_fin = coincidencia.fin_x
    token = str(regla.get("token", ""))
    if not token:
        return ""
    separador = next(
        (
            palabra
            for palabra in coincidencia.fila
            if palabra.x0 > x_fin and palabra.texto.strip() == token
        ),
        None,
    )
    if separador is None:
        return ""
    x_stop = _x_stop(coincidencia.fila, regla.get("hasta_aliases", []), separador.x1)
    distancia_maxima = regla.get("distancia_maxima_derecha")
    valores = [
        palabra.texto
        for palabra in coincidencia.fila
        if palabra.x0 > separador.x1
        and (x_stop is None or palabra.x0 < x_stop)
        and (distancia_maxima is None or palabra.x0 - separador.x1 <= float(distancia_maxima))
        and not _es_ruido_valor(palabra.texto)
    ]
    tomar = _tokens_a_tomar(regla)
    if tomar is not None:
        valores = valores[:tomar]
    separador_tokens = regla.get("separador_tokens", " ")
    return str(separador_tokens).join(valores).strip()


def _texto_derecha_cercana(
    pagina: PaginaPdf,
    coincidencia: CoincidenciaAlias,
    regla: dict[str, Any],
) -> str:
    x_fin = coincidencia.fin_x
    x_stop = _x_stop(coincidencia.fila, regla.get("hasta_aliases", []), x_fin)
    distancia_maxima = regla.get("distancia_maxima_derecha")
    limite_x_derecha = regla.get("limite_x_derecha")
    margen_solape_izquierda = float(regla.get("margen_solape_izquierda", 0))
    tolerancia_y = float(regla.get("tolerancia_y", 8))
    y_ref = coincidencia.fila[coincidencia.indice].y0
    valores = [
        palabra.texto
        for palabra in sorted(pagina.palabras, key=lambda item: (abs(item.y0 - y_ref), item.x0))
        if palabra.x0 > x_fin - margen_solape_izquierda
        and abs(palabra.y0 - y_ref) <= tolerancia_y
        and (x_stop is None or palabra.x0 < x_stop)
        and (distancia_maxima is None or palabra.x0 - x_fin <= float(distancia_maxima))
        and (limite_x_derecha is None or palabra.x0 < float(limite_x_derecha))
        and not _es_palabra_nota(palabra)
        and not _es_ruido_valor(palabra.texto)
    ]
    saltar = int(regla.get("saltar_tokens", 0))
    tomar = _tokens_a_tomar(regla)
    if saltar:
        valores = valores[saltar:]
    if tomar is not None:
        valores = valores[:tomar]
    separador = regla.get("separador_tokens", " ")
    return str(separador).join(valores).strip()


def _texto_debajo(
    coincidencia: CoincidenciaAlias,
    filas: list[list[PalabraTexto]],
    regla: dict[str, Any],
) -> str:
    try:
        indice_fila = next(
            indice for indice, fila in enumerate(filas) if fila is coincidencia.fila
        )
    except StopIteration:
        return ""

    filas_debajo = int(regla.get("filas_debajo", 1))
    limite_x_derecha = regla.get("limite_x_derecha")
    limite_x_izquierda = float(regla.get("x_min", coincidencia.fila[coincidencia.indice].x0))
    lineas: list[str] = []
    valores: list[str] = []
    for fila in filas[indice_fila + 1 : indice_fila + 1 + filas_debajo]:
        palabras_fila = [
            palabra.texto
            for palabra in fila
            if palabra.x0 >= limite_x_izquierda
            and (limite_x_derecha is None or palabra.x0 < float(limite_x_derecha))
            and not _es_ruido_valor(palabra.texto)
        ]
        if palabras_fila:
            lineas.append(" ".join(palabras_fila))
            valores.extend(palabras_fila)
    separador = regla.get("separador_tokens", " ")
    saltar = int(regla.get("saltar_tokens", 0))
    tomar = _tokens_a_tomar(regla)
    separador_filas = regla.get("separador_filas")
    if separador_filas is not None and not saltar and tomar is None:
        return str(separador_filas).join(lineas).strip()
    if saltar:
        valores = valores[saltar:]
    if tomar is not None:
        valores = valores[:tomar]
    return str(separador).join(valores).strip()


def _valor_por_token_en_texto(valor: str, regla: dict[str, Any]) -> str:
    tokens_buscados = regla.get("tokens") or [regla.get("token", "")]
    if isinstance(tokens_buscados, str):
        tokens_buscados = [tokens_buscados]
    if not isinstance(tokens_buscados, list):
        tokens_buscados = [tokens_buscados]
    tokens_normalizados = {_normalizar(token) for token in _tokens(valor)}
    buscados_normalizados = {
        _normalizar(str(token))
        for token in tokens_buscados
        if str(token).strip()
    }
    if buscados_normalizados & tokens_normalizados:
        return regla.get("valor_si_presente", "Si")
    tokens_grupo = regla.get("tokens_grupo")
    if tokens_grupo is not None:
        if isinstance(tokens_grupo, str):
            tokens_grupo = [tokens_grupo]
        grupo_normalizado = {
            _normalizar(str(token))
            for token in tokens_grupo
            if str(token).strip()
        }
        if not (grupo_normalizado & tokens_normalizados):
            return regla.get("valor_si_sin_tokens_grupo", "")
    return regla.get("valor_si_ausente", "No")


def _tokens_a_tomar(regla: dict[str, Any]) -> int | None:
    tokens = regla.get("tokens")
    if isinstance(tokens, int):
        return tokens
    if isinstance(tokens, str) and tokens.isdigit():
        return int(tokens)
    return None


def _texto_sin_tokens_con_unidad(valor: str, regla: dict[str, Any]) -> str:
    unidad = str(regla.get("unidad", "")).casefold()
    if not unidad:
        return valor
    tokens = [
        token
        for token in _tokens(valor)
        if not token.casefold().endswith(unidad)
    ]
    return " ".join(tokens).strip()


def _numero_con_unidad(valor: str, regla: dict[str, Any]) -> str:
    unidad = re.escape(str(regla.get("unidad", "")))
    if not unidad:
        return _numero_en_texto(valor, entero=regla.get("entero", False), indice=0)
    patron = rf"(\d+(?:[.,]\d+)?)\s*{unidad}\b"
    match = re.search(patron, valor, re.IGNORECASE)
    return match.group(1) if match else ""


def _x_stop(fila: list[PalabraTexto], aliases: list[str], x_min: float) -> float | None:
    candidatos: list[float] = []
    for alias in aliases:
        for indice in _indices_alias(fila, alias):
            if fila[indice].x0 <= x_min:
                continue
            candidatos.append(fila[indice].x0)
    return min(candidatos) if candidatos else None


def _numero_en_texto(valor: str, entero: bool, indice: int) -> str:
    patron = r"\d+" if entero else r"\d+(?:[.,]\d+)?"
    numeros = re.findall(patron, valor)
    return numeros[indice] if 0 <= indice < len(numeros) else ""


def _es_ruido_valor(texto: str) -> bool:
    if texto in {MARCA_CHECK, "V", "m", "mm"}:
        return True
    normalizado = texto.strip()
    if not normalizado:
        return True
    if normalizado == "-":
        return False
    caracteres_ruido = ".\u2026:_-\u00c2\u00b7\u00ab\u0164\u0e0b\u043b"
    if re.fullmatch(r"([A-Z])\1{3,}", normalizado):
        return True
    return bool(re.fullmatch(f"[{re.escape(caracteres_ruido)}]+", normalizado))


def _filas(pagina: PaginaPdf) -> list[list[PalabraTexto]]:
    filas: list[list[PalabraTexto]] = []
    palabras = [
        palabra
        for palabra in pagina.palabras
        if palabra.texto != MARCA_CHECK and not _es_palabra_nota(palabra)
    ]
    for palabra in sorted(palabras, key=lambda item: (item.y0, item.x0)):
        if not filas or abs(filas[-1][0].y0 - palabra.y0) > 6:
            filas.append([palabra])
        else:
            filas[-1].append(palabra)
    for fila in filas:
        fila.sort(key=lambda palabra: palabra.x0)
    return filas


def _indice_alias(fila: list[PalabraTexto], alias: str) -> int | None:
    indices = _indices_alias(fila, alias)
    return indices[0] if indices else None


def _indices_alias(fila: list[PalabraTexto], alias: str) -> list[int]:
    textos = [_normalizar(palabra.texto) for palabra in fila]
    objetivo = [_normalizar(token) for token in _tokens(alias)]
    if not objetivo:
        return []
    indices: list[int] = []
    for indice in range(0, len(textos) - len(objetivo) + 1):
        if textos[indice : indice + len(objetivo)] == objetivo:
            indices.append(indice)
    return indices


def _tokens(texto: str) -> list[str]:
    return [token for token in re.split(r"\s+", texto.strip()) if token]


def _normalizar(texto: str) -> str:
    texto = _reparar_mojibake(texto).rstrip(":")
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"[^a-zA-Z0-9]+", "", texto)
    return texto.casefold()


def _es_palabra_nota(palabra: PalabraTexto) -> bool:
    return _es_rojo(palabra.color)


def _es_rojo(color: int | None) -> bool:
    if color is None:
        return False
    rojo = (color >> 16) & 255
    verde = (color >> 8) & 255
    azul = color & 255
    return rojo >= 150 and rojo > verde + 50 and rojo > azul + 50

def _reparar_mojibake(texto: str) -> str:
    try:
        return texto.encode("latin1").decode("utf-8")
    except UnicodeError:
        return texto
