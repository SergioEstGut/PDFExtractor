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
    nombres_campos_seccion,
    normalizar_checks_con_texto_asociado,
    normalizar_valor_campo,
)

CHECK_MARCADO = ["[v]", "v]", "yv]", "y]", "Vv", "IS]", "IN"]
CHECK_VACIO = ["O", "0", "L]", "LJ", "C1", "Ll", "[1", "1]", "JOR"]
CHECK_MARCADO_GEOMETRICO = CHECK_MARCADO + ["y"]
CHECK_VACIO_GEOMETRICO = CHECK_VACIO + ["Ol"]
_LINEAS_OCR_CONTEXT: ContextVar[list[dict[str, Any]]] = ContextVar("lineas_ocr_context", default=[])
_IMAGEN_CONTEXT: ContextVar[Image.Image | None] = ContextVar("imagen_context", default=None)


@dataclass(frozen=True)
class CampoLeido:
    valor: str
    fuente: str
    linea: str
    patron: str


def extraer_foso_opciones_desde_ocr(
    ocr_debug: dict[str, Any], bytes_imagen: bytes | None = None
) -> dict[str, dict[str, str]]:
    return extraer_foso_opciones_desde_ocr_con_debug(ocr_debug, bytes_imagen=bytes_imagen)["data"]


def extraer_foso_opciones_desde_ocr_con_debug(
    ocr_debug: dict[str, Any], bytes_imagen: bytes | None = None
) -> dict[str, Any]:
    lineas_ocr = ocr_debug["ocr"]["lines"]
    lineas = [linea["text"] for linea in lineas_ocr]
    debug: dict[str, dict[str, CampoLeido]] = {}
    imagen = Image.open(BytesIO(bytes_imagen)).convert("L") if bytes_imagen else None

    token = _LINEAS_OCR_CONTEXT.set(lineas_ocr)
    token_imagen = _IMAGEN_CONTEXT.set(imagen)
    try:
        data_cruda = {
            "Gestion_foso_huida_reducida": _extraer_gestion_foso(lineas, lineas_ocr, debug),
            "Opciones": _extraer_opciones(lineas, lineas_ocr, debug),
        }
    finally:
        _LINEAS_OCR_CONTEXT.reset(token)
        _IMAGEN_CONTEXT.reset(token_imagen)
    data = aplicar_contrato_salida(normalizar_checks_con_texto_asociado(data_cruda))
    return {"data": data, "debug": _normalizar_debug(debug)}


def _extraer_gestion_foso(
    lineas: list[str], lineas_ocr: list[dict[str, Any]], debug: dict[str, dict[str, CampoLeido]]
) -> dict[str, str]:
    seccion = "Gestion_foso_huida_reducida"
    data = _seccion_vacia(seccion)

    for campo, etiqueta in {
        "Foso_exencion_raloe": "Exención Raloe",
        "Foso_EN81_21": "EN81-21",
        "Foso_faldon_con_contacto": "Faldón con contacto",
        "Foso_faldon_retractil_leva": "Faldón retráctil",
        "Foso_tope_movil": "Tope móvil",
        "Foso_rearme_mecanico_biestable": "Rearme mecánico",
        "Foso_rearme_electrico_biestable": "Rearme eléctrico",
        "Huida_exencion_raloe": "Exención Raloe",
        "Huida_EN81_21": "EN81-21",
        "Huida_barandilla_con_contacto": "Barandilla con contacto",
        "Huida_tope_movil": "Tope Móvil",
        "Huida_rearme_electrico_biestable": "Rearme eléctrico biestable",
    }.items():
        linea = _linea_con(lineas, etiqueta)
        data[campo] = _leer_check_en_linea(
            seccion, campo, linea, debug, etiqueta=etiqueta, lineas_ocr=lineas_ocr
        )

    return data


