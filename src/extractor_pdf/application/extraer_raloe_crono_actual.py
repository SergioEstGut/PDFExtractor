from typing import Any

from extractor_pdf.application.contrato_vacio import datos_vacios_raloe_crono
from extractor_pdf.application.campos_extra import SECCION_CAMPOS_EXTRA, detectar_campos_extra
from extractor_pdf.application.notas_extra import SECCION_NOTAS_EXTRA, detectar_notas_extra
from extractor_pdf.domain.puertos import LectorTextoPdf
from extractor_pdf.infrastructure.extraction.client_base.extractor_pagina_tecnica import (
    ExtractorPaginaTecnicaRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_foso_huida_opciones import (
    ExtractorFosoHuidaOpcionesRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_premontada_armario_botoneras import (
    ExtractorPremontadaArmarioBotonerasRaloeCrono,
)
from extractor_pdf.infrastructure.extraction.client_base.extractor_observaciones_resumen import (
    ExtractorObservacionesResumenRaloeCrono,
)
from extractor_pdf.infrastructure.selection.detectores_paginas_raloe_crono import (
    DetectorPaginaFosoHuidaOpcionesRaloeCrono,
    DetectorPaginaPremontadaArmarioBotonerasRaloeCrono,
    DetectorPaginaTecnicaRaloeCrono,
)


class CasoUsoExtraerRaloeCronoActual:
    def __init__(
        self,
        lector_pdf: LectorTextoPdf,
        detector_page_tecnica: DetectorPaginaTecnicaRaloeCrono | None = None,
        detector_page_foso_huida: DetectorPaginaFosoHuidaOpcionesRaloeCrono | None = None,
        detector_page_premontada: DetectorPaginaPremontadaArmarioBotonerasRaloeCrono | None = None,
        extractor_tecnico: ExtractorPaginaTecnicaRaloeCrono | None = None,
        extractor_foso_huida: ExtractorFosoHuidaOpcionesRaloeCrono | None = None,
        extractor_premontada: ExtractorPremontadaArmarioBotonerasRaloeCrono | None = None,
        extractor_observaciones: ExtractorObservacionesResumenRaloeCrono | None = None,
    ) -> None:
        self.lector_pdf = lector_pdf
        self.detector_page_tecnica = detector_page_tecnica or DetectorPaginaTecnicaRaloeCrono()
        self.detector_page_foso_huida = (
            detector_page_foso_huida or DetectorPaginaFosoHuidaOpcionesRaloeCrono()
        )
        self.detector_page_premontada = (
            detector_page_premontada or DetectorPaginaPremontadaArmarioBotonerasRaloeCrono()
        )
        self.extractor_tecnico = extractor_tecnico or ExtractorPaginaTecnicaRaloeCrono()
        self.extractor_foso_huida = extractor_foso_huida or ExtractorFosoHuidaOpcionesRaloeCrono()
        self.extractor_premontada = (
            extractor_premontada or ExtractorPremontadaArmarioBotonerasRaloeCrono()
        )
        self.extractor_observaciones = extractor_observaciones or ExtractorObservacionesResumenRaloeCrono()

    def ejecutar(self, bytes_pdf: bytes) -> dict[str, Any]:
        paginas = self.lector_pdf.leer_paginas(bytes_pdf)
        avisos: list[str] = []
        datos = datos_vacios_raloe_crono()
        paginas_detectadas: dict[str, int | None] = {
            "summary_page": 1 if paginas else None,
            "technical_page": None,
            "pit_escape_options_page": None,
            "premounted_cabinet_buttons_page": None,
        }

        if not _parece_raloe_crono(paginas):
            return {
                "data": datos,
                "page_1": {"Observaciones": ""},
                "metadata": {
                    **paginas_detectadas,
                    "is_raloe_crono": False,
                    "status": "not_raloe_crono",
                    "warnings": ["No se detectaron seÃ±ales suficientes de Raloe-CRONO."],
                },
            }

        datos_page_1 = {"Observaciones": ""}
        datos_tecnicos: dict[str, Any] = {}
        datos_foso_huida: dict[str, Any] = {}
        datos_premontada: dict[str, Any] = {}

        if paginas:
            datos_page_1 = self.extractor_observaciones.extraer(paginas[0])
            _unir_en(datos, self.extractor_observaciones.extraer_paginas(paginas))

        try:
            pagina_tecnica = self.detector_page_tecnica.detectar(paginas)
            paginas_detectadas["technical_page"] = pagina_tecnica.numero
            datos_tecnicos = self.extractor_tecnico.extraer(pagina_tecnica)
            _unir_en(datos, datos_tecnicos)
        except Exception as exc:
            avisos.append(f"No se pudo extraer la pagina tecnica principal: {exc}")

        try:
            pagina_foso_huida = self.detector_page_foso_huida.detectar(paginas)
            paginas_detectadas["pit_escape_options_page"] = pagina_foso_huida.numero
            datos_foso_huida = self.extractor_foso_huida.extraer(pagina_foso_huida)
            _unir_en(datos, datos_foso_huida)
        except Exception as exc:
            avisos.append(f"No se pudo extraer foso/huida/opciones: {exc}")

        try:
            pagina_premontada = self.detector_page_premontada.detectar(paginas)
            paginas_detectadas["premounted_cabinet_buttons_page"] = pagina_premontada.numero
            datos_premontada = self.extractor_premontada.extraer(pagina_premontada)
            _unir_en(datos, datos_premontada)
        except Exception as exc:
            avisos.append(f"No se pudo extraer premontada/armario/botoneras: {exc}")

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
            "page_1": datos_page_1,
            **(
                {f"page_{paginas_detectadas['technical_page']}": datos_tecnicos}
                if paginas_detectadas["technical_page"]
                else {}
            ),
            **(
                {f"page_{paginas_detectadas['pit_escape_options_page']}": datos_foso_huida}
                if paginas_detectadas["pit_escape_options_page"]
                else {}
            ),
            **(
                {f"page_{paginas_detectadas['premounted_cabinet_buttons_page']}": datos_premontada}
                if paginas_detectadas["premounted_cabinet_buttons_page"]
                else {}
            ),
            "metadata": {
                **paginas_detectadas,
                "is_raloe_crono": True,
                "status": "partial" if avisos else "ok",
                "warnings": avisos,
            },
        }


def _unir_secciones(*partes: dict[str, Any]) -> dict[str, Any]:
    unido: dict[str, Any] = {}
    for parte in partes:
        for clave, valor in parte.items():
            if clave in unido and isinstance(unido[clave], dict) and isinstance(valor, dict):
                unido[clave].update(valor)
            else:
                unido[clave] = valor
    return unido


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







