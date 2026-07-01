from typing import Any

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import shutil
import unicodedata
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile

from extractor_pdf.application.salida_plana import (
    construir_data_plana_con_observaciones,
    construir_salida_plana,
)
from extractor_pdf.infrastructure.configuracion import configuracion
from extractor_pdf.infrastructure.ocr.extractor_visual_tesseract import (
    ErrorTesseractNoDisponible,
    ExtractorVisualTesseract,
)
from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf
from extractor_pdf.infrastructure.pdf.renderizador_pymupdf import RenderizadorPaginaPyMuPdf
from extractor_pdf.interfaces.api.dependencias import (
    crear_caso_uso_extraer_aszende_crono,
    crear_caso_uso_extraer_felesa_crono,
    crear_caso_uso_extraer_raloe_crono,
    crear_caso_uso_extraer_raloe_crono_fusionado,
)

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
app = FastAPI(title=configuracion.nombre_app, version="0.1.0")

DIRECTORIO_PRUEBAS_PEDIDOS = r"D:\Pedidos pruebas PDFExtractor\Formulario\Pruebas"
DIRECTORIO_PRUEBAS_RALOE = rf"{DIRECTORIO_PRUEBAS_PEDIDOS}\Raloe"
DIRECTORIO_PRUEBAS_FELESA_ELECTRICO = rf"{DIRECTORIO_PRUEBAS_PEDIDOS}\Felesa Electrico"
DIRECTORIO_PRUEBAS_FELESA_HIDRAULICO = rf"{DIRECTORIO_PRUEBAS_PEDIDOS}\Felesa Hidraulico"
DIRECTORIO_PRUEBAS_ASZENDE_ELECTRICO = rf"{DIRECTORIO_PRUEBAS_PEDIDOS}\Aszende Electrico"
CARPETAS_PEDIDOS_POR_PLANTILLA = {
    "raloe_crono": "Raloe",
    "felesa_crono_electrico": "Felesa Electrico",
    "felesa_crono_hidraulico": "Felesa Hidraulico",
    "aszende_crono_electrico": "Aszende Electrico",
}
ASZENDE_ELECTRICO_SECCIONES_TXT = [
    "Cabecera",
    "Normas",
    "Datos_Generales",
    "Datos_Motor",
    "Opciones_Maniobra",
    "Rescates",
    "Datos_Cabina",
    "Caja_Inspeccion",
    "Pesacargas",
    "Botonera_Cabina",
    "Botoneras_Exteriores",
    "Medidas_Premontada",
    "Medidas_Entreplantas",
    "Datos_Premontada",
    "Opciones_Especiales",
    "Parametros_Variador",
    "Observaciones",
]
FELESA_ELECTRICO_SECCIONES_TXT = [
    "Cabecera",
    "Normas",
    "Datos_Generales",
    "Datos_Motor",
    "Control_Motor",
    "Rescates",
    "Datos_Cabina",
    "Pesacargas",
    "Botonera_Cabina",
    "Opciones_Especiales",
    "Medidas_Premontada",
    "Medidas_Entreplantas",
    "Datos_Premontada",
    "Caja_Inspeccion",
    "Botoneras_Rellano",
    "Placas_Botoneras_Rellano",
    "Observaciones",
    "Notas",
]
FELESA_HIDRAULICO_SECCIONES_TXT = [
    "Cabecera",
    "Normas",
    "Datos_Generales",
    "Datos_Central",
    "Datos_Cabina",
    "Botonera_Cabina",
    "Botoneras_Exteriores",
    "Medidas_Premontada",
    "Medida_Entreplantas",
    "Datos_Premontada",
    "Caja_Inspeccion",
    "Opciones_Especiales",
    "Observaciones",
    "Notas",
]
CONTRATOS_SECCIONES_POR_PLANTILLA = {
    "felesa_crono_electrico": RAIZ_PROYECTO / "docs/contrato_felesa_crono/secciones",
    "felesa_crono_hidraulico": RAIZ_PROYECTO / "docs/contrato_felesa_crono_hidraulico/secciones",
    "aszende_crono_electrico": RAIZ_PROYECTO / "docs/contrato_aszende_crono_electrico/secciones",
}


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
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=False)
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
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=False)
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
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=False)
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
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=False)
    data = construir_data_plana_con_observaciones(resultado)
    return _json_ascii_response([[campo, valor] for campo, valor in data.items()])


