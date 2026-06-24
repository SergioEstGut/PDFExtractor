from typing import Any

import re

from extractor_pdf.domain.entidades import PaginaPdf, PalabraTexto
from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import aplicar_contrato_salida
from extractor_pdf.infrastructure.extraction.client_base.extraccion_declarativa_pdf import extraer_por_reglas_pdf

MARCA_CHECK = "\x14"

class ExtractorPaginaTecnicaRaloeCrono:
    """Extractor determinista para la pagina tecnica principal del cliente base."""

    def extraer_con_debug(self, pagina: PaginaPdf) -> dict[str, Any]:
        data = self.extraer(pagina)
        return {"data": data, "debug_pdf": _debug_pdf_pagina_tecnica(data)}

    def extraer(self, pagina: PaginaPdf) -> dict[str, Any]:
        valores_generales = self._valores_de_bloque(pagina, y_min=190, y_max=225, x_min=50, x_max=100)
        caracteristicas_principales = self._valores_de_bloque(
            pagina, y_min=305, y_max=326, x_min=70, x_max=90
        )
        caracteristicas_tension = self._valores_de_bloque(
            pagina, y_min=326, y_max=348, x_min=120, x_max=140
        )
        intensidad_motor = self._valores_de_bloque(
            pagina, y_min=346, y_max=366, x_min=100, x_max=120
        )
        intensidad_sobredim = self._valores_de_bloque(
            pagina, y_min=366, y_max=386, x_min=120, x_max=140
        )
        valores_motor = self._valores_de_bloque(pagina, y_min=405, y_max=426, x_min=75, x_max=90)
        valores_potencia = _valores_numericos_en_fila(pagina, y_min=428, y_max=448, x_min=70, x_max=395)
        freno_lento_apertura = _primer_texto_en_zona(pagina, 428, 448, 525, 545)
        freno_lento_mantenimiento = _primer_texto_en_zona(pagina, 428, 448, 550, 570)
        valores_variador = self._valores_de_bloque(pagina, y_min=450, y_max=471, x_min=70, x_max=80)
        valores_parametros = self._valores_de_bloque(pagina, y_min=471, y_max=491, x_min=25, x_max=40)
        valores_encoder = self._valores_de_bloque(pagina, y_min=491, y_max=511, x_min=25, x_max=40)
        cable_valores_potencia = self._valores_de_bloque(pagina, y_min=511, y_max=531, x_min=25, x_max=40)
        valores_cable_accesorios = self._valores_de_bloque(
            pagina, y_min=531, y_max=550, x_min=25, x_max=40
        )
        fabricantes_puerta = self._valores_de_rangos(pagina, 635, 655, [(85, 100), (405, 420)])
        tipos_puerta = self._valores_de_rangos(pagina, 656, 676, [(85, 100), (405, 420)])
        manos_puerta = self._valores_de_rangos(pagina, 675, 695, [(85, 100), (405, 420)])
        circuitos_puerta = self._valores_de_rangos(pagina, 697, 717, [(85, 100), (405, 420)])
        tensiones_puerta = self._valores_de_rangos(pagina, 720, 740, [(85, 100), (405, 420)])
        barreras_puerta = self._valores_de_bloque(pagina, y_min=742, y_max=762, x_min=25, x_max=40)
        hidraulica_fabricante = _primer_texto_en_zona(pagina, 572, 592, 80, 155)
        hidraulica_grupo_valvulas = _primer_texto_en_zona(pagina, 572, 592, 230, 320)
        hidraulica_tension_valvulas = _primer_texto_en_zona(pagina, 572, 592, 405, 432)
        hidraulica_potencia = _primer_texto_en_zona(pagina, 592, 612, 75, 100)
        hidraulica_tipo_arranque = _primer_texto_en_zona(pagina, 592, 612, 225, 330)

        consola_vf_marcada = _check_en(pagina, 25, 45, 471, 491)
        tiene_consola_vf_txt = len(valores_parametros) >= 6
        desplazamiento_parametros = 1 if tiene_consola_vf_txt else 0
        parametros_traccion = _parametros_traccion_desde_fila(pagina, valores_parametros, desplazamiento_parametros)
        existe_puerta_2 = len(fabricantes_puerta) > 1
        longitud_cable_potencia = _longitud_mm(cable_valores_potencia)
        micros = _texto_sin_longitudes(cable_valores_potencia)
        longitud_cable_accesorios = _longitud_mm(valores_cable_accesorios)

        resultado = {
            "general": _seccion_con_fallback(
                extraer_por_reglas_pdf(pagina, "general"),
                {
                    "Serie": valores_generales[3],
                    "Pais_instalacion": valores_generales[2],
                    "Idioma_documentacion": valores_generales[1],
                    "Especificacion_norte_africa": _si_no(_check_en(pagina, 25, 45, 220, 236)),
                },
            ),
            "Normas": _seccion_con_fallback(
                extraer_por_reglas_pdf(pagina, "Normas"),
                {
                    "Norma_81_1_A3": _si_no(_check_en(pagina, 25, 50, 255, 270)),
                    "Norma_81_2_A3": _si_no(_check_en(pagina, 105, 130, 255, 270)),
                    "Norma_81_20_50": _si_no(_check_en(pagina, 175, 200, 255, 270)),
                    "Norma_81_70": _si_no(_check_en(pagina, 250, 275, 255, 270)),
                    "Norma_81_71_CAT_1": _si_no(_check_en(pagina, 335, 360, 255, 270)),
                    "Norma_81_71_CAT_2": _si_no(_check_en(pagina, 412, 440, 255, 270)),
                    "BS9999": _si_no(_check_en(pagina, 480, 505, 255, 270)),
                    "Norma_81_72": _si_no(_check_en(pagina, 25, 50, 272, 288)),
                    "Norma_81_77": _si_no(_check_en(pagina, 105, 135, 272, 288)),
                    "Norma_81_73": _si_no(_check_en(pagina, 250, 275, 272, 288)),
                    "Norma_81_73_txt": _primer_texto_en_zona(pagina, 272, 288, 305, 405),
                    "Shabbat": _si_no(_check_en(pagina, 412, 440, 272, 288)),
                },
            ),
            "Caracteristicas": _seccion_con_fallback(
                extraer_por_reglas_pdf(pagina, "Caracteristicas"),
                {
                    "Maniobra": caracteristicas_principales[0],
                    "Tipo": caracteristicas_principales[1],
                    "Arq": caracteristicas_principales[2],
                    "Consola_maniobra": _si_no(_check_en(pagina, 470, 500, 305, 326)),
                    "Tension_linea": caracteristicas_tension[1],
                    "Tension_motor": caracteristicas_tension[2],
                    "Mono": _si_no(_check_en(pagina, 210, 235, 328, 346)),
                    "Tri": _si_no(_check_en(pagina, 270, 295, 328, 346)),
                    "Velocidad": caracteristicas_tension[3],
                    "Paradas": caracteristicas_tension[0],
                    "Intensidad_motor": intensidad_motor[0],
                    "Frecuencia_50_Hz": _si_no(_check_en(pagina, 210, 235, 345, 365)),
                    "Frecuencia_60_Hz": _si_no(_check_en(pagina, 270, 295, 345, 365)),
                    "Neutro": _si_no(_check_en(pagina, 355, 380, 345, 365)),
                    "Intensidad_sobredim": intensidad_sobredim[0],
                    "Sin_cuarto_de_maquinas": _si_no(_check_en(pagina, 210, 235, 365, 386)),
                    "Maquina_arriba": _si_no(_check_en(pagina, 355, 380, 365, 386)),
                    "Maquina_abajo": _si_no(_check_en(pagina, 470, 500, 365, 386)),
                },
            ),
            "Traccion_electrica": _seccion_con_fallback(
                extraer_por_reglas_pdf(pagina, "Traccion_electrica"),
                {
                    "Fabricante_motor": valores_motor[2],
                    "Modelo_motor": valores_motor[3],
                    "Tipo_traccion": valores_motor[1],
                    "Frec_motor": valores_motor[0],
                    "PotenciaCV": valores_potencia[0],
                    "PotenciaKW": valores_potencia[1],
                    "Tension_freno_apertura": valores_potencia[2],
                    "Tension_freno_mantenimiento": valores_potencia[3],
                    "Pot": valores_potencia[4],
                    "Freno_lento_apertura": freno_lento_apertura,
                    "Freno_lento_mantenimiento": freno_lento_mantenimiento,
                    "Variador": valores_variador[0],
                    "Modelo": valores_variador[1],
                    "Talla": valores_variador[2],
                    "ED": valores_variador[3],
                    "F_Conm": valores_variador[4],
                    "Consola_VF": _si_no(consola_vf_marcada),
                    "Consola_VF_txt": parametros_traccion["Consola_VF_txt"],
                    "Parametro": parametros_traccion["Parametro"],
                    "Rpm": parametros_traccion["Rpm"],
                    "Relacion": parametros_traccion["Relacion"],
                    "Polea": parametros_traccion["Polea"],
                    "Encoder": "Si" if _valor_en(valores_encoder, 3) else "",
                    "Encoder_txt": _valor_en(valores_encoder, 3),
                    "Protocolo": _valor_en(valores_encoder, 0),
                    "Fasado": _valor_en(valores_encoder, 1),
                    "N_Polos": _valor_en(valores_encoder, 2),
                    "Autotrafo_240_400": _si_no(_check_en(pagina, 470, 500, 492, 510)),
                    "Cable_potencia": _si_no(_check_en(pagina, 25, 45, 512, 530)),
                    "Longitud_cable_potencia": longitud_cable_potencia,
                    "Micros": micros,
                    "Cableado_accesorios": _si_no(_check_en(pagina, 25, 45, 532, 550)),
                    "Longitud_cable_accesorios": longitud_cable_accesorios,
                    "Conectores": _si_no(_check_en(pagina, 400, 425, 532, 550)),
                },
            ),
            "Traccion_hidraulica": _seccion_con_fallback(
                extraer_por_reglas_pdf(pagina, "Traccion_hidraulica"),
                {
                    "Fabricante_oleo": hidraulica_fabricante,
                    "Grupo_valvulas": hidraulica_grupo_valvulas,
                    "Tension_valvulas": hidraulica_tension_valvulas,
                    "Potencia_oleo": hidraulica_potencia,
                    "Tipo_arranque": hidraulica_tipo_arranque,
                    "Suministrar_softstarter": _si_no(_check_en(pagina, 405, 425, 594, 612)),
                },
            ),
            "Puertas_cabina_embarque_1": _seccion_con_fallback(
                extraer_por_reglas_pdf(pagina, "Puertas_cabina_embarque_1"),
                {
                    "Fabricante_op1": fabricantes_puerta[0],
                    "Tipo_op1": tipos_puerta[0],
                    "Mano_op1": manos_puerta[0],
                    "Circuito_op1": circuitos_puerta[0],
                    "Tension_op1": tensiones_puerta[0],
                    "Barreras_Op1": "Si" if _valor_en(barreras_puerta, 0) else "",
                    "Barreras_Op1_txt": _valor_en(barreras_puerta, 0),
                    "Apertura_emergencia_op1": _si_no(_check_en(pagina, 25, 45, 760, 780)),
                    "Apertura_emergencia_op1_txt": "",
                    "Leva_electrica_op1": _si_no(_check_en(pagina, 25, 45, 780, 800)),
                    "Leva_electrica_op1_txt": "",
                },
            ),
            "Puertas_cabina_embarque_2": _seccion_con_fallback(
                extraer_por_reglas_pdf(pagina, "Puertas_cabina_embarque_2"),
                {
                    "Fabricante_op2": fabricantes_puerta[1] if existe_puerta_2 else "",
                    "Tipo_op2": tipos_puerta[1] if existe_puerta_2 else "",
                    "Mano_op2": manos_puerta[1] if existe_puerta_2 else "",
                    "Circuito_op2": circuitos_puerta[1] if existe_puerta_2 else "",
                    "Tension_op2": tensiones_puerta[1] if existe_puerta_2 else "",
                    "Barreras_op2": "Si" if existe_puerta_2 and _valor_en(barreras_puerta, 1) else "",
                    "Barreras_Op2_txt": _valor_en(barreras_puerta, 1) if existe_puerta_2 else "",
                    "Apertura_emergencia_op2": _si_no(_check_en(pagina, 350, 375, 760, 780)),
                    "Apertura_emergencia_op2_txt": "",
                    "Leva_electrica_op2": _si_no(_check_en(pagina, 350, 375, 780, 800)),
                    "Leva_electrica_op2_txt": "",
                },
            ),
        }
        return aplicar_contrato_salida(resultado)

    @staticmethod
    def _valores_de_bloque(
        pagina: PaginaPdf,
        y_min: float,
        y_max: float,
        x_min: float = 0,
        x_max: float = 10_000,
    ) -> list[str]:
        valores: list[str] = []
        for bloque in pagina.bloques:
            if y_min <= bloque.y0 <= y_max and x_min <= bloque.x0 <= x_max:
                valores.extend(
                    valor.strip()
                    for valor in bloque.texto.splitlines()
                    if valor.strip() and valor.strip() != MARCA_CHECK
                )
        return valores

    @classmethod
    def _valores_de_rangos(
        cls,
        pagina: PaginaPdf,
        y_min: float,
        y_max: float,
        rangos_x: list[tuple[float, float]],
    ) -> list[str]:
        valores: list[str] = []
        for x_min, x_max in rangos_x:
            valores.extend(cls._valores_de_bloque(pagina, y_min, y_max, x_min, x_max))
        return valores

    @staticmethod
    def _tiene_check(
        pagina: PaginaPdf,
        y_min: float,
        y_max: float,
        x_min: float = 0,
        x_max: float = 10_000,
    ) -> bool:
        return any(
            MARCA_CHECK in bloque.texto and y_min <= bloque.y0 <= y_max and x_min <= bloque.x0 <= x_max
            for bloque in pagina.bloques
        )