def _extraer_opciones(
    lineas: list[str], lineas_ocr: list[dict[str, Any]], debug: dict[str, dict[str, CampoLeido]]
) -> dict[str, str]:
    seccion = "Opciones"
    data = _seccion_vacia(seccion)

    linea_resistencia = _linea_con(lineas, "Resistencia de Caldeo")
    data["Resistencia_de_caldeo"] = _leer_check_en_linea(
        seccion, "Resistencia_de_caldeo", linea_resistencia, debug, etiqueta="Resistencia de Caldeo"
    )
    data["Refrigerador_de_aceite"] = _leer_check_en_linea(
        seccion, "Refrigerador_de_aceite", linea_resistencia, debug, etiqueta="Refrigerador de Aceite"
    )
    data["Presostato_sobrc_na"] = _leer_check_en_linea(
        seccion, "Presostato_sobrc_na", linea_resistencia, debug, etiqueta="Presostato"
    )

    linea_limitador = _linea_con(lineas, "Limitador velocidad Cab")
    data["Limitador_velocidad_cab"] = _leer_regex(
        seccion, "Limitador_velocidad_cab", linea_limitador, r"Limitador velocidad Cab:\s*(.*?)\s+y", debug
    )
    data["Limitador_velocidad_cab_txt"] = data["Limitador_velocidad_cab"]
    data["Limitador_velocidad_cab"] = _si_si_hay_valor(data["Limitador_velocidad_cab_txt"])
    data["Limitador_posicion"] = _leer_regex(
        seccion, "Limitador_posicion", linea_limitador, r"osición:\s*(.*?)\s+bicación:", debug
    )
    data["Limitador_ubicacion"] = _leer_regex(
        seccion, "Limitador_ubicacion", linea_limitador, r"bicación:\s*(.*)$", debug
    )

    linea_accionamiento = _linea_con(lineas, "Accionamiento a dist Limitador")
    data["Accionamiento_a_dist_limitador"] = _leer_regex(
        seccion,
        "Accionamiento_a_dist_limitador",
        linea_accionamiento,
        r"Accionamiento a dist Limitador:\s*([\d.,]+\s*\w*)",
        debug,
    )
    data["Accionamiento_a_dist_limitador_txt"] = data["Accionamiento_a_dist_limitador"]
    data["Accionamiento_a_dist_limitador"] = _si_si_hay_valor(data["Accionamiento_a_dist_limitador_txt"])
    data["Cont_sobrevel_manual"] = _leer_check_en_linea(
        seccion, "Cont_sobrevel_manual", linea_accionamiento, debug, etiqueta="Cont Sobrevel Manual"
    )
    data["Cont_sobrevel_a_dist"] = _leer_check_en_linea(
        seccion, "Cont_sobrevel_a_dist", linea_accionamiento, debug, etiqueta="Cont Sobrevel a Dist"
    )
    data["Cont_sobrevel_a_dist_txt"] = ""

    linea_antideriva = _linea_con(lineas, "Sistema antideriva: CBL")
    data["Sistema_antideriva_CBL"] = _leer_check_en_linea(
        seccion, "Sistema_antideriva_CBL", linea_antideriva, debug, etiqueta="Sistema antideriva"
    )
    data["Sistema_antideriva_CBL_txt"] = ""

    linea_pesacargas = _linea_con(lineas, "Pesacargas Fabricante")
    data["Pesacargas_fabricante"] = _leer_regex(
        seccion, "Pesacargas_fabricante", linea_pesacargas, r"Fabricante:\s*(.*?)\s+Tipo:", debug
    )
    data["Tipo_pesacargas"] = _leer_regex(
        seccion, "Tipo_pesacargas", linea_pesacargas, r"Tipo:\s*(.*?)\s+Modelo:", debug
    )
    data["Modelo_pesacargas"] = _leer_regex(
        seccion, "Modelo_pesacargas", linea_pesacargas, r"Modelo:\s*(.*)$", debug
    )

    linea_distancia = _linea_con(lineas, "Distancia pesacargas-maniobra")
    data["Distancia_pesacargas_maniobra"] = _leer_regex(
        seccion,
        "Distancia_pesacargas_maniobra",
        linea_distancia,
        r"Distancia pesacargas-maniobra:\s*([\d.,]+\s*\w*)",
        debug,
    )
    data["Completo"] = _leer_check_en_linea(seccion, "Completo", linea_distancia, debug, etiqueta="Completo")
    data["Luz_emergencia_cabina"] = _leer_regex(
        seccion, "Luz_emergencia_cabina", linea_distancia, r"Luz emergencia cabina:\s*(.*)$", debug
    )

    linea_rescate = _linea_con(lineas, "Rescate:")
    data["Rescate"] = _leer_regex(seccion, "Rescate", linea_rescate, r"Rescate:\s*(.*?)\s+Pos", debug)
    data["Pos_caja_cunas"] = _leer_regex(
        seccion, "Pos_caja_cunas", linea_rescate, r"Pos\.Caja Cu\w+as:\s*(.*?)\s+Luz", debug
    )
    data["Luz_emergencia_cabina_3h"] = _leer_check_en_linea(
        seccion, "Luz_emergencia_cabina_3h", linea_rescate, debug, etiqueta="Luz emergencia cabina 3h"
    )

    linea_comunicacion = _linea_con(lineas, "Comunicación Suministro")
    data["Comunicacion_suministro"] = _leer_regex(
        seccion, "Comunicacion_suministro", linea_comunicacion, r"Comunicación Suministro:\s*(.*?)\s+Modelo:", debug
    )
    data["Modelo_comunicacion"] = _leer_regex(
        seccion, "Modelo_comunicacion", linea_comunicacion, r"Modelo:\s*(.*?)\s+Bucle", debug
    )
    data["Bucl_inductivo_sordos"] = _leer_check_en_linea(
        seccion, "Bucl_inductivo_sordos", linea_comunicacion, debug, etiqueta="Bucle inductivo"
    )

    linea_sintesis = _linea_con(lineas, "Síntesis Voz")
    data["Comunicacion_adicional"] = _leer_check_en_linea(
        seccion, "Comunicacion_adicional", linea_sintesis, debug, etiqueta="Comunicación Adicional"
    )
    data["Sintesis_voz"] = _leer_regex(
        seccion, "Sintesis_voz", linea_sintesis, r"Síntesis Voz:\s*(.*?)\s+Idioma:", debug
    )
    data["Idioma_voz"] = _leer_regex(seccion, "Idioma_voz", linea_sintesis, r"Idioma:\s*(.*?)\s*/?$", debug)

    linea_interfono = _linea_con(lineas, "Interfono Suministro")
    data["Interfono_suministro"] = _leer_regex(
        seccion, "Interfono_suministro", linea_interfono, r"Interfono Suministro:\s*(.*?)\s+GSM:", debug
    )
    data["GSM"] = _leer_check_en_linea(seccion, "GSM", linea_interfono, debug, etiqueta="GSM")
    data["Intercomunicadores_EN81_72"] = _leer_check_en_linea(
        seccion, "Intercomunicadores_EN81_72", linea_interfono, debug, etiqueta="Intercomunicadores"
    )

    _leer_checks_opciones_restantes(lineas, data, debug)
    _alinear_opciones_con_contrato(data)
    return data