@app.post("/admin/pruebas/clasificar-pedidos")
def clasificar_pedidos_prueba(
    base_path: str = Form(DIRECTORIO_PRUEBAS_PEDIDOS),
    dry_run: bool = Form(True),
    usar_ocr_dudosos: bool = Form(False),
) -> dict[str, Any]:
    directorio = Path(base_path)
    if not directorio.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"No existe el directorio de pruebas: {base_path}",
        )

    respuesta: dict[str, Any] = {
        "base_path": str(directorio),
        "dry_run": dry_run,
        "usar_ocr_dudosos": usar_ocr_dudosos,
        "clasificados": [],
        "movidos": [],
        "desconocidos": [],
        "omitidos": [],
        "errores": [],
    }

    for ruta_pdf in sorted(
        item for item in directorio.iterdir() if item.is_file() and item.suffix.casefold() == ".pdf"
    ):
        try:
            clasificacion = _clasificar_pdf_por_contenido(
                ruta_pdf.read_bytes(),
                usar_ocr_dudosos=usar_ocr_dudosos,
            )
        except Exception as exc:
            respuesta["errores"].append(
                {
                    "archivo": ruta_pdf.name,
                    "error": str(exc),
                }
            )
            continue

        if clasificacion is None:
            respuesta["desconocidos"].append({"archivo": ruta_pdf.name})
            continue

        carpeta_destino = CARPETAS_PEDIDOS_POR_PLANTILLA[clasificacion]
        destino = directorio / carpeta_destino / ruta_pdf.name
        if destino.exists():
            respuesta["omitidos"].append(
                {
                    "archivo": ruta_pdf.name,
                    "plantilla": clasificacion,
                    "destino": str(destino),
                    "motivo": "El archivo ya existe en destino.",
                }
            )
            continue

        movimiento = {
            "archivo": ruta_pdf.name,
            "plantilla": clasificacion,
            "destino": str(destino),
        }
        respuesta["clasificados"].append(movimiento)
        if not dry_run:
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(ruta_pdf), str(destino))
            respuesta["movidos"].append(movimiento)

    respuesta["resumen"] = {
        "clasificados": len(respuesta["clasificados"]),
        "movidos": len(respuesta["movidos"]),
        "desconocidos": len(respuesta["desconocidos"]),
        "omitidos": len(respuesta["omitidos"]),
        "errores": len(respuesta["errores"]),
    }
    return respuesta


@app.post("/admin/pruebas/raloe/extraer-array2d")
def extraer_array2d_raloe_pruebas(
    base_path: str = Form(DIRECTORIO_PRUEBAS_RALOE),
    resultados_dir: str = Form("Resultados"),
    batch_size: int = Form(4),
    max_workers: int = Form(2),
    overwrite: bool = Form(True),
) -> dict[str, Any]:
    return _extraer_array2d_pruebas(
        base_path=base_path,
        resultados_dir=resultados_dir,
        profile_id="raloe_crono",
        nombre_formulario="Raloe",
        batch_size=batch_size,
        max_workers=max_workers,
        overwrite=overwrite,
    )


@app.post("/admin/pruebas/felesa/electrico/extraer-array2d")
def extraer_array2d_felesa_electrico_pruebas(
    base_path: str = Form(DIRECTORIO_PRUEBAS_FELESA_ELECTRICO),
    resultados_dir: str = Form("Resultados"),
    batch_size: int = Form(4),
    max_workers: int = Form(2),
    overwrite: bool = Form(True),
) -> dict[str, Any]:
    return _extraer_array2d_pruebas(
        base_path=base_path,
        resultados_dir=resultados_dir,
        profile_id="felesa_crono",
        nombre_formulario="Felesa Electrico",
        batch_size=batch_size,
        max_workers=max_workers,
        overwrite=overwrite,
        template_id_txt="felesa_crono_electrico",
    )


