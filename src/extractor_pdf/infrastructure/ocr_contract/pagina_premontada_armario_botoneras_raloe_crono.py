from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from PIL import Image, ImageOps

from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import (
    aplicar_contrato_salida,
    nombres_campos_seccion,
    normalizar_checks_con_texto_asociado,
    normalizar_valor_campo,
)

CHECK_MARCADO = ["[v]", "v]", "yv]", "y]", "Vv", "IN", "w]", "[Y]", "[4]", "[vd]", "v|"]
CHECK_VACIO = ["O", "0", "[]", "[_]", "L]", "LJ", "C1", "Ll", "[1", "1]", "U", "|]", "[|"]


@dataclass(frozen=True)
class CampoLeido:
    valor: str
    fuente: str
    linea: str
    patron: str


def extraer_premontada_armario_botoneras_desde_ocr(
    ocr_debug: dict[str, Any], bytes_imagen: bytes | None = None
) -> dict[str, dict[str, str]]:
    return extraer_premontada_armario_botoneras_desde_ocr_con_debug(
        ocr_debug, bytes_imagen=bytes_imagen
    )["data"]


def extraer_premontada_armario_botoneras_desde_ocr_con_debug(
    ocr_debug: dict[str, Any], bytes_imagen: bytes | None = None
) -> dict[str, Any]:
    lineas = [linea["text"] for linea in ocr_debug["ocr"]["lines"]]
    debug: dict[str, dict[str, CampoLeido]] = {}
    tabla_premontada = _extraer_tabla_premontada_por_imagen(bytes_imagen, debug)
    data_cruda = {
        "Premontada": _extraer_premontada(lineas, tabla_premontada, debug),
        "Armario": _extraer_armario(lineas, debug),
        "Botonera_Exterior": _extraer_botonera_exterior(lineas, debug),
        "Botonera_Cabina": _extraer_botonera_cabina(lineas, debug),
    }
    data = aplicar_contrato_salida(normalizar_checks_con_texto_asociado(data_cruda))
    return {"data": data, "debug": _normalizar_debug(debug)}


