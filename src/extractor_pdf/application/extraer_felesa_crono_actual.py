from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from extractor_pdf.application.campos_extra import SECCION_CAMPOS_EXTRA, detectar_campos_extra
from extractor_pdf.application.contrato_vacio import datos_vacios_felesa_crono
from extractor_pdf.application.notas_extra import SECCION_NOTAS_EXTRA, detectar_notas_extra
from extractor_pdf.domain.entidades import PaginaPdf
from extractor_pdf.domain.puertos import LectorTextoPdf
from extractor_pdf.infrastructure.extraction.client_base.extraccion_declarativa_pdf import (
    extraer_por_reglas_pdf,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_felesa_crono import (
    detectar_plantilla_felesa_crono,
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
        template_id = detectar_plantilla_felesa_crono(paginas)
        pages = detectar_paginas_felesa_crono(paginas)
        contratos = _cargar_contratos_felesa(template_id)
        data = _datos_vacios_felesa(template_id, contratos)
        warnings: list[str] = []

        pagina_principal = _pagina_por_rol(paginas, pages, "principal", warnings)
        if pagina_principal:
            _avisar_si_texto_pdf_no_confiable(pagina_principal, "principal", warnings)
            _extraer_secciones(
                data,
                contratos,
                pagina_principal,
                _secciones_para_rol(template_id, contratos, "principal"),
            )

        secciones_botoneras = _secciones_para_rol(template_id, contratos, "botoneras_rellano")
        pagina_botoneras = (
            _pagina_por_rol(paginas, pages, "botoneras_rellano", warnings)
            if secciones_botoneras
            else None
        )
        if pagina_botoneras:
            _avisar_si_texto_pdf_no_confiable(pagina_botoneras, "botoneras_rellano", warnings)
            _extraer_secciones(
                data,
                contratos,
                pagina_botoneras,
                secciones_botoneras,
            )

        _aplicar_derivados_felesa(data, contratos)
        data["Observaciones"]["Observaciones"] = _extraer_observaciones(
            pagina_principal,
            pagina_botoneras,
        )
        if "Notas" in data:
            data["Notas"]["Nota"] = _extraer_nota(pagina_botoneras)
        secciones_por_pagina = _secciones_por_pagina(pages, template_id, contratos)
        paginas_con_datos = _paginas_detectadas(paginas, pages)
        campos_extra = detectar_campos_extra(
            paginas_con_datos,
            data,
            secciones_por_pagina,
            _directorio_secciones_felesa(template_id),
            detectar_conocidos_fuera_de_seccion=False,
            claves_ignoradas={"PLACA_PARA_BOTONERAS_DE_RELLANO"},
            ignorar_lineas_desde_y=735,
        )
        data[SECCION_CAMPOS_EXTRA] = campos_extra
        data[SECCION_NOTAS_EXTRA] = detectar_notas_extra(
            paginas_con_datos,
            secciones_por_pagina,
            ignorar_tonos_azules=True,
            ignorar_tonos_grises_claros=True,
            detectar_marcas_visuales=True,
        )
        if campos_extra:
            warnings.append("Se detectaron campos extra no contemplados en el contrato.")

        return {
            "data": data,
            "metadata": {
                "profile_id": _profile_id_para_template(template_id),
                "template_id": template_id,
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
        _aplicar_dependencias_felesa(extraido, especificaciones)
        data[seccion].update(extraido)


def _avisar_si_texto_pdf_no_confiable(
    pagina: PaginaPdf,
    rol: str,
    warnings: list[str],
) -> None:
    if not _texto_pdf_parece_no_confiable(pagina.texto):
        return
    aviso = (
        f"La capa de texto PDF de la pagina {pagina.numero} ({rol}) parece no confiable; "
        "la extraccion por texto puede ser incompleta. Revisar con OCR o validacion manual."
    )
    if aviso not in warnings:
        warnings.append(aviso)


def _texto_pdf_parece_no_confiable(texto: str) -> bool:
    if not texto:
        return False
    caracteres_utiles = [caracter for caracter in texto if not caracter.isspace()]
    if len(caracteres_utiles) < 50:
        return False

    controles = sum(
        1
        for caracter in caracteres_utiles
        if unicodedata.category(caracter).startswith("C")
    )
    if controles / len(caracteres_utiles) >= 0.02:
        return True

    tokens = re.findall(r"\S+", texto)
    if len(tokens) < 20:
        return False
    tokens_raros = sum(1 for token in tokens if _token_pdf_raro(token))
    return tokens_raros / len(tokens) >= 0.35


def _token_pdf_raro(token: str) -> bool:
    caracteres = [caracter for caracter in token if not caracter.isspace()]
    if not caracteres:
        return False
    malos = sum(
        1
        for caracter in caracteres
        if unicodedata.category(caracter).startswith("C")
        or (ord(caracter) < 32)
    )
    return malos > 0


def _normalizar_valor(valor: str, especificacion: dict[str, Any]) -> str:
    if valor == "":
        return valor
    tipo = especificacion.get("tipo", "")
    reglas = especificacion.get("reglas", {})
    normalizacion = reglas.get("normalizacion", {})
    if normalizacion.get("modo") == "secuencia_o_texto":
        return _normalizar_secuencia_o_texto(valor, normalizacion)

    tipo_valor = reglas.get("tipo_valor", tipo)
    if tipo == "check_simple" and valor in {"Si", "No"}:
        return valor
    if tipo_valor == "int":
        return _extraer_numero(valor, entero=True)
    if tipo_valor == "double" or tipo == "double":
        return _extraer_numero(valor, entero=False)
    return valor


def _aplicar_dependencias_felesa(
    valores: dict[str, str],
    especificaciones: dict[str, dict[str, Any]],
) -> None:
    for campo, especificacion in especificaciones.items():
        dependencia_vacio = especificacion.get("reglas", {}).get("vaciar_si_campo_vacio")
        if not dependencia_vacio:
            continue
        if not valores.get(dependencia_vacio, ""):
            valores[campo] = ""


def _aplicar_derivados_felesa(
    data: dict[str, Any],
    contratos: dict[str, dict[str, Any]],
) -> None:
    for seccion, contrato in contratos.items():
        valores_seccion = data.get(seccion)
        if not isinstance(valores_seccion, dict):
            continue
        for campo in contrato.get("campos", []):
            derivado = campo.get("reglas", {}).get("derivado", {})
            if derivado.get("modo") != "planta_desde_ubicacion_y_secuencia":
                continue
            nombre = campo["nombre"]
            origen = str(valores_seccion.get(derivado.get("campo_origen", ""), ""))
            seccion_secuencia = derivado.get("seccion_secuencia", "")
            campo_secuencia = derivado.get("campo_secuencia", "")
            secuencia = ""
            valores_secuencia = data.get(seccion_secuencia)
            if isinstance(valores_secuencia, dict):
                secuencia = str(valores_secuencia.get(campo_secuencia, ""))
            valores_seccion[nombre] = _extraer_planta_desde_secuencia(origen, secuencia)


def _extraer_planta_desde_secuencia(texto: str, secuencia: str) -> str:
    texto = texto.strip()
    if not texto or not secuencia:
        return ""

    plantas = [
        planta.strip()
        for planta in re.split(r"[,;\s]+", secuencia)
        if planta.strip()
    ]
    for planta in sorted(plantas, key=len, reverse=True):
        patron = rf"(?<![A-Za-z0-9-]){re.escape(planta)}(?![A-Za-z0-9])"
        if re.search(patron, texto, re.IGNORECASE):
            return planta
    return ""


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


def _secciones_por_pagina(
    pages: dict[str, int],
    template_id: str,
    contratos: dict[str, dict[str, Any]],
) -> dict[int, list[str]]:
    secciones: dict[int, list[str]] = {}
    pagina_principal = pages.get("principal")
    if pagina_principal is not None:
        secciones[pagina_principal] = _secciones_para_rol(template_id, contratos, "principal")

    pagina_botoneras = pages.get("botoneras_rellano")
    if pagina_botoneras is not None:
        secciones[pagina_botoneras] = _secciones_para_rol(
            template_id,
            contratos,
            "botoneras_rellano",
        )

    return secciones


def _secciones_para_rol(
    template_id: str,
    contratos: dict[str, dict[str, Any]],
    rol: str,
) -> list[str]:
    secciones = [
        seccion
        for seccion, contrato in contratos.items()
        if contrato.get("extraccion_pdf", {}).get("pagina_rol") == rol
    ]
    if secciones:
        return secciones

    if template_id == "felesa_crono_electrico":
        if rol == "principal":
            return SECCIONES_PRINCIPAL
        if rol == "botoneras_rellano":
            return SECCIONES_BOTONERAS_RELLANO
        return []

    return []


def _paginas_detectadas(paginas: list[PaginaPdf], pages: dict[str, int]) -> list[PaginaPdf]:
    numeros = {numero for numero in pages.values() if numero is not None}
    return [pagina for pagina in paginas if pagina.numero in numeros]


def _extraer_observaciones(
    pagina_principal: PaginaPdf | None,
    pagina_botoneras: PaginaPdf | None,
) -> str:
    if pagina_principal and pagina_principal.texto.startswith("Formulari CRONO"):
        return _extraer_observaciones_aszende(pagina_principal)
    fragmentos: list[str] = []
    if pagina_principal is not None:
        for bloque in pagina_principal.bloques:
            if bloque.y0 > 730 and bloque.y1 < 790:
                texto = _limpiar_bloque_observacion(
                    _texto_bloque_sin_notas_coloreadas(pagina_principal, bloque)
                )
                if texto:
                    fragmentos.append(texto)
    if pagina_botoneras is not None:
        texto_botoneras = _extraer_observaciones_botoneras(pagina_botoneras)
        if texto_botoneras:
            fragmentos.append(texto_botoneras)
    return "\n".join(fragmentos)


def _extraer_observaciones_aszende(pagina: PaginaPdf) -> str:
    palabras = [
        palabra
        for palabra in pagina.palabras
        if 748 <= palabra.y0 <= 821
        and 30 <= palabra.x0 <= 560
        and palabra.color not in {2301728, 9672088}
    ]
    if not palabras:
        return ""

    lineas: list[list[Any]] = []
    for palabra in sorted(palabras, key=lambda item: (item.y0, item.x0)):
        if not lineas or abs(lineas[-1][0].y0 - palabra.y0) > 4:
            lineas.append([palabra])
        else:
            lineas[-1].append(palabra)

    textos: list[str] = []
    for linea in lineas:
        texto = _limpiar_espacios_puntuacion(" ".join(palabra.texto for palabra in linea))
        if texto:
            textos.append(texto)
    return "\n".join(textos)


def _extraer_nota(pagina_botoneras: PaginaPdf | None) -> str:
    if pagina_botoneras is None:
        return ""
    lineas: list[str] = []
    for bloque in sorted(pagina_botoneras.bloques, key=lambda item: (item.y0, item.x0)):
        if 680 <= bloque.y0 <= 805:
            for linea in bloque.texto.splitlines():
                linea = linea.strip()
                if not linea or linea == "Nota:" or linea.startswith("Plantilla-"):
                    continue
                lineas.append(linea)
    return "\n".join(lineas)


def _extraer_observaciones_botoneras(pagina_botoneras: PaginaPdf) -> str:
    bloques = sorted(pagina_botoneras.bloques, key=lambda item: (item.y0, item.x0))
    dentro_observaciones = False
    fragmentos: list[str] = []
    for bloque in bloques:
        texto_bloque = _texto_bloque_sin_notas_coloreadas(pagina_botoneras, bloque)
        if re.search(r"\bobservaciones\s*:", texto_bloque, re.IGNORECASE):
            dentro_observaciones = True
        if not dentro_observaciones:
            continue
        texto = _limpiar_bloque_observacion(texto_bloque)
        if texto:
            fragmentos.append(texto)
        texto_normalizado = texto_bloque.strip().casefold()
        if re.match(r"^nota\s*:", texto_normalizado) or texto_normalizado.startswith("plantilla-"):
            break
    return " ".join(fragmentos).strip()


def _texto_bloque_sin_notas_coloreadas(pagina: PaginaPdf, bloque: Any) -> str:
    palabras_bloque = [
        palabra
        for palabra in pagina.palabras
        if palabra.x0 >= bloque.x0 - 4
        and palabra.x1 <= bloque.x1 + 4
        and palabra.y0 >= bloque.y0 - 4
        and palabra.y1 <= bloque.y1 + 4
    ]
    palabras = [palabra for palabra in palabras_bloque if not _es_texto_rojo(palabra.color)]
    if not palabras_bloque:
        return str(bloque.texto)
    if not palabras:
        return ""
    lineas: list[list[Any]] = []
    for palabra in sorted(palabras, key=lambda item: (item.y0, item.x0)):
        if not lineas or abs(lineas[-1][0].y0 - palabra.y0) > 4:
            lineas.append([palabra])
        else:
            lineas[-1].append(palabra)
    return "\n".join(" ".join(palabra.texto for palabra in linea) for linea in lineas)


def _es_texto_rojo(color: int | None) -> bool:
    if color is None:
        return False
    rojo = (color >> 16) & 255
    verde = (color >> 8) & 255
    azul = color & 255
    return rojo >= 150 and rojo > verde * 1.4 and rojo > azul * 1.4


def _limpiar_bloque_observacion(texto: str) -> str:
    lineas: list[str] = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if re.match(r"^observaciones\s*:", linea, re.IGNORECASE):
            continue
        if linea.lower().startswith("nota"):
            break
        if linea.lower().startswith("plantilla-"):
            break
        lineas.append(linea)
    return " ".join(lineas).strip()


def _limpiar_espacios_puntuacion(texto: str) -> str:
    texto = re.sub(r"\s+([:;,.])", r"\1", texto)
    texto = re.sub(r"([¿¡])\s+", r"\1", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _cargar_contratos_felesa(template_id: str) -> dict[str, dict[str, Any]]:
    directorio = _directorio_secciones_felesa(template_id)
    contratos: dict[str, dict[str, Any]] = {}
    for ruta in directorio.glob("*.json"):
        contenido = json.loads(ruta.read_text(encoding="utf-8-sig"))
        contratos[contenido["seccion"]] = contenido
    return contratos


def _datos_vacios_felesa(
    template_id: str,
    contratos: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if template_id == "felesa_crono_electrico":
        return datos_vacios_felesa_crono()

    data: dict[str, Any] = {}
    for seccion, contrato in contratos.items():
        data[seccion] = {
            campo["nombre"]: campo.get("valor_defecto", "")
            for campo in contrato.get("campos", [])
            if isinstance(campo, dict) and campo.get("nombre")
        }
    if not template_id.startswith("aszende_"):
        data.setdefault("Notas", {"Nota": ""})
    return data


def _profile_id_para_template(template_id: str) -> str:
    if template_id.startswith("aszende_"):
        return "aszende_crono"
    return "felesa_crono"


def _directorio_secciones_felesa(template_id: str = "felesa_crono_electrico") -> Path:
    directorios = {
        "felesa_crono_electrico": "contrato_felesa_crono",
        "felesa_crono_hidraulico": "contrato_felesa_crono_hidraulico",
        "aszende_crono_electrico": "contrato_aszende_crono_electrico",
    }
    nombre_directorio = directorios.get(template_id, "contrato_felesa_crono")
    for base in Path(__file__).resolve().parents:
        candidato = base / "docs" / nombre_directorio / "secciones"
        if candidato.is_dir():
            return candidato
    raise FileNotFoundError(f"No se encontro docs/{nombre_directorio}/secciones")
