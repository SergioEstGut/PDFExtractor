import fitz

from extractor_pdf.domain.entidades import PaginaPdf, BloqueTexto, PalabraTexto
from extractor_pdf.domain.puertos import LectorOcr, LectorTextoPdf
from extractor_pdf.infrastructure.configuracion import configuracion


class LectorTextoPyMuPdf(LectorTextoPdf):
    def __init__(self, lector_ocr: LectorOcr | None = None) -> None:
        self.lector_ocr = lector_ocr

    def leer_paginas(self, bytes_pdf: bytes) -> list[PaginaPdf]:
        documento = fitz.open(stream=bytes_pdf, filetype="pdf")
        paginas: list[PaginaPdf] = []

        for indice, pagina in enumerate(documento, start=1):
            texto = pagina.get_text("text").strip()
            bloques = self._leer_bloques(pagina)
            palabras = self._leer_palabras(pagina)
            marcas_check = self._leer_marcas_check(pagina)
            metodo = "embedded_text"

            if self.lector_ocr and len(texto) < configuracion.min_caracteres_texto_pagina:
                texto_ocr, bloques_ocr = self.lector_ocr.leer_pagina(pagina)
                if texto_ocr:
                    texto = texto_ocr
                    bloques = bloques_ocr
                    palabras = []
                    marcas_check = []
                    metodo = self.lector_ocr.nombre

            paginas.append(
                PaginaPdf(
                    numero=indice,
                    texto=texto,
                    bloques=bloques,
                    palabras=palabras,
                    marcas_check=marcas_check,
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
    def _leer_palabras(pagina: fitz.Page) -> list[PalabraTexto]:
        palabras: list[PalabraTexto] = []
        for bloque in pagina.get_text("rawdict")["blocks"]:
            for linea in bloque.get("lines", []):
                for span in linea.get("spans", []):
                    palabras.extend(LectorTextoPyMuPdf._palabras_span(span))
        return palabras

    @staticmethod
    def _palabras_span(span: dict) -> list[PalabraTexto]:
        palabras: list[PalabraTexto] = []
        texto_actual = ""
        bbox_actual: list[float] | None = None
        color = span.get("color")

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
    def _leer_marcas_check(pagina: fitz.Page) -> list[PalabraTexto]:
        marcas: list[PalabraTexto] = []
        for bloque in pagina.get_text("rawdict")["blocks"]:
            for linea in bloque.get("lines", []):
                for span in linea.get("spans", []):
                    for caracter in span.get("chars", []):
                        if caracter.get("c") == "\x14":
                            x0, y0, x1, y1 = caracter["bbox"]
                            marcas.append(PalabraTexto(texto="\x14", x0=x0, y0=y0, x1=x1, y1=y1))
        return marcas







