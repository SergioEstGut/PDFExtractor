from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests


DEFAULT_API_URL = "http://192.168.1.118:8001/extract/flat"


@dataclass(frozen=True)
class ResultadoExtraccion:
    raw: dict[str, Any]
    data: dict[str, Any]
    metadata: dict[str, Any]
    campos_extra: dict[str, Any]
    notas_extra: list[dict[str, Any]]
    df_data: pd.DataFrame
    df_metadata: pd.DataFrame
    df_campos_extra: pd.DataFrame
    df_notas_extra: pd.DataFrame


def extraer_pedido(
    pdf_path: str | Path,
    api_url: str = DEFAULT_API_URL,
    profile_id: str = "raloe_crono",
    timeout: int = 300,
) -> ResultadoExtraccion:
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"No existe el PDF: {pdf_path}")

    with pdf_path.open("rb") as pdf_file:
        response = requests.post(
            api_url,
            data={"profile_id": profile_id},
            files={"file": (pdf_path.name, pdf_file, "application/pdf")},
            timeout=timeout,
        )

    response.raise_for_status()
    respuesta_json = response.json()

    data = respuesta_json.get("data", {})
    metadata = respuesta_json.get("metadata", {})
    campos_extra = respuesta_json.get("campos_extra", {})
    notas_extra = respuesta_json.get("Notas_extra", [])

    return ResultadoExtraccion(
        raw=respuesta_json,
        data=data,
        metadata=metadata,
        campos_extra=campos_extra,
        notas_extra=notas_extra,
        df_data=_dataframe_clave_valor(data, clave_columna="campo"),
        df_metadata=pd.DataFrame([metadata]),
        df_campos_extra=_dataframe_campos_extra(campos_extra),
        df_notas_extra=pd.DataFrame(notas_extra),
    )


def guardar_excel(resultado: ResultadoExtraccion, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path) as writer:
        resultado.df_data.to_excel(writer, sheet_name="data", index=False)
        resultado.df_metadata.to_excel(writer, sheet_name="metadata", index=False)
        resultado.df_campos_extra.to_excel(writer, sheet_name="campos_extra", index=False)
        resultado.df_notas_extra.to_excel(writer, sheet_name="notas_extra", index=False)

    return output_path


def _dataframe_campos_extra(campos_extra: dict[str, Any]) -> pd.DataFrame:
    filas = []
    for clave, valor in campos_extra.items():
        if isinstance(valor, dict):
            filas.append({"clave": clave, **valor})
        else:
            filas.append({"clave": clave, "valor": valor})
    return pd.DataFrame(filas)


def _dataframe_clave_valor(data: dict[str, Any], clave_columna: str = "key") -> pd.DataFrame:
    filas = []
    for clave, valor in data.items():
        seccion, separador, campo = clave.partition(".")
        filas.append(
            {
                clave_columna: clave,
                "seccion": seccion if separador else "",
                "campo": campo if separador else clave,
                "valor": valor,
            }
        )
    return pd.DataFrame(filas)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cliente Python para ExtractorPDF /extract/flat")
    parser.add_argument("pdf", nargs="?", help="Ruta del PDF a enviar. Si se omite, se abre un selector de archivo.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"URL del endpoint. Default: {DEFAULT_API_URL}")
    parser.add_argument("--excel", help="Ruta opcional para exportar el resultado a XLSX")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout HTTP en segundos")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    pdf_path = args.pdf or seleccionar_pdf()
    if not pdf_path:
        print("No se selecciono ningun PDF.")
        return

    resultado = extraer_pedido(pdf_path, api_url=args.api_url, timeout=args.timeout)

    print("metadata")
    print(resultado.df_metadata.T)
    print()
    print(f"data: {len(resultado.df_data)} registros")
    print(resultado.df_data.head())
    print(f"campos_extra: {len(resultado.campos_extra)}")
    if len(resultado.campos_extra) > 0:
        print(resultado.df_campos_extra)
    print(f"notas_extra: {len(resultado.notas_extra)}")
    if len(resultado.notas_extra) > 0:
        print(resultado.df_notas_extra)

    if args.excel:
        ruta_excel = guardar_excel(resultado, args.excel)
        print(f"Excel generado: {ruta_excel}")


def ejecutar_con_pausa() -> None:
    try:
        main()
    except Exception as exc:
        print()
        print(f"ERROR: {exc}")
    finally:
        print()
        input("Pulsa Enter para cerrar...")


def seleccionar_pdf() -> str:
    script = """
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = 'Selecciona un PDF'
$dialog.Filter = 'Archivos PDF (*.pdf)|*.pdf|Todos los archivos (*.*)|*.*'
$dialog.Multiselect = $false
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.FileName
}
"""
    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )
    return resultado.stdout.strip()


if __name__ == "__main__":
    ejecutar_con_pausa()