def _leer_checks_opciones_restantes(
    lineas: list[str], data: dict[str, str], debug: dict[str, dict[str, CampoLeido]]
) -> None:
    seccion = "Opciones"
    checks = {
        "Renivelacion": "Renivelación",
        "Apertura_anticipada": "Apertura anticipada",
        "Luz_en_armario": "Luz en armario",
        "Socorro_electrico_en_maniobra": "Socorro Eléctrico en Maniobra",
        "Trampilla_techo_cabina": "Trampilla techo cabina",
        "Escalera_techo_con_contacto": "Escalera techo con contacto",
        "Socorro_electrico_en_botonera": "Socorro Eléctrico en Botonera",
        "Escalera_foso_con_contacto": "Escalera Foso con contacto",
        "Escalera_interior_cabina_con_contacto": "Escalera interior cabina",
        "Magnetotermicos_y_diferenciales": "Magnetotérmicos y Diferenciales",
        "Bloqueo_mecanico_protec": "Bloqueo mecanico Protec",
        "Stop_adicional_maquina": "Stop Adicional Máquina",
        "Gong_exteriores": "Gong exteriores",
        "Gong_cabina": "Gong cabina",
        "Test_de_freno": "Test de freno",
        "Embalaje_fitosanitario": "Embalaje Fitosanitario",
        "Rescate_autom_hidraulicos": "Rescate Autom",
        "Modulo_ARM": "Módulo ARM",
        "Botonera_revision_aerea_especial": "Botonera Revisión",
        "Rescate_manual_hidraulicos": "Rescate Manual",
        "Modulo_DCI": "Módulo DCI",
        "Doble_rele_control_de_freno": "Doble Relé Control",
        "Semaforos_MCH": "Semáforos MCH",
        "Cableado_CCTV": "Cableado CCTV",
        "Luz_emergencia_foso_3h": "Luz emergencia foso 3h",
        "Centrado_coche_MCH": "Centrado coche",
        "Ventilacion_cabina": "Ventilación Cabina",
        "Sistema_regenerativo": "Sistema regenerativo",
        "BMS": "BMS",
        "Suministrar_mandos_MCH_cant": "Suministrar Mandos MCH",
        "Suministrar_soporteria_CS": "Suministrar soporteria CS",
    }
    for campo, etiqueta in checks.items():
        linea = _linea_con(lineas, etiqueta)
        data[campo] = _leer_check_en_linea(seccion, campo, linea, debug, etiqueta=etiqueta)

    linea_enchufes = _linea_con(lineas, "Enchufes:")
    data["Enchufes"] = _leer_regex(seccion, "Enchufes", linea_enchufes, r"Enchufes:\s*(\S+)", debug)
    data["Distancia_a_maniobra"] = _leer_regex(
        seccion, "Distancia_a_maniobra", linea_enchufes, r"Distancia a Maniobra\s*([\d.,]+\s*\w*)", debug
    )
    data["Ventilacion_maq_tipo"] = _leer_check_con_valor(
        seccion,
        "Ventilacion_maq_tipo",
        linea_enchufes,
        r"Ventilaci??n M??q\.Tipo:\s*(.*)$",
        debug,
        etiqueta="Ventilaci??n M??q.Tipo",
        valor_si_alias_sin_marca="No",
    )

    linea_stop_foso = _linea_con(lineas, "Stop Adicional Foso")
    data["Stop_adicional_foso_cant"] = _leer_check_con_valor(
        seccion,
        "Stop_adicional_foso_cant",
        linea_stop_foso,
        r"Stop Adicional Foso Cant:\s*(\d+)",
        debug,
        etiqueta="Stop Adicional Foso Cant",
        valor_si_alias_sin_marca="No",
    )
    data["Stop_adicional_techo_cab_cant"] = _leer_check_con_valor(
        seccion,
        "Stop_adicional_techo_cab_cant",
        linea_stop_foso,
        r"Stop Adicional Techo Cab\. Cant:\s*(\d+)",
        debug,
        etiqueta="Stop Adicional Techo Cab. Cant",
        valor_si_alias_sin_marca="No",
    )
    linea_tope_extra = _linea_con(lineas, "Tope extra foso")
    data["Tope_extra_foso_1_contacto_cant"] = _leer_check_con_valor(
        seccion,
        "Tope_extra_foso_1_contacto_cant",
        linea_tope_extra,
        r"Tope extra foso 1 contacto Cant:\s*(\d+)",
        debug,
        etiqueta="Tope extra foso 1 contacto Cant",
        valor_si_alias_sin_marca="No",
    )
    linea_rosario = _linea_con(lineas, "Rosario")
    data["Rosario"] = _leer_regex(seccion, "Rosario", linea_rosario, r"Rosario\s*(.*?)\s+Cant:", debug)
    data["Cant_rosario"] = _leer_regex(seccion, "Cant_rosario", linea_rosario, r"Cant:\s*(\d+)", debug)
    data["Posicionamiento"] = _leer_regex(
        seccion, "Posicionamiento", linea_rosario, r"Posicionamiento\s*(.*)$", debug
    )
    linea_ventilacion_cabina = _linea_con(lineas, "VentilaciÃ³n Cabina") or _linea_con(lineas, "Ventilación Cabina")
    ventilacion_cabina_valor = _leer_regex(
        seccion,
        "Ventilacion_cabina",
        linea_ventilacion_cabina,
        r"Ventilaci(?:Ã³|ó)n Cabina:\s*(.*?)(?:\s+Cant\.|$)",
        debug,
    )
    data["Ventilacion_cabina"] = ventilacion_cabina_valor or _leer_check_en_linea(
        seccion,
        "Ventilacion_cabina",
        linea_ventilacion_cabina,
        debug,
        etiqueta="Ventilación Cabina" if "Ventilación Cabina" in linea_ventilacion_cabina else "VentilaciÃ³n Cabina",
    )


