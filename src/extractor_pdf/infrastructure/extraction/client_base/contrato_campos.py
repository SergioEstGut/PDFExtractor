from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


def aplicar_contrato_salida(secciones: dict[str, Any]) -> dict[str, Any]:
    especificaciones = _especificaciones_por_seccion()
    return {
        seccion: _normalizar_seccion(seccion, valores, especificaciones)
        if isinstance(valores, dict)
        else valores
        for seccion, valores in secciones.items()
    }


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


def _normalizar_check_simple(valor: str, reglas: dict[str, Any]) -> str:
    if valor in {"Si", "No"}:
        return valor
    return reglas.get("valor_marcado", "Si") if valor else reglas.get("valor_no_marcado", "No")


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
