from typing import Any

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile

from extractor_pdf.application.salida_plana import (
    construir_data_plana_con_observaciones,
    construir_salida_plana,
)
from extractor_pdf.infrastructure.configuracion import configuracion
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.selection.detectores_paginas_felesa_crono import (
    detectar_plantilla_felesa_crono,
)
from extractor_pdf.interfaces.api.dependencias import (
    crear_caso_uso_extraer_felesa_crono,
    crear_caso_uso_extraer_raloe_crono,
    crear_caso_uso_extraer_raloe_crono_fusionado,
)

app = FastAPI(title=configuracion.nombre_app, version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract")
async def extraer(
    file: UploadFile = File(...),
    profile_id: str = Form("raloe_crono"),
) -> dict[str, Any]:
    _validar_perfil(profile_id)

    bytes_pdf = await file.read()
    form_version = _detectar_version_formulario(bytes_pdf, profile_id)
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=False)
    resultado["metadata"] = {
        **resultado["metadata"],
        "filename": file.filename or "documento.pdf",
        "profile_id": profile_id,
        "form_version": form_version,
    }
    return resultado


@app.post("/extract/fused")
async def extraer_fusionado(
    file: UploadFile = File(...),
    profile_id: str = Form("raloe_crono"),
) -> dict[str, Any]:
    _validar_perfil(profile_id)

    bytes_pdf = await file.read()
    form_version = _detectar_version_formulario(bytes_pdf, profile_id)
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=True)
    resultado["metadata"] = {
        **resultado["metadata"],
        "filename": file.filename or "documento.pdf",
        "profile_id": profile_id,
        "form_version": form_version,
    }
    return resultado


@app.post("/extract/flat")
async def extraer_plano(
    file: UploadFile = File(...),
    profile_id: str = Form("raloe_crono"),
) -> dict[str, Any]:
    _validar_perfil(profile_id)

    bytes_pdf = await file.read()
    form_version = _detectar_version_formulario(bytes_pdf, profile_id)
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=True)
    paginas = LectorTextoPyMuPdf().leer_paginas(bytes_pdf)
    return construir_salida_plana(
        resultado,
        paginas,
        filename=file.filename or "documento.pdf",
        profile_id=profile_id,
        form_version=form_version,
    )


@app.post("/extract/data")
async def extraer_data_plana(
    file: UploadFile | None = File(None),
    pdf_path: str | None = Form(None),
    profile_id: str = Form("raloe_crono"),
) -> dict[str, str]:
    _validar_perfil(profile_id)

    bytes_pdf = await _leer_pdf_desde_request(file=file, pdf_path=pdf_path)
    _detectar_version_formulario(bytes_pdf, profile_id)
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=True)
    return construir_data_plana_con_observaciones(resultado)


@app.post("/extract/data/path")
async def extraer_data_plana_desde_path_texto(
    request: Request,
    profile_id: str = "raloe_crono",
) -> Response:
    _validar_perfil(profile_id)

    pdf_path = (await request.body()).decode("utf-8-sig").strip()
    bytes_pdf = _leer_pdf_desde_path(pdf_path)
    _detectar_version_formulario(bytes_pdf, profile_id)
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=True)
    return _json_ascii_response(construir_data_plana_con_observaciones(resultado))


@app.post("/extract/data/path/array2d")
async def extraer_data_array_2d_desde_path_texto(
    request: Request,
    profile_id: str = "raloe_crono",
) -> Response:
    _validar_perfil(profile_id)

    pdf_path = (await request.body()).decode("utf-8-sig").strip()
    bytes_pdf = _leer_pdf_desde_path(pdf_path)
    _detectar_version_formulario(bytes_pdf, profile_id)
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=True)
    data = construir_data_plana_con_observaciones(resultado)
    return _json_ascii_response([[campo, valor] for campo, valor in data.items()])


def _extraer_por_perfil(
    bytes_pdf: bytes,
    profile_id: str,
    fusionado: bool,
) -> dict[str, Any]:
    if profile_id == "raloe_crono":
        if fusionado:
            return crear_caso_uso_extraer_raloe_crono_fusionado().ejecutar(bytes_pdf)
        return crear_caso_uso_extraer_raloe_crono().ejecutar(bytes_pdf)
    if profile_id == "felesa_crono":
        _validar_plantilla_felesa_soportada(bytes_pdf)
        resultado = crear_caso_uso_extraer_felesa_crono().ejecutar(bytes_pdf)
        if fusionado:
            warnings = resultado.setdefault("metadata", {}).setdefault("warnings", [])
            if "OCR no implementado para felesa_crono; se usa extraccion PDF." not in warnings:
                warnings.append("OCR no implementado para felesa_crono; se usa extraccion PDF.")
            resultado["metadata"]["status"] = "partial"
        return resultado
    raise HTTPException(
        status_code=400,
        detail=f"Perfil no soportado: {profile_id}.",
    )


def _validar_perfil(profile_id: str) -> None:
    if profile_id not in {"raloe_crono", "felesa_crono"}:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Perfil no soportado: {profile_id}. "
                "Perfiles disponibles: raloe_crono, felesa_crono."
            ),
        )


def _detectar_version_formulario(bytes_pdf: bytes, profile_id: str) -> str:
    if profile_id in {"raloe_crono", "felesa_crono"}:
        return "0"
    raise HTTPException(
        status_code=400,
        detail=f"No hay detector de version para el perfil: {profile_id}.",
    )


def _validar_plantilla_felesa_soportada(bytes_pdf: bytes) -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas(bytes_pdf)
    template_id = detectar_plantilla_felesa_crono(paginas)
    if template_id == "felesa_crono_electrico":
        return
    raise HTTPException(
        status_code=422,
        detail={
            "status": "unsupported_template",
            "profile_id": "felesa_crono",
            "template_id": template_id,
            "form_version": "0",
            "message": (
                "Formulario Felesa CRONO hidraulico detectado, "
                "contrato no implementado."
            ),
        },
    )


async def _leer_pdf_desde_request(
    file: UploadFile | None,
    pdf_path: str | None,
) -> bytes:
    if pdf_path:
        return _leer_pdf_desde_path(pdf_path)

    if file is None:
        raise HTTPException(
            status_code=422,
            detail="Debe enviarse 'pdf_path' o un archivo en el campo 'file'.",
        )

    return await file.read()


def _leer_pdf_desde_path(pdf_path: str) -> bytes:
    if not pdf_path:
        raise HTTPException(
            status_code=422,
            detail="Debe enviarse el path del PDF.",
        )

    ruta_pdf = Path(pdf_path)
    if not ruta_pdf.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"No existe el PDF en el servidor: {pdf_path}",
        )
    return ruta_pdf.read_bytes()


def _json_ascii_response(data: Any) -> Response:
    return Response(
        content=json.dumps(data, ensure_ascii=True),
        media_type="application/json",
    )







