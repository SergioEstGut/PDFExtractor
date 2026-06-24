from pathlib import Path

from extractor_pdf.infrastructure.pdf.lector_pymupdf import LectorTextoPyMuPdf


PDF_PATH = Path(__file__).resolve().parents[1] / "pdfs" / "Raloe" / "654391.pdf"


def test_lee_texto_embebido_de_pagina_fisica_5() -> None:
    paginas = LectorTextoPyMuPdf().leer_paginas(PDF_PATH.read_bytes())

    pagina_5 = paginas[4]

    assert pagina_5.numero == 5
    assert pagina_5.metodo_extraccion == "embedded_text"
    assert "MO/4473005" in pagina_5.texto
    assert "PEDIDO CON OBSERVACIONES" in pagina_5.texto
    assert "Serie:" in pagina_5.texto
    assert "Normas:" in pagina_5.texto
    assert "Caracter" in pagina_5.texto
    assert "ctrica:" in pagina_5.texto
    assert pagina_5.bloques
    assert all(bloque.x1 > bloque.x0 and bloque.y1 > bloque.y0 for bloque in pagina_5.bloques)








