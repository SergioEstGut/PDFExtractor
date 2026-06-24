from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from extractor_pdf.infrastructure.extraction.client_base.contrato_campos import (
    especificacion_campo,
    normalizar_valor_campo,
)


class ClienteLlm(Protocol):
    def completar(self, prompt: str) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class DiscrepanciaCampo:
    seccion: str
    campo: str
    tipo_discrepancia: str
    valor_pdf: str
    valor_ocr: str


@dataclass(frozen=True)
class CandidatoResolucionCampo:
    seccion: str
    campo: str
    tipo_candidato: str
    valor_pdf: str
    valor_ocr: str
    pagina_pdf: int
    especificacion: dict[str, Any]
    evidencia_pdf: dict[str, Any]
    evidencia_ocr: dict[str, Any]
    lineas_ocr_cercanas: list[str]


def discrepancias_para_resolver(comparacion: dict[str, Any]) -> list[DiscrepanciaCampo]:
    discrepancias: list[DiscrepanciaCampo] = []
    for tipo in ("diferencias", "solo_pdf", "solo_ocr"):
        for seccion, campos in comparacion.get(tipo, {}).items():
            for campo, valor in campos.items():
                if tipo == "diferencias":
                    valor_pdf = valor.get("pdf", "")
                    valor_ocr = valor.get("ocr", "")
                elif tipo == "solo_pdf":
                    valor_pdf = valor
                    valor_ocr = ""
                else:
                    valor_pdf = ""
                    valor_ocr = valor
                discrepancias.append(
                    DiscrepanciaCampo(
                        seccion=seccion,
                        campo=campo,
                        tipo_discrepancia=tipo,
                        valor_pdf=valor_pdf,
                        valor_ocr=valor_ocr,
                    )
                )
    return discrepancias


def candidatos_para_resolver(
    comparacion: dict[str, Any],
    pagina_pdf: int,
    debug_pdf: dict[str, Any] | None = None,
    debug_ocr: dict[str, Any] | None = None,
    ocr_debug: dict[str, Any] | None = None,
    incluir_vacios_en_ambos: bool = True,
) -> list[CandidatoResolucionCampo]:
    candidatos: list[CandidatoResolucionCampo] = []
    for tipo in ("diferencias", "solo_pdf", "solo_ocr"):
        for seccion, campos in comparacion.get(tipo, {}).items():
            for campo, valor in campos.items():
                if tipo == "diferencias":
                    valor_pdf = valor.get("pdf", "")
                    valor_ocr = valor.get("ocr", "")
                elif tipo == "solo_pdf":
                    valor_pdf = valor
                    valor_ocr = ""
                else:
                    valor_pdf = ""
                    valor_ocr = valor
                candidatos.append(
                    _crear_candidato(
                        seccion,
                        campo,
                        tipo,
                        valor_pdf,
                        valor_ocr,
                        pagina_pdf,
                        debug_pdf,
                        debug_ocr,
                        ocr_debug,
                    )
                )

    if incluir_vacios_en_ambos:
        for seccion, campos in comparacion.get("vacios_en_ambos", {}).items():
            for campo in campos:
                candidatos.append(
                    _crear_candidato(
                        seccion,
                        campo,
                        "vacios_en_ambos",
                        "",
                        "",
                        pagina_pdf,
                        debug_pdf,
                        debug_ocr,
                        ocr_debug,
                    )
                )
    return candidatos


