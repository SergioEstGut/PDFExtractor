from extractor_pdf.application.extraer_aszende_crono_actual import (
    CasoUsoExtraerAszendeCronoActual,
)
from extractor_pdf.application.extraer_felesa_crono_actual import (
    CasoUsoExtraerFelesaCronoActual,
)
from extractor_pdf.application.extraer_raloe_crono_actual import (
    CasoUsoExtraerRaloeCronoActual,
)
from extractor_pdf.application.extraer_raloe_crono_fusionado import (
    CasoUsoExtraerRaloeCronoFusionado,
)
from extractor_pdf.infrastructure.ocr.extractor_visual_tesseract import ExtractorVisualTesseract
from extractor_pdf.infrastructure.ocr.lector_ocr_nulo import LectorOcrNulo
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf


def crear_caso_uso_extraer_raloe_crono() -> CasoUsoExtraerRaloeCronoActual:
    return CasoUsoExtraerRaloeCronoActual(
        lector_pdf=LectorTextoPyMuPdf(lector_ocr=LectorOcrNulo()),
    )


def crear_caso_uso_extraer_raloe_crono_fusionado() -> CasoUsoExtraerRaloeCronoFusionado:
    return CasoUsoExtraerRaloeCronoFusionado(
        lector_pdf=LectorTextoPyMuPdf(lector_ocr=LectorOcrNulo()),
        renderizador=RenderizadorPaginaPyMuPdf(),
        extractor_visual=ExtractorVisualTesseract(),
    )


def crear_caso_uso_extraer_felesa_crono() -> CasoUsoExtraerFelesaCronoActual:
    return CasoUsoExtraerFelesaCronoActual(
        lector_pdf=LectorTextoPyMuPdf(lector_ocr=LectorOcrNulo()),
    )


def crear_caso_uso_extraer_aszende_crono() -> CasoUsoExtraerAszendeCronoActual:
    return CasoUsoExtraerAszendeCronoActual(
        lector_pdf=LectorTextoPyMuPdf(lector_ocr=LectorOcrNulo()),
    )
