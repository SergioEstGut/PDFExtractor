import re
from typing import Any

from extractor_pdf.domain.entidades import PaginaPdf, PalabraTexto
from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import aplicar_contrato_salida
from extractor_pdf.infrastructure.extraction.client_base.extraccion_declarativa_pdf import extraer_por_reglas_pdf

MARCA_CHECK = "\x14"


class ExtractorFosoHuidaOpcionesRaloeCrono:
    def extraer_con_debug(self, pagina: PaginaPdf) -> dict[str, Any]:
        data = self.extraer(pagina)
        return {"data": data, "debug_pdf": _debug_pdf_foso_opciones(data)}

    def extraer(self, pagina: PaginaPdf) -> dict[str, Any]:
        valores = _valores_pagina(pagina)

        resultado = {
            "Gestion_foso_huida_reducida": {
                "Foso_exencion_raloe": _si_no(_check_en(pagina, 25, 45, 150, 168)),
                "Foso_EN81_21": _si_no(_check_en(pagina, 220, 245, 150, 168)),
                "Foso_faldon_con_contacto": _si_no(_check_en(pagina, 305, 330, 150, 168)),
                "Foso_faldon_con_contacto_txt": "",
                "Foso_faldon_retractil_leva": _si_no(_check_en(pagina, 420, 445, 150, 168)),
                "Foso_faldon_retractil_leva_txt": "",
                "Foso_tope_movil": _si_no(_check_en(pagina, 25, 45, 168, 184)),
                "Foso_tope_cant": valores["Foso_tope_cant"],
                "Foso_tope_contactos": valores["Foso_tope_contactos"],
                "Foso_rearme_mecanico_biestable": _si_no(_check_en(pagina, 25, 45, 184, 202)),
                "Foso_rearme_electrico_biestable": _si_no(_check_en(pagina, 220, 245, 184, 202)),
                "Foso_rearme_electrico_biestable_txt": "",
                "Huida_exencion_raloe": _si_no(_check_en(pagina, 25, 45, 204, 222)),
                "Huida_EN81_21": _si_no(_check_en(pagina, 390, 420, 204, 222)),
                "Huida_barandilla_con_contacto": _si_no(_check_en(pagina, 220, 245, 204, 222)),
                "Huida_barandilla_cant": valores["Huida_barandilla_cant"],
                "Huida_tope_movil": _si_no(_check_en(pagina, 25, 45, 222, 238)),
                "Huida_tope_cant": valores["Huida_tope_cant"],
                "Huida_tope_ubicacion": valores["Huida_tope_ubicacion"],
                "Huida_rearme_electrico_biestable": _si_no(_check_en(pagina, 25, 45, 238, 256)),
                "Huida_rearme_electrico_biestable_txt": "",
            },
            "Opciones": {
                "Resistencia_de_caldeo": _si_no(_check_en(pagina, 25, 45, 264, 280)),
                "Refrigerador_de_aceite": _si_no(_check_en(pagina, 235, 260, 264, 280)),
                "Presostato_sobrc_na": _si_no(_check_en(pagina, 385, 405, 264, 280)),
                "Limitador_velocidad_cab": _si_si_hay_valor(valores["Limitador_velocidad_cab"]),
                "Limitador_velocidad_cab_txt": valores["Limitador_velocidad_cab"],
                "Limitador_posicion": valores["Limitador_posicion"],
                "Limitador_ubicacion": valores["Limitador_ubicacion"],
                "Accionamiento_a_dist_limitador": _si_si_hay_valor(valores["Accionamiento_a_dist_limitador"]),
                "Accionamiento_a_dist_limitador_txt": valores["Accionamiento_a_dist_limitador"],
                "Cont_sobrevel_manual": _si_no(_check_en(pagina, 235, 260, 298, 315)),
                "Cont_sobrevel_a_dist": _si_no(_check_en(pagina, 380, 405, 298, 315)),
                "Cont_sobrevel_a_dist_txt": valores["Cont_sobrevel_a_dist"],
                "Sistema_antideriva_CBL": _si_no(_check_en(pagina, 25, 45, 315, 332)),
                "Sistema_antideriva_CBL_txt": "",
                "Limitador_vel_contrapeso": _si_no(_check_en(pagina, 25, 45, 332, 350)),
                "Limitador_contrapeso_posicion": valores["Limitador_contrapeso_posicion"],
                "Limitador_vel_contrapeso_txt": "",
                "Limitador_contrapeso_ubicacion": valores["Limitador_contrapeso_ubicacion"],
                "Accionamiento_a_dist_limitador_contrapeso": _si_no(
                    _check_en(pagina, 25, 45, 348, 366)
                ),
                "Accionamiento_a_dist_limitador_contrapeso_txt": "",
                "Cont_sobrevel_manual_contrapeso": _si_no(_check_en(pagina, 235, 260, 348, 366)),
                "Cont_sobrevel_a_dist_contrapeso": _si_no(_check_en(pagina, 380, 405, 348, 366)),
                "Cont_sobrevel_a_dist_contrapeso_txt": "",
                "Sistema_antideriva_contrapeso_CBL": "",
                "Sistema_antideriva_contrapeso_CBL_txt": "",
                "Pesacargas_fabricante": valores["Pesacargas_fabricante"],
                "Tipo_pesacargas": valores["Tipo_pesacargas"],
                "Modelo_pesacargas": valores["Modelo_pesacargas"],
                "Qt": valores["Qt"],
                "N_cables": valores["N_cables"],
                "Diametro_cables": valores["Diametro_cables"],
                "Tension_pesacargas": valores["Tension_pesacargas"],
                "Distancia_pesacargas_maniobra": valores["Distancia_pesacargas_maniobra"],
                "Completo": _si_no(_check_en(pagina, 230, 250, 418, 434)),
                "Luz_emergencia_cabina": valores["Luz_emergencia_cabina"],
                "Rescate": valores["Rescate"],
                "Pos_caja_cunas": valores["Pos_caja_cunas"],
                "Luz_emergencia_cabina_3h": _si_no(_check_en(pagina, 450, 480, 434, 452)),
                "Comunicacion_suministro": _si_si_hay_valor(valores["Comunicacion_suministro"]),
                "Comunicacion_suministro_txt": valores["Comunicacion_suministro"],
                "Modelo_comunicacion": valores["Modelo_comunicacion"],
                "Bucl_inductivo_sordos": _si_no(_check_en(pagina, 450, 480, 454, 470)),
                "Comunicacion_adicional": _si_no(_check_en(pagina, 25, 45, 472, 490)),
                "Sintesis_voz": _si_si_hay_valor(valores["Sintesis_voz"]),
                "Sintesis_voz_txt": valores["Sintesis_voz"],
                "Idioma_voz_1": valores["Idioma_voz"],
                "Idioma_voz_2": "",
                "Interfono_suministro": _si_si_hay_valor(valores["Interfono_suministro"]),
                "Interfono_suministro_txt": valores["Interfono_suministro"],
                "GSM": _si_no(_check_en(pagina, 235, 260, 490, 508)),
                "GSM_txt": "",
                "Intercomunicadores_EN81_72": _si_no(_check_en(pagina, 390, 420, 490, 508)),
                "Renivelacion": _si_no(_check_en(pagina, 25, 45, 508, 524)),
                "Renivelacion_txt": "",
                "Apertura_anticipada": _si_no(_check_en(pagina, 235, 260, 508, 524)),
                "Apertura_anticipada_txt": "",
                "Luz_en_armario": _si_no(_check_en(pagina, 385, 405, 508, 524)),
                "Socorro_electrico_en_maniobra": _si_no(_check_en(pagina, 25, 45, 524, 542)),
                "Trampilla_techo_cabina": _si_no(_check_en(pagina, 235, 260, 524, 542)),
                "Escalera_techo_con_contacto": _si_no(_check_en(pagina, 385, 405, 524, 542)),
                "Socorro_electrico_en_botonera": _si_no(_check_en(pagina, 25, 45, 540, 558)),
                "Escalera_foso_con_contacto": _si_no(_check_en(pagina, 235, 260, 540, 558)),
                "Escalera_interior_cabina_con_contacto": _si_no(
                    _check_en(pagina, 385, 405, 540, 558)
                ),
                "Magnetotermicos_y_diferenciales": _si_no(_check_en(pagina, 25, 45, 558, 576)),
                "Bloqueo_mecanico_protec": _si_no(_check_en(pagina, 235, 260, 558, 576)),
                "Enchufes": _si_si_hay_valor(valores["Enchufes"]),
                "Enchufes_txt": valores["Enchufes"],
                "Distancia_a_maniobra": valores["Distancia_a_maniobra"],
                "Stop_adicional_maquina": _si_no(_check_en(pagina, 235, 260, 575, 592)),
                "Ventilacion_maq_tipo": _si_si_hay_valor(valores["Ventilacion_maq_tipo"]),
                "Ventilacion_maq_tipo_txt": valores["Ventilacion_maq_tipo"],
                "Stop_adicional_foso_cant": _si_si_hay_valor(valores["Stop_adicional_foso_cant"]),
                "Stop_adicional_foso_cant_txt": valores["Stop_adicional_foso_cant"],
                "Gong_exteriores": _si_no(_check_en(pagina, 235, 260, 592, 610)),
                "Stop_adicional_techo_cab_cant": _si_si_hay_valor(valores["Stop_adicional_techo_cab_cant"]),
                "Stop_adicional_techo_cab_cant_txt": valores["Stop_adicional_techo_cab_cant"],
                "Gong_cabina": _si_no(_check_en(pagina, 25, 45, 610, 626)),
                "Test_de_freno": _si_no(_check_en(pagina, 235, 260, 610, 626)),
                "Tope_extra_foso_1_contacto_cant": _si_si_hay_valor(valores["Tope_extra_foso_1_contacto_cant"]),
                "Tope_extra_foso_1_contacto_cant_txt": valores["Tope_extra_foso_1_contacto_cant"],
                "Rosario": _si_no(bool(valores["Rosario"]) or _check_en(pagina, 25, 45, 626, 644)),
                "Rosario_txt": valores["Rosario"],
                "Cant_rosario": valores["Cant_rosario"],
                "Embalaje_fitosanitario": _si_no(_check_en(pagina, 235, 260, 626, 644)),
                "Posicionamiento": valores["Posicionamiento"],
                "Rescate_autom_hidraulicos": _si_no(_check_en(pagina, 25, 45, 644, 660)),
                "Modulo_ARM": _si_no(_check_en(pagina, 235, 260, 644, 660)),
                "Botonera_revision_aerea_especial": _si_no(_check_en(pagina, 390, 420, 644, 660)),
                "Rescate_manual_hidraulicos": _si_no(_check_en(pagina, 25, 45, 660, 678)),
                "Modulo_DCI": _si_no(_check_en(pagina, 235, 260, 660, 678)),
                "Doble_rele_control_de_freno": _si_no(_check_en(pagina, 390, 420, 660, 678)),
                "Semaforos_MCH": _si_no(_check_en(pagina, 25, 45, 678, 694)),
                "Cableado_CCTV": _si_no(_check_en(pagina, 235, 260, 678, 694)),
                "Cableado_CCTV_txt": "",
                "Contactos_magneticos_pta_cab": _si_no(_check_en(pagina, 390, 420, 678, 694)),
                "Contactos_magneticos_pta_cab_txt": "",
                "Luz_emergencia_foso_3h": _si_no(_check_en(pagina, 25, 45, 694, 712)),
                "Centrado_coche_MCH": _si_no(_check_en(pagina, 235, 260, 694, 712)),
                "Ventilacion_cabina": _si_no(
                    bool(valores["Ventilacion_cabina"]) or _check_en(pagina, 385, 420, 694, 712)
                ),
                "Ventilacion_cabina_txt": valores["Ventilacion_cabina"],
                "Sistema_regenerativo": _si_no(_check_en(pagina, 25, 45, 710, 728)),
                "Sistema_regenerativo_txt": "",
                "BMS": _si_no(_check_en(pagina, 235, 260, 710, 728)),
                "Suministrar_mandos_MCH_cant": _si_no(_check_en(pagina, 390, 420, 710, 728)),
                "Suministrar_mandos_MCH_cant_txt": valores["Suministrar_mandos_MCH_cant_txt"],
                "Suministrar_soporteria_CS": _si_no(_check_en(pagina, 390, 420, 728, 746)),
            },
        }
        _mezclar_valores_declarativos(resultado, pagina, "Gestion_foso_huida_reducida")
        _mezclar_valores_declarativos(resultado, pagina, "Opciones")
        return aplicar_contrato_salida(resultado)


