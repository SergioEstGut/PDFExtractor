import json
from importlib import resources
from typing import Any


def datos_vacios_raloe_crono() -> dict[str, Any]:
    contract = resources.files(
        "extractor_pdf.infrastructure.extraction.client_base"
    ).joinpath("raloe_crono_empty_contract.json")
    return json.loads(contract.read_text(encoding="utf-8"))


def datos_vacios_felesa_crono() -> dict[str, Any]:
    contract = resources.files(
        "extractor_pdf.infrastructure.extraction.client_base"
    ).joinpath("felesa_crono_empty_contract.json")
    return json.loads(contract.read_text(encoding="utf-8"))