def _si_no(valor: bool) -> str:
    return "Si" if valor else "No"


def _longitud_mm(valores: list[str]) -> str:
    for valor in valores:
        if re.fullmatch(r"\d+(?:[.,]\d{3})?", valor):
            return valor
    return ""


def _texto_sin_longitudes(valores: list[str]) -> str:
    return " ".join(valor for valor in valores if not re.fullmatch(r"\d+(?:[.,]\d{3})?", valor))


def _valores_numericos_en_fila(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 0,
    x_max: float = 10_000,
) -> list[str]:
    return [
        palabra.texto
        for palabra in sorted(pagina.palabras, key=lambda palabra: palabra.x0)
        if y_min <= palabra.y0 <= y_max
        and x_min <= palabra.x0 <= x_max
        and re.fullmatch(r"\d+(?:[.,]\d+)?", palabra.texto)
    ]


def _valor_en(valores: list[str], indice: int) -> str:
    return valores[indice] if 0 <= indice < len(valores) else ""


def _seccion_con_fallback(declarativa: dict[str, str], fallback: dict[str, str]) -> dict[str, str]:
    resultado = dict(fallback)
    for campo, valor in declarativa.items():
        if valor != "":
            resultado[campo] = valor
    return resultado


def _parametros_traccion_desde_fila(
    pagina: PaginaPdf,
    valores_parametros: list[str],
    desplazamiento_parametros: int,
) -> dict[str, str]:
    fallback = {
        "Consola_VF_txt": valores_parametros[0] if desplazamiento_parametros else "",
        "Parametro": _valor_en(valores_parametros, desplazamiento_parametros),
        "Rpm": _valor_en(valores_parametros, desplazamiento_parametros + 3),
        "Relacion": _valor_en(valores_parametros, desplazamiento_parametros + 1),
        "Polea": _valor_en(valores_parametros, desplazamiento_parametros + 2),
    }
    palabras = [
        palabra
        for palabra in sorted(pagina.palabras, key=lambda palabra: palabra.x0)
        if 471 <= palabra.y0 <= 491 and 20 <= palabra.x0 <= 570
    ]
    if not palabras:
        return fallback

    consola_fin = _fin_secuencia(palabras, ["Consola", "VF"])
    parametro = _palabra_con_prefijo(palabras, ("Parámetro", "Parametro"))
    rpm = _palabra_con_prefijo(palabras, ("Rpm",))
    relacion = _palabra_con_prefijo(palabras, ("Relación", "Relacion"))
    polea = _palabra_con_prefijo(palabras, ("Polea",))

    extraido = {
        "Consola_VF_txt": _texto_entre(palabras, consola_fin, parametro.x0 if parametro else None),
        "Parametro": _primer_valor_tras_etiqueta(palabras, parametro, rpm),
        "Rpm": _primer_numero_tras_etiqueta(palabras, rpm, relacion),
        "Relacion": _primer_valor_tras_etiqueta(palabras, relacion, polea),
        "Polea": _primer_numero_tras_etiqueta(palabras, polea, None),
    }
    return {campo: valor or fallback[campo] for campo, valor in extraido.items()}