def _extraer_premontada(
    lineas: list[str],
    tabla_premontada: dict[str, str],
    debug: dict[str, dict[str, CampoLeido]],
) -> dict[str, str]:
    seccion = "Premontada"
    data = _seccion_vacia(seccion)
    data.update(tabla_premontada)

    linea_bomberos = _linea_con(lineas, "Planta acceso bomberos")
    data["Planta_acceso_bomberos"] = _leer_regex(
        seccion,
        "Planta_acceso_bomberos",
        linea_bomberos,
        r"Planta acceso bomberos:\s*(.*?)\s+Planta acceso bomberos 2:",
        debug,
    )
    data["Planta_acceso_bomberos_2"] = _leer_regex(
        seccion, "Planta_acceso_bomberos_2", linea_bomberos, r"Planta acceso bomberos 2:\s*(\S+)", debug
    )
    data["Planta_principal"] = _leer_regex(
        seccion, "Planta_principal", _linea_con(lineas, "Planta Principal"), r"Planta Principal:\s*(\S+)", debug
    )

    for campo, etiqueta in {
        "Recorrido": "Recorrido",
        "Foso": "Foso",
        "Huida": "Huida",
        "Distancia_maniobra_motor": "Distancia maniobra motor",
        "Dist_maniobra_piso_mas_prox": "Dist. Maniobra-Piso",
        "Manguera_plana": "Manguera Plana",
        "Extra": "Extra",
        "P": "P",
        "Carga_nominal": "Carga Nominal",
    }.items():
        linea = _linea_con(lineas, "P:") if campo == "P" else _linea_con(lineas, etiqueta)
        data[campo] = _leer_valor_tras_etiqueta(seccion, campo, linea, etiqueta, debug)

    data["Distancia_niveles"] = ""

    linea_puertas = _linea_con(lineas, "Puertas Piso Precableadas")
    data["Puertas_piso_precableadas"] = _leer_check_en_linea(
        seccion, "Puertas_piso_precableadas", linea_puertas, "Puertas Piso Precableadas", debug
    )

    linea_doble = _linea_con(lineas, "Doble acceso")
    data["Doble_acceso_alternado"] = _leer_check_en_linea(
        seccion, "Doble_acceso_alternado", linea_doble, "Alternado", debug
    )
    data["Doble_acceso_simultaneo"] = _leer_check_en_linea(
        seccion, "Doble_acceso_simultaneo", linea_doble, "Simultaneo", debug
    )
    data["Doble_acceso_simultaneo_selectivo"] = _leer_check_en_linea(
        seccion, "Doble_acceso_simultaneo_selectivo", linea_doble, "Simultaneo Selectivo", debug
    )

    linea_cableado = _linea_con(lineas, "Cableado LSF")
    data["Cableado_LSF"] = _leer_check_en_linea(seccion, "Cableado_LSF", linea_cableado, "Cableado LSF", debug)
    data["Premontada_mas_larga"] = _leer_check_en_linea(
        seccion, "Premontada_mas_larga", _linea_con(lineas, "Premontada mas larga"), "Premontada mas larga", debug
    )

    linea_medidas = _linea_con(lineas, "Medidas Cabina")
    medidas = re.search(r"Medidas Cabina:\s*([\d.,]+)?\s*x\s*([\d.,]+)?", linea_medidas)
    if medidas:
        if medidas.group(1):
            data["Medidas_cabina_ancho"] = _registrar(
                seccion, "Medidas_cabina_ancho", medidas.group(1), linea_medidas, "Medidas Cabina ancho", debug
            )
        if medidas.group(2):
            data["Medidas_cabina_profundo"] = _registrar(
                seccion, "Medidas_cabina_profundo", medidas.group(2), linea_medidas, "Medidas Cabina profundo", debug
            )
    return data


def _extraer_armario(lineas: list[str], debug: dict[str, dict[str, CampoLeido]]) -> dict[str, str]:
    seccion = "Armario"
    data = _seccion_vacia(seccion)

    linea_planta = _linea_con(lineas, "Planta ubicacion armario")
    data["Planta_ubicacion_armario"] = _leer_regex_con_contenido(
        seccion, "Planta_ubicacion_armario", linea_planta, r"Planta ubicaci[oó]n armario:\s*(.*?)\s+Acabado:", debug
    )
    data["Acabado"] = _leer_regex(seccion, "Acabado", linea_planta, r"Acabado:\s*(.*)$", debug)

    for campo, etiqueta in {
        "Una_pieza_integral": "1 pieza",
        "Tapa_trasera_para_zocalo": "Tapa trasera",
        "Dos_piezas": "2 piezas",
        "Control_en_rellano": "Control en rellano",
        "Control_en_marco_puerta": "Control en marco puerta",
    }.items():
        linea = _linea_con(lineas, etiqueta)
        data[campo] = _leer_check_en_linea(seccion, campo, linea, etiqueta, debug)

    for campo, etiqueta in {
        "Longitud_cables_interconexion_armarios": "Longitud cables interconexion armarios",
        "Longitud_cables_potencia_modulo_de_piso": "Longitud cables potencia",
        "Apertura_marco": "Apertura marco",
    }.items():
        linea = _linea_con(lineas, etiqueta)
        data[campo] = _leer_valor_tras_etiqueta(seccion, campo, linea, etiqueta, debug)

    linea_talla_cabina = _linea_con(lineas, "Talla Cabina")
    linea_talla_hueco = _linea_con(lineas, "Talla Hueco")
    for indice in range(1, 6):
        data[f"Talla_cabina_{indice}"] = _leer_check_en_linea(
            seccion, f"Talla_cabina_{indice}", linea_talla_cabina, f"Talla {indice}", debug
        )
        data[f"Talla_hueco_{indice}"] = _leer_check_en_linea(
            seccion, f"Talla_hueco_{indice}", linea_talla_hueco, f"Talla {indice}", debug
        )
    return data


