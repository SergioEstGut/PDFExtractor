from __future__ import annotations

import re
import unicodedata
from contextvars import ContextVar
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from PIL import Image

from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import (
    aplicar_contrato_salida,
    normalizar_checks_con_texto_asociado,
    normalizar_valor_campo,
)

CHECK_MARCADO_GEOMETRICO = ["[v]", "v]", "yv]", "y]", "Vv", "IS]", "IN", "y", "vi", "Y]", "[Y]", "w]"]
CHECK_VACIO_GEOMETRICO = ["O", "0", "L]", "LJ", "C1", "Ll", "[1", "1]", "JOR", "Ol"]
_LINEAS_OCR_CONTEXT: ContextVar[list[dict[str, Any]]] = ContextVar("lineas_ocr_context_p5", default=[])
_IMAGEN_CONTEXT: ContextVar[Image.Image | None] = ContextVar("imagen_context_p5", default=None)


@dataclass(frozen=True)
class CampoLeido:
    valor: str
    fuente: str
    linea: str
    patron: str


def extraer_pagina_5_desde_ocr(
    ocr_debug: dict[str, Any], bytes_imagen: bytes | None = None
) -> dict[str, dict[str, str]]:
    resultado = extraer_pagina_5_desde_ocr_con_debug(ocr_debug, bytes_imagen=bytes_imagen)
    return resultado["data"]


def extraer_pagina_5_desde_ocr_con_debug(
    ocr_debug: dict[str, Any], bytes_imagen: bytes | None = None
) -> dict[str, Any]:
    """Experimental honest OCR parser for Raloe-CRONO page 5.

    It only returns values that can be tied to OCR text evidence. If a field
    cannot be read from OCR, it remains empty.
    """

    lineas_ocr = ocr_debug["ocr"]["lines"]
    lineas = [linea["text"] for linea in lineas_ocr]
    debug: dict[str, dict[str, CampoLeido]] = {}
    imagen = Image.open(BytesIO(bytes_imagen)).convert("L") if bytes_imagen else None

    token_lineas = _LINEAS_OCR_CONTEXT.set(lineas_ocr)
    token_imagen = _IMAGEN_CONTEXT.set(imagen)
    try:
        data_cruda = {
            "general": _extraer_general(lineas, debug),
            "Normas": _extraer_normas(lineas, debug),
            "Caracteristicas": _extraer_caracteristicas(lineas, debug),
            "Traccion_electrica": _extraer_traccion_electrica(lineas, debug),
            "Traccion_hidraulica": _extraer_traccion_hidraulica(lineas, debug),
            "Puertas_cabina_embarque_1": _extraer_puertas(lineas, 1, debug),
            "Puertas_cabina_embarque_2": _extraer_puertas(lineas, 2, debug),
        }
    finally:
        _LINEAS_OCR_CONTEXT.reset(token_lineas)
        _IMAGEN_CONTEXT.reset(token_imagen)
    data = aplicar_contrato_salida(normalizar_checks_con_texto_asociado(data_cruda))
    return {
        "data": data,
        "debug": _normalizar_debug(debug),
    }


def _extraer_general(lineas: list[str], debug: dict[str, dict[str, CampoLeido]]) -> dict[str, str]:
    seccion = "general"
    linea_serie = _linea_con(lineas, "Serie:")
    linea_pais = _linea_anterior(lineas, linea_serie)

    data = {
        "Serie": _leer_regex(seccion, "Serie", linea_serie, r"Serie:\s*(\S+)", debug),
        "Pais_instalacion": "",
        "Idioma_documentacion": "",
        "Especificacion_norte_africa": _leer_check_en_linea(
            seccion, "Especificacion_norte_africa", _linea_con(lineas, "Especificación Norte"), debug
        ),
    }

    partes = linea_pais.split()
    if len(partes) >= 2:
        data["Pais_instalacion"] = _registrar(
            seccion, "Pais_instalacion", _normalizar_ocr_es(partes[0]), linea_pais, "linea_anterior", debug
        )
        data["Idioma_documentacion"] = _registrar(
            seccion, "Idioma_documentacion", _normalizar_ocr_es(partes[1]), linea_pais, "linea_anterior", debug
        )
    return data