def _fin_secuencia(palabras: list[PalabraTexto], secuencia: list[str]) -> float | None:
    normalizada = [_normalizar_etiqueta(palabra.texto) for palabra in palabras]
    objetivo = [_normalizar_etiqueta(token) for token in secuencia]
    for indice in range(0, len(normalizada) - len(objetivo) + 1):
        if normalizada[indice : indice + len(objetivo)] == objetivo:
            return palabras[indice + len(objetivo) - 1].x1
    return None


def _palabra_con_prefijo(palabras: list[PalabraTexto], prefijos: tuple[str, ...]) -> PalabraTexto | None:
    prefijos_normalizados = tuple(_normalizar_etiqueta(prefijo) for prefijo in prefijos)
    for palabra in palabras:
        texto = _normalizar_etiqueta(palabra.texto.rstrip(":"))
        if texto in prefijos_normalizados:
            return palabra
    return None


def _normalizar_etiqueta(texto: str) -> str:
    reemplazos = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
    return texto.translate(reemplazos).strip().lower()


def _texto_entre(palabras: list[PalabraTexto], x_min: float | None, x_max: float | None) -> str:
    if x_min is None or x_max is None:
        return ""
    valores = [
        palabra.texto
        for palabra in palabras
        if palabra.x0 > x_min and palabra.x1 < x_max and palabra.texto != MARCA_CHECK
    ]
    return " ".join(valores).strip()