def _seccion_vacia(seccion: str) -> dict[str, str]:
    return {campo: "" for campo in nombres_campos_seccion(seccion)}


def _alinear_opciones_con_contrato(data: dict[str, str]) -> None:
    for campo in [
        "Limitador_velocidad_cab",
        "Accionamiento_a_dist_limitador",
        "Cont_sobrevel_a_dist",
        "Sistema_antideriva_CBL",
        "Limitador_vel_contrapeso",
        "Accionamiento_a_dist_limitador_contrapeso",
        "Cont_sobrevel_a_dist_contrapeso",
        "Sistema_antideriva_contrapeso_CBL",
        "Comunicacion_suministro",
        "Sintesis_voz",
        "Interfono_suministro",
        "GSM",
        "Renivelacion",
        "Apertura_anticipada",
        "Enchufes",
        "Ventilacion_maq_tipo",
        "Stop_adicional_foso_cant",
        "Stop_adicional_techo_cab_cant",
        "Tope_extra_foso_1_contacto_cant",
        "Rosario",
        "Cableado_CCTV",
        "Contactos_magneticos_pta_cab",
        "Ventilacion_cabina",
        "Sistema_regenerativo",
    ]:
        _separar_check_y_valor(data, campo)

    if "Idioma_voz" in data:
        data["Idioma_voz_1"] = data.pop("Idioma_voz")
        data.setdefault("Idioma_voz_2", "")


