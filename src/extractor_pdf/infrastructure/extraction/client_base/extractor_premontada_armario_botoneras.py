import re
from typing import Any

from extractor_pdf.domain.entidades import PaginaPdf, PalabraTexto
from extractor_pdf.infrastructure.extraction.client_base.extraccion_declarativa_pdf import extraer_por_reglas_pdf

MARCA_CHECK = "\x14"


class ExtractorPremontadaArmarioBotonerasRaloeCrono:
    def extraer_con_debug(self, pagina: PaginaPdf) -> dict[str, Any]:
        data = self.extraer(pagina)
        return {"data": data, "debug_pdf": _debug_pdf_premontada_armario_botoneras(data)}

    def extraer(self, pagina: PaginaPdf) -> dict[str, Any]:
        tabla = _extraer_tabla_premontada(pagina)
        valores = _valores_pagina(pagina, tabla)

        resultado = {
            "general": {},
            "Premontada": {
                "Piso_E1": _lista_tabla(tabla["Piso_E1"]),
                "Piso_E2": _lista_tabla(tabla["Piso_E2"]),
                "Acceso_E1": _lista_tabla(tabla["Acceso_E1"]),
                "Acceso_E2": _lista_tabla(tabla["Acceso_E2"]),
                "Display_modelo_E1": _lista_tabla(tabla["Display_modelo_E1"]),
                "Display_modelo_E2": _lista_tabla(tabla["Display_modelo_E2"]),
                "Orient_E1": _lista_tabla(tabla["Orient_E1"]),
                "Orient_E2": _lista_tabla(tabla["Orient_E2"]),
                "Distancia_niveles": _lista(tabla["Distancia_niveles"]),
                "Puertas_piso_precableadas": _si_no(_check_en(pagina, 265, 285, 148, 162)),
                "Doble_acceso_alternado": _si_no(_check_en(pagina, 345, 370, 162, 178)),
                "Doble_acceso_simultaneo": _si_no(_check_en(pagina, 410, 440, 162, 178)),
                "Doble_acceso_simultaneo_selectivo": _si_no(_check_en(pagina, 470, 490, 162, 178)),
                "Planta_acceso_bomberos": "",
                "Planta_acceso_bomberos_2": "",
                "Planta_principal": valores["Planta_principal"],
                "Recorrido": valores["Recorrido"],
                "Foso": valores["Foso"],
                "Huida": valores["Huida"],
                "Distancia_maniobra_motor": valores["Distancia_maniobra_motor"],
                "Dist_maniobra_piso_mas_prox": valores["Dist_maniobra_piso_mas_prox"],
                "Manguera_plana": valores["Manguera_plana"],
                "Extra": valores["Extra"],
                "P": valores["P"],
                "Carga_nominal": valores["Carga_nominal"],
                "Cableado_LSF": _si_no(_check_en(pagina, 25, 45, 330, 348)),
                "Premontada_mas_larga": _si_no(_check_en(pagina, 205, 225, 330, 348)),
                "Medidas_cabina_ancho": "",
                "Medidas_cabina_profundo": "",
            },
            "Armario": {
                "Planta_ubicacion_armario": valores["Planta_ubicacion_armario"],
                "Acabado": valores["Acabado"],
                "Una_pieza_integral": _si_no(_check_en(pagina, 270, 285, 380, 394)),
                "Tapa_trasera_para_zocalo": _si_no(_check_en(pagina, 430, 450, 380, 394)),
                "Dos_piezas": _si_no(_check_en(pagina, 270, 285, 396, 410)),
                "Longitud_cables_interconexion_armarios": valores["Longitud_cables_interconexion_armarios"],
                "Longitud_cables_potencia_modulo_de_piso": valores["Longitud_cables_potencia_modulo_de_piso"],
                "Control_en_rellano": _si_no(_check_en(pagina, 270, 285, 426, 440)),
                "Control_en_marco_puerta": _si_no(
                    bool(valores["Control_en_marco_puerta_txt"]) or _check_en(pagina, 335, 355, 440, 460)
                ),
                "Control_en_marco_puerta_txt": valores["Control_en_marco_puerta_txt"],
                "Apertura_marco": valores["Apertura_marco"],
                "Talla_cabina_1": _si_no(_check_en(pagina, 335, 350, 474, 486)),
                "Talla_cabina_2": _si_no(_check_en(pagina, 385, 400, 474, 486)),
                "Talla_cabina_3": _si_no(_check_en(pagina, 435, 450, 474, 486)),
                "Talla_cabina_4": _si_no(_check_en(pagina, 485, 500, 474, 486)),
                "Talla_cabina_5": _si_no(_check_en(pagina, 535, 550, 474, 486)),
                "Talla_hueco_1": _si_no(_check_en(pagina, 335, 350, 488, 500)),
                "Talla_hueco_2": _si_no(_check_en(pagina, 385, 400, 488, 500)),
                "Talla_hueco_3": _si_no(_check_en(pagina, 435, 450, 488, 500)),
                "Talla_hueco_4": _si_no(_check_en(pagina, 485, 500, 488, 500)),
                "Talla_hueco_5": _si_no(_check_en(pagina, 535, 550, 488, 500)),
            },
            "Botonera_Exterior": {
                "Botonera_ext_fabricante": valores["Botonera_ext_fabricante"],
                "Enviaran_botoneras_para_cablear_ext": _si_no(_check_en(pagina, 20, 35, 596, 608)),
                "Botoneras_ubicadas_en_marco": _si_no(_check_en(pagina, 125, 140, 612, 624)),
                "Botoneras_ubicadas_en_pared": _si_no(_check_en(pagina, 178, 192, 612, 624)),
                "Flechas_direccion": _si_no(_check_en(pagina, 20, 35, 628, 638)),
                "Flechas_direccion_dintel": _si_no(_check_en(pagina, 125, 140, 628, 638)),
                "Flechas_direccion_botonera": _si_no(_check_en(pagina, 178, 192, 628, 638)),
                "Flechas_predirecc": _si_no(_check_en(pagina, 20, 35, 642, 655)),
                "Flechas_predirecc_exterior": _si_no(_check_en(pagina, 125, 140, 642, 655)),
                "Flechas_predirecc_embocadura_cab": _si_no(_check_en(pagina, 178, 192, 642, 655)),
                "Esta": _si_no(_check_en(pagina, 20, 35, 658, 670)),
                "Ocupado": _si_no(_check_en(pagina, 75, 90, 658, 670)),
                "Pta_abierta": _si_no(_check_en(pagina, 125, 140, 658, 670)),
                "Reg_ext": valores["Reg_ext"],
                "Prohibido_paso": _si_no(_check_en(pagina, 20, 35, 674, 686)),
                "Prohibido_paso_cant": valores["Prohibido_paso_cant"],
                "Llavin_pulsador_ext": _si_no(_check_en(pagina, 20, 35, 690, 702)),
                "Llavin_pulsador_ext_cant": valores["Llavin_pulsador_ext_cant"],
                "Llavin_extra_ext": _si_no(_check_en(pagina, 20, 35, 706, 718)),
                "Llavin_extra_ext_cant": valores["Llavin_extra_ext_cant"],
                "Llavin_extra_ext_funcion": valores["Llavin_extra_ext_funcion"],
                "Display_ext_E1": _si_no(bool(valores["Display_ext_E1"])),
                "Display_ext_E1_txt": valores["Display_ext_E1"],
                "Display_ext_E1_cant": valores["Display_ext_E1_cant"],
                "Display_ext_E2": _si_no(bool(valores["Display_ext_E2"])),
                "Display_ext_E2_txt": valores["Display_ext_E2"],
                "Display_ext_E2_cant": "",
                "Reg_acustico_pisos_RAP": _si_no(_check_en(pagina, 20, 35, 765, 780)),
            },
            "Botonera_Cabina": {
                "Botonera_cab_fabricante": valores["Botonera_cab_fabricante"],
                "Modelo": valores["Modelo_botonera_cabina"],
                "Pulsador_fabricante": valores["Pulsador_fabricante"],
                "Color_pulsador": valores["Color_pulsador"],
                "Doble_botonera_en_cabina": _si_no(_check_en(pagina, 270, 285, 550, 562)),
                "Comunicacion_en_2a_botonera": _si_no(_check_en(pagina, 420, 440, 550, 562)),
                "Enviaran_botonera_para_cablear_cab": _si_no(_check_en(pagina, 270, 285, 566, 578)),
                "Pulsador_abrir_puertas": _si_no(_check_en(pagina, 270, 285, 580, 592)),
                "AP_iluminado_en_cierre": _si_no(_check_en(pagina, 420, 440, 580, 592)),
                "Pulsador_cerrar_puertas": _si_no(_check_en(pagina, 270, 285, 596, 608)),
                "Luminoso_exceso_carga": _si_no(_check_en(pagina, 270, 285, 612, 624)),
                "Luminoso_prohibido_fumar": _si_no(_check_en(pagina, 420, 440, 612, 624)),
                "Llavin_pulsador_cab": _si_no(_check_en(pagina, 270, 285, 628, 640)),
                "Llavin_pulsador_cab_cant": valores["Llavin_pulsador_cab_cant"]
                if _check_en(pagina, 270, 285, 628, 640)
                else "",
                "Llavin_extra_cab": _si_no(_check_en(pagina, 270, 285, 642, 655)),
                "Llavin_extra_cab_Funcion": "",
                "Pulsador_de_stop_en_cabina": _si_no(_check_en(pagina, 270, 285, 658, 670)),
                "Pulsador_alarma": _si_no(bool(valores["Pulsador_alarma"])),
                "Pulsador_alarma_txt": valores["Pulsador_alarma"],
                "Llavin_VIP_bomberos": _si_no(_check_en(pagina, 270, 285, 690, 702)),
                "Placa_caract_retroiluminada": _si_no(_check_en(pagina, 420, 440, 690, 702)),
                "Display_cabina": _si_no(bool(valores["Display_cabina"])),
                "Display_cabina_txt": valores["Display_cabina"],
                "Secuencia": _lista(valores["Secuencia"]),
                "Texto_display": valores["Texto_display"],
                "Orientacion": valores["Orientacion"],
                "Reg_acustico_cabina_RAP": _si_no(_check_en(pagina, 270, 285, 765, 780)),
            },
        }
        for seccion in ("Premontada", "Armario", "Botonera_Exterior", "Botonera_Cabina"):
            declarativos = extraer_por_reglas_pdf(pagina, seccion)
            if declarativos:
                resultado.setdefault(seccion, {}).update(declarativos)
        return resultado