def _primer_valor_tras_etiqueta(
    palabras: list[PalabraTexto],
    etiqueta: PalabraTexto | None,
    siguiente_etiqueta: PalabraTexto | None,
) -> str:
    if etiqueta is None:
        return ""
    limite = siguiente_etiqueta.x0 if siguiente_etiqueta else 10_000
    for palabra in palabras:
        if etiqueta.x1 < palabra.x0 < limite and palabra.texto not in {MARCA_CHECK, "mm"}:
            return palabra.texto
    return ""


def _primer_numero_tras_etiqueta(
    palabras: list[PalabraTexto],
    etiqueta: PalabraTexto | None,
    siguiente_etiqueta: PalabraTexto | None,
) -> str:
    if etiqueta is None:
        return ""
    limite = siguiente_etiqueta.x0 if siguiente_etiqueta else 10_000
    for palabra in palabras:
        if etiqueta.x1 < palabra.x0 < limite and re.fullmatch(r"\d+(?:[.,]\d+)?", palabra.texto):
            return palabra.texto
    return ""


def _primer_texto_en_zona(
    pagina: PaginaPdf,
    y_min: float,
    y_max: float,
    x_min: float = 0,
    x_max: float = 10_000,
) -> str:
    ignorar = {MARCA_CHECK, "/", "V", "CV", "Kw", "W", "mm", "A"}
    valores = [
        palabra.texto
        for palabra in sorted(pagina.palabras, key=lambda palabra: (palabra.y0, palabra.x0))
        if y_min <= palabra.y0 <= y_max
        and x_min <= palabra.x0 <= x_max
        and palabra.texto not in ignorar
    ]
    return valores[0] if valores else ""


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


def _debug_pdf_pagina_tecnica(data: dict[str, dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    valores_por_zona = {
        ("Traccion_electrica", "Freno_lento_apertura"),
        ("Traccion_electrica", "Freno_lento_mantenimiento"),
        ("Traccion_hidraulica", "Fabricante_oleo"),
        ("Traccion_hidraulica", "Grupo_valvulas"),
        ("Traccion_hidraulica", "Tension_valvulas"),
        ("Traccion_hidraulica", "Potencia_oleo"),
        ("Traccion_hidraulica", "Tipo_arranque"),
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
