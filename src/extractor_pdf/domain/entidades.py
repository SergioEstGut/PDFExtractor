from pydantic import BaseModel, Field


class BloqueTexto(BaseModel):
    texto: str
    x0: float
    y0: float
    x1: float
    y1: float


class PalabraTexto(BaseModel):
    texto: str
    x0: float
    y0: float
    x1: float
    y1: float
    color: int | None = None


class PaginaPdf(BaseModel):
    numero: int
    texto: str
    bloques: list[BloqueTexto] = Field(default_factory=list)
    palabras: list[PalabraTexto] = Field(default_factory=list)
    marcas_check: list[PalabraTexto] = Field(default_factory=list)
    metodo_extraccion: str


class PaginaRenderizada(BaseModel):
    numero_pagina: int
    bytes_imagen: bytes
    formato_imagen: str
    ancho: int
    alto: int
    dpi: int







