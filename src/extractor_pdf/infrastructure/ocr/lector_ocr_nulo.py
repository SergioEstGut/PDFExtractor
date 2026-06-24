from extractor_pdf.domain.puertos import LectorOcr


class LectorOcrNulo(LectorOcr):
    nombre = "no_ocr"

    def leer_pagina(self, pagina: object) -> tuple[str, list]:
        return "", []