def _valores_pagina(pagina: PaginaPdf) -> dict[str, str]:
    limitador = _lineas_bloque_en_zona(pagina, 282, 298, 25, 40)
    accionamientos = _lineas_bloque_en_zona(pagina, 298, 314, 25, 40)
    pesacargas = _lineas_bloque_en_zona(pagina, 382, 400, 130, 150)
    tension = _lineas_bloque_en_zona(pagina, 400, 416, 350, 390)
    distancia_luz = _lineas_bloque_en_zona(pagina, 418, 434, 170, 185)
    pos_rescate = _lineas_bloque_en_zona(pagina, 434, 452, 70, 85)
    comunicacion = _lineas_bloque_en_zona(pagina, 454, 470, 25, 40)
    sintesis = _lineas_bloque_en_zona(pagina, 472, 490, 25, 40)
    interfono = _lineas_bloque_en_zona(pagina, 490, 508, 25, 40)
    enchufes = _lineas_bloque_en_zona(pagina, 558, 576, 25, 40)
    rosario = _texto_entre_etiquetas_en_fila(pagina, ["Rosario"], ["Cant"])

    cont_sobrevel_a_dist, accionamiento = _leer_accionamientos_limitador(accionamientos)
    return {
        "Foso_tope_cant": _primer_texto_en_zona(pagina, 168, 184, 245, 300),
        "Foso_tope_contactos": _primer_texto_en_zona(pagina, 168, 184, 350, 400),
        "Huida_barandilla_cant": _primer_texto_en_zona(pagina, 204, 222, 470, 520),
        "Huida_tope_cant": _primer_texto_en_zona(pagina, 222, 238, 245, 300),
        "Huida_tope_ubicacion": _primer_texto_en_zona(pagina, 222, 238, 350, 430),
        "Limitador_velocidad_cab": limitador[0] if len(limitador) > 0 else "",
        "Limitador_posicion": limitador[1] if len(limitador) > 1 else "",
        "Limitador_ubicacion": limitador[2] if len(limitador) > 2 else "",
        "Accionamiento_a_dist_limitador": accionamiento,
        "Cont_sobrevel_a_dist": cont_sobrevel_a_dist,
        "Limitador_contrapeso_posicion": _primer_texto_en_zona(pagina, 333, 350, 282, 370),
        "Limitador_contrapeso_ubicacion": _primer_texto_en_zona(pagina, 333, 350, 424, 520),
        "Pesacargas_fabricante": pesacargas[0] if len(pesacargas) > 0 else "",
        "Tipo_pesacargas": pesacargas[1] if len(pesacargas) > 1 else "",
        "Modelo_pesacargas": pesacargas[2] if len(pesacargas) > 2 else "",
        "Qt": _primer_texto_en_zona(pagina, 400, 416, 45, 82),
        "N_cables": _primer_texto_en_zona(pagina, 400, 416, 184, 230),
        "Diametro_cables": _primer_texto_en_zona(pagina, 400, 416, 243, 284),
        "Tension_pesacargas": tension[0] if tension else "",
        "Distancia_pesacargas_maniobra": distancia_luz[0] if len(distancia_luz) > 0 else "",
        "Luz_emergencia_cabina": distancia_luz[1] if len(distancia_luz) > 1 else "",
        "Pos_caja_cunas": pos_rescate[0] if len(pos_rescate) > 0 else "",
        "Rescate": pos_rescate[1] if len(pos_rescate) > 1 else "",
        "Comunicacion_suministro": comunicacion[0] if len(comunicacion) > 0 else "",
        "Modelo_comunicacion": comunicacion[1] if len(comunicacion) > 1 else "",
        "Idioma_voz": sintesis[0] if len(sintesis) > 0 else "",
        "Sintesis_voz": sintesis[1] if len(sintesis) > 1 else "",
        "Interfono_suministro": interfono[0] if interfono else "",
        "Enchufes": enchufes[0] if enchufes else "",
        "Distancia_a_maniobra": _valor_con_mm(pagina, 575, 592, 175, 230),
        "Ventilacion_maq_tipo": _primer_texto_en_zona(pagina, 575, 592, 500, 570),
        "Stop_adicional_foso_cant": _primer_texto_en_zona(pagina, 592, 610, 160, 220),
        "Stop_adicional_techo_cab_cant": _primer_texto_en_zona(pagina, 592, 610, 545, 585),
        "Tope_extra_foso_1_contacto_cant": _primer_texto_en_zona(pagina, 610, 626, 545, 585),
        "Rosario": rosario,
        "Cant_rosario": _numero_en_fila_despues_de_etiqueta(pagina, ["Rosario"], ["Cant"]),
        "Posicionamiento": _texto_en_fila_despues_de_etiqueta(pagina, ["Posicionamiento"]),
        "Ventilacion_cabina": _texto_en_fila_despues_de_etiqueta(pagina, ["Ventilación", "Cabina"]),
        "Suministrar_mandos_MCH_cant_txt": _primer_texto_en_zona(pagina, 710, 728, 555, 590),
    }