def _extraer_tabla_premontada(pagina: PaginaPdf) -> dict[str, list[str]]:
    columnas = {
        "Piso_E1": (30, 48),
        "Piso_E2": (49, 67),
        "Acceso_E1": (68, 86),
        "Acceso_E2": (87, 104),
        "Display_modelo_E1": (105, 122),
        "Display_modelo_E2": (123, 141),
        "Orient_E1": (142, 160),
        "Orient_E2": (161, 178),
    }
    y_fin_tabla = _inicio_armario(pagina)
    palabras_tabla = [
        palabra
        for palabra in pagina.palabras
        if 176 <= palabra.y0 <= y_fin_tabla
        and 25 <= palabra.x0 <= 180
        and palabra.texto != MARCA_CHECK
    ]
    grupos_y = _agrupar_por_fila(palabras_tabla)
    filas: list[dict[str, str]] = []

    for grupo in grupos_y:
        fila = {clave: "-" for clave in columnas}
        for palabra in grupo:
            columna = _columna_por_x(palabra.x0, columnas)
            if columna:
                fila[columna] = palabra.texto
        if any(valor != "-" for valor in fila.values()):
            filas.append(fila)

    distancias = [
        palabra.texto
        for palabra in sorted(pagina.palabras, key=lambda palabra: (palabra.y0, palabra.x0))
        if 180 <= palabra.y0 <= y_fin_tabla
        and 200 <= palabra.x0 <= 255
        and re.fullmatch(r"\d{3}|\d+\.\d{3}", palabra.texto)
    ]

    resultado = {clave: [fila[clave] for fila in filas] for clave in columnas}
    resultado["Distancia_niveles"] = distancias
    return resultado