def _extraer_botonera_cabina(lineas: list[str], debug: dict[str, dict[str, CampoLeido]]) -> dict[str, str]:
    seccion = "Botonera_Cabina"
    data = _seccion_vacia(seccion)

    linea_fabricante = _linea_con_despues(lineas, "Botonera Cabina", "Botonera fabricante")
    data["Botonera_cab_fabricante"] = _leer_regex(
        seccion, "Botonera_cab_fabricante", linea_fabricante, r"Botonera fabricante\s+(\S+)", debug
    )
    data["Modelo"] = _leer_regex(seccion, "Modelo", linea_fabricante, r"Modelo:\s*(\S+)", debug)

    linea_pulsador = _linea_con(lineas, "Pulsador fabricante")
    data["Pulsador_fabricante"] = _leer_regex(
        seccion, "Pulsador_fabricante", linea_pulsador, r"Pulsador fabricante\s+(\S+)", debug
    )
    data["Color_pulsador"] = _leer_regex(
        seccion, "Color_pulsador", linea_pulsador, r"Color Pulsador:\s*(.*)$", debug
    )

    for campo, etiqueta in {
        "Doble_botonera_en_cabina": "Doble botonera en cabina",
        "Comunicacion_en_2a_botonera": "Comunicacion en 2",
        "Enviaran_botonera_para_cablear_cab": "Enviaran botonera para cablear",
        "Pulsador_abrir_puertas": "Pulsador abrir puertas",
        "AP_iluminado_en_cierre": "AP iluminado en cierre",
        "Pulsador_cerrar_puertas": "Pulsador cerrar puertas",
        "Luminoso_exceso_carga": "Luminoso exceso carga",
        "Luminoso_prohibido_fumar": "Luminoso prohibido fumar",
        "Llavin_pulsador_cab": "Llavin Pulsador",
        "Llavin_extra_cab": "Llavin Extra",
        "Pulsador_de_stop_en_cabina": "Pulsador de stop en cabina",
        "Llavin_VIP_bomberos": "Llavin VIP",
        "Placa_caract_retroiluminada": "Placa Caract",
        "Reg_acustico_cabina_RAP": "Reg. acustico cabina",
    }.items():
        linea = _linea_con(lineas, etiqueta)
        data[campo] = _leer_check_en_linea(seccion, campo, linea, etiqueta, debug)

    linea_llavin = _linea_con(lineas, "Llavin Pulsador Cantidad")
    data["Llavin_pulsador_cab_cant"] = _leer_regex(
        seccion, "Llavin_pulsador_cab_cant", linea_llavin, r"Cantidad:\s*(\d+)", debug
    )
    linea_llavin_extra = _linea_con(lineas, "Llavin Extra Funcion")
    data["Llavin_extra_cab_Funcion"] = _leer_regex(
        seccion, "Llavin_extra_cab_Funcion", linea_llavin_extra, r"Funcion:\s*(.*)$", debug
    )

    linea_alarma = _linea_con(lineas, "Pulsador alarma")
    data["Pulsador_alarma"] = _leer_texto_despues_de_check_con_valor(
        seccion, "Pulsador_alarma", linea_alarma, "Pulsador alarma", debug
    )

    linea_display_cabina = _linea_con(lineas, "Display Cabina")
    data["Display_cabina"] = _leer_texto_despues_de_check_con_valor(
        seccion, "Display_cabina", linea_display_cabina, "Display Cabina", debug
    )

    data["Secuencia"] = _leer_regex(
        seccion, "Secuencia", _linea_con(lineas, "Secuencia:"), r"Secuencia:\s*(.*)$", debug
    )
    data["Texto_display"] = _leer_regex(
        seccion, "Texto_display", _linea_con(lineas, "Texto:"), r"Texto:\s*(.*)$", debug
    )
    data["Orientacion"] = _leer_regex(
        seccion, "Orientacion", _linea_con(lineas, "Orientacion:"), r"Orientaci[oó]n:\s*(\S+)", debug
    )
    return data


