from __future__ import annotations

from typing import Any

from extractor_pdf.application.campos_extra import SECCION_CAMPOS_EXTRA, detectar_campos_extra
from extractor_pdf.application.contrato_vacio import datos_vacios_raloe_crono
from extractor_pdf.application.notas_extra import SECCION_NOTAS_EXTRA, detectar_notas_extra
from extractor_pdf.domain.puertos import ExtractorVisualPagina, LectorTextoPdf, RenderizadorPaginaPdf
from extractor_pdf.infrastructure.comparison.comparador_extracciones import comparar_extracciones
from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import aplicar_contrato_salida
from extractor_pdf.infrastructure.extraction.client_base.extractor_foso_huida_opciones import (
    ExtractorFosoHuidaOpcionesRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_observaciones_resumen import (
    ExtractorObservacionesResumenRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_pagina_tecnica import (
    ExtractorPaginaTecnicaRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_premontada_armario_botoneras import (
    ExtractorPremontadaArmarioBotonerasRaloeCrono,
)
from extractor_pdf.infrastructure.ocr_contract.pagina_5_raloe_crono import (
    extraer_pagina_5_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.ocr_contract.pagina_foso_opciones_raloe_crono import (
    extraer_foso_opciones_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.ocr_contract.pagina_premontada_armario_botoneras_raloe_crono import (
    extraer_premontada_armario_botoneras_desde_ocr_con_debug,
)
from extractor_pdf.infrastructure.selection.detectores_paginas_raloe_crono import (
    DetectorPaginaFosoHuidaOpcionesRaloeCrono,
    DetectorPaginaPremontadaArmarioBotonerasRaloeCrono,
    DetectorPaginaTecnicaRaloeCrono,
)


class CasoUsoExtraerRaloeCronoFusionado:
    def __init__(
        self,
        lector_pdf: LectorTextoPdf,
        renderizador: RenderizadorPaginaPdf,
        extractor_visual: ExtractorVisualPagina,
        extractor_observaciones: ExtractorObservacionesResumenRaloeCrono | None = None,
        dpi: int = 200,
    ) -> None:
        self.lector_pdf = lector_pdf
        self.renderizador = renderizador
        self.extractor_visual = extractor_visual
        self.extractor_observaciones = extractor_observaciones or ExtractorObservacionesResumenRaloeCrono()
        self.dpi = dpi
        self.trabajos = [
            {
                "clave_pagina": "technical_page",
                "nombre": "pagina_tecnica",
                "detector": DetectorPaginaTecnicaRaloeCrono(),
                "extractor_pdf": ExtractorPaginaTecnicaRaloeCrono(),
                "extractor_ocr": extraer_pagina_5_desde_ocr_con_debug,
            },
            {
                "clave_pagina": "pit_escape_options_page",
                "nombre": "foso_opciones",
                "detector": DetectorPaginaFosoHuidaOpcionesRaloeCrono(),
                "extractor_pdf": ExtractorFosoHuidaOpcionesRaloeCrono(),
                "extractor_ocr": extraer_foso_opciones_desde_ocr_con_debug,
            },
            {
                "clave_pagina": "premounted_cabinet_buttons_page",
                "nombre": "premontada_armario_botoneras",
                "detector": DetectorPaginaPremontadaArmarioBotonerasRaloeCrono(),
                "extractor_pdf": ExtractorPremontadaArmarioBotonerasRaloeCrono(),
                "extractor_ocr": extraer_premontada_armario_botoneras_desde_ocr_con_debug,
            },
        ]

    def ejecutar(self, bytes_pdf: bytes) -> dict[str, Any]:
        paginas = self.lector_pdf.leer_paginas(bytes_pdf)
        datos = datos_vacios_raloe_crono()
        avisos: list[str] = []
        paginas_detectadas: dict[str, int | None] = {
            "summary_page": 1 if paginas else None,
            "technical_page": None,
            "pit_escape_options_page": None,
            "premounted_cabinet_buttons_page": None,
        }
        resumen_por_bloque: dict[str, dict[str, int]] = {}
        comparaciones: dict[str, Any] = {}

        if not _parece_raloe_crono(paginas):
            return {
                "data": datos,
                "comparison_summary": {},
                "comparisons": {},
                "metadata": {
                    **paginas_detectadas,
                    "is_raloe_crono": False,
                    "status": "not_raloe_crono",
                    "warnings": ["No se detectaron señales suficientes de Raloe-CRONO."],
                    "fusion_strategy": "pdf_ocr_no_ai",
                },
            }

        if paginas:
            _unir_en(datos, self.extractor_observaciones.extraer_paginas(paginas))

        for trabajo in self.trabajos:
            try:
                pagina = trabajo["detector"].detectar(paginas)
                paginas_detectadas[trabajo["clave_pagina"]] = pagina.numero
                pdf_data = aplicar_contrato_salida(trabajo["extractor_pdf"].extraer_con_debug(pagina)["data"])

                render = self.renderizador.renderizar_pagina(
                    bytes_pdf,
                    numero_pagina=pagina.numero,
                    dpi=self.dpi,
                )
                ocr_debug = self.extractor_visual.extraer(render, cliente_id="cliente_base")
                ocr_debug.update(
                    {
                        "pdf": "",
                        "page_number": pagina.numero,
                        "dpi": self.dpi,
                        "image": {"width": render.ancho, "height": render.alto},
                    }
                )
                ocr_resultado = trabajo["extractor_ocr"](ocr_debug, bytes_imagen=render.bytes_imagen)
                ocr_data = aplicar_contrato_salida(ocr_resultado["data"])

                comparacion = comparar_extracciones(pdf_data, ocr_data)
                fusion = fusionar_comparacion(comparacion)
                _unir_en(datos, fusion)
                resumen_por_bloque[trabajo["nombre"]] = comparacion["resumen"]
                comparaciones[trabajo["nombre"]] = comparacion
            except Exception as exc:
                avisos.append(f"No se pudo fusionar {trabajo['nombre']}: {exc}")

        secciones_por_pagina = _secciones_por_pagina(paginas_detectadas)
        paginas_con_datos = _paginas_detectadas(paginas, paginas_detectadas)
        campos_extra = detectar_campos_extra(
            paginas_con_datos,
            datos,
            secciones_por_pagina,
        )
        datos[SECCION_CAMPOS_EXTRA] = campos_extra
        datos[SECCION_NOTAS_EXTRA] = detectar_notas_extra(paginas_con_datos, secciones_por_pagina)
        if campos_extra:
            avisos.append("Se detectaron campos extra no contemplados en el contrato.")

        return {
            "data": datos,
            "comparison_summary": resumen_total(resumen_por_bloque),
            "comparisons": comparaciones,
            "metadata": {
                **paginas_detectadas,
                "is_raloe_crono": True,
                "status": "partial" if avisos else "ok",
                "warnings": avisos,
                "fusion_strategy": "pdf_ocr_no_ai",
                "ocr_engine": "tesseract",
                "dpi": self.dpi,
            },
        }


def fusionar_comparacion(comparacion: dict[str, Any]) -> dict[str, dict[str, str]]:
    fusion: dict[str, dict[str, str]] = {}
    for bloque in ("coincidencias", "solo_pdf", "solo_ocr"):
        for seccion, campos in comparacion.get(bloque, {}).items():
            fusion.setdefault(seccion, {}).update(campos)

    for seccion, campos in comparacion.get("diferencias", {}).items():
        for campo, valores in campos.items():
            fusion.setdefault(seccion, {})[campo] = valores.get("pdf", "")

    for seccion, campos in comparacion.get("vacios_en_ambos", {}).items():
        for campo in campos:
            fusion.setdefault(seccion, {})[campo] = ""
    return fusion


def resumen_total(resumenes: dict[str, dict[str, int]]) -> dict[str, int]:
    claves = ("coincidencias", "diferencias", "solo_pdf", "solo_ocr", "vacios_en_ambos")
    return {clave: sum(resumen.get(clave, 0) for resumen in resumenes.values()) for clave in claves}


def _unir_en(destino: dict[str, Any], origen: dict[str, Any]) -> None:
    for clave, valor in origen.items():
        if clave in destino and isinstance(destino[clave], dict) and isinstance(valor, dict):
            _unir_dict(destino[clave], valor)
        else:
            destino[clave] = valor


def _unir_dict(destino: dict[str, Any], origen: dict[str, Any]) -> None:
    for campo, valor in origen.items():
        actual = destino.get(campo, "")
        if actual and actual != "No" and valor in {"", "No"}:
            continue
        if actual == "Si" and valor == "No":
            continue
        destino[campo] = valor


def _parece_raloe_crono(paginas: list) -> bool:
    texto = "\n".join(pagina.texto for pagina in paginas[: min(len(paginas), 8)])
    senales = [
        "CRONO",
        "MANIOBRA CARLOS SILVA",
        "Tracción Eléctrica:",
        "Gestión foso / huida reducida:",
        "Premontada:",
    ]
    return sum(1 for senal in senales if senal in texto) >= 2


def _paginas_detectadas(paginas: list, paginas_detectadas: dict[str, int | None]) -> list:
    numeros_pagina = {
        numero_pagina for numero_pagina in paginas_detectadas.values() if isinstance(numero_pagina, int)
    }
    seleccionadas = [pagina for pagina in paginas if pagina.numero in numeros_pagina]
    return seleccionadas or paginas


def _secciones_por_pagina(paginas_detectadas: dict[str, int | None]) -> dict[int, list[str]]:
    secciones: dict[int, list[str]] = {}
    tecnica = paginas_detectadas.get("technical_page")
    if isinstance(tecnica, int):
        secciones[tecnica] = [
            "general",
            "Normas",
            "Caracteristicas",
            "Traccion_electrica",
            "Traccion_hidraulica",
            "Puertas_cabina_embarque_1",
            "Puertas_cabina_embarque_2",
        ]
    foso_opciones = paginas_detectadas.get("pit_escape_options_page")
    if isinstance(foso_opciones, int):
        secciones[foso_opciones] = ["Gestion_foso_huida_reducida", "Opciones"]
    premontada = paginas_detectadas.get("premounted_cabinet_buttons_page")
    if isinstance(premontada, int):
        secciones[premontada] = [
            "Premontada",
            "Armario",
            "Botonera_Exterior",
            "Botonera_Cabina",
        ]
    return secciones
