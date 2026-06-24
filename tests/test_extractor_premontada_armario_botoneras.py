import json
from pathlib import Path

from extractor_pdf.infrastructure.extraction.client_base.extractor_premontada_armario_botoneras import (
    ExtractorPremontadaArmarioBotonerasRaloeCrono,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_raloe_crono import (
    DetectorPaginaPremontadaArmarioBotonerasRaloeCrono,
)


ROOT = Path(__file__).resolve().parents[1]
ESPERADO = ROOT / "tests" / "fixtures" / "expected"


def test_extrae_premontada_armario_botoneras_de_654391_pagina_7() -> None:
    pagina_7 = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654391.pdf").read_bytes())[6]

    resultado = ExtractorPremontadaArmarioBotonerasRaloeCrono().extraer(pagina_7)

    assert resultado == _load_esperado("654391_page_7.json")


def test_extrae_premontada_armario_botoneras_de_654340_pagina_6() -> None:
    pagina_6 = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654340.pdf").read_bytes())[5]

    resultado = ExtractorPremontadaArmarioBotonerasRaloeCrono().extraer(pagina_6)

    assert resultado["Premontada"]["Recorrido"]
    assert resultado["Botonera_Cabina"]["Botonera_cab_fabricante"]
    assert resultado["Botonera_Cabina"]["Pulsador_de_stop_en_cabina"] in {"Si", "No"}


def test_extrae_premontada_armario_botoneras_de_654824_sin_valores_fijos() -> None:
    pagina_6 = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "654824.pdf").read_bytes())[5]

    resultado = ExtractorPremontadaArmarioBotonerasRaloeCrono().extraer(pagina_6)

    assert resultado["Premontada"]["Acceso_E1"] == "-1,0,1"
    assert resultado["Premontada"]["Distancia_niveles"] == "3.920,4.060"
    assert resultado["Premontada"]["Recorrido"] == "7.980"
    assert resultado["Premontada"]["Foso"] == "1.300"
    assert resultado["Premontada"]["Huida"] == "3.780"
    assert resultado["Premontada"]["Distancia_maniobra_motor"] == "9.960"
    assert resultado["Premontada"]["Manguera_plana"] == "15.980"
    assert resultado["Premontada"]["P"] == "896"
    assert resultado["Premontada"]["Carga_nominal"] == "600"
    assert resultado["Armario"]["Planta_ubicacion_armario"] == "1"
    assert resultado["Armario"]["Acabado"] == "INOX 304 SB"
    assert resultado["Botonera_Cabina"]["Modelo"] == "BAS120N"
    assert resultado["Botonera_Cabina"]["Secuencia"] == "-1,0,1"
    assert resultado["Botonera_Cabina"]["Texto_display"] == "SCHINDLER, S.A."
    assert resultado["Botonera_Cabina"]["Orientacion"] == "VERTICAL"
    assert resultado["Botonera_Exterior"]["Display_ext_E1"] == "Si"
    assert resultado["Botonera_Exterior"]["Display_ext_E1_txt"] == "TFT COLOR 5,6"
    assert resultado["Botonera_Exterior"]["Display_ext_E1_cant"] == "3"


def test_extrae_acceso_e2_aunque_la_primera_fila_este_vacia_en_655009() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas((ROOT / "pdfs" / "655009.pdf").read_bytes())
    pagina = DetectorPaginaPremontadaArmarioBotonerasRaloeCrono().detectar(paginas)

    resultado = ExtractorPremontadaArmarioBotonerasRaloeCrono().extraer(pagina)

    assert resultado["Premontada"]["Piso_E2"] == "-,M,M,M,M,M,M"
    assert resultado["Premontada"]["Acceso_E2"] == "-,1,2,3,4,5,6"
    assert resultado["Premontada"]["Display_modelo_E1"] == "-,-,-,-,-,-,-"
    assert resultado["Premontada"]["Display_modelo_E2"] == "-,-,-,-,-,-,-"
    assert resultado["Premontada"]["Orient_E1"] == "-,-,-,-,-,-,-"
    assert resultado["Premontada"]["Orient_E2"] == "-,-,-,-,-,-,-"


def _load_esperado(nombre_archivo: str) -> dict:
    return json.loads((ESPERADO / nombre_archivo).read_text(encoding="utf-8"))








