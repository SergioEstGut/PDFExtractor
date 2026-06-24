from extractor_pdf.infrastructure.llm.resolucion_discrepancias import (
    CandidatoResolucionCampo,
    ClienteLlamaServer,
    DiscrepanciaCampo,
    candidatos_para_resolver,
    construir_prompt_candidato,
    construir_prompt_resolucion,
    discrepancias_para_resolver,
    resolver_candidato_con_llm,
    resolver_discrepancia_con_llm,
)


def test_crea_discrepancias_para_diferencias_y_valores_solo_en_una_fuente() -> None:
    comparacion = {
        "diferencias": {
            "Caracteristicas": {
                "Velocidad": {"pdf": "0.80", "ocr": "0.90"},
            }
        },
        "solo_pdf": {"Normas": {"Norma_81_1_A3": "No"}},
        "solo_ocr": {"general": {"Serie": "CRONO"}},
    }

    discrepancias = discrepancias_para_resolver(comparacion)

    assert discrepancias == [
        DiscrepanciaCampo("Caracteristicas", "Velocidad", "diferencias", "0.80", "0.90"),
        DiscrepanciaCampo("Normas", "Norma_81_1_A3", "solo_pdf", "No", ""),
        DiscrepanciaCampo("general", "Serie", "solo_ocr", "", "CRONO"),
    ]


def test_prompt_incluye_pagina_zona_contrato_y_evidencia_ocr() -> None:
    discrepancia = DiscrepanciaCampo("Caracteristicas", "Velocidad", "diferencias", "0.80", "0.90")
    debug_ocr = {
        "Caracteristicas": {
            "Velocidad": {
                "valor_crudo": "0,90",
                "valor": "0.90",
                "linea": "Velocidad: 0,90 m/s",
                "patron": "Velocidad",
            }
        }
    }

    prompt = construir_prompt_resolucion(discrepancia, pagina_pdf=5, debug_ocr=debug_ocr)

    assert "Pagina PDF: 5" in prompt
    assert "Zona contractual: Caracteristicas" in prompt
    assert '"tipo": "double"' in prompt
    assert '"extraer_solo_numero": true' in prompt
    assert '"linea": "Velocidad: 0,90 m/s"' in prompt


def test_respuesta_llm_se_normaliza_con_contrato() -> None:
    discrepancia = DiscrepanciaCampo("Caracteristicas", "Velocidad", "diferencias", "0.80", "0.90")

    resultado = resolver_discrepancia_con_llm(
        discrepancia,
        pagina_pdf=5,
        llm=LlmFake('{"valor_resuelto":"0,80 m/s","fuente":"pdf","confianza":"alta","motivo":"PDF legible"}'),
    )

    assert resultado["valor_resuelto"] == "0.80"
    assert resultado["fuente"] == "pdf"
    assert resultado["confianza"] == "alta"


def test_corrige_fuente_si_llm_resuelve_con_valor_pdf() -> None:
    discrepancia = DiscrepanciaCampo("Caracteristicas", "Frecuencia_60_Hz", "solo_pdf", "No", "")

    resultado = resolver_discrepancia_con_llm(
        discrepancia,
        pagina_pdf=5,
        llm=LlmFake(
            '{"valor_resuelto":"No","fuente":"ninguno","confianza":"media","motivo":"Sin OCR"}'
        ),
    )

    assert resultado["valor_resuelto"] == "No"
    assert resultado["fuente"] == "pdf"


def test_crea_candidatos_enriquecidos_incluyendo_vacios_en_ambos() -> None:
    comparacion = {
        "diferencias": {},
        "solo_pdf": {"Normas": {"Norma_81_1_A3": "No"}},
        "solo_ocr": {},
        "vacios_en_ambos": {"Traccion_electrica": ["Freno_lento_apertura"]},
    }
    debug_pdf = {
        "Normas": {"Norma_81_1_A3": {"valor": "No", "fuente": "check_zona"}},
        "Traccion_electrica": {"Freno_lento_apertura": {"valor": "", "fuente": "zona_vacia"}},
    }
    ocr_debug = {
        "ocr": {
            "lines": [
                {"text": "81- 1/A3 81- 2/A3 vi 81- 20/50"},
                {"text": "Freno Lento(apert/mant): / V"},
            ]
        }
    }

    candidatos = candidatos_para_resolver(
        comparacion,
        pagina_pdf=5,
        debug_pdf=debug_pdf,
        debug_ocr={},
        ocr_debug=ocr_debug,
    )

    assert [c.tipo_candidato for c in candidatos] == ["solo_pdf", "vacios_en_ambos"]
    assert candidatos[0].evidencia_pdf["fuente"] == "check_zona"
    assert candidatos[0].especificacion["tipo"] == "check_simple"
    assert candidatos[0].lineas_ocr_cercanas == ["81- 1/A3 81- 2/A3 vi 81- 20/50"]
    assert candidatos[1].evidencia_pdf["fuente"] == "zona_vacia"