def _normalizar_debug(debug: dict[str, dict[str, CampoLeido]]) -> dict[str, dict[str, dict[str, str]]]:
    normalizado: dict[str, dict[str, dict[str, str]]] = {}
    for seccion, campos in debug.items():
        normalizado[seccion] = {}
        for campo, evidencia in campos.items():
            valor_normalizado = normalizar_valor_campo(seccion, campo, evidencia.valor)
            item = {
                "valor": valor_normalizado,
                "valor_crudo": evidencia.valor,
                "fuente": evidencia.fuente,
                "linea": evidencia.linea,
                "patron": evidencia.patron,
            }
            if valor_normalizado != evidencia.valor:
                item["valor_normalizado"] = valor_normalizado
            normalizado[seccion][campo] = item
    return normalizado


def _extraer_normas(lineas: list[str], debug: dict[str, dict[str, CampoLeido]]) -> dict[str, str]:
    seccion = "Normas"
    linea_1 = _linea_con(lineas, "81- 1/A3")
    linea_2 = _linea_con(lineas, "81-73")

    return {
        "Norma_81_1_A3": _leer_check_en_linea(seccion, "Norma_81_1_A3", linea_1, debug, etiqueta="81- 1/A3"),
        "Norma_81_2_A3": _leer_check_en_linea(seccion, "Norma_81_2_A3", linea_1, debug, etiqueta="81- 2/A3"),
        "Norma_81_20_50": _leer_check_en_linea(seccion, "Norma_81_20_50", linea_1, debug, etiqueta="81- 20/50"),
        "Norma_81_70": _leer_check_en_linea(seccion, "Norma_81_70", linea_1, debug, etiqueta="81-70"),
        "Norma_81_71_CAT_1": _leer_check_en_linea(seccion, "Norma_81_71_CAT_1", linea_1, debug, etiqueta="81-71 CAT.1"),
        "Norma_81_71_CAT_2": _leer_check_en_linea(seccion, "Norma_81_71_CAT_2", linea_1, debug, etiqueta="181-71 CAT.2"),
        "BS9999": _leer_check_en_linea(seccion, "BS9999", linea_1, debug, etiqueta="BS9999"),
        "Norma_81_72": _leer_check_en_linea(seccion, "Norma_81_72", linea_2, debug, etiqueta="1181-72"),
        "Norma_81_77": _leer_check_en_linea(seccion, "Norma_81_77", linea_2, debug, etiqueta="181.77"),
        "Norma_81_73": _leer_check_en_linea(seccion, "Norma_81_73", linea_2, debug, etiqueta="81-73"),
        "Norma_81_73_txt": _leer_texto_norma_81_73(linea_2, debug),
        "Shabbat": _leer_check_en_linea(seccion, "Shabbat", linea_2, debug, etiqueta="Shabbat"),
    }


def _leer_texto_norma_81_73(linea: str, debug: dict[str, dict[str, CampoLeido]]) -> str:
    seccion = "Normas"
    campo = "Norma_81_73_txt"
    if "81-73" not in linea:
        return ""

    match = re.search(r"81-73\s*(.*?)\s+(?:\S+\]\s*)?Shabbat", linea)
    valor = match.group(1).strip() if match else ""
    valor = _limpiar_marcadores_check_norma_81_73_txt(valor)
    debug.setdefault(seccion, {})[campo] = CampoLeido(valor, "ocr_text", linea, "texto entre 81-73 y Shabbat")
    return valor