def _separar_check_y_valor(data: dict[str, str], campo: str) -> None:
    valor = data.get(campo, "")
    txt = f"{campo}_txt"
    if txt not in data:
        data[txt] = ""
    if valor not in {"", "Si", "No"}:
        data[txt] = valor
        data[campo] = "Si"


def _si_no(valor: bool) -> str:
    return "Si" if valor else "No"


def _si_si_hay_valor(valor: str) -> str:
    return "Si" if valor else ""


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


def _leer_check_con_valor(
    seccion: str,
    campo: str,
    linea: str,
    patron_valor: str,
    debug: dict[str, dict[str, CampoLeido]],
    etiqueta: str | None = None,
    valor_si_alias_sin_marca: str = "",
) -> str:
    valor = _leer_regex(seccion, campo, linea, patron_valor, debug)
    if valor:
        return valor
    etiqueta_check = etiqueta or campo
    valor_check = _leer_check_en_linea(seccion, campo, linea, debug, etiqueta=etiqueta_check)
    if valor_check:
        return valor_check
    if valor_si_alias_sin_marca and linea and etiqueta_check in linea:
        return _registrar(
            seccion,
            campo,
            valor_si_alias_sin_marca,
            linea,
            f"alias visto sin marca: {etiqueta_check}",
            debug,
        )
    return ""


