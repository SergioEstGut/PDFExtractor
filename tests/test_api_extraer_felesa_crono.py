import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from extractor_pdf.interfaces.api.main import app, _clasificar_texto_normalizado, _normalizar_texto


ROOT = Path(__file__).resolve().parents[1]
PDF_FELESA = ROOT / "pdfs" / "Felesa" / "654277.pdf"
PDF_FELESA_654883 = ROOT / "pdfs" / "Felesa" / "654883.pdf"
PDF_FELESA_654884 = ROOT / "pdfs" / "Felesa" / "654884.pdf"
PDF_FELESA_HIDRAULICO = ROOT / "pdfs" / "Felesa" / "654938.pdf"
PDF_RALOE = ROOT / "pdfs" / "Raloe" / "654107.pdf"
PDF_ASZENDE = ROOT / "pdfs" / "Aszende" / "655073.pdf"


def test_endpoint_extraer_felesa_crono_devuelve_datos_del_contrato() -> None:
    with PDF_FELESA.open("rb") as pdf_file:
        respuesta = TestClient(app).post(
            "/extract",
            data={"profile_id": "felesa_crono"},
            files={"file": ("654277.pdf", pdf_file, "application/pdf")},
        )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["metadata"]["profile_id"] == "felesa_crono"
    assert cuerpo["metadata"]["template_id"] == "felesa_crono_electrico"
    assert cuerpo["metadata"]["form_version"] == "0"
    assert cuerpo["metadata"]["pages"] == {"principal": 1, "botoneras_rellano": 2}
    assert cuerpo["data"]["Cabecera"]["Pais_destino"] == "IRLANDA"
    assert cuerpo["data"]["Normas"]["EN81_20"] == "SI"
    assert cuerpo["data"]["Datos_Generales"]["Secuencia"] == "-1,G,1,2,3"
    assert cuerpo["data"]["Datos_Generales"]["Tension_entrada"] == "400"
    assert cuerpo["data"]["Datos_Generales"]["Tension_entrada_tri"] == "Si"
    assert cuerpo["data"]["Datos_Motor"]["Consumo"] == "10.2"
    assert cuerpo["data"]["Botoneras_Rellano"]["Tipo_Llavin"] == ""
    assert cuerpo["data"]["Placas_Botoneras_Rellano"]["NEO_1T"] == "Si"
    assert cuerpo["data"]["Placas_Botoneras_Rellano"]["NEO_1T_cantidad"] == "4"
    assert "Armario MRL-S acabado INOX" in cuerpo["data"]["Observaciones"]["Observaciones"]
    assert "PULSADOR FLECHA EN.81-70" in cuerpo["data"]["Notas"]["Nota"]