def _limpiar_marcadores_check_norma_81_73_txt(valor: str) -> str:
    marcadores = {
        "O",
        "0",
        "L]",
        "LJ",
        "LC]",
        "[]",
        "C1",
        "Ll",
        "LC",
        "[1",
        "1]",
        "JOR",
        "Ol",
        "lv]",
        "lV]",
        "Iv]",
        "LV]",
        "[Y]",
        "[v]",
        "[V]",
        "v]",
        "V]",
        "yv]",
        "Y]",
        "w]",
        "[4]",
        "[vd]",
    }
    tokens = [
        token
        for token in valor.split()
        if token not in marcadores and not _parece_marcador_check_ocr(token)
    ]
    return " ".join(tokens).strip()


def _parece_marcador_check_ocr(token: str) -> bool:
    return bool(re.fullmatch(r"\[[A-Za-z0-9]{1,3}\]", token) or re.fullmatch(r"[A-Za-z0-9]{1,3}\]", token))


def _extraer_caracteristicas(
    lineas: list[str], debug: dict[str, dict[str, CampoLeido]]
) -> dict[str, str]:
    seccion = "Caracteristicas"
    linea_maniobra = _linea_con(lineas, "Maniobra:")
    linea_tension = _linea_con(lineas, "Tensión Línea")
    linea_intensidad = _linea_con(lineas, "Intensidad motor:")
    linea_sobredim = _linea_con(lineas, "Intensidad sobredim.:")

    tensiones = re.search(r"Motor:\s*([\d.,]+)\s*/\s*([\d.,]+)", linea_tension)
    data = {
        "Maniobra": _leer_regex(seccion, "Maniobra", linea_maniobra, r"Maniobra:\s*(.*?)\s+Tipo:", debug),
        "Tipo": _leer_regex(seccion, "Tipo", linea_maniobra, r"Tipo:\s*(\S+)", debug),
        "Arq": _leer_regex(seccion, "Arq", linea_maniobra, r"\b(MRL)\b", debug),
        "Consola_maniobra": _leer_check_en_linea(seccion, "Consola_maniobra", linea_maniobra, debug, etiqueta="Consola"),
        "Tension_linea": "",
        "Tension_motor": "",
        "Mono": _leer_check_en_linea(seccion, "Mono", linea_tension, debug, etiqueta="Mono"),
        "Tri": _leer_check_en_linea(seccion, "Tri", linea_tension, debug, etiqueta="Tri"),
        "Velocidad": _leer_numero(seccion, "Velocidad", linea_tension, r"Velocidad:\s*([\d.,]+)", debug),
        "Paradas": _leer_numero(seccion, "Paradas", linea_tension, r"Paradas:\s*(\d+)", debug),
        "Intensidad_motor": _leer_numero(seccion, "Intensidad_motor", linea_intensidad, r"Intensidad motor:\s*([\d.,]+)", debug),
        "Frecuencia_50_Hz": _leer_check_en_linea(seccion, "Frecuencia_50_Hz", linea_intensidad, debug, etiqueta="50 Hz"),
        "Frecuencia_60_Hz": _leer_check_en_linea(seccion, "Frecuencia_60_Hz", linea_intensidad, debug, etiqueta="60 Hz"),
        "Neutro": _leer_check_en_linea(seccion, "Neutro", linea_intensidad, debug, etiqueta="Neutro"),
        "Intensidad_sobredim": _leer_numero(
            seccion, "Intensidad_sobredim", linea_sobredim, r"Intensidad sobredim\.:\s*([\d.,]+)", debug
        ),
        "Sin_cuarto_de_maquinas": _leer_check_en_linea(
            seccion, "Sin_cuarto_de_maquinas", linea_sobredim, debug, etiqueta="Sin cuarto"
        ),
        "Maquina_arriba": _leer_check_en_linea(seccion, "Maquina_arriba", linea_sobredim, debug, etiqueta="Máquina arriba"),
        "Maquina_abajo": _leer_check_en_linea(seccion, "Maquina_abajo", linea_sobredim, debug, etiqueta="Maquina abajo"),
    }
    if tensiones:
        data["Tension_linea"] = _registrar(seccion, "Tension_linea", tensiones.group(1), linea_tension, "Motor: a/b", debug)
        data["Tension_motor"] = _registrar(seccion, "Tension_motor", tensiones.group(2), linea_tension, "Motor: a/b", debug)
    return data