def test_prompt_candidato_incluye_evidencias_y_contrato() -> None:
    candidato = CandidatoResolucionCampo(
        seccion="Normas",
        campo="Norma_81_1_A3",
        tipo_candidato="solo_pdf",
        valor_pdf="No",
        valor_ocr="",
        pagina_pdf=5,
        especificacion={"tipo": "check_simple", "aliases": ["81- 1/A3"], "reglas": {"valor_marcado": "Si"}},
        evidencia_pdf={"valor": "No", "fuente": "check_zona"},
        evidencia_ocr={},
        lineas_ocr_cercanas=["81- 1/A3 81- 2/A3 vi 81- 20/50"],
    )

    prompt = construir_prompt_candidato(candidato)

    assert '"tipo_candidato": "solo_pdf"' in prompt
    assert '"fuente": "check_zona"' in prompt
    assert '"tipo": "check_simple"' in prompt
    assert "decision=indeterminado" in prompt


def test_resolver_candidato_valida_check_simple_invalido() -> None:
    candidato = CandidatoResolucionCampo(
        seccion="Normas",
        campo="Norma_81_1_A3",
        tipo_candidato="solo_pdf",
        valor_pdf="No",
        valor_ocr="",
        pagina_pdf=5,
        especificacion={"tipo": "check_simple"},
        evidencia_pdf={"valor": "No", "fuente": "check_zona"},
        evidencia_ocr={},
        lineas_ocr_cercanas=[],
    )

    resultado = resolver_candidato_con_llm(
        candidato,
        LlmFake('{"decision":"valor","valor_resuelto":"quizas","fuente":"evidencia","confianza":"alta"}'),
    )

    assert resultado["valor_resuelto"] == "SIN_RESOLVER"
    assert resultado["fuente"] == "ninguno"


def test_resolver_candidato_normaliza_y_corrige_fuente_pdf() -> None:
    candidato = CandidatoResolucionCampo(
        seccion="Caracteristicas",
        campo="Velocidad",
        tipo_candidato="diferencias",
        valor_pdf="0.80",
        valor_ocr="0.90",
        pagina_pdf=5,
        especificacion={"tipo": "double", "reglas": {"extraer_solo_numero": True}},
        evidencia_pdf={"valor": "0.80", "fuente": "valor_leido"},
        evidencia_ocr={"valor": "0.90"},
        lineas_ocr_cercanas=["Velocidad: 0,90"],
    )

    resultado = resolver_candidato_con_llm(
        candidato,
        LlmFake('{"decision":"pdf","valor_resuelto":"0,80 m/s","fuente":"pdf","confianza":"alta"}'),
    )

    assert resultado["valor_resuelto"] == "0.80"
    assert resultado["fuente"] == "pdf"


def test_resolver_candidato_rechaza_check_simple_sin_respaldo_en_evidencia() -> None:
    candidato = CandidatoResolucionCampo(
        seccion="Normas",
        campo="Norma_81_2_A3",
        tipo_candidato="solo_pdf",
        valor_pdf="No",
        valor_ocr="",
        pagina_pdf=5,
        especificacion={"tipo": "check_simple"},
        evidencia_pdf={"valor": "No", "fuente": "check_zona"},
        evidencia_ocr={},
        lineas_ocr_cercanas=["81- 1/A3 81- 2/A3 vi 81- 20/50"],
    )

    resultado = resolver_candidato_con_llm(
        candidato,
        LlmFake('{"decision":"valor","valor_resuelto":"Si","fuente":"evidencia","confianza":"alta"}'),
    )

    assert resultado["valor_resuelto"] == "SIN_RESOLVER"
    assert resultado["fuente"] == "ninguno"


def test_resolver_candidato_rechaza_valor_en_vacios_en_ambos() -> None:
    candidato = CandidatoResolucionCampo(
        seccion="Traccion_hidraulica",
        campo="Grupo_valvulas",
        tipo_candidato="vacios_en_ambos",
        valor_pdf="",
        valor_ocr="",
        pagina_pdf=5,
        especificacion={"tipo": "string"},
        evidencia_pdf={"valor": "", "fuente": "zona_vacia"},
        evidencia_ocr={},
        lineas_ocr_cercanas=["Grupo Válvulas:"],
    )

    resultado = resolver_candidato_con_llm(
        candidato,
        LlmFake('{"decision":"valor","valor_resuelto":"Valvulas","fuente":"evidencia","confianza":"alta"}'),
    )

    assert resultado["valor_resuelto"] == "SIN_RESOLVER"
    assert resultado["fuente"] == "ninguno"


class LlmFake:
    def __init__(self, respuesta: str) -> None:
        self.respuesta = respuesta

    def completar(self, prompt: str) -> str:
        return self.respuesta


def test_cliente_llama_server_parsea_respuesta_openai_compatible(monkeypatch) -> None:
    class ResponseFake:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return (
                '{"choices":[{"message":{"content":'
                '"{\\"valor_resuelto\\":\\"No\\"}"'
                "}}]}"
            ).encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: ResponseFake(),
    )

    assert ClienteLlamaServer().completar("prompt") == '{"valor_resuelto":"No"}'
