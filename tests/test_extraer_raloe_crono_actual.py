import json
from pathlib import Path
from typing import Any

from extractor_pdf.application.extraer_raloe_crono_actual import (
    CasoUsoExtraerRaloeCronoActual,
)
from extractor_pdf.domain.entidades import PaginaPdf
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf


ROOT = Path(__file__).resolve().parents[1]
ESPERADO = ROOT / "tests" / "fixtures" / "expected"


def test_extrae_alcance_actual_de_pdf_654391() -> None:
    resultado = CasoUsoExtraerRaloeCronoActual(
        lector_pdf=LectorTextoPyMuPdf()
    ).ejecutar((ROOT / "pdfs" / "Raloe" / "654391.pdf").read_bytes())

    assert resultado["metadata"] == {
        "summary_page": 1,
        "technical_page": 5,
        "pit_escape_options_page": 6,
        "premounted_cabinet_buttons_page": 7,
        "is_raloe_crono": True,
        "status": "ok",
        "warnings": [],
    }
    assert resultado["page_1"] == _load_esperado("654391_page_1.json")
    assert resultado["page_5"] == _load_esperado("654391_page_5.json")
    assert resultado["page_6"] == _load_esperado("654391_page_6.json")
    assert resultado["page_7"] == _load_esperado("654391_page_7.json")
    assert resultado["data"] == _load_esperado("654391_full.json")


def test_extrae_alcance_actual_de_pdf_654340() -> None:
    resultado = CasoUsoExtraerRaloeCronoActual(
        lector_pdf=LectorTextoPyMuPdf()
    ).ejecutar((ROOT / "pdfs" / "Raloe" / "654340.pdf").read_bytes())

    assert resultado["metadata"] == {
        "summary_page": 1,
        "technical_page": 4,
        "pit_escape_options_page": 5,
        "premounted_cabinet_buttons_page": 6,
        "is_raloe_crono": True,
        "status": "ok",
        "warnings": [],
    }
    assert resultado["data"]["general"]["Serie"] == "CRONO"
    assert resultado["page_6"]["Botonera_Cabina"]["Pulsador_de_stop_en_cabina"] in {"Si", "No"}


def test_devuelve_contrato_vacio_si_pdf_no_es_raloe_crono() -> None:
    resultado = CasoUsoExtraerRaloeCronoActual(
        lector_pdf=StaticPdfReader(
            [
                PaginaPdf(
                    numero=1,
                    texto="Documento cualquiera sin seÃ±ales del perfil",
                    bloques=[],
                    metodo_extraccion="test",
                )
            ]
        )
    ).ejecutar(b"not-a-real-pdf")

    assert resultado["metadata"]["is_raloe_crono"] is False
    assert resultado["metadata"]["status"] == "not_raloe_crono"
    assert resultado["data"]["general"]["Serie"] == ""
    assert resultado["data"]["Traccion_electrica"]["Modelo_motor"] == ""
    assert resultado["data"]["Campos_extra"] == {}
    assert resultado["data"]["Notas_extra"] == []


def test_devuelve_contrato_parcial_si_falta_una_seccion() -> None:
    resultado = CasoUsoExtraerRaloeCronoActual(
        lector_pdf=StaticPdfReader(
            [
                PaginaPdf(
                    numero=1,
                    texto="CRONO MANIOBRA CARLOS SILVA",
                    bloques=[],
                    metodo_extraccion="test",
                )
            ]
        )
    ).ejecutar(b"partial-pdf")

    assert resultado["metadata"]["is_raloe_crono"] is True
    assert resultado["metadata"]["status"] == "partial"
    assert resultado["metadata"]["warnings"]
    assert resultado["data"]["general"]["Serie"] == ""
    assert resultado["data"]["Premontada"]["Piso_E1"] == ""
    assert resultado["data"]["Campos_extra"] == {}