def _extraer_traccion_electrica(
    lineas: list[str], debug: dict[str, dict[str, CampoLeido]]
) -> dict[str, str]:
    seccion = "Traccion_electrica"
    linea_motor = _linea_con(lineas, "Fabricante:")
    linea_potencia = _linea_con(lineas, "Potencia:")
    linea_variador = _linea_con(lineas, "Variador:")
    linea_parametro = _linea_con(lineas, "Consola VF")
    linea_encoder = _linea_con(lineas, "Encoder")
    linea_cable_potencia = _linea_con(lineas, "Cable Potencia")
    linea_cable_accesorios = _linea_con(lineas, "Cableado Accesorios")

    data = {
        "Fabricante_motor": _leer_regex(seccion, "Fabricante_motor", linea_motor, r"Fabricante:\s*(\S+)", debug),
        "Modelo_motor": _leer_regex(seccion, "Modelo_motor", linea_motor, r"Modelo motor:\s*(.*?)\s+Tipo:", debug),
        "Tipo_traccion": _leer_regex(seccion, "Tipo_traccion", linea_motor, r"Tipo:\s*(.*?)\s+Frec\.", debug),
        "Frec_motor": _leer_numero(seccion, "Frec_motor", linea_motor, r"Frec\. Motor:\s*([\d.,]+)", debug),
        "PotenciaCV": "",
        "PotenciaKW": "",
        "Tension_freno_apertura": "",
        "Tension_freno_mantenimiento": "",
        "Pot": _leer_numero(seccion, "Pot", linea_potencia, r"Pot:\s*([\d.,]+)", debug),
        "Freno_lento_apertura": "",
        "Freno_lento_mantenimiento": "",
        "Variador": _leer_regex(seccion, "Variador", linea_variador, r"Variador:\s*(\S+)", debug),
        "Modelo": _normalizar_modelo_variador(_leer_regex(seccion, "Modelo", linea_variador, r"Modelo:\s*(.*?)\s+_", debug)),
        "Talla": _leer_numero(seccion, "Talla", linea_variador, r"Talla:\s*([\d.,]+)", debug),
        "ED": _leer_numero(seccion, "ED", linea_variador, r"ED \(%\):\s*([\d.,]+)", debug),
        "F_Conm": _leer_numero(seccion, "F_Conm", linea_variador, r"F\.Conm:\s*([\d.,]+)", debug),
        "Consola_VF": _leer_check_en_linea(seccion, "Consola_VF", linea_parametro, debug, etiqueta="Consola VF"),
        "Consola_VF_txt": _leer_regex(
            seccion,
            "Consola_VF_txt",
            linea_parametro,
            r"Consola VF\s+(.*?)\s+Par(?:Ã¡|á|a)metro:",
            debug,
        ),
        "Parametro": _normalizar_parametro(_leer_regex(seccion, "Parametro", linea_parametro, r"Parámetro:\s*(\S+)", debug)),
        "Rpm": _leer_numero(seccion, "Rpm", linea_parametro, r"Rpm:\s*([\d.,]+)", debug),
        "Relacion": _leer_regex(seccion, "Relacion", linea_parametro, r"Relación:([^_]+)", debug).strip(),
        "Polea": _leer_numero(seccion, "Polea", linea_parametro, r"Polea:\s*([\d.,]+)", debug),
        "Encoder": _leer_check_en_linea(seccion, "Encoder", linea_encoder, debug, etiqueta="Encoder"),
        "Encoder_txt": _leer_regex(seccion, "Encoder_txt", linea_encoder, r"Encoder\s+(?!Protocolo\b)(\S+)", debug),
        "Protocolo": _leer_regex(seccion, "Protocolo", linea_encoder, r"Protocolo:\s*(?!Fasado)(\S+)", debug),
        "Fasado": _leer_numero(seccion, "Fasado", linea_encoder, r"Fasado\s*([\d.,]+)", debug),
        "N_Polos": _leer_numero(seccion, "N_Polos", linea_encoder, r"Polos:\s*(\d+)", debug),
        "Autotrafo_240_400": _leer_check_en_linea(seccion, "Autotrafo_240_400", linea_encoder, debug, etiqueta="Autotrafo"),
        "Cable_potencia": _leer_check_en_linea(seccion, "Cable_potencia", linea_cable_potencia, debug, etiqueta="Cable Potencia"),
        "Longitud_cable_potencia": _leer_numero(
            seccion, "Longitud_cable_potencia", linea_cable_potencia, r"Longitud Cable Potencia:\s*([\d.,]+)", debug
        ),
        "Micros": _leer_regex(seccion, "Micros", linea_cable_potencia, r"Micros:\s*(.*)", debug).strip(),
        "Cableado_accesorios": _leer_check_en_linea(
            seccion, "Cableado_accesorios", linea_cable_accesorios, debug, etiqueta="Cableado Accesorios"
        ),
        "Longitud_cable_accesorios": _leer_numero(
            seccion, "Longitud_cable_accesorios", linea_cable_accesorios, r"Longitud Cable Accesorios:\s*([\d.,]+)", debug
        ),
        "Conectores": _leer_check_en_linea(seccion, "Conectores", linea_cable_accesorios, debug, etiqueta="Conectores"),
    }

    potencia = re.search(r"Potencia:\s*([\d.,]+)\s*CV/\s*([\d.,]+)\s*Kw", linea_potencia)
    if potencia:
        data["PotenciaCV"] = _registrar(seccion, "PotenciaCV", potencia.group(1), linea_potencia, "Potencia a CV/ b Kw", debug)
        data["PotenciaKW"] = _registrar(seccion, "PotenciaKW", potencia.group(2), linea_potencia, "Potencia a CV/ b Kw", debug)

    tension_freno = re.search(r"(\d+)/(\d+)V", linea_potencia)
    if tension_freno:
        data["Tension_freno_apertura"] = _registrar(
            seccion, "Tension_freno_apertura", tension_freno.group(1), linea_potencia, "a/bV", debug
        )
        data["Tension_freno_mantenimiento"] = _registrar(
            seccion, "Tension_freno_mantenimiento", tension_freno.group(2), linea_potencia, "a/bV", debug
        )
    return data