def _extraer_botonera_exterior(lineas: list[str], debug: dict[str, dict[str, CampoLeido]]) -> dict[str, str]:
    seccion = "Botonera_Exterior"
    data = _seccion_vacia(seccion)
    lineas_ext = _lineas_despues(lineas, "Botonera Exterior")

    linea_fabricante = _linea_con(lineas_ext, "Botonera fabricante")
    data["Botonera_ext_fabricante"] = _leer_regex(
        seccion, "Botonera_ext_fabricante", linea_fabricante, r"Botonera fabricante\s+(\S+)", debug
    )

    for campo, etiqueta in {
        "Enviaran_botoneras_para_cablear_ext": "Enviaran botoneras para cablear",
        "Botoneras_ubicadas_en_marco": "Marco",
        "Botoneras_ubicadas_en_pared": "Pared",
        "Flechas_direccion": "Flechas direccion",
        "Flechas_direccion_dintel": "Dintel",
        "Flechas_direccion_botonera": "Botonera",
        "Flechas_predirecc": "Flechas predirecc",
        "Flechas_predirecc_exterior": "Exterior",
        "Flechas_predirecc_embocadura_cab": "Embocadura cab",
        "Esta": "Esta",
        "Ocupado": "Ocupado",
        "Pta_abierta": "Pta abierta",
        "Prohibido_paso": "Prohibido paso",
        "Llavin_pulsador_ext": "Llavin Pulsador",
        "Llavin_extra_ext": "Llavin Extra",
        "Reg_acustico_pisos_RAP": "Reg. acustico pisos",
    }.items():
        linea = (
            _linea_con_alias_mas_temprano(lineas_ext, etiqueta)
            if campo == "Llavin_pulsador_ext"
            else _linea_con(lineas_ext, etiqueta)
        )
        data[campo] = _leer_check_en_linea(seccion, campo, linea, etiqueta, debug)

    data["Reg_ext"] = _leer_regex(seccion, "Reg_ext", _linea_con(lineas_ext, "Reg.ext"), r"Reg\.ext\.:\s*([\d.,]+)", debug)
    data["Prohibido_paso_cant"] = _leer_regex(
        seccion, "Prohibido_paso_cant", _linea_con(lineas_ext, "Prohibido paso Cant"), r"Cant:\s*(\d+)", debug
    )
    data["Llavin_pulsador_ext_cant"] = _leer_regex(
        seccion, "Llavin_pulsador_ext_cant", _linea_con(lineas_ext, "Llavin Pulsador Cant"), r"Cant\s*(\d+)", debug
    )
    linea_llavin_extra = _linea_con(lineas_ext, "Llavin Extra Cant")
    data["Llavin_extra_ext_cant"] = _leer_regex(
        seccion, "Llavin_extra_ext_cant", linea_llavin_extra, r"Cant:\s*(\d+)(?=\s|$)", debug
    )
    data["Llavin_extra_ext_funcion"] = _leer_regex(
        seccion, "Llavin_extra_ext_funcion", _linea_con(lineas_ext, "Funcion:"), r"Funcion:\s*(.*)$", debug
    )

    linea_display_e1 = _linea_con(lineas_ext, "Display Ext 1")
    data["Display_ext_E1"] = _leer_texto_despues_de_check_con_valor(
        seccion, "Display_ext_E1", linea_display_e1, "Display Ext 1", debug, hasta=r"\s+Cant:"
    )
    data["Display_ext_E1_cant"] = _leer_regex(
        seccion, "Display_ext_E1_cant", linea_display_e1, r"Cant:\s*_?(\d+)(?=\s|$)", debug
    )

    linea_display_e2 = _linea_con(lineas_ext, "Display Ext 2")
    data["Display_ext_E2"] = _leer_texto_despues_de_check_con_valor(
        seccion, "Display_ext_E2", linea_display_e2, "Display Ext 2", debug, hasta=r"\s+Cant:"
    )
    data["Display_ext_E2_cant"] = _leer_regex(
        seccion, "Display_ext_E2_cant", linea_display_e2, r"Cant:\s*_?(\d+)(?=\s|$)", debug
    )
    return data