def _inicio_armario(pagina: PaginaPdf) -> float:
    candidatos = [
        palabra.y0
        for palabra in pagina.palabras
        if palabra.texto == "Armario" and 320 <= palabra.y0 <= 380
    ]
    return min(candidatos) if candidatos else 345


def _agrupar_por_fila(palabras: list[PalabraTexto]) -> list[list[PalabraTexto]]:
    filas: list[list[PalabraTexto]] = []
    for palabra in sorted(palabras, key=lambda item: (item.y0, item.x0)):
        if not filas or abs(filas[-1][0].y0 - palabra.y0) > 4:
            filas.append([palabra])
        else:
            filas[-1].append(palabra)
    return filas


def _columna_por_x(x0: float, columnas: dict[str, tuple[float, float]]) -> str | None:
    for clave, (x_min, x_max) in columnas.items():
        if x_min <= x0 <= x_max:
            return clave
    return None


def _valores_pagina(pagina: PaginaPdf, tabla: dict[str, list[str]]) -> dict[str, str | list[str]]:
    planta_armario, acabado = _planta_armario_y_acabado(pagina)
    armario = _datos_armario(pagina)
    botonera_cabina = _datos_botonera_cabina(pagina)
    botonera_exterior = _datos_botonera_exterior(pagina)
    datos_display = _datos_display(pagina)
    manguera_extra = _lineas_bloque_en_zona(pagina, 300, 315, 345, 490)
    peso_carga = _lineas_bloque_en_zona(pagina, 317, 333, 280, 500)

    return {
        "Planta_principal": _primer_texto_en_zona(pagina, 196, 206, 400, 430),
        "Recorrido": _valor_con_unidad(pagina, 215, 232, 405, 440, 470, 492),
        "Foso": _valor_con_unidad(pagina, 232, 250, 405, 435, 470, 492),
        "Huida": _valor_con_unidad(pagina, 249, 267, 405, 435, 470, 492),
        "Distancia_maniobra_motor": _valor_con_unidad(pagina, 266, 284, 405, 440, 470, 492),
        "Dist_maniobra_piso_mas_prox": _valor_con_unidad(pagina, 283, 301, 405, 435, 470, 492),
        "Manguera_plana": _valor_con_unidad(pagina, 300, 318, 345, 385, 410, 435),
        "Extra": _valor_con_unidad(pagina, 300, 318, 480, 492, 545, 567),
        "P": _valor_con_unidad(pagina, 318, 335, 280, 305, 318, 335),
        "Carga_nominal": _valor_con_unidad(pagina, 318, 335, 420, 445, 442, 457),
        "Planta_ubicacion_armario": planta_armario,
        "Acabado": acabado,
        **armario,
        **botonera_cabina,
        **botonera_exterior,
        **datos_display,
    }