def _extraer_traccion_hidraulica(
    lineas: list[str], debug: dict[str, dict[str, CampoLeido]]
) -> dict[str, str]:
    seccion = "Traccion_hidraulica"
    linea_hidraulica_1 = _linea_con(lineas, "Grupo Válvulas")
    linea_hidraulica_2 = _linea_con(lineas, "Tipo Arranque")
    return {
        "Fabricante_oleo": _leer_regex_sin_etiquetas(
            seccion,
            "Fabricante_oleo",
            linea_hidraulica_1,
            r"Fabricante:\s*(.*?)\s+Grupo Válvulas:",
            debug,
        ),
        "Grupo_valvulas": _leer_regex_sin_etiquetas(
            seccion,
            "Grupo_valvulas",
            linea_hidraulica_1,
            r"Grupo Válvulas:\s*(.*?)\s+Tensión Valvulas:",
            debug,
        ),
        "Tension_valvulas": _leer_numero(seccion, "Tension_valvulas", linea_hidraulica_1, r"Tensión Valvulas:\s*([\d.,]+)", debug),
        "Potencia_oleo": _leer_numero(seccion, "Potencia_oleo", linea_hidraulica_2, r"Potencia:\s*([\d.,]+)", debug),
        "Tipo_arranque": _leer_regex(seccion, "Tipo_arranque", linea_hidraulica_2, r"Tipo Arranque:\s*(.*?)\s+Suministrar", debug),
        "Suministrar_softstarter": _leer_check_en_linea(
            seccion, "Suministrar_softstarter", linea_hidraulica_2, debug, etiqueta="Suministrar softstarter"
        ),
    }