@app.post("/admin/pruebas/felesa/hidraulico/extraer-array2d")
def extraer_array2d_felesa_hidraulico_pruebas(
    base_path: str = Form(DIRECTORIO_PRUEBAS_FELESA_HIDRAULICO),
    resultados_dir: str = Form("Resultados"),
    batch_size: int = Form(4),
    max_workers: int = Form(2),
    overwrite: bool = Form(True),
) -> dict[str, Any]:
    return _extraer_array2d_pruebas(
        base_path=base_path,
        resultados_dir=resultados_dir,
        profile_id="felesa_crono",
        nombre_formulario="Felesa Hidraulico",
        batch_size=batch_size,
        max_workers=max_workers,
        overwrite=overwrite,
        template_id_txt="felesa_crono_hidraulico",
    )


@app.post("/admin/pruebas/aszende/electrico/extraer-array2d")
def extraer_array2d_aszende_electrico_pruebas(
    base_path: str = Form(DIRECTORIO_PRUEBAS_ASZENDE_ELECTRICO),
    resultados_dir: str = Form("Resultados"),
    batch_size: int = Form(4),
    max_workers: int = Form(2),
    overwrite: bool = Form(True),
) -> dict[str, Any]:
    return _extraer_array2d_pruebas(
        base_path=base_path,
        resultados_dir=resultados_dir,
        profile_id="aszende_crono",
        nombre_formulario="Aszende Electrico",
        batch_size=batch_size,
        max_workers=max_workers,
        overwrite=overwrite,
        template_id_txt="aszende_crono_electrico",
    )


@app.post("/admin/pruebas/resultados/formatear-txt")
def formatear_txt_resultados_pruebas(
    base_path: str = Form(DIRECTORIO_PRUEBAS_PEDIDOS),
    resultados_dir: str = Form("Resultados"),
    incluir_raloe: bool = Form(False),
) -> dict[str, Any]:
    directorio_base = Path(base_path)
    if not directorio_base.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"No existe el directorio de pruebas: {base_path}",
        )

    carpetas: list[str] = []
    if incluir_raloe:
        carpetas.insert(0, "Raloe")

    respuesta: dict[str, Any] = {
        "base_path": str(directorio_base),
        "resultados_dir": resultados_dir,
        "incluir_raloe": incluir_raloe,
        "procesados": [],
        "omitidos": [],
        "errores": [],
    }

    for carpeta in carpetas:
        directorio_resultados = directorio_base / carpeta / resultados_dir
        if not directorio_resultados.is_dir():
            respuesta["omitidos"].append(
                {
                    "carpeta": carpeta,
                    "motivo": "No existe el directorio de resultados.",
                    "path": str(directorio_resultados),
                }
            )
            continue

        for ruta_txt in sorted(directorio_resultados.glob("*.txt")):
            try:
                lineas = _txt_array2d_a_lineas_clave_valor(ruta_txt)
                ruta_txt.write_text("\n".join(lineas) + "\n", encoding="utf-8")
            except ValueError as exc:
                respuesta["omitidos"].append(
                    {
                        "carpeta": carpeta,
                        "archivo": ruta_txt.name,
                        "motivo": str(exc),
                    }
                )
                continue
            except Exception as exc:
                respuesta["errores"].append(
                    {
                        "carpeta": carpeta,
                        "archivo": ruta_txt.name,
                        "error": str(exc),
                    }
                )
                continue

            respuesta["procesados"].append(
                {
                    "carpeta": carpeta,
                    "archivo": ruta_txt.name,
                    "lineas": len(lineas),
                }
            )

    respuesta["resumen"] = {
        "procesados": len(respuesta["procesados"]),
        "omitidos": len(respuesta["omitidos"]),
        "errores": len(respuesta["errores"]),
    }
    return respuesta