def construir_prompt_candidato(candidato: CandidatoResolucionCampo) -> str:
    contrato = {
        "tipo": candidato.especificacion.get("tipo", ""),
        "valor_defecto": candidato.especificacion.get("valor_defecto", ""),
        "aliases": candidato.especificacion.get("aliases", []),
        "reglas": candidato.especificacion.get("reglas", {}),
    }
    payload = {
        "pagina_pdf": candidato.pagina_pdf,
        "seccion": candidato.seccion,
        "campo": candidato.campo,
        "tipo_candidato": candidato.tipo_candidato,
        "contrato": contrato,
        "lecturas": {
            "pdf": candidato.valor_pdf,
            "ocr": candidato.valor_ocr,
        },
        "evidencias": {
            "pdf": candidato.evidencia_pdf,
            "ocr": candidato.evidencia_ocr,
            "lineas_ocr_cercanas": candidato.lineas_ocr_cercanas,
        },
    }
    return (
        "Resuelve un campo candidato tras comparar extraccion PDF y OCR. "
        "No inventes datos y no uses conocimiento externo.\n"
        "El contrato describe como interpretar el campo, pero NO es evidencia de que el valor este presente.\n"
        "Puedes elegir una de estas decisiones: pdf, ocr, valor, indeterminado.\n"
        "Usa decision=valor solo si el valor aparece claramente en las evidencias. "
        "No uses valor_marcado, valor_no_marcado ni valor_defecto como valor leido; son reglas, no lecturas.\n"
        "Si solo hay valor PDF y no hay evidencia OCR contraria, normalmente elige decision=pdf.\n"
        "Si no hay evidencia suficiente, usa decision=indeterminado y valor_resuelto=SIN_RESOLVER.\n"
        "Devuelve SOLO JSON valido con estas claves: decision, valor_resuelto, fuente, confianza, motivo.\n"
        "Valores de fuente permitidos: pdf, ocr, ambos, evidencia, ninguno.\n\n"
        f"CASO={json.dumps(payload, ensure_ascii=False)}"
    )


def resolver_candidato_con_llm(
    candidato: CandidatoResolucionCampo,
    llm: ClienteLlm,
) -> dict[str, str]:
    prompt = construir_prompt_candidato(candidato)
    respuesta = _parsear_json(llm.completar(prompt))
    valor_resuelto = _validar_valor_resuelto(candidato, respuesta.get("valor_resuelto", "SIN_RESOLVER"))
    if not _valor_tiene_respaldo(candidato, valor_resuelto):
        valor_resuelto = "SIN_RESOLVER"
    fuente = _corregir_fuente(
        valor_resuelto,
        candidato.valor_pdf,
        candidato.valor_ocr,
        respuesta.get("fuente", "ninguno"),
    )
    if valor_resuelto == "SIN_RESOLVER":
        fuente = "ninguno"
    return {
        "seccion": candidato.seccion,
        "campo": candidato.campo,
        "tipo_candidato": candidato.tipo_candidato,
        "valor_pdf": candidato.valor_pdf,
        "valor_ocr": candidato.valor_ocr,
        "valor_resuelto": valor_resuelto,
        "decision": respuesta.get("decision", "indeterminado"),
        "fuente": fuente,
        "confianza": respuesta.get("confianza", "baja"),
        "motivo": respuesta.get("motivo", ""),
        "prompt": prompt,
    }


def construir_prompt_resolucion(
    discrepancia: DiscrepanciaCampo,
    pagina_pdf: int,
    debug_ocr: dict[str, Any] | None = None,
) -> str:
    especificacion = especificacion_campo(discrepancia.seccion, discrepancia.campo) or {}
    evidencia_ocr = (debug_ocr or {}).get(discrepancia.seccion, {}).get(discrepancia.campo, {})
    contrato = {
        "tipo": especificacion.get("tipo", ""),
        "valor_defecto": especificacion.get("valor_defecto", ""),
        "aliases": especificacion.get("aliases", []),
        "reglas": especificacion.get("reglas", {}),
    }
    return (
        "Resuelve una discrepancia de extraccion PDF/OCR. No inventes datos.\n"
        "La lectura PDF y la lectura OCR son evidencias validas. Si eliges la lectura PDF, usa fuente=pdf.\n"
        "Si no hay evidencia suficiente en ninguna fuente, usa valor_resuelto=SIN_RESOLVER y fuente=ninguno.\n"
        "Devuelve SOLO JSON valido con estas claves: valor_resuelto, fuente, confianza, motivo.\n\n"
        f"Pagina PDF: {pagina_pdf}\n"
        f"Zona contractual: {discrepancia.seccion}\n"
        f"Campo: {discrepancia.campo}\n"
        f"Tipo discrepancia: {discrepancia.tipo_discrepancia}\n"
        f"Contrato campo: {json.dumps(contrato, ensure_ascii=False)}\n"
        f"Lectura PDF: {json.dumps(discrepancia.valor_pdf, ensure_ascii=False)}\n"
        f"Lectura OCR: {json.dumps(discrepancia.valor_ocr, ensure_ascii=False)}\n"
        "Evidencia OCR: "
        f"{json.dumps({'valor_crudo': evidencia_ocr.get('valor_crudo', ''), 'valor_normalizado': evidencia_ocr.get('valor', ''), 'linea': evidencia_ocr.get('linea', ''), 'patron': evidencia_ocr.get('patron', '')}, ensure_ascii=False)}\n"
        'Respuesta JSON ejemplo: {"valor_resuelto":"No","fuente":"pdf","confianza":"alta","motivo":"..."}'
    )