def _extraer_puertas(
    lineas: list[str], embarque: int, debug: dict[str, dict[str, CampoLeido]]
) -> dict[str, str]:
    indice = 0 if embarque == 1 else 1
    seccion = f"Puertas_cabina_embarque_{embarque}"

    fabricante_linea = _linea_con(lineas, "Fabricante: FERMATOR")
    tipo_linea = _linea_con(lineas, "Tipo: V")
    mano_linea = _linea_con(lineas, "Mano:")
    circuito_linea = _linea_con(lineas, "Circuito:")
    tension_linea = _linea_con(lineas, "Tension:")
    barreras_linea = _linea_con(lineas, "Barreras:")
    apertura_linea = _linea_con(lineas, "Apertura de emergencia:")
    leva_linea = _linea_con(lineas, "Leva eléctrica:")

    fabricante = _partes_dobles(fabricante_linea, r"Fabricante:\s*(\S+)")
    tipo = _partes_dobles(tipo_linea, r"Tipo:\s*(\S+)")
    mano = _partes_dobles(mano_linea, r"Mano:\s*(\S+)")
    circuito = _partes_dobles(circuito_linea, r"Circuito:\s*(.*?)(?=\s+Circuito:|$)")
    tension = _partes_dobles(tension_linea, r"Tensi[oó]n:\s*(\d+)|Tension:\s*(\d+)")
    barreras = _partes_dobles(barreras_linea, r"Barreras:\s*(\S+)")

    sufijo = "op1" if embarque == 1 else "op2"
    barrera_key = "Barreras_Op1" if embarque == 1 else "Barreras_op2"
    barrera_txt_key = "Barreras_Op1_txt" if embarque == 1 else "Barreras_Op2_txt"
    barrera_txt = _leer_valor_doble(
        seccion,
        barrera_txt_key,
        indice,
        barreras,
        barreras_linea,
        debug,
    )
    barrera_check = (
        _registrar(seccion, barrera_key, "Si", barreras_linea, f"valor asociado {barrera_txt_key}", debug)
        if barrera_txt
        else ("" if embarque == 2 else _leer_check_en_linea(seccion, barrera_key, barreras_linea, debug, etiqueta="Barreras"))
    )
    return {
        f"Fabricante_{sufijo}": _registrar_valor(seccion, f"Fabricante_{sufijo}", indice, fabricante, fabricante_linea, "Fabricante", debug),
        f"Tipo_{sufijo}": _normalizar_tipo_puerta(
            _registrar_valor(seccion, f"Tipo_{sufijo}", indice, tipo, tipo_linea, "Tipo", debug)
        ),
        f"Mano_{sufijo}": _registrar_valor(seccion, f"Mano_{sufijo}", indice, mano, mano_linea, "Mano", debug),
        f"Circuito_{sufijo}": _registrar_valor(seccion, f"Circuito_{sufijo}", indice, circuito, circuito_linea, "Circuito", debug),
        f"Tension_{sufijo}": _registrar_valor(seccion, f"Tension_{sufijo}", indice, tension, tension_linea, "Tension", debug),
        barrera_key: barrera_check,
        barrera_txt_key: barrera_txt,
        f"Apertura_emergencia_{sufijo}": _leer_check_en_linea(seccion, f"Apertura_emergencia_{sufijo}", apertura_linea, debug, etiqueta="Apertura"),
        f"Apertura_emergencia_{sufijo}_txt": "",
        f"Leva_electrica_{sufijo}": _leer_check_en_linea(seccion, f"Leva_electrica_{sufijo}", leva_linea, debug, etiqueta="Leva"),
        f"Leva_electrica_{sufijo}_txt": "",
    }