def _extraer_array2d_pruebas(
    base_path: str,
    resultados_dir: str,
    profile_id: str,
    nombre_formulario: str,
    batch_size: int,
    max_workers: int,
    overwrite: bool,
    template_id_txt: str | None = None,
) -> dict[str, Any]:
    directorio = Path(base_path)
    if not directorio.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"No existe el directorio {nombre_formulario} de pruebas: {base_path}",
        )

    directorio_resultados = directorio / resultados_dir
    directorio_resultados.mkdir(parents=True, exist_ok=True)
    rutas_pdf = sorted(
        item for item in directorio.iterdir() if item.is_file() and item.suffix.casefold() == ".pdf"
    )

    batch_size = max(1, batch_size)
    max_workers = max(1, min(max_workers, batch_size, 4))
    respuesta: dict[str, Any] = {
        "base_path": str(directorio),
        "resultados_dir": str(directorio_resultados),
        "batch_size": batch_size,
        "max_workers": max_workers,
        "overwrite": overwrite,
        "procesados": [],
        "omitidos": [],
        "errores": [],
        "lotes": [],
    }

    for indice_lote, lote in enumerate(_trocear(rutas_pdf, batch_size), start=1):
        lote_info: dict[str, Any] = {
            "indice": indice_lote,
            "archivos": [ruta.name for ruta in lote],
            "procesados": 0,
            "omitidos": 0,
            "errores": 0,
        }
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _extraer_array2d_a_txt,
                    ruta_pdf,
                    directorio_resultados,
                    profile_id,
                    overwrite,
                    template_id_txt,
                ): ruta_pdf
                for ruta_pdf in lote
            }
            for future in as_completed(futures):
                ruta_pdf = futures[future]
                try:
                    resultado = future.result()
                except Exception as exc:
                    error = {"archivo": ruta_pdf.name, "error": str(exc)}
                    respuesta["errores"].append(error)
                    lote_info["errores"] += 1
                    continue

                if resultado.get("omitido"):
                    respuesta["omitidos"].append(resultado)
                    lote_info["omitidos"] += 1
                else:
                    respuesta["procesados"].append(resultado)
                    lote_info["procesados"] += 1

        respuesta["lotes"].append(lote_info)

    respuesta["resumen"] = {
        "pdfs": len(rutas_pdf),
        "procesados": len(respuesta["procesados"]),
        "omitidos": len(respuesta["omitidos"]),
        "errores": len(respuesta["errores"]),
        "lotes": len(respuesta["lotes"]),
    }
    return respuesta


def _extraer_array2d_a_txt(
    ruta_pdf: Path,
    directorio_resultados: Path,
    profile_id: str,
    overwrite: bool,
    template_id_txt: str | None = None,
) -> dict[str, Any]:
    ruta_salida = directorio_resultados / f"{ruta_pdf.stem}.txt"
    if ruta_salida.exists() and not overwrite:
        return {
            "archivo": ruta_pdf.name,
            "salida": str(ruta_salida),
            "omitido": True,
            "motivo": "El resultado ya existe.",
        }

    bytes_pdf = ruta_pdf.read_bytes()
    _detectar_version_formulario(bytes_pdf, profile_id)
    resultado = _extraer_por_perfil(bytes_pdf, profile_id, fusionado=False)
    data = construir_data_plana_con_observaciones(resultado)
    if template_id_txt in {
        "aszende_crono_electrico",
        "felesa_crono_electrico",
        "felesa_crono_hidraulico",
    }:
        secciones_txt = {
            "aszende_crono_electrico": ASZENDE_ELECTRICO_SECCIONES_TXT,
            "felesa_crono_electrico": FELESA_ELECTRICO_SECCIONES_TXT,
            "felesa_crono_hidraulico": FELESA_HIDRAULICO_SECCIONES_TXT,
        }[template_id_txt]
        contenido = _txt_clave_valor_ordenado_por_contrato(
            data=data,
            template_id=template_id_txt,
            secciones_ordenadas=secciones_txt,
        )
        ruta_salida.write_text(contenido, encoding="utf-8")
        campos = sum(1 for linea in contenido.splitlines() if linea.strip())
    else:
        array2d = [[campo, valor] for campo, valor in data.items()]
        ruta_salida.write_text(json.dumps(array2d, ensure_ascii=True), encoding="utf-8")
        campos = len(array2d)
    return {
        "archivo": ruta_pdf.name,
        "salida": str(ruta_salida),
        "campos": campos,
        "omitido": False,
    }


