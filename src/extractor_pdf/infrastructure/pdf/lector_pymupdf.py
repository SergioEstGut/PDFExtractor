import fitz

from extractor_pdf.domain.entidades import PaginaPdf, BloqueTexto, MarcaVisual, PalabraTexto
from extractor_pdf.domain.puertos import LectorOcr, LectorTextoPdf
from extractor_pdf.infrastructure.configuracion import configuracion

MARCA_CHECK = "\x14"


class LectorTextoPyMuPdf(LectorTextoPdf):
    def __init__(self, lector_ocr: LectorOcr | None = None) -> None:
        self.lector_ocr = lector_ocr

    def leer_paginas(self, bytes_pdf: bytes) -> list[PaginaPdf]:
        documento = fitz.open(stream=bytes_pdf, filetype="pdf")
        paginas: list[PaginaPdf] = []

        for indice, pagina in enumerate(documento, start=1):
            texto = pagina.get_text("text").strip()
            bloques = self._leer_bloques(pagina)
            fuente_aszende_codificada = self._parece_fuente_aszende_codificada(texto)
            palabras = self._leer_palabras(pagina, reparar_fuente_aszende=fuente_aszende_codificada)
            marcas_check = self._leer_marcas_check(pagina, palabras)
            palabras = self._normalizar_contenido_checks(palabras, marcas_check)
            palabras = self._deduplicar_palabras(palabras)
            marcas_visuales = self._leer_marcas_visuales(pagina)
            metodo = "embedded_text"
            if fuente_aszende_codificada:
                texto = self._reparar_texto_fuente_aszende(texto).strip()
                bloques = [
                    BloqueTexto(
                        texto=self._reparar_texto_fuente_aszende(bloque.texto),
                        x0=bloque.x0,
                        y0=bloque.y0,
                        x1=bloque.x1,
                        y1=bloque.y1,
                    )
                    for bloque in bloques
                ]
                marcas_check = []

            if self.lector_ocr and len(texto) < configuracion.min_caracteres_texto_pagina:
                texto_ocr, bloques_ocr = self.lector_ocr.leer_pagina(pagina)
                if texto_ocr:
                    texto = texto_ocr
                    bloques = bloques_ocr
                    palabras = []
                    marcas_check = []
                    marcas_visuales = []
                    metodo = self.lector_ocr.nombre

            paginas.append(
                PaginaPdf(
                    numero=indice,
                    texto=texto,
                    bloques=bloques,
                    palabras=palabras,
                    marcas_check=marcas_check,
                    marcas_visuales=marcas_visuales,
                    metodo_extraccion=metodo,
                )
            )

        documento.close()
        return paginas

    @staticmethod
    def _leer_bloques(pagina: fitz.Page) -> list[BloqueTexto]:
        bloques: list[BloqueTexto] = []
        for bloque in pagina.get_text("blocks"):
            x0, y0, x1, y1, texto, *_ = bloque
            texto_limpio = str(texto).strip()
            if texto_limpio:
                bloques.append(BloqueTexto(texto=texto_limpio, x0=x0, y0=y0, x1=x1, y1=y1))
        return bloques

    @staticmethod
    def _leer_palabras(
        pagina: fitz.Page,
        reparar_fuente_aszende: bool = False,
    ) -> list[PalabraTexto]:
        palabras: list[PalabraTexto] = []
        for bloque in pagina.get_text("rawdict")["blocks"]:
            for linea in bloque.get("lines", []):
                for span in linea.get("spans", []):
                    palabras.extend(
                        LectorTextoPyMuPdf._palabras_span(
                            span,
                            reparar_fuente_aszende=reparar_fuente_aszende,
                        )
                    )
        return palabras

    @staticmethod
    def _palabras_span(
        span: dict,
        reparar_fuente_aszende: bool = False,
    ) -> list[PalabraTexto]:
        palabras: list[PalabraTexto] = []
        texto_actual = ""
        bbox_actual: list[float] | None = None
        color = span.get("color")
        fuente = str(span.get("font", ""))
        reparar_span = (
            reparar_fuente_aszende
            and not fuente.startswith("Verdana")
            and fuente != "Arial-BoldMT"
        )

        def cerrar_palabra() -> None:
            nonlocal texto_actual, bbox_actual
            texto_limpio = texto_actual.strip()
            if texto_limpio and bbox_actual is not None:
                palabras.append(
                    PalabraTexto(
                        texto=texto_limpio,
                        x0=bbox_actual[0],
                        y0=bbox_actual[1],
                        x1=bbox_actual[2],
                        y1=bbox_actual[3],
                        color=color,
                    )
                )
            texto_actual = ""
            bbox_actual = None

        for caracter in span.get("chars", []):
            texto = str(caracter.get("c", ""))
            if reparar_span:
                texto = LectorTextoPyMuPdf._reparar_texto_fuente_aszende(texto)
            if texto.isspace():
                cerrar_palabra()
                continue

            x0, y0, x1, y1 = caracter["bbox"]
            texto_actual += texto
            if bbox_actual is None:
                bbox_actual = [x0, y0, x1, y1]
            else:
                bbox_actual = [
                    min(bbox_actual[0], x0),
                    min(bbox_actual[1], y0),
                    max(bbox_actual[2], x1),
                    max(bbox_actual[3], y1),
                ]

        cerrar_palabra()
        return palabras

    @staticmethod
    def _leer_marcas_check(pagina: fitz.Page, palabras: list[PalabraTexto]) -> list[PalabraTexto]:
        marcas: list[PalabraTexto] = []
        for bloque in pagina.get_text("rawdict")["blocks"]:
            for linea in bloque.get("lines", []):
                for span in linea.get("spans", []):
                    for caracter in span.get("chars", []):
                        if caracter.get("c") == MARCA_CHECK:
                            x0, y0, x1, y1 = caracter["bbox"]
                            marcas.append(PalabraTexto(texto=MARCA_CHECK, x0=x0, y0=y0, x1=x1, y1=y1))

        for caja in LectorTextoPyMuPdf._leer_cajas_check(pagina):
            if LectorTextoPyMuPdf._hay_contenido_en_caja(caja, palabras):
                marcas.append(
                    PalabraTexto(
                        texto=MARCA_CHECK,
                        x0=caja.x0,
                        y0=caja.y0,
                        x1=caja.x1,
                        y1=caja.y1,
                    )
                )
        marcas.extend(LectorTextoPyMuPdf._leer_marcas_check_rellenas(pagina))
        return LectorTextoPyMuPdf._deduplicar_marcas(marcas)

    @staticmethod
    def _leer_cajas_check(pagina: fitz.Page) -> list[fitz.Rect]:
        cajas: list[fitz.Rect] = []
        for dibujo in pagina.get_drawings():
            rect = dibujo.get("rect")
            if rect is None:
                continue

            ancho = abs(rect.x1 - rect.x0)
            alto = abs(rect.y1 - rect.y0)
            if not (5 <= ancho <= 16 and 5 <= alto <= 16):
                continue
            if abs(ancho - alto) > 2:
                continue
            if dibujo.get("fill") is not None:
                continue
            if dibujo.get("color") is None:
                continue
            cajas.append(rect)
        return cajas

    @staticmethod
    def _leer_marcas_check_rellenas(pagina: fitz.Page) -> list[PalabraTexto]:
        marcas: list[PalabraTexto] = []
        for dibujo in pagina.get_drawings():
            rect = dibujo.get("rect")
            relleno = dibujo.get("fill")
            if rect is None or relleno is None:
                continue

            ancho = abs(rect.x1 - rect.x0)
            alto = abs(rect.y1 - rect.y0)
            if not (3 <= ancho <= 10 and 3 <= alto <= 10):
                continue
            if abs(ancho - alto) > 2:
                continue
            if not _es_color_oscuro(relleno):
                continue

            marcas.append(
                PalabraTexto(
                    texto=MARCA_CHECK,
                    x0=rect.x0,
                    y0=rect.y0,
                    x1=rect.x1,
                    y1=rect.y1,
                )
            )
        return marcas

    @staticmethod
    def _hay_contenido_en_caja(caja: fitz.Rect, palabras: list[PalabraTexto]) -> bool:
        return any(LectorTextoPyMuPdf._centro_en_rect(palabra, caja) for palabra in palabras)

    @staticmethod
    def _normalizar_contenido_checks(
        palabras: list[PalabraTexto],
        marcas_check: list[PalabraTexto],
    ) -> list[PalabraTexto]:
        if not marcas_check:
            return palabras

        normalizadas: list[PalabraTexto] = []
        for palabra in palabras:
            if palabra.texto == MARCA_CHECK:
                normalizadas.append(palabra)
                continue
            if any(LectorTextoPyMuPdf._centro_en_rect(palabra, marca) for marca in marcas_check):
                normalizadas.append(
                    PalabraTexto(
                        texto=MARCA_CHECK,
                        x0=palabra.x0,
                        y0=palabra.y0,
                        x1=palabra.x1,
                        y1=palabra.y1,
                        color=palabra.color,
                    )
                )
                continue
            normalizadas.append(palabra)
        return normalizadas

    @staticmethod
    def _centro_en_rect(palabra: PalabraTexto, rect: fitz.Rect | PalabraTexto) -> bool:
        x = (palabra.x0 + palabra.x1) / 2
        y = (palabra.y0 + palabra.y1) / 2
        margen = 1.25
        return rect.x0 - margen <= x <= rect.x1 + margen and rect.y0 - margen <= y <= rect.y1 + margen

    @staticmethod
    def _deduplicar_marcas(marcas: list[PalabraTexto]) -> list[PalabraTexto]:
        unicas: list[PalabraTexto] = []
        for marca in marcas:
            if any(
                abs(marca.x0 - existente.x0) <= 1.5 and abs(marca.y0 - existente.y0) <= 1.5
                for existente in unicas
            ):
                continue
            unicas.append(marca)
        return unicas

    @staticmethod
    def _deduplicar_palabras(palabras: list[PalabraTexto]) -> list[PalabraTexto]:
        unicas: list[PalabraTexto] = []
        for palabra in palabras:
            if any(_misma_palabra_superpuesta(palabra, existente) for existente in unicas):
                continue
            unicas.append(palabra)
        return unicas

    @staticmethod
    def _leer_marcas_visuales(pagina: fitz.Page) -> list[MarcaVisual]:
        marcas: list[MarcaVisual] = []
        for dibujo in pagina.get_drawings():
            rect = dibujo.get("rect")
            if rect is None:
                continue

            relleno = dibujo.get("fill")
            trazo = dibujo.get("color")
            ancho = float(dibujo.get("width") or 0)

            alto = abs(rect.y1 - rect.y0)
            ancho_rect = abs(rect.x1 - rect.x0)
            area = alto * ancho_rect

            if relleno and area >= 20 and _es_color_no_neutro(relleno):
                marcas.append(
                    MarcaVisual(
                        tipo="fondo_coloreado",
                        x0=rect.x0,
                        y0=rect.y0,
                        x1=rect.x1,
                        y1=rect.y1,
                    )
                )
            elif trazo and ancho > 0 and max(alto, ancho_rect) >= 15 and _es_color_no_neutro(trazo):
                marcas.append(
                    MarcaVisual(
                        tipo="linea_coloreada",
                        x0=rect.x0,
                        y0=rect.y0,
                        x1=rect.x1,
                        y1=rect.y1,
                    )
                )
        return marcas

    @staticmethod
    def _parece_fuente_aszende_codificada(texto: str) -> bool:
        return ")RUPXODUL" in texto or "&OLHQWH" in texto or "5HIHUHQFLD" in texto

    @staticmethod
    def _reparar_texto_fuente_aszende(texto: str) -> str:
        traducciones = {
            "\x03": " ",
            "\x9e": "º",
            "p": "é",
            "t": "í",
            "y": "ó",
            "~": "ú",
            "๓": "ó",
        }
        caracteres: list[str] = []
        for caracter in texto:
            if caracter in {" ", "\n", "\r", "\t"}:
                caracteres.append(caracter)
                continue
            if caracter in traducciones:
                caracteres.append(traducciones[caracter])
                continue
            codigo = ord(caracter)
            if codigo <= 96:
                caracteres.append(chr(codigo + 29))
                continue
            caracteres.append(caracter)
        return "".join(caracteres)


def _es_color_no_neutro(color: tuple[float, float, float]) -> bool:
    canal_max = max(color)
    canal_min = min(color)
    if canal_max <= 0.25:
        return False
    return canal_max - canal_min > 0.08


def _es_color_oscuro(color: tuple[float, float, float]) -> bool:
    return max(color) <= 0.25


def _misma_palabra_superpuesta(a: PalabraTexto, b: PalabraTexto) -> bool:
    if a.texto != b.texto:
        return False
    return (
        abs(a.x0 - b.x0) <= 0.5
        and abs(a.y0 - b.y0) <= 0.5
        and abs(a.x1 - b.x1) <= 0.5
        and abs(a.y1 - b.y1) <= 0.5
    )