def _leer_regex(
    seccion: str,
    campo: str,
    linea: str,
    patron: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    match = re.search(patron, linea)
    if not match:
        return ""
    valor = next((grupo for grupo in match.groups() if grupo is not None), "").strip()
    if not valor:
        return ""
    return _registrar(seccion, campo, valor, linea, patron, debug)


def _leer_regex_sin_etiquetas(
    seccion: str,
    campo: str,
    linea: str,
    patron: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    valor = _leer_regex(seccion, campo, linea, patron, debug)
    if valor and re.search(r"[A-Za-z0-9]", valor):
        return valor
    debug.get(seccion, {}).pop(campo, None)
    return ""


def _leer_numero(
    seccion: str,
    campo: str,
    linea: str,
    patron: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    valor = _leer_regex(seccion, campo, linea, patron, debug)
    if not valor:
        return ""
    return valor


def _leer_check_en_linea(
    seccion: str,
    campo: str,
    linea: str,
    debug: dict[str, dict[str, CampoLeido]],
    etiqueta: str | None = None,
) -> str:
    if not linea:
        return ""
    etiqueta = etiqueta or campo
    indice = linea.find(etiqueta)
    if indice < 0:
        marca_visual = _leer_check_por_imagen(linea, etiqueta)
        if marca_visual:
            valor, ratio = marca_visual
            return _registrar(
                seccion, campo, valor, linea, f"check visual ratio={ratio:.4f} antes de {etiqueta}", debug
            )
        return ""
    ventana = linea[max(0, indice - 6) : indice]
    if re.search(r"(v\]|w\]|\[Y\]|vi|\bY\])", ventana):
        return _registrar(seccion, campo, "Si", linea, f"check antes de {etiqueta}", debug)
    if re.search(r"(\bO\b|L\]|\[\]|LJ)", ventana):
        return _registrar(seccion, campo, "No", linea, f"check antes de {etiqueta}", debug)
    check_fusionado = _leer_check_fusionado(linea, etiqueta)
    if check_fusionado:
        return _registrar(seccion, campo, check_fusionado, linea, f"check fusionado con {etiqueta}", debug)
    marca_visual = _leer_check_por_imagen(linea, etiqueta)
    if marca_visual:
        valor, ratio = marca_visual
        return _registrar(
            seccion, campo, valor, linea, f"check visual ratio={ratio:.4f} antes de {etiqueta}", debug
        )
    return ""


def _leer_check_fusionado(linea: str, etiqueta: str) -> str:
    etiqueta_normalizada = _normalizar_token(etiqueta)
    for palabra in re.findall(r"\S+", linea):
        palabra_normalizada = _normalizar_token(palabra)
        if palabra_normalizada != etiqueta_normalizada:
            continue
        if palabra.startswith(("[", "|")):
            return "Si"
    return ""


def _leer_check_con_valor(
    seccion: str,
    campo: str,
    linea: str,
    patron_valor: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    valor = _leer_regex(seccion, campo, linea, patron_valor, debug)
    if valor:
        return valor
    check = _leer_check_en_linea(seccion, campo, linea, debug, etiqueta=campo)
    return check


def _leer_check_con_valor_doble(
    seccion: str,
    campo: str,
    indice: int,
    valores: list[str],
    linea: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    valor = _valor(indice, valores)
    if valor:
        return _registrar(seccion, campo, valor, linea, "check_con_valor doble", debug)
    return ""


def _leer_valor_doble(
    seccion: str,
    campo: str,
    indice: int,
    valores: list[str],
    linea: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    valor = _valor(indice, valores)
    if valor:
        return _registrar(seccion, campo, valor, linea, "valor doble", debug)
    return ""


def _leer_check_por_imagen(linea: str, etiqueta: str) -> tuple[str, float] | None:
    imagen = _IMAGEN_CONTEXT.get()
    if imagen is None:
        return None
    linea_ocr = next((item for item in _LINEAS_OCR_CONTEXT.get() if item.get("text") == linea), None)
    if not linea_ocr:
        return None
    palabras = linea_ocr.get("words", [])
    indice_alias = _indice_inicio_alias(palabras, etiqueta)
    if indice_alias is None:
        return None

    palabra_alias = palabras[indice_alias]
    marcador = _marcador_geometrico_izquierda(palabras, palabra_alias)
    if marcador in CHECK_MARCADO_GEOMETRICO:
        return "Si", 1.0
    if marcador in CHECK_VACIO_GEOMETRICO:
        return "No", 0.0

    x0 = max(0, palabra_alias["x0"] - 90)
    x1 = max(0, palabra_alias["x0"] - 5)
    y0 = max(0, palabra_alias["y0"] - 12)
    y1 = min(imagen.height, palabra_alias["y1"] + 12)
    if x1 <= x0 or y1 <= y0:
        return None

    histograma = imagen.crop((x0, y0, x1, y1)).histogram()
    total_pixeles = sum(histograma)
    ratio_oscuros = sum(histograma[:170]) / total_pixeles
    if ratio_oscuros >= 0.04:
        return "No", ratio_oscuros
    return None


def _marcador_geometrico_izquierda(palabras: list[dict[str, Any]], palabra_alias: dict[str, Any]) -> str:
    candidatos = [
        palabra
        for palabra in palabras
        if palabra.get("x1", 0) <= palabra_alias.get("x0", 0)
        and palabra_alias.get("x0", 0) - palabra.get("x1", 0) <= 80
    ]
    if not candidatos:
        return ""
    return max(candidatos, key=lambda palabra: palabra.get("x1", 0)).get("text", "")


def _indice_inicio_alias(palabras: list[dict[str, Any]], etiqueta: str) -> int | None:
    tokens_alias = [_normalizar_token(token) for token in re.findall(r"\w+", etiqueta)]
    tokens_alias = [token for token in tokens_alias if token]
    if not tokens_alias:
        return None
    tokens_ocr = [_normalizar_token(palabra.get("text", "")) for palabra in palabras]
    for indice in range(0, len(tokens_ocr) - len(tokens_alias) + 1):
        if tokens_ocr[indice : indice + len(tokens_alias)] == tokens_alias:
            return indice
    return None


def _normalizar_token(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return re.sub(r"\W+", "", texto).lower()


def _registrar_valor(
    seccion: str,
    campo: str,
    indice: int,
    valores: list[str],
    linea: str,
    patron: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    valor = _valor(indice, valores)
    if not valor:
        return ""
    return _registrar(seccion, campo, valor, linea, patron, debug)


def _registrar(
    seccion: str,
    campo: str,
    valor: str,
    linea: str,
    patron: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    debug.setdefault(seccion, {})[campo] = CampoLeido(valor, "ocr_text", linea, patron)
    return valor


def _linea_con(lineas: list[str], texto: str) -> str:
    return next((linea for linea in lineas if texto in linea), "")


def _linea_anterior(lineas: list[str], linea: str) -> str:
    try:
        indice = lineas.index(linea)
    except ValueError:
        return ""
    return lineas[indice - 1] if indice > 0 else ""


def _partes_dobles(linea: str, patron: str) -> list[str]:
    valores: list[str] = []
    for match in re.finditer(patron, linea):
        valor = next((grupo for grupo in match.groups() if grupo is not None), "")
        valores.append(valor.strip())
    return valores


def _valor(indice: int, valores: list[str]) -> str:
    return valores[indice] if indice < len(valores) else ""


def _normalizar_ocr_es(valor: str) -> str:
    return valor.replace("ESPANA", "ESPAÑA").replace("ESPANOL", "ESPAÑOL")


def _normalizar_modelo_variador(valor: str) -> str:
    return valor


def _normalizar_parametro(valor: str) -> str:
    return valor


def _normalizar_tipo_puerta(valor: str) -> str:
    return valor
