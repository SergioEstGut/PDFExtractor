from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


def aplicar_contrato_salida(secciones: dict[str, Any]) -> dict[str, Any]:
    especificaciones = _especificaciones_por_seccion()
    normalizadas = {
        seccion: _normalizar_seccion(seccion, valores, especificaciones)
        if isinstance(valores, dict)
        else valores
        for seccion, valores in secciones.items()
    }
    warnings = _warnings_checks_durante_normalizacion(secciones, normalizadas, especificaciones)
    if warnings:
        normalizadas["warning"] = [*normalizadas.get("warning", []), *warnings]
    return normalizadas


def normalizar_valor_campo(seccion: str, campo: str, valor: str) -> str:
    especificacion = especificacion_campo(seccion, campo)
    return _normalizar_valor(valor, especificacion)


def especificacion_campo(seccion: str, campo: str) -> dict[str, Any] | None:
    return _especificaciones_por_seccion().get(seccion, {}).get(campo)


def nombres_campos_seccion(seccion: str) -> list[str]:
    return list(_especificaciones_por_seccion().get(seccion, {}).keys())


def especificaciones_seccion(seccion: str) -> dict[str, dict[str, Any]]:
    return dict(_especificaciones_por_seccion().get(seccion, {}))


def configuracion_extraccion_pdf_seccion(seccion: str) -> dict[str, Any]:
    return dict(_contratos_por_seccion().get(seccion, {}).get("extraccion_pdf", {}))


def check_asociado_a_txt(seccion: str, campo: str) -> str:
    especificacion = especificacion_campo(seccion, campo)
    if especificacion is None:
        return ""
    return especificacion.get("reglas", {}).get("infiere_check_marcado", "")


def normalizar_checks_con_texto_asociado(secciones: dict[str, Any]) -> dict[str, Any]:
    especificaciones = _especificaciones_por_seccion()
    normalizadas: dict[str, Any] = {}
    for seccion, valores in secciones.items():
        if not isinstance(valores, dict):
            normalizadas[seccion] = valores
            continue
        normalizadas[seccion] = _normalizar_checks_con_texto_en_seccion(
            seccion, valores, especificaciones.get(seccion, {})
        )
    return normalizadas


def warnings_checks_con_texto_asociado(secciones: dict[str, Any]) -> list[dict[str, str]]:
    especificaciones = _especificaciones_por_seccion()
    warnings: list[dict[str, str]] = []
    for seccion, valores in secciones.items():
        if not isinstance(valores, dict):
            continue
        campos = especificaciones.get(seccion, {})
        for campo_txt, especificacion_txt in campos.items():
            check_asociado = especificacion_txt.get("reglas", {}).get("infiere_check_marcado")
            if not check_asociado:
                continue
            if campo_txt not in valores and check_asociado not in valores:
                continue

            valor_txt = str(valores.get(campo_txt, "") or "").strip()
            valor_check = str(valores.get(check_asociado, "") or "").strip()
            ruta_check = f"{seccion}.{check_asociado}"
            ruta_txt = f"{seccion}.{campo_txt}"

            if valor_txt and valor_check == "No":
                warnings.append(
                    _warning_check_txt(
                        "check_no_marcado_con_valor_asociado",
                        seccion,
                        check_asociado,
                        campo_txt,
                        valor_check,
                        valor_txt,
                    )
                )
            elif not valor_txt and valor_check == "Si":
                warnings.append(
                    _warning_check_txt(
                        "check_marcado_sin_valor_asociado",
                        seccion,
                        check_asociado,
                        campo_txt,
                        valor_check,
                        "",
                    )
                )
    return warnings