def _txt_array2d_a_lineas_clave_valor(ruta_txt: Path) -> list[str]:
    contenido = ruta_txt.read_text(encoding="utf-8-sig").strip()
    if not contenido:
        raise ValueError("El archivo esta vacio.")

    try:
        data = json.loads(contenido)
    except json.JSONDecodeError as exc:
        raise ValueError("El archivo no contiene un array 2D JSON.") from exc

    if not isinstance(data, list):
        raise ValueError("El JSON no es una lista.")

    lineas: list[str] = []
    for indice, fila in enumerate(data, start=1):
        if not isinstance(fila, list) or len(fila) != 2:
            raise ValueError(f"La fila {indice} no tiene formato [clave, valor].")
        clave, valor = fila
        lineas.append(f"{_valor_txt(clave)}: {_valor_txt(valor)}")
    return lineas


def _valor_txt(valor: Any) -> str:
    texto = "" if valor is None else str(valor)
    return texto.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")


def _txt_clave_valor_ordenado_por_contrato(
    data: dict[str, Any],
    template_id: str,
    secciones_ordenadas: list[str],
) -> str:
    orden_campos = _cargar_orden_campos_contrato(template_id)
    claves_escritas: set[str] = set()
    bloques: list[str] = []

    for seccion in secciones_ordenadas:
        campos = orden_campos.get(seccion, [])
        lineas_seccion: list[str] = []
        for campo in campos:
            clave = f"{seccion}.{campo}"
            if clave not in data:
                continue
            lineas_seccion.append(f"{clave}: {_valor_txt(data.get(clave))}")
            claves_escritas.add(clave)

        extras_seccion = [
            clave
            for clave in data
            if clave.startswith(f"{seccion}.") and clave not in claves_escritas
        ]
        for clave in extras_seccion:
            lineas_seccion.append(f"{clave}: {_valor_txt(data.get(clave))}")
            claves_escritas.add(clave)

        if lineas_seccion:
            bloques.append("\n".join(lineas_seccion))

    lineas_extra = [
        f"{clave}: {_valor_txt(valor)}"
        for clave, valor in data.items()
        if clave not in claves_escritas
    ]
    if lineas_extra:
        bloques.append("\n".join(lineas_extra))

    return "\n\n".join(bloques) + "\n"


def _cargar_orden_campos_contrato(template_id: str) -> dict[str, list[str]]:
    directorio = CONTRATOS_SECCIONES_POR_PLANTILLA.get(template_id)
    if directorio is None:
        return {}

    orden: dict[str, list[str]] = {}
    for ruta in sorted(directorio.glob("*.json")):
        with ruta.open("r", encoding="utf-8-sig") as archivo:
            contrato = json.load(archivo)
        seccion = str(contrato.get("seccion") or ruta.stem)
        campos = contrato.get("campos") or []
        orden[seccion] = [
            str(campo["nombre"])
            for campo in campos
            if isinstance(campo, dict) and campo.get("nombre")
        ]
    return orden


def _trocear(items: list[Path], size: int) -> list[list[Path]]:
    return [items[indice : indice + size] for indice in range(0, len(items), size)]


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
        resultado = crear_caso_uso_extraer_felesa_crono().ejecutar(bytes_pdf)
        if fusionado:
            warnings = resultado.setdefault("metadata", {}).setdefault("warnings", [])
            aviso = f"OCR no implementado para {profile_id}; se usa extraccion PDF."
            if aviso not in warnings:
                warnings.append(aviso)
            resultado["metadata"]["status"] = "partial"
        return resultado
    if profile_id == "aszende_crono":
        resultado = crear_caso_uso_extraer_aszende_crono().ejecutar(bytes_pdf)
        if fusionado:
            warnings = resultado.setdefault("metadata", {}).setdefault("warnings", [])
            aviso = f"OCR no implementado para {profile_id}; se usa extraccion PDF."
            if aviso not in warnings:
                warnings.append(aviso)
            resultado["metadata"]["status"] = "partial"
        return resultado
    raise HTTPException(
        status_code=400,
        detail=f"Perfil no soportado: {profile_id}.",
    )


def _validar_perfil(profile_id: str) -> None:
    if profile_id not in {"raloe_crono", "felesa_crono", "aszende_crono"}:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Perfil no soportado: {profile_id}. "
                "Perfiles disponibles: raloe_crono, felesa_crono, aszende_crono."
            ),
        )


