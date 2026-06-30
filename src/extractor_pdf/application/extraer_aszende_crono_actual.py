from __future__ import annotations

from io import BytesIO
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from extractor_pdf.application.campos_extra import SECCION_CAMPOS_EXTRA, detectar_campos_extra
from extractor_pdf.application.notas_extra import SECCION_NOTAS_EXTRA, detectar_notas_extra
from extractor_pdf.domain.entidades import PaginaPdf, PalabraTexto
from extractor_pdf.domain.puertos import LectorTextoPdf
from extractor_pdf.infrastructure.extraction.client_base.extraccion_declarativa_pdf import (
    extraer_por_reglas_pdf,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_aszende_crono import (
    detectar_paginas_aszende_crono,
    detectar_plantilla_aszende_crono,
)


TEMPLATE_ASZENDE_ELECTRICO = "aszende_crono_electrico"


class CasoUsoExtraerAszendeCronoActual:
    def __init__(self, lector_pdf: LectorTextoPdf | None = None) -> None:
        self.lector_pdf = lector_pdf or LectorTextoPyMuPdf()

    def ejecutar(self, bytes_pdf: bytes) -> dict[str, Any]:
        paginas = self.lector_pdf.leer_paginas(bytes_pdf)
        template_id = detectar_plantilla_aszende_crono(paginas)
        pages = detectar_paginas_aszende_crono(paginas)
        contratos = _cargar_contratos_aszende(template_id)
        data = _datos_vacios_aszende(contratos)
        warnings: list[str] = []

        pagina_principal = _pagina_por_rol(paginas, pages, "principal", warnings)
        if pagina_principal:
            _avisar_si_texto_pdf_no_confiable(pagina_principal, "principal", warnings)
            _extraer_secciones(
                data,
                contratos,
                pagina_principal,
                _secciones_para_rol(contratos, "principal"),
            )
            _aplicar_extracciones_estructurales(data, pagina_principal)

        _aplicar_derivados(data, contratos)
        data["Observaciones"]["Observaciones"] = _extraer_observaciones_aszende(
            pagina_principal
        )
        secciones_por_pagina = _secciones_por_pagina(pages, contratos)
        paginas_con_datos = _paginas_detectadas(paginas, pages)
        campos_extra = detectar_campos_extra(
            paginas_con_datos,
            data,
            secciones_por_pagina,
            _directorio_secciones_aszende(template_id),
            detectar_conocidos_fuera_de_seccion=False,
            claves_ignoradas={"PLACA_PARA_BOTONERAS_DE_RELLANO"},
            ignorar_lineas_desde_y=735,
        )
        data[SECCION_CAMPOS_EXTRA] = campos_extra
        data[SECCION_NOTAS_EXTRA] = _decodificar_notas_aszende(
            detectar_notas_extra(
                paginas_con_datos,
                secciones_por_pagina,
                ignorar_tonos_azules=True,
                ignorar_tonos_grises_claros=True,
                detectar_marcas_visuales=True,
                incluir_coordenadas=True,
            ),
            bytes_pdf,
        )
        if campos_extra:
            warnings.append("Se detectaron campos extra no contemplados en el contrato.")

        return {
            "data": data,
            "metadata": {
                "profile_id": "aszende_crono",
                "template_id": template_id,
                "form_version": "0",
                "pages": pages,
                "principal_page": pages.get("principal"),
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
        _aplicar_dependencias(extraido, especificaciones)
        data[seccion].update(extraido)


def _aplicar_extracciones_estructurales(data: dict[str, Any], pagina: PaginaPdf) -> None:
    _actualizar_si_hay_valor(data, "Normas", _extraer_normas_estructurales(pagina))
    _actualizar_si_hay_valor(
        data,
        "Medidas_Entreplantas",
        _extraer_medidas_entreplantas_estructurales(pagina),
    )
    _actualizar_si_hay_valor(data, "Datos_Motor", _extraer_datos_motor_estructurales(pagina))


def _actualizar_si_hay_valor(
    data: dict[str, Any],
    seccion: str,
    valores: dict[str, str],
) -> None:
    datos_seccion = data.get(seccion)
    if not isinstance(datos_seccion, dict):
        return
    for campo, valor in valores.items():
        if valor != "":
            datos_seccion[campo] = valor


def _extraer_normas_estructurales(pagina: PaginaPdf) -> dict[str, str]:
    palabras_valor = [
        palabra
        for palabra in pagina.palabras
        if 25 <= palabra.x0 <= 190
        and 168 <= palabra.y0 <= 250
        and _parece_valor_norma(palabra)
    ]
    filas = _agrupar_por_fila(palabras_valor, tolerancia_y=7)
    filas = [
        fila
        for fila in filas
        if any(_normalizar_texto(palabra.texto) in {"si", "no"} for palabra in fila)
        or len(fila) > 1
    ]

    valores: dict[str, str] = {}
    orden = [
        ("EN81_20", "EN81_72"),
        ("Anti_UCM_A3",),
        ("EN81_70",),
        ("EN81_71", "EN81_73"),
        ("EN81_77_sismico",),
    ]
    if _pagina_contiene_alias(pagina, {"U-36", "U 36"}):
        orden.append(("U_36",))

    for fila, campos in zip(filas, orden):
        tokens = [
            palabra.texto
            for palabra in sorted(fila, key=lambda item: item.x0)
            if not _es_ruido_estructural(palabra.texto)
        ]
        if not tokens:
            continue
        if len(campos) == 1:
            valores[campos[0]] = " ".join(tokens).strip()
            continue
        tokens_izquierda = [token for token in tokens if token]
        if len(tokens_izquierda) >= 1:
            valores[campos[0]] = tokens_izquierda[0]
        if len(tokens_izquierda) >= 2:
            valores[campos[1]] = tokens_izquierda[1]
    return valores


def _pagina_contiene_alias(pagina: PaginaPdf, aliases: set[str]) -> bool:
    texto = " ".join(palabra.texto for palabra in pagina.palabras)
    texto_normalizado = _normalizar_texto(texto)
    return any(_normalizar_texto(alias) in texto_normalizado for alias in aliases)


def _parece_valor_norma(palabra: PalabraTexto) -> bool:
    if _es_ruido_estructural(palabra.texto):
        return False
    if palabra.color in {2301728, 9672088}:
        return False
    return True


def _extraer_medidas_entreplantas_estructurales(pagina: PaginaPdf) -> dict[str, str]:
    valores: dict[str, str] = {}
    columnas = [
        {
            "labels": ["P6", "P5", "P4", "P3", "P2", "P1"],
            "x_linea_min": 400,
            "x_linea_max": 437,
            "x_valor_min": 402,
            "x_valor_max": 440,
        },
        {
            "labels": ["P12", "P11", "P10", "P9", "P8", "P7"],
            "x_linea_min": 454,
            "x_linea_max": 493,
            "x_valor_min": 452,
            "x_valor_max": 496,
        },
        {
            "labels": ["P18", "P17", "P16", "P15", "P14", "P13"],
            "x_linea_min": 512,
            "x_linea_max": 550,
            "x_valor_min": 510,
            "x_valor_max": 556,
        },
    ]
    for columna in columnas:
        anclas = _anclas_columna_entreplantas_desde_lineas(pagina, columna)
        for campo, y_ancla in zip(columna["labels"], anclas):
            valor = _numero_en_banda(
                pagina,
                x_min=float(columna["x_valor_min"]),
                x_max=float(columna["x_valor_max"]),
                y_min=y_ancla - 7,
                y_max=y_ancla + 4,
            )
            if valor:
                valores[campo] = valor
    return valores


def _anclas_columna_entreplantas_desde_lineas(
    pagina: PaginaPdf,
    columna: dict[str, Any],
) -> list[float]:
    palabras = [
        palabra
        for palabra in pagina.palabras
        if float(columna["x_linea_min"]) <= palabra.x0 <= float(columna["x_linea_max"])
        and 298 <= palabra.y0 <= 371
        and _es_linea_entreplanta(palabra.texto)
    ]
    anclas: list[float] = []
    for palabra in sorted(palabras, key=lambda item: item.y0):
        if anclas and abs(anclas[-1] - palabra.y0) <= 4:
            continue
        anclas.append(palabra.y0)
    return anclas[:6]


def _es_linea_entreplanta(texto: str) -> bool:
    limpio = texto.strip()
    if not limpio:
        return False
    return "." in limpio or "Ť" in limpio or "_" in limpio


def _numero_en_banda(
    pagina: PaginaPdf,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> str:
    candidatos = [
        palabra
        for palabra in pagina.palabras
        if x_min <= palabra.x0 <= x_max
        and y_min <= palabra.y0 <= y_max
        and re.fullmatch(r"\d+(?:[.,]\d+)?", palabra.texto.strip())
    ]
    if not candidatos:
        return ""
    return candidatos[0].texto.replace(",", ".")


def _extraer_datos_motor_estructurales(pagina: PaginaPdf) -> dict[str, str]:
    valores: dict[str, str] = {}
    tipo_encoder = _texto_blanco_en_banda(
        pagina,
        x_min=85,
        x_max=150,
        y_min=520,
        y_max=532,
    )
    if tipo_encoder:
        valores["Tipo_encoder"] = tipo_encoder
    return valores


def _texto_blanco_en_banda(
    pagina: PaginaPdf,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> str:
    palabras = [
        palabra
        for palabra in pagina.palabras
        if x_min <= palabra.x0 <= x_max
        and y_min <= palabra.y0 <= y_max
        and palabra.color == 16777215
        and not _es_ruido_estructural(palabra.texto)
    ]
    return " ".join(palabra.texto for palabra in sorted(palabras, key=lambda item: item.x0)).strip()


def _agrupar_por_fila(
    palabras: list[PalabraTexto],
    tolerancia_y: float,
) -> list[list[PalabraTexto]]:
    filas: list[list[PalabraTexto]] = []
    for palabra in sorted(palabras, key=lambda item: (item.y0, item.x0)):
        if not filas or abs(filas[-1][0].y0 - palabra.y0) > tolerancia_y:
            filas.append([palabra])
        else:
            filas[-1].append(palabra)
    return filas


def _es_ruido_estructural(texto: str) -> bool:
    texto = texto.strip()
    if not texto:
        return True
    if texto == "\x14":
        return True
    return bool(re.fullmatch(r"[\W_Ť.·:;-]+", texto))


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


def _aplicar_dependencias(
    valores: dict[str, str],
    especificaciones: dict[str, dict[str, Any]],
) -> None:
    for campo, especificacion in especificaciones.items():
        dependencia_vacio = especificacion.get("reglas", {}).get("vaciar_si_campo_vacio")
        if not dependencia_vacio:
            continue
        if not valores.get(dependencia_vacio, ""):
            valores[campo] = ""


def _aplicar_derivados(
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
            valores_secuencia = data.get(derivado.get("seccion_secuencia", ""))
            secuencia = ""
            if isinstance(valores_secuencia, dict):
                secuencia = str(valores_secuencia.get(derivado.get("campo_secuencia", ""), ""))
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
    contratos: dict[str, dict[str, Any]],
) -> dict[int, list[str]]:
    pagina_principal = pages.get("principal")
    if pagina_principal is None:
        return {}
    return {pagina_principal: _secciones_para_rol(contratos, "principal")}


def _secciones_para_rol(
    contratos: dict[str, dict[str, Any]],
    rol: str,
) -> list[str]:
    return [
        seccion
        for seccion, contrato in contratos.items()
        if contrato.get("extraccion_pdf", {}).get("pagina_rol") == rol
    ]


def _paginas_detectadas(paginas: list[PaginaPdf], pages: dict[str, int]) -> list[PaginaPdf]:
    numeros = {numero for numero in pages.values() if numero is not None}
    return [pagina for pagina in paginas if pagina.numero in numeros]


def _extraer_observaciones_aszende(pagina: PaginaPdf | None) -> str:
    if pagina is None:
        return ""
    palabras = [
        palabra
        for palabra in pagina.palabras
        if 748 <= palabra.y0 <= 805
        and 30 <= palabra.x0 <= 560
        and _es_color_respuesta_aszende(palabra.color)
        and not _es_ruido_observaciones_aszende(palabra.texto)
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
        texto = _decodificar_texto_aszende_si_corrupto(texto)
        if texto:
            textos.append(texto)
    return "\n".join(textos)


def _es_ruido_observaciones_aszende(texto: str) -> bool:
    texto = texto.strip()
    if not texto:
        return True
    if texto == "\x14":
        return True
    if _normalizar_texto(texto) == "observaciones":
        return True
    if len(texto) > 2 and re.fullmatch(r"[.·«»Ť_ -]+", texto):
        return True
    return False


def _es_color_respuesta_aszende(color: int | None) -> bool:
    if color is None:
        return False
    rojo = (color >> 16) & 255
    verde = (color >> 8) & 255
    azul = color & 255
    return rojo <= 80 and verde <= 110 and azul <= 190


def _decodificar_notas_aszende(
    notas: list[dict[str, Any]],
    bytes_pdf: bytes | None = None,
) -> list[dict[str, Any]]:
    for nota in notas:
        valor = nota.get("valor")
        if isinstance(valor, str):
            valor_ocr = _leer_nota_aszende_por_ocr(bytes_pdf, nota, valor)
            if valor_ocr:
                nota["valor"] = valor_ocr
            elif valor.strip() in {"P", "V"}:
                nota["valor"] = _decodificar_token_aszende_corrupto(valor.strip())
            else:
                nota["valor"] = _decodificar_texto_aszende_si_corrupto(valor)
        for clave in ("x0", "y0", "x1", "y1"):
            nota.pop(clave, None)
    return notas


def _leer_nota_aszende_por_ocr(
    bytes_pdf: bytes | None,
    nota: dict[str, Any],
    valor_pdf: str,
) -> str:
    if not bytes_pdf or not _nota_aszende_requiere_ocr(valor_pdf):
        return ""
    try:
        import fitz
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError:
        return ""

    try:
        pagina_numero = int(nota.get("pagina", 0))
        if pagina_numero <= 0:
            return ""
        x0 = float(nota["x0"])
        y0 = float(nota["y0"])
        x1 = float(nota["x1"])
        y1 = float(nota["y1"])
    except (KeyError, TypeError, ValueError):
        return ""

    documento = None
    try:
        documento = fitz.open(stream=bytes_pdf, filetype="pdf")
        pagina = documento[pagina_numero - 1]
        rect = fitz.Rect(
            max(0, x0 - 8),
            max(0, y0 - 5),
            min(float(pagina.rect.width), x1 + 12),
            min(float(pagina.rect.height), y1 + 7),
        )
        pixmap = pagina.get_pixmap(dpi=450, clip=rect, alpha=False)
        imagen = Image.open(BytesIO(pixmap.tobytes("png")))
        imagen = ImageOps.grayscale(imagen)
        imagen = ImageOps.autocontrast(imagen)
        texto = pytesseract.image_to_string(
            imagen,
            lang="spa+eng",
            config="--psm 7",
        )
    except Exception:
        return ""
    finally:
        if documento is not None:
            documento.close()

    texto_limpio = _limpiar_texto_ocr_nota_aszende(texto)
    if not texto_limpio:
        return ""
    if _texto_ocr_nota_es_util(texto_limpio, valor_pdf):
        return texto_limpio
    return ""


def _nota_aszende_requiere_ocr(valor: str) -> bool:
    if not _parece_texto_aszende_corrupto(valor):
        return False
    if valor.strip() in {"P", "V"}:
        return False
    return True


def _limpiar_texto_ocr_nota_aszende(texto: str) -> str:
    lineas = [" ".join(linea.split()) for linea in texto.splitlines()]
    texto_limpio = " ".join(linea for linea in lineas if linea)
    texto_limpio = texto_limpio.replace("—", "-").replace("–", "-")
    texto_limpio = re.sub(r"\s+([,.;:])", r"\1", texto_limpio)
    texto_limpio = re.sub(r"\s*-\s*", "-", texto_limpio)
    texto_limpio = re.sub(r"\s+", " ", texto_limpio)
    return texto_limpio.strip(" .\n\t")


def _texto_ocr_nota_es_util(texto_ocr: str, valor_pdf: str) -> bool:
    if len(texto_ocr) < 2:
        return False
    if texto_ocr == valor_pdf:
        return False
    if _parece_texto_aszende_corrupto(texto_ocr):
        return False
    return any(caracter.isalpha() for caracter in texto_ocr)


def _decodificar_texto_aszende_si_corrupto(texto: str) -> str:
    if not _parece_texto_aszende_corrupto(texto):
        return texto.replace("í", "t")
    return " ".join(_decodificar_token_aszende_corrupto(token) for token in texto.split())


def _decodificar_token_aszende_corrupto(token: str) -> str:
    correcciones = {
        "iibs^": "LLEVA",
        "_o^hb": "BRAKE",
        "bk": "EN",
        "bgb": "EJE",
        "ibkql": "LENTO",
        "ia": "La",
        "pb": "SE",
        "bi": "EL",
        "Imbol": "PERO",
        "ó": "y",
        "qcq": "TFT",
        "T?": '7"',
        "bsseníial": "Essential",
        "bssential": "Essential",
        "pala": "Sala",
        "mrpeJmrii": "PUSH-PULL",
        "Gpf": "*SI",
        "bncoder": "Encoder",
        "incremeníal": "incremental",
        "mushJmull": "Push-Pull",
        "Gplil": "*SOLO",
        "qfo^": "TIRA",
        "iba": "LED",
        "OKU": "2.8",
        "qramiíar": "Tramitar",
        "qramitar": "Tramitar",
        "jonofàsic": "Monofàsic",
        "éassar": "passar",
        "bdm": "EdP",
        "03": "MP",
        "MP": "MP",
        "P": "3",
        "V": "9",
        "lhI": "OK,",
        "CDO": "Cal",
        "`al": "Cal",
        "alimeníarJlo": "alimentar-lo",
        "alimentarJlo": "alimentar-lo",
        "rescaí": "rescat",
    }
    if token in correcciones:
        return correcciones[token]
    token_casefold = token.casefold()
    for clave, valor in correcciones.items():
        if token_casefold == clave.casefold():
            return valor
    if not _token_aszende_fuertemente_corrupto(token):
        return token.replace("í", "t")

    mapa = str.maketrans(
        {
            "^": "A",
            "_": "B",
            "`": "C",
            "a": "D",
            "b": "E",
            "d": "G",
            "f": "I",
            "g": "J",
            "h": "K",
            "i": "L",
            "j": "M",
            "k": "N",
            "l": "O",
            "m": "P",
            "o": "R",
            "p": "S",
            "q": "T",
            "s": "V",
            "í": "t",
            "I": "P",
            "M": "0",
            "N": "1",
            "O": "2",
            "P": "3",
            "Q": "4",
            "T": "7",
            "U": "8",
        }
    )
    return token.translate(mapa)


def _token_aszende_fuertemente_corrupto(token: str) -> bool:
    if any(caracter in token for caracter in {"^", "_", "`"}):
        return True
    if re.fullmatch(r"[MNOPQTU]+v?", token):
        return True
    return token in {
        "iibs^",
        "_o^hb",
        "bk",
        "bgb",
        "ibkql",
        "ia",
        "pb",
        "Imbol",
        "qcq",
        "T?",
        "bssential",
        "pala",
        "mrpeJmrii",
        "Gpf",
        "bncoder",
        "incremeníal",
        "mushJmull",
        "Gplil",
        "qfo^",
        "iba",
        "OKU",
        "qramiíar",
        "qramitar",
        "jonofàsic",
        "éassar",
        "bdm",
        "03",
        "P",
        "V",
        "lhI",
        "CDO",
        "`al",
        "alimeníarJlo",
        "alimentarJlo",
        "rescaí",
    }


def _parece_texto_aszende_corrupto(texto: str) -> bool:
    if any(patron in texto for patron in {"CDO", "`al", "alimeníarJlo", "alimentarJlo", "rescaí"}):
        return True
    if any(caracter in texto for caracter in {"^", "_", "`"}):
        return True
    tokens = texto.split()
    if any(re.fullmatch(r"[MNOPQTU]+v?", token) for token in tokens):
        return True
    return bool(re.search(r"\b(?:iibs|fkpq|j\^k|mloq|NMQv|OMTv|PUM|qcq|bssential|pala|mrpeJmrii|Gpf|bncoder|incremen|mushJmull|Gplil|qfo\^|iba|OKU|qramitar|qramiíar|jonof|éassar|bdm|03|lhI|CDO|alimentarJlo)\b", texto))


def _limpiar_espacios_puntuacion(texto: str) -> str:
    texto = re.sub(r"\s+([:;,.])", r"\1", texto)
    texto = re.sub(r"([Â¿Â¡])\s+", r"\1", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


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


def _cargar_contratos_aszende(template_id: str) -> dict[str, dict[str, Any]]:
    directorio = _directorio_secciones_aszende(template_id)
    contratos: dict[str, dict[str, Any]] = {}
    for ruta in directorio.glob("*.json"):
        contenido = json.loads(ruta.read_text(encoding="utf-8-sig"))
        contratos[contenido["seccion"]] = contenido
    return contratos


def _datos_vacios_aszende(contratos: dict[str, dict[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for seccion, contrato in contratos.items():
        data[seccion] = {
            campo["nombre"]: campo.get("valor_defecto", "")
            for campo in contrato.get("campos", [])
            if isinstance(campo, dict) and campo.get("nombre")
        }
    return data


def _directorio_secciones_aszende(template_id: str = TEMPLATE_ASZENDE_ELECTRICO) -> Path:
    directorios = {
        TEMPLATE_ASZENDE_ELECTRICO: "contrato_aszende_crono_electrico",
    }
    nombre_directorio = directorios.get(template_id, "contrato_aszende_crono_electrico")
    for base in Path(__file__).resolve().parents:
        candidato = base / "docs" / nombre_directorio / "secciones"
        if candidato.is_dir():
            return candidato
    raise FileNotFoundError(f"No se encontro docs/{nombre_directorio}/secciones")
