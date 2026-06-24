import re
from typing import Any

from extractor_pdf.domain.entidades import PaginaPdf


def construir_salida_plana(
    resultado: dict[str, Any],
    paginas: list[PaginaPdf],
    filename: str,
    profile_id: str,
    form_version: str = "0",
) -> dict[str, Any]:
    data = resultado.get("data", {})
    campos_extra = data.get("Campos_extra", {})
    notas_extra = data.get("Notas_extra", [])

    return {
        "data": _aplanar_data(data),
        "campos_extra": campos_extra,
        "Notas_extra": notas_extra,
        "metadata": _construir_metadata(resultado, paginas, filename, profile_id, form_version),
    }


def construir_data_plana_con_observaciones(resultado: dict[str, Any]) -> dict[str, str]:
    data = resultado.get("data", {})
    plano = _aplanar_data(data)
    observaciones = str(plano.get("Observaciones", "") or "")
    extras = [
        *_formatear_campos_extra(data.get("Campos_extra", {})),
        *_formatear_notas_extra(data.get("Notas_extra", [])),
    ]

    if extras:
        registros = [registro for registro in [observaciones, *extras] if registro]
        plano["Observaciones"] = "\n".join(registros)

    return plano


def extraer_num_pedido(paginas: list[PaginaPdf]) -> str:
    if not paginas:
        return ""

    lineas = [linea.strip() for linea in paginas[0].texto.splitlines() if linea.strip()]
    for indice, linea in enumerate(lineas):
        match = re.search(r"\b([A-Z]{1,3}/\d{5,})\b", linea)
        if match:
            return match.group(1)

        if "pedido" in linea.lower():
            ventana = " ".join(lineas[indice : indice + 4])
            match = re.search(r"\b([A-Z]{1,3}/\d{5,})\b", ventana)
            if match:
                return match.group(1)
            match = re.search(r"\b(\d{6,})\b", ventana)
            if match:
                return match.group(1)

    match = re.search(r"\b([A-Z]{1,3}/\d{5,})\b", paginas[0].texto)
    if match:
        return match.group(1)
    match = re.search(r"(?:N[ºo]\s*)?Pedido\s*:?\s*(\d{6,})", paginas[0].texto, re.IGNORECASE)
    return match.group(1) if match else ""


def _aplanar_data(data: dict[str, Any]) -> dict[str, str]:
    plano: dict[str, str] = {}
    for seccion, valor in data.items():
        if seccion in {"Campos_extra", "Notas_extra"}:
            continue
        if isinstance(valor, dict):
            for campo, campo_valor in valor.items():
                plano[f"{seccion}.{campo}"] = campo_valor
        else:
            plano[seccion] = valor
    return plano


def _formatear_campos_extra(campos_extra: dict[str, Any]) -> list[str]:
    registros: list[str] = []
    for clave, valor in campos_extra.items():
        if isinstance(valor, dict):
            nombre = valor.get("nombre_campo") or clave
            contenido = valor.get("valor", "")
            pagina = valor.get("pagina", "")
            seccion = valor.get("seccion", "")
            registros.append(
                f"Campo extra: {nombre} = {contenido} (pagina {pagina}, seccion {seccion})"
            )
        else:
            registros.append(f"Campo extra: {clave} = {valor}")
    return registros


def _formatear_notas_extra(notas_extra: list[Any]) -> list[str]:
    registros: list[str] = []
    for nota in notas_extra:
        if isinstance(nota, dict):
            texto = nota.get("valor", nota.get("texto", ""))
            pagina = nota.get("pagina", "")
            seccion = nota.get("seccion", "")
            registros.append(f"Nota extra: {texto} (pagina {pagina}, seccion {seccion})")
        else:
            registros.append(f"Nota extra: {nota}")
    return registros


def _normalizar_status(status: str) -> str:
    if status == "ok":
        return "Ok"
    return status


def _construir_metadata(
    resultado: dict[str, Any],
    paginas: list[PaginaPdf],
    filename: str,
    profile_id: str,
    form_version: str,
) -> dict[str, Any]:
    metadata = resultado.get("metadata", {})
    return {
        "summary_page": metadata.get("summary_page"),
        "technical_page": metadata.get("technical_page"),
        "pit_escape_options_page": metadata.get("pit_escape_options_page"),
        "premounted_cabinet_buttons_page": metadata.get("premounted_cabinet_buttons_page"),
        "is_raloe_crono": metadata.get("is_raloe_crono", False),
        "status": _normalizar_status(metadata.get("status", "")),
        "warnings": metadata.get("warnings", []),
        "filename": filename,
        "num_pedido": extraer_num_pedido(paginas),
        "profile_id": profile_id,
        "template_id": metadata.get("template_id", profile_id),
        "form_version": form_version,
    }