def resolver_discrepancia_con_llm(
    discrepancia: DiscrepanciaCampo,
    pagina_pdf: int,
    llm: ClienteLlm,
    debug_ocr: dict[str, Any] | None = None,
) -> dict[str, str]:
    prompt = construir_prompt_resolucion(discrepancia, pagina_pdf, debug_ocr)
    respuesta = _parsear_json(llm.completar(prompt))
    valor_resuelto = respuesta.get("valor_resuelto", "SIN_RESOLVER")
    if valor_resuelto != "SIN_RESOLVER":
        valor_resuelto = normalizar_valor_campo(discrepancia.seccion, discrepancia.campo, valor_resuelto)
    fuente = _corregir_fuente(
        valor_resuelto,
        discrepancia.valor_pdf,
        discrepancia.valor_ocr,
        respuesta.get("fuente", "ninguno"),
    )
    return {
        "seccion": discrepancia.seccion,
        "campo": discrepancia.campo,
        "tipo_discrepancia": discrepancia.tipo_discrepancia,
        "valor_pdf": discrepancia.valor_pdf,
        "valor_ocr": discrepancia.valor_ocr,
        "valor_resuelto": valor_resuelto,
        "fuente": fuente,
        "confianza": respuesta.get("confianza", "baja"),
        "motivo": respuesta.get("motivo", ""),
        "prompt": prompt,
    }


