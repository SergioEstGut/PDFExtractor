import fitz

from extractor_pdf.domain.entidades import PaginaRenderizada
from extractor_pdf.domain.puertos import RenderizadorPaginaPdf


class RenderizadorPaginaPyMuPdf(RenderizadorPaginaPdf):
    def contar_paginas(self, bytes_pdf: bytes) -> int:
        documento = fitz.open(stream=bytes_pdf, filetype="pdf")
        total = documento.page_count
        documento.close()
        return total

    def renderizar_pagina(self, bytes_pdf: bytes, numero_pagina: int, dpi: int = 200) -> PaginaRenderizada:
        documento = fitz.open(stream=bytes_pdf, filetype="pdf")
        pagina = documento[numero_pagina - 1]
        pixmap = pagina.get_pixmap(dpi=dpi, alpha=False)
        bytes_imagen = pixmap.tobytes("png")

        resultado = PaginaRenderizada(
            numero_pagina=numero_pagina,
            bytes_imagen=bytes_imagen,
            formato_imagen="png",
            ancho=pixmap.width,
            alto=pixmap.height,
            dpi=dpi,
        )
        documento.close()
        return resultado







