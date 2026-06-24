from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from extractor_pdf.application.contrato_vacio import datos_vacios_felesa_crono
from extractor_pdf.domain.entidades import PaginaPdf
from extractor_pdf.domain.puertos import LectorTextoPdf
from extractor_pdf.infrastructure.extraction.client_base.extraccion_declarativa_pdf import (
    extraer_por_reglas_pdf,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_felesa_crono import (
    detectar_paginas_felesa_crono,
)


SECCIONES_PRINCIPAL = [
    "Cabecera",
    "Normas",
    "Datos_Generales",
    "Datos_Motor",
    "Control_Motor",
    "Rescates",
    "Datos_Cabina",
    "Pesacargas",
    "Botonera_Cabina",
    "Opciones_Especiales",
    "Medidas_Premontada",
    "Medidas_Entreplantas",
    "Datos_Premontada",
    "Caja_Inspeccion",
]

SECCIONES_BOTONERAS_RELLANO = [
    "Botoneras_Rellano",
    "Placas_Botoneras_Rellano",
]


class CasoUsoExtraerFelesaCronoActual:
    def __init__(self, lector_pdf: LectorTextoPdf | None = None) -> None:
        self.lector_pdf = lector_pdf or LectorTextoPyMuPdf()

    def ejecutar(self, bytes_pdf: bytes) -> dict[str, Any]:
        paginas = self.lector_pdf.leer_paginas(bytes_pdf)
        pages = detectar_paginas_felesa_crono(paginas)
        contratos = _cargar_contratos_felesa()
        data = datos_vacios_felesa_crono()
        warnings: list[str] = []

        pagina_principal = _pagina_por_rol(paginas, pages, "principal", warnings)
        if pagina_principal:
            _extraer_secciones(
                data,
                contratos,
                pagina_principal,
                SECCIONES_PRINCIPAL,
            )

        pagina_botoneras = _pagina_por_rol(paginas, pages, "botoneras_rellano", warnings)
        if pagina_botoneras:
            _extraer_secciones(
                data,
                contratos,
                pagina_botoneras,
                SECCIONES_BOTONERAS_RELLANO,
            )

        data["Observaciones"]["Observaciones"] = _extraer_observaciones(paginas)
        data["Notas"]["Nota"] = _extraer_nota(paginas)

        return {
            "data": data,
            "metadata": {
                "profile_id": "felesa_crono",
                "template_id": "felesa_crono_electrico",
                "form_version": "0",
                "pages": pages,
                "principal_page": pages.get("principal"),
                "landing_buttons_page": pages.get("botoneras_rellano"),
                "status": "ok" if not warnings else "partial",
                "warnings": warnings,
                "ocr_supported": False,
            },
        }


def _extraer_secciones(
    data: dict[str, Any],
    contratos: dict[str, dict[str, Any]],
    pagina: PaginaPdf,
    secciones: list[str],
) -> None:
    for seccion in secciones:
        contrato = contratos.get(seccion)
        if contrato is None:
            continue
        especificaciones = {
            campo["nombre"]: campo
            for campo in contrato.get("campos", [])
        }
        extraido = extraer_por_reglas_pdf(
            pagina,
            seccion,
            especificaciones_param=especificaciones,
            configuracion_pdf_param=contrato.get("extraccion_pdf", {}),
            normalizador=lambda sec, campo, valor: _normalizar_valor(
                valor, especificaciones.get(campo, {})
            ),
        )
        data[seccion].update(extraido)


def _normalizar_valor(valor: str, especificacion: dict[str, Any]) -> str:
    if valor == "":
        return valor
    tipo = especificacion.get("tipo", "")
    reglas = especificacion.get("reglas", {})
    tipo_valor = reglas.get("tipo_valor", tipo)
    if tipo == "check_simple" and valor in {"Si", "No"}:
        return valor
    if tipo_valor == "int":
        return _extraer_numero(valor, entero=True)
    if tipo_valor == "double" or tipo == "double":
        return _extraer_numero(valor, entero=False)
    return valor


def _extraer_numero(valor: str, entero: bool) -> str:
    patron = r"\d+" if entero else r"\d+(?:[.,]\d+)?"
    match = re.search(patron, valor)
    if not match:
        return ""
    return match.group(0).replace(",", ".")


def _pagina_por_rol(
    paginas: list[PaginaPdf],
    pages: dict[str, int],
    rol: str,
    warnings: list[str],
) -> PaginaPdf | None:
    numero = pages.get(rol)
    if numero is None:
        warnings.append(f"No se detecto la pagina de rol '{rol}'.")
        return None
    return next((pagina for pagina in paginas if pagina.numero == numero), None)


def _extraer_observaciones(paginas: list[PaginaPdf]) -> str:
    fragmentos: list[str] = []
    if len(paginas) >= 1:
        for bloque in paginas[0].bloques:
            if bloque.y0 > 730 and bloque.y1 < 790:
                texto = _limpiar_bloque_observacion(bloque.texto)
                if texto:
                    fragmentos.append(texto)
    if len(paginas) >= 2:
        for bloque in paginas[1].bloques:
            if "Observaciones" in bloque.texto or "botoneras" in bloque.texto:
                texto = _limpiar_bloque_observacion(bloque.texto)
                if texto:
                    fragmentos.append(texto)
    return "\n".join(fragmentos)


def _extraer_nota(paginas: list[PaginaPdf]) -> str:
    if len(paginas) < 2:
        return ""
    lineas: list[str] = []
    for bloque in sorted(paginas[1].bloques, key=lambda item: (item.y0, item.x0)):
        if 680 <= bloque.y0 <= 805:
            for linea in bloque.texto.splitlines():
                linea = linea.strip()
                if not linea or linea == "Nota:" or linea.startswith("Plantilla-"):
                    continue
                lineas.append(linea)
    return "\n".join(lineas)


def _limpiar_bloque_observacion(texto: str) -> str:
    lineas: list[str] = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if linea.lower().startswith("observaciones"):
            continue
        if linea.lower().startswith("nota"):
            break
        if linea.lower().startswith("plantilla-"):
            break
        lineas.append(linea)
    return " ".join(lineas).strip()


def _cargar_contratos_felesa() -> dict[str, dict[str, Any]]:
    directorio = _directorio_secciones_felesa()
    contratos: dict[str, dict[str, Any]] = {}
    for ruta in directorio.glob("*.json"):
        contenido = json.loads(ruta.read_text(encoding="utf-8-sig"))
        contratos[contenido["seccion"]] = contenido
    return contratos


def _directorio_secciones_felesa() -> Path:
    for base in Path(__file__).resolve().parents:
        candidato = base / "docs" / "contrato_felesa_crono" / "secciones"
        if candidato.is_dir():
            return candidato
    raise FileNotFoundError("No se encontro docs/contrato_felesa_crono/secciones")