def _warnings_checks_durante_normalizacion(
    originales: dict[str, Any],
    normalizadas: dict[str, Any],
    especificaciones: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for seccion, valores_originales in originales.items():
        if not isinstance(valores_originales, dict):
            continue
        valores_normalizados = normalizadas.get(seccion, {})
        if not isinstance(valores_normalizados, dict):
            continue
        campos = especificaciones.get(seccion, {})
        for campo_txt, especificacion_txt in campos.items():
            check_asociado = especificacion_txt.get("reglas", {}).get("infiere_check_marcado")
            if not check_asociado:
                continue

            valor_txt = str(valores_normalizados.get(campo_txt, "") or "").strip()
            valor_check_original = str(valores_originales.get(check_asociado, "") or "").strip()
            valor_check_final = str(valores_normalizados.get(check_asociado, "") or "").strip()

            if valor_txt and valor_check_original == "No" and valor_check_final == "Si":
                warnings.append(
                    _warning_check_txt(
                        "check_no_marcado_con_valor_asociado",
                        seccion,
                        check_asociado,
                        campo_txt,
                        valor_check_original,
                        valor_txt,
                    )
                )
    return warnings


def _warning_check_txt(
    tipo: str,
    seccion: str,
    check_asociado: str,
    campo_txt: str,
    valor_check: str,
    valor_txt: str,
) -> dict[str, str]:
    return {
        "tipo": tipo,
        "campo_check": f"{seccion}.{check_asociado}",
        "campo_valor": f"{seccion}.{campo_txt}",
        "valor_check": valor_check,
        "valor_asociado": valor_txt,
    }


def _normalizar_seccion(
    seccion: str,
    valores: dict[str, str],
    especificaciones: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, str]:
    campos = especificaciones.get(seccion, {})
    normalizados = {
        campo: _normalizar_valor(valor, campos.get(campo))
        for campo, valor in valores.items()
    }
    _aplicar_inferencias_desde_valores(normalizados, campos)
    return normalizados


def _normalizar_checks_con_texto_en_seccion(
    seccion: str,
    valores: dict[str, str],
    campos: dict[str, dict[str, Any]],
) -> dict[str, str]:
    normalizados = dict(valores)
    for campo_txt, especificacion_txt in campos.items():
        check_asociado = especificacion_txt.get("reglas", {}).get("infiere_check_marcado")
        if not check_asociado:
            continue

        valor_check = normalizados.get(check_asociado, "")
        if valor_check in {"", "Si", "No"}:
            continue

        normalizados[campo_txt] = valor_check
        normalizados[check_asociado] = "Si"

    return normalizados


def _normalizar_valor(valor: str, especificacion: dict[str, Any] | None) -> str:
    if valor == "" or especificacion is None:
        return valor

    tipo = especificacion.get("tipo", "")
    reglas = especificacion.get("reglas", {})
    normalizacion = reglas.get("normalizacion", {})

    if _es_guion_vacio(valor, tipo, reglas, normalizacion):
        return ""

    if tipo == "texto" and _es_texto_sin_contenido(valor):
        return ""

    if normalizacion.get("modo") == "secuencia_o_texto":
        return _normalizar_secuencia_o_texto(valor, normalizacion)

    tipo_valor = reglas.get("tipo_valor", tipo)

    if tipo in {"check_simple", "check_con_valor"} and valor in {"Si", "No"}:
        return valor

    if tipo == "tabla_columna" and reglas.get("formato_salida") == "csv":
        tipo_celda = reglas.get("tipo_celda", "")
        if tipo_celda in {"double", "int"} or reglas.get("extraer_solo_numero"):
            return ",".join(
                _extraer_numero(celda.strip(), entero=tipo_celda == "int")
                if celda.strip() and celda.strip() != "-"
                else celda.strip()
                for celda in valor.split(",")
            )

    if tipo == "check_simple":
        return _normalizar_check_simple(valor, reglas)

    if reglas.get("extraer_solo_numero") or tipo_valor in {"double", "int"}:
        return _extraer_numero(valor, entero=tipo_valor == "int")

    return valor


def _es_texto_sin_contenido(valor: str) -> bool:
    limpio = valor.strip()
    if not limpio:
        return True
    return not bool(re.search(r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]", limpio))


def _es_guion_vacio(
    valor: str,
    tipo: str,
    reglas: dict[str, Any],
    normalizacion: dict[str, Any],
) -> bool:
    if valor.strip() != "-":
        return False
    if reglas.get("preservar_guion"):
        return False
    if tipo == "tabla_columna":
        return False
    if normalizacion.get("modo") in {"secuencia_o_texto"}:
        return False
    return True


def _normalizar_check_simple(valor: str, reglas: dict[str, Any]) -> str:
    if valor in {"Si", "No"}:
        return valor
    return reglas.get("valor_marcado", "Si") if valor else reglas.get("valor_no_marcado", "No")


def _normalizar_secuencia_o_texto(valor: str, reglas: dict[str, Any]) -> str:
    valor_limpio = " ".join(valor.replace(",", " ").split())
    if not valor_limpio:
        return ""

    valores_texto = {
        _normalizar_texto(valor_texto)
        for valor_texto in reglas.get("valores_texto", [])
    }
    if _normalizar_texto(valor_limpio) in valores_texto:
        return valor_limpio

    tokens = valor_limpio.split()
    if tokens and all(_es_codigo_planta(token) for token in tokens):
        return str(reglas.get("separador", ",")).join(tokens)
    return valor_limpio


def _normalizar_texto(valor: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "", valor).casefold()


def _es_codigo_planta(token: str) -> bool:
    return bool(re.fullmatch(r"-?\d+|[A-Za-z]{1,3}\d?", token))


def _aplicar_inferencias_desde_valores(
    valores: dict[str, str],
    campos: dict[str, dict[str, Any]],
) -> None:
    for campo, valor in list(valores.items()):
        if not valor:
            continue

        reglas = campos.get(campo, {}).get("reglas", {})
        check_inferido = reglas.get("infiere_check_marcado")
        if not check_inferido:
            continue

        especificacion_check = campos.get(check_inferido)
        if especificacion_check is None:
            continue

        reglas_check = especificacion_check.get("reglas", {})
        valores[check_inferido] = reglas_check.get("valor_marcado", "Si")


def _extraer_numero(valor: str, entero: bool) -> str:
    patron = r"\d+" if entero else r"\d+(?:[.,]\d+)?"
    match = re.search(patron, valor)
    if not match:
        return ""
    return match.group(0).replace(",", ".")


@lru_cache(maxsize=1)
def _especificaciones_por_seccion() -> dict[str, dict[str, dict[str, Any]]]:
    especificaciones: dict[str, dict[str, dict[str, Any]]] = {}
    for contenido in _contratos_por_seccion().values():
        seccion = contenido["seccion"]
        especificaciones[seccion] = {
            campo["nombre"]: campo
            for campo in contenido.get("campos", [])
        }
    return especificaciones


@lru_cache(maxsize=1)
def _contratos_por_seccion() -> dict[str, dict[str, Any]]:
    directorio = _directorio_secciones_contrato()
    contratos: dict[str, dict[str, Any]] = {}
    for ruta in directorio.glob("*.json"):
        contenido = json.loads(ruta.read_text(encoding="utf-8-sig"))
        contratos[contenido["seccion"]] = contenido
    return contratos


def _directorio_secciones_contrato() -> Path:
    for base in Path(__file__).resolve().parents:
        candidato = base / "docs" / "contrato_raloe_crono" / "secciones"
        if candidato.is_dir():
            return candidato
    raise FileNotFoundError("No se encontro docs/contrato_raloe_crono/secciones")
