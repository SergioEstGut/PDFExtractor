from extractor_pdf.domain.entidades import PaginaPdf


class ExtractorObservacionesResumenRaloeCrono:
    def extraer_paginas(self, paginas: list[PaginaPdf]) -> dict[str, str]:
        if not paginas:
            return {"Observaciones": ""}

        fragmentos: list[str] = []
        principal = self.extraer(paginas[0])["Observaciones"]
        if principal:
            fragmentos.append(principal)

        for pagina in paginas[1:]:
            continuacion = self._extraer_continuacion_antes_detalle_precios(pagina)
            if continuacion:
                fragmentos.append(continuacion)

        return {"Observaciones": " ".join(fragmentos).strip()}

    def extraer(self, pagina: PaginaPdf) -> dict[str, str]:
        bloque_ref = self._buscar_bloque_ref_cliente(pagina)
        if bloque_ref is None:
            return {"Observaciones": ""}

        candidatas = [
            bloque.texto.strip()
            for bloque in pagina.bloques
            if bloque.y0 > bloque_ref.y1
            and bloque.x0 >= bloque_ref.x0 - 5
            and bloque.x0 <= bloque_ref.x0 + 5
            and bloque.texto.strip()
        ]

        if not candidatas:
            return {"Observaciones": ""}

        observacion = " ".join(_normalizar_saltos_linea(candidata) for candidata in candidatas).strip()
        return {"Observaciones": observacion}

    @staticmethod
    def _extraer_continuacion_antes_detalle_precios(pagina: PaginaPdf) -> str:
        bloque_detalle = next(
            (bloque for bloque in pagina.bloques if "DETALLE DE ETIQUETAS DE PRECIO" in bloque.texto),
            None,
        )
        if bloque_detalle is None:
            return ""

        lineas = [
            _normalizar_saltos_linea(bloque.texto.strip())
            for bloque in sorted(pagina.bloques, key=lambda bloque: (bloque.y0, bloque.x0))
            if 100 <= bloque.y0 < bloque_detalle.y0
            and bloque.x0 >= 100
            and bloque.texto.strip()
        ]
        return " ".join(linea for linea in lineas if linea).strip()

    @staticmethod
    def _buscar_bloque_ref_cliente(pagina: PaginaPdf):
        for bloque in pagina.bloques:
            if "Ref. Cliente:" in bloque.texto:
                return bloque
        return None


def _normalizar_saltos_linea(valor: str) -> str:
    return " ".join(linea.strip() for linea in valor.splitlines() if linea.strip())