class ClienteLlamaCli:
    def __init__(
        self,
        ejecutable: str,
        modelo: str,
        max_tokens: int = 160,
        temperature: float = 0.0,
    ) -> None:
        self.ejecutable = ejecutable
        self.modelo = modelo
        self.max_tokens = max_tokens
        self.temperature = temperature

    def completar(self, prompt: str) -> str:
        comando = [
            self.ejecutable,
            "-m",
            self.modelo,
            "-p",
            prompt,
            "-n",
            str(self.max_tokens),
            "--temp",
            str(self.temperature),
            "--no-display-prompt",
        ]
        resultado = subprocess.run(
            comando,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return resultado.stdout.strip()


class ClienteLlamaServer:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8081",
        max_tokens: int = 160,
        temperature: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature

    def completar(self, prompt: str) -> str:
        body = {
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un verificador estricto de extracciones. Devuelves solo JSON valido.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"].get("content", "").strip()


def _parsear_json(texto: str) -> dict[str, str]:
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", texto, flags=re.DOTALL)
        if not match:
            return {
                "valor_resuelto": "SIN_RESOLVER",
                "fuente": "ninguno",
                "confianza": "baja",
                "motivo": "El LLM no devolvio JSON valido.",
            }
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {
                "valor_resuelto": "SIN_RESOLVER",
                "fuente": "ninguno",
                "confianza": "baja",
                "motivo": "El JSON devuelto por el LLM no se pudo interpretar.",
            }


def _corregir_fuente(valor_resuelto: str, valor_pdf: str, valor_ocr: str, fuente_llm: str) -> str:
    if valor_resuelto == "SIN_RESOLVER":
        return "ninguno"
    if valor_pdf and valor_ocr and valor_resuelto == valor_pdf == valor_ocr:
        return "ambos"
    if valor_pdf and valor_resuelto == valor_pdf:
        return "pdf"
    if valor_ocr and valor_resuelto == valor_ocr:
        return "ocr"
    return fuente_llm if fuente_llm in {"pdf", "ocr", "ambos", "evidencia", "ninguno"} else "ninguno"


def _crear_candidato(
    seccion: str,
    campo: str,
    tipo: str,
    valor_pdf: str,
    valor_ocr: str,
    pagina_pdf: int,
    debug_pdf: dict[str, Any] | None,
    debug_ocr: dict[str, Any] | None,
    ocr_debug: dict[str, Any] | None,
) -> CandidatoResolucionCampo:
    especificacion = especificacion_campo(seccion, campo) or {}
    evidencia_pdf = (debug_pdf or {}).get(seccion, {}).get(campo, {})
    evidencia_ocr = (debug_ocr or {}).get(seccion, {}).get(campo, {})
    lineas_ocr_cercanas = _lineas_ocr_cercanas(ocr_debug, especificacion, evidencia_ocr)
    return CandidatoResolucionCampo(
        seccion=seccion,
        campo=campo,
        tipo_candidato=tipo,
        valor_pdf=valor_pdf,
        valor_ocr=valor_ocr,
        pagina_pdf=pagina_pdf,
        especificacion=especificacion,
        evidencia_pdf=evidencia_pdf,
        evidencia_ocr=evidencia_ocr,
        lineas_ocr_cercanas=lineas_ocr_cercanas,
    )


def _lineas_ocr_cercanas(
    ocr_debug: dict[str, Any] | None,
    especificacion: dict[str, Any],
    evidencia_ocr: dict[str, Any],
) -> list[str]:
    lineas: list[str] = []
    linea_evidencia = evidencia_ocr.get("linea", "")
    if linea_evidencia:
        lineas.append(linea_evidencia)

    aliases = [alias for alias in especificacion.get("aliases", []) if alias]
    aliases_normalizados = [_normalizar_texto_busqueda(alias) for alias in aliases]
    for linea in (ocr_debug or {}).get("ocr", {}).get("lines", []):
        texto = linea.get("text", "")
        texto_normalizado = _normalizar_texto_busqueda(texto)
        if (
            texto
            and any(alias in texto_normalizado for alias in aliases_normalizados)
            and texto not in lineas
        ):
            lineas.append(texto)
        if len(lineas) >= 5:
            break
    return lineas


def _validar_valor_resuelto(candidato: CandidatoResolucionCampo, valor: str) -> str:
    if not valor or valor == "SIN_RESOLVER":
        return "SIN_RESOLVER"

    tipo = candidato.especificacion.get("tipo", "")
    if tipo == "check_simple" and str(valor) not in {"Si", "No"}:
        return "SIN_RESOLVER"

    valor_normalizado = normalizar_valor_campo(candidato.seccion, candidato.campo, str(valor))
    if not valor_normalizado:
        return "SIN_RESOLVER"

    if tipo == "check_simple" and valor_normalizado not in {"Si", "No"}:
        return "SIN_RESOLVER"
    if tipo == "check_con_valor" and valor_normalizado not in {"Si", "No"}:
        return valor_normalizado
    return valor_normalizado


def _valor_tiene_respaldo(candidato: CandidatoResolucionCampo, valor_resuelto: str) -> bool:
    if valor_resuelto == "SIN_RESOLVER":
        return True
    if candidato.valor_pdf and valor_resuelto == candidato.valor_pdf:
        return True
    if candidato.valor_ocr and valor_resuelto == candidato.valor_ocr:
        return True
    if candidato.tipo_candidato == "vacios_en_ambos":
        return False

    tipo = candidato.especificacion.get("tipo", "")
    if tipo == "check_simple":
        return False

    evidencias = [
        json.dumps(candidato.evidencia_pdf, ensure_ascii=False),
        json.dumps(candidato.evidencia_ocr, ensure_ascii=False),
        *candidato.lineas_ocr_cercanas,
    ]
    return any(str(valor_resuelto) in evidencia for evidencia in evidencias)


def _normalizar_texto_busqueda(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", texto.lower())