def _planta_armario_y_acabado(pagina: PaginaPdf) -> tuple[str, str]:
    valores = _lineas_bloque_en_zona(pagina, 365, 382, 385, 545)
    if not valores:
        return "", ""
    return valores[0], " ".join(valores[1:])


def _datos_botonera_cabina(pagina: PaginaPdf) -> dict[str, str]:
    valores = _lineas_bloque_en_zona(pagina, 520, 552, 360, 565)
    return {
        "Botonera_cab_fabricante": valores[0] if len(valores) > 0 else "",
        "Modelo_botonera_cabina": valores[1] if len(valores) > 1 else "",
        "Pulsador_fabricante": valores[2] if len(valores) > 2 else "",
        "Color_pulsador": valores[3] if len(valores) > 3 else "",
        "Botonera_ext_fabricante": _primer_texto_en_zona(pagina, 583, 600, 110, 140),
    }


def _datos_botonera_exterior(pagina: PaginaPdf) -> dict[str, str]:
    return {
        "Prohibido_paso_cant": _primera_linea_numerica_en_zona(pagina, 674, 689, 153, 190),
        "Llavin_pulsador_ext_cant": _primera_linea_numerica_en_zona(pagina, 690, 705, 153, 190),
        "Llavin_extra_ext_cant": _numero_en_fila_despues_de_etiqueta(pagina, ["Llavín", "Extra"], ["Cant"]),
        "Llavin_extra_ext_funcion": _texto_despues_de_etiqueta(pagina, 721, 736, 65, 220),
    }