def _leer_accionamientos_limitador(valores: list[str]) -> tuple[str, str]:
    datos = [valor for valor in valores if valor != MARCA_CHECK]
    if len(datos) >= 2:
        return datos[0], datos[1]
    if datos:
        return "", datos[0]
    return "", ""


def _mezclar_valores_declarativos(resultado: dict[str, dict[str, str]], pagina: PaginaPdf, seccion: str) -> None:
    declarativos = extraer_por_reglas_pdf(pagina, seccion)
    if declarativos:
        resultado.setdefault(seccion, {}).update(declarativos)


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


def _primer_texto_en_zona(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 0,
    x_max: float = 10_000,
) -> str:
    ignorar = {MARCA_CHECK, "/", "V", "mm", "Kg", "Ø"}
    valores = [
        palabra.texto
        for palabra in sorted(pagina.palabras, key=lambda palabra: (palabra.y0, palabra.x0))
        if y_min <= palabra.y0 <= y_max
        and x_min <= palabra.x0 <= x_max
        and palabra.texto not in ignorar
    ]
    return valores[0] if valores else ""


def _texto_en_fila_despues_de_etiqueta(pagina: PaginaPdf, etiqueta: list[str]) -> str:
    fila, x_fin = _fila_y_fin_etiqueta(pagina, etiqueta)
    if not fila or x_fin is None:
        return ""
    return _texto_entre_x(fila, x_fin, None)


