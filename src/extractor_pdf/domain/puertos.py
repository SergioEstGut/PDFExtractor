from abc import ABC, abstractmethod

from extractor_pdf.domain.entidades import PaginaPdf, PaginaRenderizada


class LectorTextoPdf(ABC):
    @abstractmethod
    def leer_paginas(self, bytes_pdf: bytes) -> list[PaginaPdf]:
        raise NotImplementedError


class LectorOcr(ABC):
    nombre: str

    @abstractmethod
    def leer_pagina(self, pagina: object) -> tuple[str, list]:
        raise NotImplementedError


class RenderizadorPaginaPdf(ABC):
    @abstractmethod
    def renderizar_pagina(self, bytes_pdf: bytes, numero_pagina: int, dpi: int = 200) -> PaginaRenderizada:
        raise NotImplementedError


class ExtractorVisualPagina(ABC):
    @abstractmethod
    def extraer(self, pagina_renderizada: PaginaRenderizada, cliente_id: str) -> dict:
        raise NotImplementedError