def _debug_pdf_premontada_armario_botoneras(
    data: dict[str, dict[str, str]],
) -> dict[str, dict[str, dict[str, str]]]:
    zonas_conocidas = {
        ("Premontada", "Orient_E1"),
        ("Premontada", "Orient_E2"),
        ("Botonera_Exterior", "Prohibido_paso_cant"),
        ("Botonera_Exterior", "Llavin_pulsador_ext_cant"),
        ("Botonera_Exterior", "Llavin_extra_ext_cant"),
        ("Botonera_Exterior", "Llavin_extra_ext_funcion"),
    }
    debug: dict[str, dict[str, dict[str, str]]] = {}
    for seccion, campos in data.items():
        if not isinstance(campos, dict):
            continue
        debug[seccion] = {}
        for campo, valor in campos.items():
            if valor in {"Si", "No"}:
                fuente = "check_zona"
            elif valor:
                fuente = "valor_leido"
            elif (seccion, campo) in zonas_conocidas:
                fuente = "zona_vacia"
            else:
                fuente = ""
            debug[seccion][campo] = {"valor": valor, "fuente": fuente}
    return debug


def _datos_display(pagina: PaginaPdf) -> dict[str, str | list[str]]:
    linea_display = _lineas_bloque_en_zona(pagina, 722, 754, 20, 520)
    linea_display_2 = _lineas_bloque_en_zona(pagina, 754, 765, 20, 180)
    secuencia = (_texto_en_fila_despues_de_etiqueta(pagina, ["Secuencia"]) or (linea_display[0] if linea_display else "")).split(",")
    texto_display = _texto_en_fila_despues_de_etiqueta(pagina, ["Texto"]) or (linea_display[1] if len(linea_display) > 1 else "")
    display_ext_fila = _texto_entre_etiquetas_en_fila_o_none(pagina, ["Display", "Ext", "1"], ["Cant"])
    display_ext = _normalizar_display(
        display_ext_fila
        if display_ext_fila is not None
        else (linea_display[2] if len(linea_display) > 2 else "")
    )
    display_ext_cant = _numero_en_fila_despues_de_etiqueta(pagina, ["Display", "Ext", "1"], ["Cant"]) or (
        linea_display[3] if len(linea_display) > 3 else ""
    )
    orientacion = _buscar_orientacion(linea_display) or _primer_linea_bloque_en_zona(
        pagina, 750, 768, 20, 35
    )

    display_cabina = _normalizar_display(_primer_linea_bloque_en_zona(pagina, 706, 723, 20, 160))
    reg_ext = _primera_linea_numerica_en_zona(pagina, 660, 676, 20, 280)
    llavin_cab_cant = _primera_linea_numerica_en_zona(pagina, 628, 646, 20, 440)

    return {
        "Secuencia": secuencia,
        "Texto_display": texto_display,
        "Display_ext_E1": display_ext,
        "Display_ext_E1_cant": display_ext_cant,
        "Display_ext_E2": _normalizar_display(linea_display_2[0]) if linea_display_2 else "",
        "Orientacion": orientacion,
        "Display_cabina": display_cabina,
        "Reg_ext": reg_ext,
        "Llavin_pulsador_cab_cant": llavin_cab_cant,
        "Pulsador_alarma": _texto_despues_de_etiqueta(pagina, 674, 686, 360, 500),
    }


