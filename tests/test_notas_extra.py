from extractor_pdf.application.notas_extra import detectar_notas_extra
from extractor_pdf.domain.entidades import PaginaPdf, PalabraTexto


def test_tonos_azules_pueden_ignorarse_como_texto_normal() -> None:
    pagina = PaginaPdf(
        numero=1,
        texto="",
        metodo_extraccion="embedded_text",
        palabras=[
            PalabraTexto(texto="Cab", x0=10, y0=10, x1=20, y1=18, color=0x2C4FA2),
            PalabraTexto(texto="Talla", x0=24, y0=10, x1=42, y1=18, color=0x3953A4),
        ],
    )

    assert detectar_notas_extra([pagina], ignorar_tonos_azules=True) == []
    assert detectar_notas_extra([pagina], ignorar_tonos_azules=False) == [
        {"valor": "Cab Talla", "pagina": 1, "seccion": ""}
    ]
