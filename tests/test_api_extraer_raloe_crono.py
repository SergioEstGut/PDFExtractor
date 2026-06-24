import json
from pathlib import Path

from fastapi.testclient import TestClient

from extractor_pdf.interfaces.api.main import app


ROOT = Path(__file__).resolve().parents[1]
ESPERADO = ROOT / "tests" / "fixtures" / "expected"


def test_endpoint_extraer_devuelve_datos_completos_654391() -> None:
    respuesta = _post_pdf("654391.pdf")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["metadata"]["profile_id"] == "raloe_crono"
    assert cuerpo["metadata"]["filename"] == "654391.pdf"
    assert cuerpo["metadata"]["form_version"] == "0"
    assert cuerpo["data"] == _load_esperado("654391_full.json")


def test_endpoint_extraer_devuelve_datos_completos_654340() -> None:
    respuesta = _post_pdf("654340.pdf")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["metadata"]["profile_id"] == "raloe_crono"
    assert cuerpo["metadata"]["filename"] == "654340.pdf"
    assert cuerpo["metadata"]["status"] == "ok"
    assert cuerpo["data"]["general"]["Serie"] == "CRONO"


def test_endpoint_extraer_rechaza_perfil_desconocido() -> None:
    pdf_path = ROOT / "pdfs" / "654391.pdf"
    with pdf_path.open("rb") as pdf_file:
        respuesta = TestClient(app).post(
            "/extract",
            data={"profile_id": "unknown"},
            files={"file": ("654391.pdf", pdf_file, "application/pdf")},
        )

    assert respuesta.status_code == 400


def test_endpoint_extraer_fusionado_devuelve_contrato_con_observaciones() -> None:
    respuesta = _post_pdf_fusionado("654391.pdf")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["metadata"]["profile_id"] == "raloe_crono"
    assert cuerpo["metadata"]["filename"] == "654391.pdf"
    assert cuerpo["metadata"]["form_version"] == "0"
    assert cuerpo["metadata"]["fusion_strategy"] == "pdf_ocr_no_ai"
    assert cuerpo["data"] == _load_esperado("654391_full.json")
    assert cuerpo["data"]["Observaciones"]
    assert cuerpo["comparison_summary"]["coincidencias"] == 202


def test_endpoint_extraer_plano_devuelve_data_sin_secciones() -> None:
    respuesta = _post_pdf_plano("654206.pdf")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "general" not in cuerpo["data"]
    assert cuerpo["data"]["general.Serie"] == "CRONO"
    assert cuerpo["data"]["Normas.Norma_81_73_txt"] == ""
    assert "Traccion_electrica.Modelo" in cuerpo["data"]
    assert "Botonera_Cabina.Modelo" in cuerpo["data"]
    assert "campos_extra" in cuerpo
    assert "Notas_extra" in cuerpo
    assert cuerpo["metadata"]["filename"] == "654206.pdf"
    assert cuerpo["metadata"]["profile_id"] == "raloe_crono"
    assert cuerpo["metadata"]["form_version"] == "0"
    assert cuerpo["metadata"]["num_pedido"] == "VO/4472412"
    assert cuerpo["metadata"]["status"] == "Ok"


def test_endpoint_extraer_data_devuelve_solo_data_con_extras_en_observaciones() -> None:
    respuesta = _post_pdf_data("654144.pdf")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "data" not in cuerpo
    assert "metadata" not in cuerpo
    assert "campos_extra" not in cuerpo
    assert "Notas_extra" not in cuerpo
    assert cuerpo["general.Serie"] == "CRONO"
    assert "Campo extra:" in cuerpo["Observaciones"]
    assert "Nota extra:" in cuerpo["Observaciones"]
    assert "con pulsador" in cuerpo["Observaciones"]
    assert "\n" in cuerpo["Observaciones"]


def test_endpoint_extraer_data_acepta_pdf_path_del_servidor() -> None:
    pdf_path = ROOT / "pdfs" / "654144.pdf"

    respuesta = TestClient(app).post(
        "/extract/data",
        data={"profile_id": "raloe_crono", "pdf_path": str(pdf_path)},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["general.Serie"] == "CRONO"
    assert "con pulsador" in cuerpo["Observaciones"]


def test_endpoint_extraer_data_path_acepta_path_como_texto_plano() -> None:
    pdf_path = ROOT / "pdfs" / "654144.pdf"

    respuesta = TestClient(app).post(
        "/extract/data/path",
        content=str(pdf_path).encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["general.Serie"] == "CRONO"
    assert "con pulsador" in cuerpo["Observaciones"]
    assert "A\\u00f1adir" in respuesta.text
    assert "AÃ" not in respuesta.text


def test_endpoint_extraer_data_path_array2d_devuelve_lista_de_pares() -> None:
    pdf_path = ROOT / "pdfs" / "654144.pdf"

    respuesta = TestClient(app).post(
        "/extract/data/path/array2d?profile_id=raloe_crono",
        content=str(pdf_path).encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo, list)
    assert all(isinstance(fila, list) and len(fila) == 2 for fila in cuerpo)
    assert ["general.Serie", "CRONO"] in cuerpo
    observaciones = next(valor for campo, valor in cuerpo if campo == "Observaciones")
    assert "con pulsador" in observaciones
    assert "A\\u00f1adir" in respuesta.text


def test_endpoint_extraer_data_devuelve_404_si_pdf_path_no_existe() -> None:
    respuesta = TestClient(app).post(
        "/extract/data",
        data={"profile_id": "raloe_crono", "pdf_path": str(ROOT / "pdfs" / "no_existe.pdf")},
    )

    assert respuesta.status_code == 404


def _post_pdf(nombre_archivo: str):
    pdf_path = ROOT / "pdfs" / nombre_archivo
    with pdf_path.open("rb") as pdf_file:
        return TestClient(app).post(
            "/extract",
            data={"profile_id": "raloe_crono"},
            files={"file": (nombre_archivo, pdf_file, "application/pdf")},
        )


def _post_pdf_fusionado(nombre_archivo: str):
    pdf_path = ROOT / "pdfs" / nombre_archivo
    with pdf_path.open("rb") as pdf_file:
        return TestClient(app).post(
            "/extract/fused",
            data={"profile_id": "raloe_crono"},
            files={"file": (nombre_archivo, pdf_file, "application/pdf")},
        )


def _post_pdf_plano(nombre_archivo: str):
    pdf_path = ROOT / "pdfs" / nombre_archivo
    with pdf_path.open("rb") as pdf_file:
        return TestClient(app).post(
            "/extract/flat",
            data={"profile_id": "raloe_crono"},
            files={"file": (nombre_archivo, pdf_file, "application/pdf")},
        )


def _post_pdf_data(nombre_archivo: str):
    pdf_path = ROOT / "pdfs" / nombre_archivo
    with pdf_path.open("rb") as pdf_file:
        return TestClient(app).post(
            "/extract/data",
            data={"profile_id": "raloe_crono"},
            files={"file": (nombre_archivo, pdf_file, "application/pdf")},
        )


def _load_esperado(nombre_archivo: str) -> dict:
    return json.loads((ESPERADO / nombre_archivo).read_text(encoding="utf-8"))