def _datos_armario(pagina: PaginaPdf) -> dict[str, str]:
    return {
        "Longitud_cables_interconexion_armarios": _numero_en_fila_despues_de_etiqueta(
            pagina, ["Longitud", "cables", "interconexión", "armarios"]
        ),
        "Longitud_cables_potencia_modulo_de_piso": _numero_en_fila_despues_de_etiqueta(
            pagina, ["Longitud", "cables", "potencia"]
        ),
        "Control_en_marco_puerta_txt": _texto_en_fila_despues_de_etiqueta(
            pagina, ["Control", "en", "marco", "puerta"]
        ),
        "Apertura_marco": _texto_en_fila_despues_de_etiqueta(pagina, ["Apertura", "marco"]),
    }


def _textos_en_zona(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 0,
    x_max: float = 10_000,
) -> list[str]:
    return [
        palabra.texto
        for palabra in sorted(pagina.palabras, key=lambda palabra: (palabra.y0, palabra.x0))
        if y_min <= palabra.y0 <= y_max
        and x_min <= palabra.x0 <= x_max
        and palabra.texto != MARCA_CHECK
    ]


def _primer_texto_en_zona(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 0,
    x_max: float = 10_000,
) -> str:
    valores = _textos_en_zona(pagina, y_min, y_max, x_min, x_max)
    return valores[0] if valores else ""


def _lineas_bloque_en_zona(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 0,
    x_max: float = 10_000,
) -> list[str]:
    lineas: list[str] = []
    for bloque in sorted(pagina.bloques, key=lambda bloque: (bloque.y0, bloque.x0)):
        if y_min <= bloque.y0 <= y_max and x_min <= bloque.x0 <= x_max:
            lineas.extend(
                linea.strip()
                for linea in bloque.texto.splitlines()
                if linea.strip() and linea.strip() != MARCA_CHECK
            )
    return lineas


def _primer_linea_bloque_en_zona(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 0,
    x_max: float = 10_000,
) -> str:
    valores = _lineas_bloque_en_zona(pagina, y_min, y_max, x_min, x_max)
    return valores[0] if valores else ""


def _texto_en_fila_despues_de_etiqueta(
    pagina: PaginaPdf,
    etiqueta: list[str],
    stop: list[str] | None = None,
) -> str:
    fila, x_fin = _fila_y_fin_etiqueta(pagina, etiqueta)
    if not fila or x_fin is None:
        return ""
    x_stop = _inicio_etiqueta_en_fila(fila, stop) if stop else None
    return _texto_entre_x(fila, x_fin, x_stop)


def _texto_entre_etiquetas_en_fila(
    pagina: PaginaPdf,
    etiqueta_inicio: list[str],
    etiqueta_fin: list[str],
) -> str:
    valor = _texto_entre_etiquetas_en_fila_o_none(pagina, etiqueta_inicio, etiqueta_fin)
    return valor or ""


def _texto_entre_etiquetas_en_fila_o_none(
    pagina: PaginaPdf,
    etiqueta_inicio: list[str],
    etiqueta_fin: list[str],
) -> str | None:
    fila, x_fin = _fila_y_fin_etiqueta(pagina, etiqueta_inicio)
    if not fila or x_fin is None:
        return None
    x_stop = _inicio_etiqueta_en_fila(fila, etiqueta_fin)
    return _texto_entre_x(fila, x_fin, x_stop)


def _numero_en_fila_despues_de_etiqueta(
    pagina: PaginaPdf,
    etiqueta_fila: list[str],
    etiqueta_valor: list[str] | None = None,
) -> str:
    etiqueta = etiqueta_valor or etiqueta_fila
    fila, x_fin = _fila_y_fin_etiqueta(pagina, etiqueta, etiqueta_fila)
    if not fila or x_fin is None:
        return ""
    for palabra in fila:
        if palabra.x0 > x_fin and re.fullmatch(r"\d+(?:[.,]\d+)?", palabra.texto):
            return palabra.texto
    return ""