def _seccion_vacia(seccion: str) -> dict[str, str]:
    return {campo: "" for campo in nombres_campos_seccion(seccion)}


def _extraer_tabla_premontada_por_imagen(
    bytes_imagen: bytes | None,
    debug: dict[str, dict[str, CampoLeido]],
) -> dict[str, str]:
    if not bytes_imagen:
        return {}

    try:
        import cv2
        import numpy as np
        import pytesseract
    except ImportError:
        return {}

    imagen = Image.open(BytesIO(bytes_imagen)).convert("L")
    ancho, alto = imagen.size
    escala_x = ancho / 1653
    escala_y = alto / 2337
    crop_box = (
        int(40 * escala_x),
        int(430 * escala_y),
        int(760 * escala_x),
        int(1030 * escala_y),
    )
    crop = imagen.crop(crop_box)
    array = np.array(crop)
    binaria = cv2.threshold(array, 180, 255, cv2.THRESH_BINARY_INV)[1]

    horizontales = _posiciones_lineas_tabla(cv2, binaria, horizontal=True)
    verticales = _posiciones_lineas_tabla(cv2, binaria, horizontal=False)
    horizontales_izq = [pos for pos in horizontales if _linea_horizontal_de_tabla(pos, binaria, cv2)]
    verticales_izq = [pos for pos in verticales if 30 <= pos <= 470]

    if len(horizontales_izq) < 3 or len(verticales_izq) < 5:
        return {}

    y_filas = horizontales_izq
    x_columnas = verticales_izq[:9]
    if len(x_columnas) < 9:
        return {}

    columnas = {
        "Piso_E1": 0,
        "Piso_E2": 1,
        "Acceso_E1": 2,
        "Acceso_E2": 3,
        "Orient_E1": 6,
        "Orient_E2": 7,
    }
    valores: dict[str, list[str]] = {campo: [] for campo in columnas}

    for indice_fila in range(len(y_filas) - 1):
        fila: dict[str, str] = {}
        for campo, indice_columna in columnas.items():
            whitelist = _whitelist_columna_tabla(campo)
            texto = _ocr_celda_tabla(
                pytesseract,
                crop,
                (
                    x_columnas[indice_columna] + 4,
                    y_filas[indice_fila] + 4,
                    x_columnas[indice_columna + 1] - 4,
                    y_filas[indice_fila + 1] - 4,
                ),
                whitelist,
            )
            fila[campo] = _normalizar_celda_tabla(texto)

        if not any(valor and valor != "-" for valor in fila.values()):
            continue
        for campo in columnas:
            valores[campo].append(fila[campo] or "-")

    resultado: dict[str, str] = {}
    for campo, celdas in valores.items():
        celdas = _recortar_celdas_finales_vacias(celdas)
        if not celdas or not _columna_tabla_confiable(campo, celdas):
            continue
        resultado[campo] = _registrar(
            "Premontada",
            campo,
            ",".join(celdas),
            "tabla premontada recortada por OpenCV",
            "ocr por celda",
            debug,
        )
    return resultado


def _columna_tabla_confiable(campo: str, celdas: list[str]) -> bool:
    if campo.startswith("Acceso"):
        return "-" not in celdas
    if campo.startswith("Orient"):
        return any(celda in {"V", "H"} for celda in celdas) and all(celda in {"V", "H", "-"} for celda in celdas)
    if campo.startswith("Piso"):
        return all(re.fullmatch(r"[A-Za-z0-9-]+", celda) for celda in celdas)
    return True