def _texto_entre_etiquetas_en_fila(
    pagina: PaginaPdf,
    etiqueta_inicio: list[str],
    etiqueta_fin: list[str],
) -> str:
    fila, x_fin = _fila_y_fin_etiqueta(pagina, etiqueta_inicio)
    if not fila or x_fin is None:
        return ""
    x_stop = _inicio_etiqueta_en_fila(fila, etiqueta_fin)
    return _texto_entre_x(fila, x_fin, x_stop)


def _numero_en_fila_despues_de_etiqueta(
    pagina: PaginaPdf,
    etiqueta_fila: list[str],
    etiqueta_valor: list[str],
) -> str:
    fila, x_fin = _fila_y_fin_etiqueta(pagina, etiqueta_valor, etiqueta_fila)
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


def _agrupar_por_fila(palabras: list[PalabraTexto]) -> list[list[PalabraTexto]]:
    filas: list[list[PalabraTexto]] = []
    for palabra in sorted(palabras, key=lambda item: (item.y0, item.x0)):
        if not filas or abs(filas[-1][0].y0 - palabra.y0) > 4:
            filas.append([palabra])
        else:
            filas[-1].append(palabra)
    return filas


def _inicio_etiqueta_en_fila(fila: list[PalabraTexto], etiqueta: list[str]) -> float | None:
    indice = _indice_etiqueta_en_fila(fila, etiqueta)
    return fila[indice].x0 if indice is not None else None