def _leer_check_en_linea(
    seccion: str,
    campo: str,
    linea: str,
    debug: dict[str, dict[str, CampoLeido]],
    etiqueta: str,
    lineas_ocr: list[dict[str, Any]] | None = None,
) -> str:
    if not linea:
        return ""
    indice = linea.find(etiqueta)
    if indice < 0:
        return ""
    ventana = linea[max(0, indice - 12) : indice]
    if _contiene_marcador(ventana, CHECK_MARCADO):
        return _registrar(seccion, campo, "Si", linea, f"check antes de {etiqueta}", debug)
    if _contiene_marcador(ventana, CHECK_VACIO):
        return _registrar(seccion, campo, "No", linea, f"check antes de {etiqueta}", debug)
    marca_geometrica = _leer_marcador_por_geometria(linea, etiqueta, lineas_ocr)
    if marca_geometrica:
        valor, marcador = marca_geometrica
        return _registrar(
            seccion, campo, valor, linea, f"check geometrico {marcador} antes de {etiqueta}", debug
        )
    marca_visual = _leer_check_por_imagen(linea, etiqueta)
    if marca_visual:
        valor, ratio = marca_visual
        return _registrar(
            seccion, campo, valor, linea, f"check visual ratio={ratio:.4f} antes de {etiqueta}", debug
        )
    return ""


def _contiene_marcador(texto: str, marcadores: list[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(marcador)}(?!\w)", texto) for marcador in marcadores)


def _leer_marcador_por_geometria(
    linea: str, etiqueta: str, lineas_ocr: list[dict[str, Any]] | None
) -> tuple[str, str] | None:
    lineas_disponibles = lineas_ocr or _LINEAS_OCR_CONTEXT.get()
    linea_ocr = next((item for item in lineas_disponibles if item.get("text") == linea), None)
    if not linea_ocr:
        return None
    palabras = linea_ocr.get("words", [])
    indice_alias = _indice_inicio_alias(palabras, etiqueta)
    if indice_alias is None:
        return None

    palabra_alias = palabras[indice_alias]
    candidatos = [
        palabra
        for palabra in palabras
        if palabra.get("x1", 0) <= palabra_alias.get("x0", 0)
        and palabra_alias.get("x0", 0) - palabra.get("x1", 0) <= 80
    ]
    if not candidatos:
        return None
    marcador = max(candidatos, key=lambda palabra: palabra.get("x1", 0)).get("text", "")
    if marcador in CHECK_MARCADO_GEOMETRICO:
        return "Si", marcador
    if marcador in CHECK_VACIO_GEOMETRICO:
        return "No", marcador
    return None


def _leer_check_por_imagen(linea: str, etiqueta: str) -> tuple[str, float] | None:
    imagen = _IMAGEN_CONTEXT.get()
    if imagen is None:
        return None
    lineas_disponibles = _LINEAS_OCR_CONTEXT.get()
    linea_ocr = next((item for item in lineas_disponibles if item.get("text") == linea), None)
    if not linea_ocr:
        return None
    palabras = linea_ocr.get("words", [])
    indice_alias = _indice_inicio_alias(palabras, etiqueta)
    if indice_alias is None:
        return None

    palabra_alias = palabras[indice_alias]
    x0 = max(0, palabra_alias["x0"] - 90)
    x1 = max(0, palabra_alias["x0"] - 5)
    y0 = max(0, palabra_alias["y0"] - 12)
    y1 = min(imagen.height, palabra_alias["y1"] + 12)
    if x1 <= x0 or y1 <= y0:
        return None

    histograma = imagen.crop((x0, y0, x1, y1)).histogram()
    total_pixeles = sum(histograma)
    ratio_oscuros = sum(histograma[:170]) / total_pixeles
    if ratio_oscuros >= 0.08:
        return "Si", ratio_oscuros
    if ratio_oscuros >= 0.04:
        return "No", ratio_oscuros
    return None


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

