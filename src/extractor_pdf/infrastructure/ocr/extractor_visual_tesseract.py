from io import BytesIO
from typing import Any

from PIL import Image

from extractor_pdf.domain.entidades import PaginaRenderizada
from extractor_pdf.domain.puertos import ExtractorVisualPagina


class ErrorTesseractNoDisponible(RuntimeError):
    pass


class ExtractorVisualTesseract(ExtractorVisualPagina):
    def __init__(self, idioma: str = "spa+eng", comando_tesseract: str | None = None) -> None:
        self.idioma = idioma
        self.comando_tesseract = comando_tesseract

    def extraer(self, pagina_renderizada: PaginaRenderizada, cliente_id: str) -> dict[str, Any]:
        pytesseract = self._load_pytesseract()
        if self.comando_tesseract:
            pytesseract.pytesseract.tesseract_cmd = self.comando_tesseract

        imagen = Image.open(BytesIO(pagina_renderizada.bytes_imagen))
        try:
            texto = pytesseract.image_to_string(imagen, lang=self.idioma)
            cajas = pytesseract.image_to_data(
                imagen,
                lang=self.idioma,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:
            raise ErrorTesseractNoDisponible(str(exc)) from exc

        palabras = self._palabras_desde_datos(cajas)
        lineas = _lineas_desde_palabras(palabras)

        return {
            "ocr": {
                "engine": "tesseract",
                "language": self.idioma,
                "text": texto.strip(),
                "word_count": len(palabras),
                "line_count": len(lineas),
                "words": palabras,
                "lines": lineas,
            }
        }

    @staticmethod
    def _load_pytesseract() -> Any:
        try:
            import pytesseract
        except ImportError as exc:
            raise ErrorTesseractNoDisponible(
                "Instala pytesseract con: pip install pytesseract"
            ) from exc
        return pytesseract

    @staticmethod
    def _palabras_desde_datos(datos: dict[str, list[Any]]) -> list[dict[str, Any]]:
        palabras: list[dict[str, Any]] = []
        for indice, texto in enumerate(datos.get("text", [])):
            texto_limpio = str(texto).strip()
            if not texto_limpio:
                continue

            confianza = _leer_confianza(datos["conf"][indice])
            if confianza < 0:
                continue

            izquierda = int(datos["left"][indice])
            superior = int(datos["top"][indice])
            ancho = int(datos["width"][indice])
            alto = int(datos["height"][indice])
            palabras.append(
                {
                    "text": texto_limpio,
                    "confidence": confianza,
                    "x0": izquierda,
                    "y0": superior,
                    "x1": izquierda + ancho,
                    "y1": superior + alto,
                }
            )
        return palabras


def _leer_confianza(valor: Any) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return -1.0


def _lineas_desde_palabras(palabras: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not palabras:
        return []

    lineas: list[list[dict[str, Any]]] = []
    for palabra in sorted(palabras, key=lambda item: (item["y0"], item["x0"])):
        centro_y = (palabra["y0"] + palabra["y1"]) / 2
        linea = _buscar_linea(lineas, centro_y)
        if linea is None:
            lineas.append([palabra])
        else:
            linea.append(palabra)

    resultado: list[dict[str, Any]] = []
    for palabras_linea in lineas:
        ordenadas = sorted(palabras_linea, key=lambda item: item["x0"])
        resultado.append(
            {
                "text": " ".join(palabra["text"] for palabra in ordenadas),
                "x0": min(palabra["x0"] for palabra in ordenadas),
                "y0": min(palabra["y0"] for palabra in ordenadas),
                "x1": max(palabra["x1"] for palabra in ordenadas),
                "y1": max(palabra["y1"] for palabra in ordenadas),
                "avg_confidence": sum(palabra["confidence"] for palabra in ordenadas) / len(ordenadas),
                "words": ordenadas,
            }
        )
    return resultado


def _buscar_linea(
    lineas: list[list[dict[str, Any]]],
    centro_y: float,
    tolerancia: float = 12.0,
) -> list[dict[str, Any]] | None:
    for linea in lineas:
        centros = [(palabra["y0"] + palabra["y1"]) / 2 for palabra in linea]
        if abs((sum(centros) / len(centros)) - centro_y) <= tolerancia:
            return linea
    return None