def _whitelist_columna_tabla(campo: str) -> str:
    if campo.startswith("Acceso"):
        return "0123456789-"
    if campo.startswith("Orient"):
        return "VH"
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"


def _posiciones_lineas_tabla(cv2: Any, binaria: Any, horizontal: bool) -> list[int]:
    if horizontal:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 1))
        minimo_largo = 100
    else:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 35))
        minimo_largo = 100

    lineas = cv2.dilate(cv2.erode(binaria, kernel, iterations=1), kernel, iterations=1)
    contornos, _ = cv2.findContours(lineas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    posiciones: list[int] = []
    for contorno in contornos:
        x, y, ancho, alto = cv2.boundingRect(contorno)
        if horizontal and ancho >= minimo_largo:
            posiciones.append(y + alto // 2)
        if not horizontal and alto >= minimo_largo:
            posiciones.append(x + ancho // 2)
    return sorted(_agrupar_posiciones(posiciones))


def _linea_horizontal_de_tabla(posicion_y: int, binaria: Any, cv2: Any) -> bool:
    franja = binaria[max(0, posicion_y - 2) : posicion_y + 3, :]
    contornos, _ = cv2.findContours(franja, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return any(cv2.boundingRect(contorno)[2] >= 350 for contorno in contornos)


def _agrupar_posiciones(posiciones: list[int], tolerancia: int = 3) -> list[int]:
    grupos: list[list[int]] = []
    for posicion in sorted(posiciones):
        if not grupos or abs(grupos[-1][-1] - posicion) > tolerancia:
            grupos.append([posicion])
        else:
            grupos[-1].append(posicion)
    return [round(sum(grupo) / len(grupo)) for grupo in grupos]


def _ocr_celda_tabla(pytesseract: Any, imagen: Image.Image, box: tuple[int, int, int, int], whitelist: str) -> str:
    if box[2] <= box[0] or box[3] <= box[1]:
        return ""
    celda = imagen.crop(box)
    celda = ImageOps.expand(celda, border=8, fill=255)
    celda = celda.resize((celda.width * 4, celda.height * 4), Image.Resampling.LANCZOS)
    return pytesseract.image_to_string(
        celda,
        lang="eng",
        config=f"--psm 10 -c tessedit_char_whitelist={whitelist}",
    ).strip()


def _normalizar_celda_tabla(texto: str) -> str:
    texto = texto.strip().replace("—", "-").replace("_", "")
    texto = re.sub(r"[^A-Za-z0-9-]", "", texto)
    return texto


def _recortar_celdas_finales_vacias(celdas: list[str]) -> list[str]:
    resultado = list(celdas)
    while resultado and resultado[-1] == "-":
        resultado.pop()
    return resultado


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


def _leer_distancias_niveles(lineas: list[str], debug: dict[str, dict[str, CampoLeido]]) -> str:
    seccion = "Premontada"
    valores: list[str] = []
    for linea in lineas:
        if _contiene(linea, "Recorrido"):
            break
        for valor in re.findall(r"\b\d+[.,]\d{3}\b", linea):
            valores.append(valor)
    if not valores:
        return ""
    return _registrar(seccion, "Distancia_niveles", ",".join(valores), "\n".join(lineas), "distancias antes de Recorrido", debug)


def _leer_valor_tras_etiqueta(
    seccion: str,
    campo: str,
    linea: str,
    etiqueta: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    if not linea:
        return ""
    etiqueta_patron = re.escape(etiqueta).replace("\\ ", r"\s+")
    valor = _leer_regex(seccion, campo, linea, rf"{etiqueta_patron}\.?:\s*([\d.,]+\s*\S*)", debug)
    if valor:
        return valor
    return _leer_regex(seccion, campo, linea, rf"{etiqueta_patron}\.?.*?([\d.,]+\s*\S*)", debug)


def _leer_texto_despues_de_check_con_valor(
    seccion: str,
    campo: str,
    linea: str,
    etiqueta: str,
    debug: dict[str, dict[str, CampoLeido]],
    hasta: str = r"$",
) -> str:
    if not linea:
        return ""
    check = _leer_check_en_linea(seccion, campo, linea, etiqueta, debug)
    texto = _texto_despues_alias(linea, etiqueta, hasta=hasta).strip(' "_')
    if texto:
        return _registrar(seccion, campo, texto, linea, f"valor despues de {etiqueta}", debug)
    return check


def _leer_check_en_linea(
    seccion: str,
    campo: str,
    linea: str,
    etiqueta: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    if not linea:
        return ""
    palabras = re.findall(r"\S+", linea)
    indice = _indice_alias_en_palabras(palabras, etiqueta)
    if indice is None:
        return ""
    marcador = palabras[indice - 1] if indice > 0 else ""
    if _es_marcador(marcador, CHECK_MARCADO):
        return _registrar(seccion, campo, "Si", linea, f"check antes de {etiqueta}", debug)
    if _es_marcador(marcador, CHECK_VACIO):
        return _registrar(seccion, campo, "No", linea, f"check antes de {etiqueta}", debug)
    return ""


def _leer_regex(
    seccion: str,
    campo: str,
    linea: str,
    patron: str,
    debug: dict[str, dict[str, CampoLeido]],
) -> str:
    match = re.search(patron, linea, flags=re.IGNORECASE)
    if not match:
        return ""
    valor = next((grupo for grupo in match.groups() if grupo is not None), "").strip()
    if not valor:
        return ""
    return _registrar(seccion, campo, valor, linea, patron, debug)


def _leer_regex_con_contenido(
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
    return next((linea for linea in lineas if _contiene(linea, texto)), "")


def _linea_con_despues(lineas: list[str], marcador: str, texto: str) -> str:
    return _linea_con(_lineas_despues(lineas, marcador), texto)


def _linea_con_alias_mas_temprano(lineas: list[str], etiqueta: str) -> str:
    candidatas = []
    for linea in lineas:
        palabras = re.findall(r"\S+", linea)
        indice = _indice_alias_en_palabras(palabras, etiqueta)
        if indice is not None:
            candidatas.append((indice, linea))
    return min(candidatas, key=lambda candidata: candidata[0])[1] if candidatas else ""


def _lineas_despues(lineas: list[str], marcador: str) -> list[str]:
    for indice, linea in enumerate(lineas):
        if _contiene(linea, marcador):
            return lineas[indice + 1 :]
    return lineas


def _texto_despues_alias(linea: str, etiqueta: str, hasta: str) -> str:
    patron = r"\s+".join(re.escape(token) for token in etiqueta.split())
    match = re.search(rf"{patron}:?\s*(.*?)(?:{hasta})", linea, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _indice_alias_en_palabras(palabras: list[str], etiqueta: str) -> int | None:
    alias = [_normalizar_token(token) for token in re.findall(r"\w+", etiqueta)]
    alias = [token for token in alias if token]
    tokens = [_normalizar_token(palabra) for palabra in palabras]
    for indice in range(0, len(tokens) - len(alias) + 1):
        if tokens[indice : indice + len(alias)] == alias:
            return indice
    return None


def _es_marcador(valor: str, marcadores: list[str]) -> bool:
    normalizado = valor.strip()
    return normalizado in marcadores


def _contiene(linea: str, texto: str) -> bool:
    return _normalizar_texto(texto) in _normalizar_texto(linea)


def _normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return texto.lower()


def _normalizar_token(texto: str) -> str:
    texto = _normalizar_texto(texto)
    return re.sub(r"\W+", "", texto)