def _fin_etiqueta_en_fila(fila: list[PalabraTexto], etiqueta: list[str]) -> float | None:
    indice = _indice_etiqueta_en_fila(fila, etiqueta)
    if indice is None:
        return None
    return fila[indice + len(etiqueta) - 1].x1


def _indice_etiqueta_en_fila(fila: list[PalabraTexto], etiqueta: list[str]) -> int | None:
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


def _texto_entre_x(fila: list[PalabraTexto], x_min: float, x_max: float | None) -> str:
    valores = [
        palabra.texto
        for palabra in fila
        if palabra.x0 > x_min
        and (x_max is None or palabra.x0 < x_max)
        and palabra.texto not in {MARCA_CHECK, "mm"}
    ]
    return " ".join(valores).strip()


def _valor_con_mm(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float,
    x_max: float,
) -> str:
    valor = _primer_texto_en_zona(pagina, y_min, y_max, x_min, x_max)
    if valor.lower() == "mm":
        return ""
    return valor


def _check_en(
    pagina: PaginaPdf,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> bool:
    return any(
        x_min <= marca.x0 <= x_max and y_min <= marca.y0 <= y_max
        for marca in pagina.marcas_check
    )


def _si_no(valor: bool) -> str:
    return "Si" if valor else "No"


def _si_si_hay_valor(valor: str) -> str:
    return "Si" if valor else ""


def _debug_pdf_foso_opciones(data: dict[str, dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    valores_por_zona = {
        ("Gestion_foso_huida_reducida", "Huida_barandilla_cant"),
        ("Opciones", "Limitador_contrapeso_posicion"),
        ("Opciones", "Limitador_contrapeso_ubicacion"),
        ("Opciones", "Qt"),
        ("Opciones", "N_cables"),
        ("Opciones", "Diametro_cables"),
    } | {
        ("Gestion_foso_huida_reducida", "Foso_tope_cant"),
        ("Gestion_foso_huida_reducida", "Foso_tope_contactos"),
        ("Gestion_foso_huida_reducida", "Huida_tope_cant"),
        ("Gestion_foso_huida_reducida", "Huida_tope_ubicacion"),
        ("Opciones", "Limitador_velocidad_cab"),
        ("Opciones", "Limitador_posicion"),
        ("Opciones", "Limitador_ubicacion"),
        ("Opciones", "Accionamiento_a_dist_limitador"),
        ("Opciones", "Cont_sobrevel_a_dist"),
        ("Opciones", "Pesacargas_fabricante"),
        ("Opciones", "Tipo_pesacargas"),
        ("Opciones", "Modelo_pesacargas"),
        ("Opciones", "Tension_pesacargas"),
        ("Opciones", "Distancia_pesacargas_maniobra"),
        ("Opciones", "Luz_emergencia_cabina"),
        ("Opciones", "Pos_caja_cunas"),
        ("Opciones", "Rescate"),
        ("Opciones", "Comunicacion_suministro"),
        ("Opciones", "Modelo_comunicacion"),
        ("Opciones", "Idioma_voz"),
        ("Opciones", "Sintesis_voz"),
        ("Opciones", "Interfono_suministro"),
        ("Opciones", "Enchufes"),
        ("Opciones", "Distancia_a_maniobra"),
        ("Opciones", "Ventilacion_maq_tipo"),
        ("Opciones", "Stop_adicional_foso_cant"),
        ("Opciones", "Stop_adicional_techo_cab_cant"),
        ("Opciones", "Tope_extra_foso_1_contacto_cant"),
        ("Opciones", "Rosario"),
        ("Opciones", "Cant_rosario"),
        ("Opciones", "Posicionamiento"),
        ("Opciones", "Suministrar_mandos_MCH_cant_txt"),
    }
    debug: dict[str, dict[str, dict[str, str]]] = {}
    for seccion, campos in data.items():
        debug[seccion] = {}
        for campo, valor in campos.items():
            clave = (seccion, campo)
            if clave in valores_por_zona:
                fuente = "valor_leido" if valor else "zona_vacia"
            elif valor in {"Si", "No"}:
                fuente = "check_zona"
            elif valor:
                fuente = "valor_leido"
            else:
                fuente = "zona_vacia"
            debug[seccion][campo] = {"valor": valor, "fuente": fuente}
    return debug