def _fila_y_fin_etiqueta(
    pagina: PaginaPdf,
    etiqueta: list[str],
    etiqueta_fila: list[str] | None = None,
) -> tuple[list[PalabraTexto], float | None]:
    filas = _agrupar_por_fila([palabra for palabra in pagina.palabras if palabra.texto != MARCA_CHECK])
    for fila in filas:
        if etiqueta_fila and _inicio_etiqueta_en_fila(fila, etiqueta_fila) is None:
            continue
        fin = _fin_etiqueta_en_fila(fila, etiqueta)
        if fin is not None:
            return fila, fin
    return [], None


def _inicio_etiqueta_en_fila(fila: list[PalabraTexto], etiqueta: list[str] | None) -> float | None:
    indice = _indice_etiqueta_en_fila(fila, etiqueta)
    return fila[indice].x0 if indice is not None else None


def _fin_etiqueta_en_fila(fila: list[PalabraTexto], etiqueta: list[str]) -> float | None:
    indice = _indice_etiqueta_en_fila(fila, etiqueta)
    if indice is None:
        return None
    return fila[indice + len(etiqueta) - 1].x1


def _indice_etiqueta_en_fila(fila: list[PalabraTexto], etiqueta: list[str] | None) -> int | None:
    if not etiqueta:
        return None
    textos = [_normalizar_token(palabra.texto) for palabra in fila]
    objetivo = [_normalizar_token(token) for token in etiqueta]
    for indice in range(0, len(textos) - len(objetivo) + 1):
        if textos[indice : indice + len(objetivo)] == objetivo:
            return indice
    return None


def _normalizar_token(texto: str) -> str:
    texto = texto.rstrip(":")
    texto = texto.translate(str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU"))
    return texto.lower()


def _texto_entre_x(fila: list[PalabraTexto], x_min: float, x_max: float | None = None) -> str:
    valores = [
        palabra.texto
        for palabra in fila
        if palabra.x0 > x_min
        and (x_max is None or palabra.x0 < x_max)
        and palabra.texto not in {MARCA_CHECK, "m", "mm", "UN"}
    ]
    return " ".join(valores).strip()


def _primera_linea_numerica_en_zona(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 0,
    x_max: float = 10_000,
) -> str:
    for valor in _lineas_bloque_en_zona(pagina, y_min, y_max, x_min, x_max):
        if valor.isdigit():
            return valor
    return ""


def _valor_con_mm(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 405,
    x_max: float = 440,
    por_defecto: str = "",
) -> str:
    return _primer_texto_en_zona(pagina, y_min, y_max, x_min, x_max) or por_defecto


def _primer_valor(valores: list[str]) -> str:
    for valor in valores:
        if valor != "-":
            return valor
    return ""


def _normalizar_display(valor: str) -> str:
    return valor.replace('"', "").strip()


def _buscar_orientacion(valores: list[str]) -> str:
    for valor in valores:
        if valor in {"HORIZONTAL", "VERTICAL"}:
            return valor
    return ""


def _texto_despues_de_etiqueta(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float,
    x_max: float,
) -> str:
    palabras = _textos_en_zona(pagina, y_min, y_max, x_min, x_max)
    return " ".join(palabras)


def _check_en(
    pagina: PaginaPdf,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> bool:
    return any(
        _solapa_zona(marca, x_min, x_max, y_min, y_max)
        for marca in pagina.marcas_check
    )


def _solapa_zona(
    palabra: PalabraTexto,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> bool:
    return palabra.x1 >= x_min and palabra.x0 <= x_max and palabra.y1 >= y_min and palabra.y0 <= y_max


def _lista(valores: list[str]) -> str:
    if valores and not any(valor != "-" for valor in valores):
        return ""
    return ",".join(valores)


def _lista_tabla(valores: list[str]) -> str:
    if not valores:
        return ""
    return ",".join(valores)


def _valor_con_unidad(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    valor_x_min: float,
    valor_x_max: float,
    unidad_x_min: float,
    unidad_x_max: float,
) -> str:
    valor = _primer_texto_en_zona(pagina, y_min, y_max, valor_x_min, valor_x_max)
    if not valor:
        return ""
    return valor


def _si_no(valor: bool) -> str:
    return "Si" if valor else "No"

