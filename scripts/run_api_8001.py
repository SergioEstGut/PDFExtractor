from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

uvicorn.run("extractor_pdf.interfaces.api.main:app", host="127.0.0.1", port=8001)
