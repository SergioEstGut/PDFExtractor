import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from extractor_pdf.application.extraer_felesa_crono_actual import _extraer_nota, _extraer_observaciones
from extractor_pdf.domain.entidades import BloqueTexto, PaginaPdf, PalabraTexto
from extractor_pdf.infrastructure.selection.detectores_paginas_felesa_crono import (
    detectar_plantilla_felesa_crono,
)
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


def test_extraer_nota_usa_pagina_de_botoneras() -> None:
    pagina_botoneras = PaginaPdf(
        numero=4,
        texto="Nota:\n- T:\nPULSADOR FLECHA EN.81-70\nPlantilla-Bot.Rellano",
        bloques=[
            BloqueTexto(
                texto="Nota:\n- T:\nPULSADOR FLECHA EN.81-70\nPlantilla-Bot.Rellano",
                x0=40,
                y0=690,
                x1=500,
                y1=760,
            )
        ],
        metodo_extraccion="test",
    )

    assert _extraer_nota(pagina_botoneras) == "- T:\nPULSADOR FLECHA EN.81-70"


def test_extraer_observaciones_usa_paginas_detectadas_por_rol() -> None:
    pagina_principal = PaginaPdf(
        numero=3,
        texto="",
        bloques=[
            BloqueTexto(
                texto="OBSERVACIONES:\n/ Observacion principal",
                x0=30,
                y0=745,
                x1=550,
                y1=770,
            )
        ],
        metodo_extraccion="test",
    )
    pagina_botoneras = PaginaPdf(
        numero=7,
        texto="",
        bloques=[
            BloqueTexto(
                texto="Observaciones:\n/ Observacion botoneras\nNota:\ntexto legal",
                x0=30,
                y0=650,
                x1=550,
                y1=720,
            )
        ],
        metodo_extraccion="test",
    )

    assert _extraer_observaciones(pagina_principal, pagina_botoneras) == (
        "/ Observacion principal\n/ Observacion botoneras"
    )


def test_extraer_observaciones_no_descarta_linea_que_empieza_por_observaciones() -> None:
    pagina_principal = PaginaPdf(
        numero=1,
        texto="",
        bloques=[
            BloqueTexto(
                texto=(
                    "OBSERVACIONES:\n"
                    "/ Se adjunta\n"
                    "observaciones y ficha tecnica / Suministrar modelo"
                ),
                x0=30,
                y0=745,
                x1=550,
                y1=780,
            )
        ],
        metodo_extraccion="test",
    )

    assert _extraer_observaciones(pagina_principal, None) == (
        "/ Se adjunta observaciones y ficha tecnica / Suministrar modelo"
    )


def test_extraer_observaciones_ignora_texto_rojo_y_lo_deja_para_notas_extra() -> None:
    pagina_principal = PaginaPdf(
        numero=1,
        texto="",
        bloques=[
            BloqueTexto(
                texto="OBSERVACIONES:\n/ Maniobra duplex\n/ Pulsador selectivo",
                x0=20,
                y0=738,
                x1=560,
                y1=782,
            ),
            BloqueTexto(
                texto="654682",
                x0=20,
                y0=760,
                x1=90,
                y1=774,
            )
        ],
        palabras=[
            PalabraTexto(texto="OBSERVACIONES:", x0=20, y0=738, x1=93, y1=748, color=0),
            PalabraTexto(texto="/", x0=23, y0=750, x1=26, y1=760, color=0),
            PalabraTexto(texto="Maniobra", x0=28, y0=750, x1=70, y1=760, color=0),
            PalabraTexto(texto="duplex", x0=72, y0=750, x1=100, y1=760, color=0),
            PalabraTexto(texto="654682", x0=25, y0=762, x1=65, y1=772, color=0xFF0000),
            PalabraTexto(texto="/", x0=23, y0=774, x1=26, y1=784, color=0),
            PalabraTexto(texto="Pulsador", x0=28, y0=774, x1=70, y1=784, color=0),
            PalabraTexto(texto="selectivo", x0=72, y0=774, x1=115, y1=784, color=0),
        ],
        metodo_extraccion="test",
    )

    assert _extraer_observaciones(pagina_principal, None) == "/ Maniobra duplex / Pulsador selectivo"


def test_extraer_observaciones_botoneras_concatena_bloques_despues_de_etiqueta() -> None:
    pagina_botoneras = PaginaPdf(
        numero=2,
        texto="",
        bloques=[
            BloqueTexto(texto="Observaciones:", x0=21, y0=625, x1=97, y1=636),
            BloqueTexto(
                texto="/ Suministrar llavin LUMI.1C para colocar en puerta\nreset)",
                x0=21,
                y0=638,
                x1=553,
                y1=660,
            ),
            BloqueTexto(texto="Nota:", x0=21, y0=684, x1=47, y1=695),
        ],
        palabras=[
            PalabraTexto(texto="Observaciones:", x0=21, y0=625, x1=97, y1=636, color=0),
            PalabraTexto(texto="/", x0=24, y0=638, x1=27, y1=649, color=0),
            PalabraTexto(texto="Suministrar", x0=29, y0=638, x1=75, y1=649, color=0),
            PalabraTexto(texto="llavin", x0=77, y0=638, x1=98, y1=649, color=0),
            PalabraTexto(texto="LUMI.1C", x0=101, y0=638, x1=136, y1=649, color=0),
            PalabraTexto(texto="para", x0=139, y0=638, x1=160, y1=649, color=0),
            PalabraTexto(texto="colocar", x0=163, y0=638, x1=195, y1=649, color=0),
            PalabraTexto(texto="en", x0=198, y0=638, x1=210, y1=649, color=0),
            PalabraTexto(texto="puerta", x0=213, y0=638, x1=245, y1=649, color=0),
            PalabraTexto(texto="reset)", x0=21, y0=650, x1=45, y1=660, color=0),
            PalabraTexto(texto="Nota:", x0=21, y0=684, x1=47, y1=695, color=0),
        ],
        metodo_extraccion="test",
    )

    assert _extraer_observaciones(None, pagina_botoneras) == (
        "/ Suministrar llavin LUMI.1C para colocar en puerta reset)"
    )


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
    assert cuerpo["data"]["Datos_Central"]["Rescate_automatico"] == "A Planta Inferior"
    assert cuerpo["data"]["Datos_Central"]["Potencia_cv"] == "6.50"
    assert cuerpo["data"]["Datos_Central"]["Potencia_kw"] == "4.70"
    assert "Suministrar_display" not in cuerpo["data"]["Botonera_Cabina"]
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
    assert "Notas" not in cuerpo["data"]
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


def test_detector_plantilla_aszende_electrico_busca_en_paginas_posteriores() -> None:
    paginas = [
        PaginaPdf(numero=1, texto="Pedido Especial Cliente ASZENDE", metodo_extraccion="pdf"),
        PaginaPdf(numero=2, texto="Documento de compra", metodo_extraccion="pdf"),
        PaginaPdf(
            numero=3,
            texto="FORMULARIO MANIOBRAS ASZENDE ELECTRICAS Cliente ASZENDE Datos Motor",
            metodo_extraccion="pdf",
        ),
    ]

    assert detectar_plantilla_felesa_crono(paginas) == "aszende_crono_electrico"