def test_devuelve_campos_extra_para_pares_clave_valor_no_esperados() -> None:
    resultado = CasoUsoExtraerRaloeCronoActual(
        lector_pdf=StaticPdfReader(
            [
                PaginaPdf(
                    numero=1,
                    texto=(
                        "CRONO MANIOBRA CARLOS SILVA\n"
                        "Campo nuevo especial: Valor de prueba\n"
                        "Serie: CRONO\n"
                        "Sistema antideriva: CBL:\n"
                    ),
                    bloques=[],
                    metodo_extraccion="test",
                )
            ]
        )
    ).ejecutar(b"partial-pdf-with-extra")

    assert resultado["metadata"]["is_raloe_crono"] is True
    assert resultado["metadata"]["status"] == "partial"
    assert resultado["data"]["Campos_extra"] == {
        "Campo_nuevo_especial": {
            "nombre_campo": "Campo_nuevo_especial",
            "valor": "Valor de prueba",
            "pagina": 1,
            "seccion": "general",
        }
    }
    assert "Serie" not in resultado["data"]["Campos_extra"]


def test_reporta_checks_contractuales_encontrados_fuera_de_su_seccion() -> None:
    resultado = CasoUsoExtraerRaloeCronoActual(
        lector_pdf=LectorTextoPyMuPdf()
    ).ejecutar((ROOT / "pdfs" / "Raloe" / "654144.pdf").read_bytes())

    assert resultado["data"]["Botonera_Cabina"]["Reg_acustico_cabina_RAP"] == "No"
    assert resultado["data"]["Botonera_Exterior"]["Reg_acustico_pisos_RAP"] == "No"
    assert resultado["data"]["Campos_extra"]["Opciones.Reg_acustico_cabina_RAP"] == {
        "nombre_campo": "Reg_acustico_cabina_RAP",
        "valor": "Si",
        "pagina": 6,
        "seccion": "Opciones",
    }
    assert resultado["data"]["Campos_extra"]["Opciones.Reg_acustico_pisos_RAP"] == {
        "nombre_campo": "Reg_acustico_pisos_RAP",
        "valor": "Si",
        "pagina": 6,
        "seccion": "Opciones",
    }


def test_reporta_textos_no_negros_como_notas_extra() -> None:
    resultado = CasoUsoExtraerRaloeCronoActual(
        lector_pdf=LectorTextoPyMuPdf()
    ).ejecutar((ROOT / "pdfs" / "Raloe" / "654144.pdf").read_bytes())

    assert resultado["data"]["Notas_extra"] == [
        {"valor": "con pulsador", "pagina": 6, "seccion": "Opciones"},
        {"valor": "ok", "pagina": 7, "seccion": "Premontada"},
        {"valor": "isolation", "pagina": 7, "seccion": "Botonera_Cabina"},
        {
            "valor": "Miguel me confirma que las flechas de predirección las hace el display en todas las plantas",
            "pagina": 7,
            "seccion": "Botonera_Exterior",
        },
    ]


def test_no_confunde_gris_oscuro_del_formulario_con_notas_extra() -> None:
    resultado = CasoUsoExtraerRaloeCronoActual(
        lector_pdf=LectorTextoPyMuPdf()
    ).ejecutar((ROOT / "pdfs" / "Raloe" / "654436.pdf").read_bytes())

    assert resultado["data"]["Notas_extra"] == [
        {
            "valor": "INCLUIR ARM Y CONTROL DE LLAMADAS BOTONERA CABINA CODIFICADA.",
            "pagina": 5,
            "seccion": "Opciones",
        },
        {
            "valor": "ESTOS DOS EXTRAS SON A COSTE 0 (HABLADO JESÚS DE MIGUEL CON JOSE Y FERRAN.",
            "pagina": 5,
            "seccion": "Opciones",
        },
    ]


def _load_esperado(nombre_archivo: str) -> dict[str, Any]:
    return json.loads((ESPERADO / nombre_archivo).read_text(encoding="utf-8"))


class StaticPdfReader:
    def __init__(self, paginas: list[PaginaPdf]) -> None:
        self.paginas = paginas

    def leer_paginas(self, pdf_bytes: bytes) -> list[PaginaPdf]:
        return self.paginas