def test_endpoint_extraer_data_path_array2d_felesa_crono() -> None:
    respuesta = TestClient(app).post(
        "/extract/data/path/array2d?profile_id=felesa_crono",
        content=str(PDF_FELESA).encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert ["Cabecera.Pais_destino", "IRLANDA"] in cuerpo
    assert ["Datos_Generales.Secuencia", "-1,G,1,2,3"] in cuerpo
    assert ["Placas_Botoneras_Rellano.NEO_1T_cantidad", "4"] in cuerpo
    observaciones = next(valor for campo, valor in cuerpo if campo == "Observaciones.Observaciones")
    assert "Pulsadores acabado INOX" in observaciones


def test_extractor_felesa_crono_lee_campos_desplazados_654884() -> None:
    with PDF_FELESA_654884.open("rb") as pdf_file:
        respuesta = TestClient(app).post(
            "/extract",
            data={"profile_id": "felesa_crono"},
            files={"file": ("654884.pdf", pdf_file, "application/pdf")},
        )

    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["Botoneras_Rellano"]["Num_Llavines_Ext"] == ""
    assert data["Botoneras_Rellano"]["Tipo_Llavin"] == ""
    assert data["Botoneras_Rellano"]["Funcion_Llavin"] == ""
    assert data["Datos_Cabina"]["Premontada_en_cabina"] == "SI"
    assert data["Datos_Generales"]["Planta_acceso"] == "1"


def test_extractor_felesa_crono_separa_maquina_y_peso_654883() -> None:
    with PDF_FELESA_654883.open("rb") as pdf_file:
        respuesta = TestClient(app).post(
            "/extract",
            data={"profile_id": "felesa_crono"},
            files={"file": ("654883.pdf", pdf_file, "application/pdf")},
        )

    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["Datos_Generales"]["Maquina"] == "miniACT240 240mm 2:1"
    assert data["Datos_Generales"]["Peso_maquina"] == "1000"


def test_endpoint_extraer_felesa_crono_detecta_hidraulico_desde_profile_generico() -> None:
    with PDF_FELESA_HIDRAULICO.open("rb") as pdf_file:
        respuesta = TestClient(app).post(
            "/extract",
            data={"profile_id": "felesa_crono"},
            files={"file": ("654938.pdf", pdf_file, "application/pdf")},
        )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["metadata"]["profile_id"] == "felesa_crono"
    assert cuerpo["metadata"]["template_id"] == "felesa_crono_hidraulico"
    assert "Datos_Central" in cuerpo["data"]
    assert "Datos_Motor" not in cuerpo["data"]
    assert cuerpo["data"]["Campos_extra"] == {}
    assert cuerpo["data"]["Notas_extra"] == []


def test_endpoint_extraer_aszende_crono_carga_contrato_y_campos_extra() -> None:
    with (ROOT / "pdfs" / "Aszende" / "655073.pdf").open("rb") as pdf_file:
        respuesta = TestClient(app).post(
            "/extract",
            data={"profile_id": "aszende_crono"},
            files={"file": ("655073.pdf", pdf_file, "application/pdf")},
        )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["metadata"]["profile_id"] == "aszende_crono"
    assert cuerpo["metadata"]["template_id"] == "aszende_crono_electrico"
    assert "Parametros_Variador" in cuerpo["data"]
    assert cuerpo["data"]["Campos_extra"] == {}
    assert cuerpo["data"]["Notas_extra"] == [
        {
            "valor": "Linea coloreada en pagina 1",
            "pagina": 1,
            "seccion": "Botoneras_Exteriores",
        },
        {
            "valor": "Fondo coloreado en pagina 1",
            "pagina": 1,
            "seccion": "Datos_Generales",
        },
    ]


def test_endpoint_clasifica_y_mueve_pedidos_de_prueba(tmp_path: Path) -> None:
    muestras = {
        "654107.pdf": PDF_RALOE,
        "654884.pdf": PDF_FELESA_654884,
        "654938.pdf": PDF_FELESA_HIDRAULICO,
        "655073.pdf": PDF_ASZENDE,
    }
    for nombre, origen in muestras.items():
        shutil.copyfile(origen, tmp_path / nombre)

    respuesta = TestClient(app).post(
        "/admin/pruebas/clasificar-pedidos",
        data={
            "base_path": str(tmp_path),
            "dry_run": "false",
        },
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["resumen"] == {
        "clasificados": 4,
        "movidos": 4,
        "desconocidos": 0,
        "omitidos": 0,
        "errores": 0,
    }
    assert (tmp_path / "Raloe" / "654107.pdf").is_file()
    assert (tmp_path / "Felesa Electrico" / "654884.pdf").is_file()
    assert (tmp_path / "Felesa Hidraulico" / "654938.pdf").is_file()
    assert (tmp_path / "Aszende Electrico" / "655073.pdf").is_file()


def test_clasificador_no_marca_portecnic_evo_como_raloe_crono() -> None:
    texto = _normalizar_texto(
        "Pedido de maniobra electrica Portecnic Formulari Sirius EVO Electric ESP "
        "Maniobra Carlos Silva Premontada Botonera Cabina"
    )

    assert _clasificar_texto_normalizado(texto) is None


def test_clasificador_no_marca_hidraulico_compartido_sin_cliente_felesa() -> None:
    texto = _normalizar_texto(
        "Cliente INELSA Formulario maniobras crono hidraulicas "
        "Grupo valvulas Tension valvulas doble piston micronivelacion "
        "Suministrar protecciones electricas"
    )

    assert _clasificar_texto_normalizado(texto) is None