def _detectar_version_formulario(bytes_pdf: bytes, profile_id: str) -> str:
    if profile_id in {"raloe_crono", "felesa_crono", "aszende_crono"}:
        return "0"
    raise HTTPException(
        status_code=400,
        detail=f"No hay detector de version para el perfil: {profile_id}.",
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


def _clasificar_pdf_por_contenido(bytes_pdf: bytes, usar_ocr_dudosos: bool = False) -> str | None:
    paginas = LectorTextoPyMuPdf().leer_paginas(bytes_pdf)
    texto = _normalizar_texto("\n".join(pagina.texto for pagina in paginas))
    clasificacion = _clasificar_texto_normalizado(texto)
    if clasificacion is not None:
        return clasificacion

    if usar_ocr_dudosos:
        texto_ocr = _leer_texto_ocr_para_clasificacion(bytes_pdf, max_paginas=min(len(paginas), 2))
        return _clasificar_texto_normalizado(texto_ocr)

    return None


def _clasificar_texto_normalizado(texto: str) -> str | None:
    if _parece_raloe_crono(texto):
        return "raloe_crono"

    if _parece_aszende_crono_electrico(texto):
        return "aszende_crono_electrico"

    if _parece_felesa_crono_hidraulico(texto):
        return "felesa_crono_hidraulico"

    if _parece_felesa_crono_electrico(texto):
        return "felesa_crono_electrico"

    return None


def _leer_texto_ocr_para_clasificacion(bytes_pdf: bytes, max_paginas: int) -> str:
    renderizador = RenderizadorPaginaPyMuPdf()
    extractor = ExtractorVisualTesseract()
    textos: list[str] = []
    for numero_pagina in range(1, max_paginas + 1):
        try:
            render = renderizador.renderizar_pagina(bytes_pdf, numero_pagina=numero_pagina, dpi=150)
            ocr = extractor.extraer(render, cliente_id="clasificador")
        except ErrorTesseractNoDisponible:
            return ""
        textos.append(ocr.get("ocr", {}).get("text", ""))
    return _normalizar_texto("\n".join(textos))


def _parece_raloe_crono(texto: str) -> bool:
    if "formulario sirius evo" in texto or ("portecnic" in texto and "evo" in texto):
        return False

    if "raloe" in texto and "serie crono" in texto and "pedido compra" in texto:
        return True

    senales = {
        "detalle de material",
        "maniobra carlos silva",
        "gestion foso huida reducida",
        "limitador velocidad cab",
        "premontada",
        "botonera cabina",
    }
    return "raloe" in texto and sum(1 for senal in senales if senal in texto) >= 4


def _parece_aszende_crono_electrico(texto: str) -> bool:
    return "aszende" in texto and "formulari crono" in texto and "datos motor" in texto


def _parece_felesa_crono_hidraulico(texto: str) -> bool:
    if "felesa" not in texto:
        return False

    if "formulario maniobra crono" in texto or "formulario maniobras crono" in texto:
        return (
            "datos central" in texto
            or "hidraulicas" in texto
            or "hidraulica" in texto
            or "hidraulico" in texto
        )

    senales_hidraulicas = {
        "maniobra a central",
        "grupo valvulas",
        "grupo vilvulas",
        "tension valvulas",
        "tension vilvulas",
        "doble piston",
        "cerrojos de seguridad",
        "micronivelacion",
    }
    return ("pais destino" in texto or "cliente felesa" in texto) and sum(
        1 for senal in senales_hidraulicas if senal in texto
    ) >= 3


def _parece_felesa_crono_electrico(texto: str) -> bool:
    if "felesa" not in texto:
        return False

    if "formulario maniobra crono" in texto or "formulario maniobras crono" in texto:
        return (
            "datos motor" in texto
            or "control motor" in texto
            or "electricas" in texto
            or "electrico" in texto
        )

    senales_formulario = {
        "pais destino",
        "datos instalacion",
        "botoneras de rellano",
        "ubicacion maniobra",
    }
    return all(senal in texto for senal in senales_formulario)


def _normalizar_texto(texto: str) -> str:
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"[^a-zA-Z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip().casefold()







