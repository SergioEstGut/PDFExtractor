from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

GUIA_TXT = DOCS / "guia_desde_cero_extractor_pdf.txt"
TECNICO_MD = DOCS / "documentacion_tecnica_programador_raloe_crono.md"

PDF_GUIA = DOCS / "guia_desde_cero_extractor_pdf.pdf"
PDF_TECNICO = DOCS / "documentacion_tecnica_programador_raloe_crono.pdf"


PALETA = {
    "azul": colors.HexColor("#1F4E79"),
    "azul_oscuro": colors.HexColor("#17324D"),
    "azul_claro": colors.HexColor("#EAF2F8"),
    "verde": colors.HexColor("#2F855A"),
    "verde_claro": colors.HexColor("#EAF7EF"),
    "ambar": colors.HexColor("#B7791F"),
    "ambar_claro": colors.HexColor("#FFF4D6"),
    "gris": colors.HexColor("#5F6B7A"),
    "gris_claro": colors.HexColor("#F4F6F8"),
    "borde": colors.HexColor("#CBD5E1"),
    "codigo": colors.HexColor("#F7F9FB"),
    "texto": colors.HexColor("#1F2933"),
}


def leer_texto(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalizar_mojibake(texto: str) -> str:
    reemplazos = {
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã±": "ñ",
        "Ã": "Á",
        "Ã‰": "É",
        "Ã": "Í",
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Ã‘": "Ñ",
        "Â¿": "¿",
        "Â¡": "¡",
        "â€œ": '"',
        "â€": '"',
        "â€™": "'",
        "â€“": "-",
        "â€”": "-",
    }
    for malo, bueno in reemplazos.items():
        texto = texto.replace(malo, bueno)
    return texto


def estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "Titulo",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=PALETA["azul_oscuro"],
            spaceAfter=10,
        ),
        "subtitulo": ParagraphStyle(
            "Subtitulo",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=PALETA["gris"],
            spaceAfter=18,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=PALETA["azul"],
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=PALETA["azul_oscuro"],
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=PALETA["texto"],
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.5,
            leftIndent=12,
            firstLineIndent=-7,
            textColor=PALETA["texto"],
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.8,
            leading=9.8,
            textColor=colors.HexColor("#263238"),
            backColor=PALETA["codigo"],
            borderColor=PALETA["borde"],
            borderWidth=0.5,
            borderPadding=6,
            spaceBefore=4,
            spaceAfter=7,
        ),
        "tree": ParagraphStyle(
            "Tree",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8.2,
            leading=11,
            textColor=colors.HexColor("#263238"),
            backColor=colors.HexColor("#F8FAFC"),
            borderColor=PALETA["borde"],
            borderWidth=0.5,
            borderPadding=7,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "kv": ParagraphStyle(
            "KV",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            leftIndent=12,
            spaceAfter=4,
            textColor=PALETA["texto"],
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=PALETA["gris"],
        ),
    }


def limpiar_parrafo(texto: str) -> str:
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texto = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", texto)
    return texto


def es_subrayado(linea: str) -> bool:
    limpia = linea.strip()
    return len(limpia) >= 3 and set(limpia) in ({"="}, {"-"})


def es_titulo_numerado(linea: str) -> bool:
    return bool(re.match(r"^\d+(\.\d+)*\.\s+.+", linea) or re.match(r"^\d+\.\s+.+", linea))


def iconizar_arbol(lineas: list[str]) -> str:
    resultado = []
    for linea in lineas:
        indent = len(linea) - len(linea.lstrip(" "))
        nombre = linea.strip()
        if not nombre:
            resultado.append("")
            continue
        es_archivo = "." in nombre and not nombre.startswith(".venv")
        icono = "[FILE]" if es_archivo else "[DIR]"
        resultado.append(f"{' ' * indent}{icono} {nombre}")
    return "\n".join(resultado)


def parece_bloque_arbol(lineas: list[str]) -> bool:
    if len(lineas) < 2:
        return False
    nombres = [linea.strip() for linea in lineas if linea.strip()]
    if not nombres:
        return False
    indicadores = {"src", "tests", "docs", "pdfs", "infrastructure", "application", "domain", "interfaces"}
    return any(nombre in indicadores or nombre.endswith(".py") or nombre.endswith(".json") for nombre in nombres)


def crear_cover(titulo: str, subtitulo: str) -> list:
    s = estilos()
    tabla = Table(
        [
            [
                Paragraph(f"<b>{titulo}</b>", s["titulo"]),
            ],
            [
                Paragraph(subtitulo, s["subtitulo"]),
            ],
        ],
        colWidths=[16 * cm],
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETA["azul_claro"]),
                ("BOX", (0, 0), (-1, -1), 1, PALETA["azul"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 18),
                ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                ("TOPPADDING", (0, 0), (-1, -1), 18),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return [tabla, Spacer(1, 0.35 * cm)]


def construir_guia() -> list:
    texto = normalizar_mojibake(leer_texto(GUIA_TXT))
    lineas = texto.splitlines()
    s = estilos()
    story: list = []
    story.extend(
        crear_cover(
            "Guia desde cero - Extractor PDF",
            "Instalacion, creacion del proyecto, dependencias, estructura y flujo de ejecucion.",
        )
    )

    i = 0
    while i < len(lineas):
        linea = lineas[i].rstrip()
        siguiente = lineas[i + 1].strip() if i + 1 < len(lineas) else ""

        if not linea.strip():
            i += 1
            continue

        if siguiente and es_subrayado(siguiente):
            estilo = s["h1"] if set(siguiente) == {"="} or re.match(r"^\d+\.\s", linea) else s["h2"]
            story.append(Paragraph(limpiar_parrafo(linea), estilo))
            i += 2
            continue

        if linea.strip().startswith("- "):
            items = []
            while i < len(lineas) and lineas[i].strip().startswith("- "):
                items.append(
                    ListItem(
                        Paragraph(limpiar_parrafo(lineas[i].strip()[2:]), s["body"]),
                        leftIndent=10,
                    )
                )
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=14, bulletFontSize=7))
            story.append(Spacer(1, 3))
            continue

        bloque = [linea]
        j = i + 1
        while (
            j < len(lineas)
            and lineas[j].strip()
            and not (j + 1 < len(lineas) and es_subrayado(lineas[j + 1]))
            and not lineas[j].strip().startswith("- ")
            and not re.match(r"^\d+\.\s", lineas[j].strip())
        ):
            if lineas[j].startswith(" ") or lineas[j].startswith("\t"):
                bloque.append(lineas[j].rstrip())
                j += 1
            else:
                break

        if parece_bloque_arbol(bloque) and len(bloque) > 1:
            story.append(ArbolCarpetas(bloque))
            story.append(Spacer(1, 6))
            i = j
            continue

        if len(bloque) > 1 and any(linea_b.startswith("    ") for linea_b in bloque[1:]):
            clave = bloque[0].strip()
            descripcion = " ".join(linea_b.strip() for linea_b in bloque[1:] if linea_b.strip())
            story.append(Paragraph(f"<b>{limpiar_parrafo(clave)}</b><br/>{limpiar_parrafo(descripcion)}", s["kv"]))
            i = j
            continue

        if (
            "\\" in linea
            or linea.startswith("{")
            or linea.startswith("}")
            or linea.startswith("pip ")
            or linea.startswith("python ")
            or linea.startswith("uvicorn ")
            or linea.startswith("pytest")
            or linea.startswith("http://")
            or linea.startswith(".venv")
        ):
            story.append(Preformatted(linea, s["code"]))
        else:
            story.append(Paragraph(limpiar_parrafo(linea), s["body"]))
        i += 1

    return story


@dataclass
class Edge:
    origen: str
    destino: str
    etiqueta: str | None = None


class FlowchartBasico(Flowable):
    def __init__(self, codigo: str, ancho: float = 470, titulo: str | None = None):
        super().__init__()
        self.codigo = codigo
        self.ancho = ancho
        self.titulo = titulo
        self.nodos, self.edges, self.direccion = self._parsear(codigo)
        self.alto = self._calcular_alto()

    def wrap(self, availWidth, availHeight):
        self.ancho = min(self.ancho, availWidth)
        self.alto = self._calcular_alto()
        return self.ancho, self.alto

    def _parsear(self, codigo: str):
        lineas = [l.strip() for l in codigo.splitlines() if l.strip() and not l.strip().startswith("flowchart")]
        direccion = "LR" if codigo.splitlines()[0].strip().endswith("LR") else "TD"
        nodos: dict[str, str] = {}
        edges: list[Edge] = []

        def leer_nodo(token: str) -> tuple[str, str]:
            token = token.strip()
            ident_match = re.match(r"^(\w+)", token)
            if not ident_match:
                return token, token
            ident = ident_match.group(1)
            label_match = re.search(r'\["(.+?)"\]|\{"(.+?)"\}', token)
            etiqueta = ident
            if label_match:
                etiqueta = label_match.group(1) or label_match.group(2) or ident
            return ident, etiqueta

        for linea in lineas:
            etiqueta = None
            m_etiqueta = re.search(r'--\s*"(.+?)"\s*-->', linea)
            if m_etiqueta:
                etiqueta = m_etiqueta.group(1)
                izquierda, derecha = linea.split(m_etiqueta.group(0), 1)
            elif "-->" in linea:
                izquierda, derecha = linea.split("-->", 1)
            else:
                continue
            o, etiqueta_origen = leer_nodo(izquierda)
            d, etiqueta_destino = leer_nodo(derecha)
            nodos.setdefault(o, etiqueta_origen)
            nodos.setdefault(d, etiqueta_destino)
            edges.append(Edge(o, d, etiqueta))
        return nodos, edges, direccion

    def _calcular_alto(self):
        n = max(1, len(self.nodos))
        if self.direccion == "LR":
            filas = max(2, (n + 3) // 4)
            return 42 + filas * 70
        if n > 9:
            filas = (n + 1) // 2
            return 36 + filas * 43
        return 35 + n * 42

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(PALETA["gris_claro"])
        c.setStrokeColor(PALETA["borde"])
        c.roundRect(0, 0, self.ancho, self.alto, 8, fill=1, stroke=1)

        if self.titulo:
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(PALETA["azul_oscuro"])
            c.drawString(12, self.alto - 22, self.titulo)

        ids = list(self.nodos.keys())
        posiciones: dict[str, tuple[float, float]] = {}
        caja_w = min(260, self.ancho - 52)
        caja_h = 28
        top = self.alto - 52

        if self.direccion == "LR":
            cols = 4
            caja_w = (self.ancho - 60) / cols
            for idx, nodo in enumerate(ids):
                fila = idx // cols
                col = idx % cols
                x = 16 + col * (caja_w + 14)
                y = top - fila * 70
                posiciones[nodo] = (x, y)
        elif len(ids) > 9:
            cols = 2
            caja_w = (self.ancho - 52) / cols
            for idx, nodo in enumerate(ids):
                fila = idx // cols
                col = idx % cols
                x = 16 + col * (caja_w + 20)
                y = top - fila * 43
                posiciones[nodo] = (x, y)
        else:
            for idx, nodo in enumerate(ids):
                x = (self.ancho - caja_w) / 2
                y = top - idx * 42
                posiciones[nodo] = (x, y)

        c.setStrokeColor(PALETA["azul"])
        c.setFillColor(PALETA["azul"])
        for edge in self.edges:
            if edge.origen not in posiciones or edge.destino not in posiciones:
                continue
            x1, y1 = posiciones[edge.origen]
            x2, y2 = posiciones[edge.destino]
            if self.direccion == "LR" and abs(y1 - y2) < 2:
                start = (x1 + caja_w, y1 + caja_h / 2)
                end = (x2, y2 + caja_h / 2)
            else:
                start = (x1 + caja_w / 2, y1)
                end = (x2 + caja_w / 2, y2 + caja_h)
            c.line(start[0], start[1], end[0], end[1])
            c.circle(end[0], end[1], 2, fill=1, stroke=0)
            if edge.etiqueta:
                c.setFont("Helvetica", 6.5)
                c.setFillColor(PALETA["gris"])
                c.drawCentredString((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 3, edge.etiqueta)
                c.setFillColor(PALETA["azul"])

        for nodo, (x, y) in posiciones.items():
            etiqueta = self.nodos[nodo]
            c.setFillColor(colors.white)
            c.setStrokeColor(PALETA["azul"])
            c.roundRect(x, y, caja_w, caja_h, 5, fill=1, stroke=1)
            c.setFillColor(PALETA["texto"])
            c.setFont("Helvetica", 7.1)
            lineas = textwrap.wrap(etiqueta, width=max(14, int(caja_w / 5)))
            for k, texto in enumerate(lineas[:2]):
                c.drawCentredString(x + caja_w / 2, y + 17 - k * 8, texto)

        c.restoreState()


class ArbolCarpetas(Flowable):
    def __init__(self, lineas: list[str], ancho: float = 470):
        super().__init__()
        self.lineas = [linea.rstrip() for linea in lineas if linea.strip()]
        self.ancho = ancho
        self.line_height = 13
        self.alto = 16 + len(self.lineas) * self.line_height

    def wrap(self, availWidth, availHeight):
        self.ancho = min(self.ancho, availWidth)
        return self.ancho, self.alto

    @staticmethod
    def _es_archivo(nombre: str) -> bool:
        return "." in nombre and not nombre.startswith(".venv")

    @staticmethod
    def _dibujar_icono_carpeta(c, x: float, y: float):
        c.setFillColor(colors.HexColor("#F6C453"))
        c.setStrokeColor(colors.HexColor("#C9972B"))
        c.roundRect(x, y + 1, 11, 7, 1.5, fill=1, stroke=1)
        c.rect(x + 1, y + 7, 5, 3, fill=1, stroke=1)

    @staticmethod
    def _dibujar_icono_archivo(c, x: float, y: float):
        c.setFillColor(colors.HexColor("#DDEBFF"))
        c.setStrokeColor(colors.HexColor("#5B7DB1"))
        c.roundRect(x + 1, y, 9, 11, 1.2, fill=1, stroke=1)
        c.line(x + 7, y + 11, x + 10, y + 8)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.setStrokeColor(PALETA["borde"])
        c.roundRect(0, 0, self.ancho, self.alto, 6, fill=1, stroke=1)
        c.setFont("Courier", 8.1)
        y = self.alto - 14
        for linea in self.lineas:
            indent = len(linea) - len(linea.lstrip(" "))
            nombre = linea.strip()
            x = 10 + indent * 5
            if self._es_archivo(nombre):
                self._dibujar_icono_archivo(c, x, y - 3)
            else:
                self._dibujar_icono_carpeta(c, x, y - 2)
            c.setFillColor(PALETA["texto"])
            c.drawString(x + 16, y, nombre)
            y -= self.line_height
        c.restoreState()


class SequenceBasico(Flowable):
    def __init__(self, codigo: str, ancho: float = 470):
        super().__init__()
        self.codigo = codigo
        self.ancho = ancho
        self.participantes, self.mensajes = self._parsear(codigo)
        self.alto = 58 + len(self.mensajes) * 14

    def wrap(self, availWidth, availHeight):
        self.ancho = min(self.ancho, availWidth)
        return self.ancho, self.alto

    def _parsear(self, codigo: str):
        participantes: list[str] = []
        mensajes: list[tuple[str, str, str]] = []
        for linea in codigo.splitlines():
            linea = linea.strip()
            if linea.startswith("participant "):
                partes = linea.split(" as ", 1)
                ident = partes[0].split()[1]
                nombre = partes[1] if len(partes) > 1 else ident
                participantes.append(nombre)
            elif "->>" in linea or "-->>" in linea:
                flecha = "-->>" if "-->>" in linea else "->>"
                izq, resto = linea.split(flecha, 1)
                der, texto = resto.split(":", 1)
                mensajes.append((izq.strip(), der.strip(), texto.strip()))
        return participantes, mensajes

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(PALETA["gris_claro"])
        c.setStrokeColor(PALETA["borde"])
        c.roundRect(0, 0, self.ancho, self.alto, 8, fill=1, stroke=1)

        count = max(1, len(self.participantes))
        margen = 18
        paso = (self.ancho - margen * 2) / max(1, count - 1)
        xs = [margen + i * paso for i in range(count)]

        c.setFont("Helvetica-Bold", 6.8)
        for x, nombre in zip(xs, self.participantes):
            c.setFillColor(colors.white)
            c.setStrokeColor(PALETA["azul"])
            c.roundRect(x - 30, self.alto - 30, 60, 17, 4, fill=1, stroke=1)
            c.setFillColor(PALETA["azul_oscuro"])
            c.drawCentredString(x, self.alto - 23, nombre[:16])
            c.setStrokeColor(PALETA["borde"])
            c.line(x, self.alto - 33, x, 12)

        alias = {
            "Cliente": 0,
            "API": 1,
            "Dep": 2,
            "CU": 3,
            "Lector": 4,
            "Det": 5,
            "Ext": 6,
            "Extra": 7,
        }
        y = self.alto - 47
        c.setFont("Helvetica", 5.8)
        for origen, destino, texto in self.mensajes:
            if origen not in alias or destino not in alias:
                continue
            x1 = xs[min(alias[origen], len(xs) - 1)]
            x2 = xs[min(alias[destino], len(xs) - 1)]
            c.setStrokeColor(PALETA["azul"])
            c.line(x1, y, x2, y)
            c.circle(x2, y, 2, fill=1, stroke=0)
            c.setFillColor(PALETA["texto"])
            c.drawCentredString((x1 + x2) / 2, y + 4, texto[:42])
            y -= 14
        c.restoreState()


def construir_tecnico() -> list:
    texto = normalizar_mojibake(leer_texto(TECNICO_MD))
    lineas = texto.splitlines()
    s = estilos()
    story: list = []
    story.extend(
        crear_cover(
            "Documentacion tecnica - Raloe-CRONO",
            "Guia para programador basada en el caso de uso actual y sus dependencias.",
        )
    )

    en_codigo = False
    tipo_codigo = ""
    buffer_codigo: list[str] = []

    def volcar_codigo():
        nonlocal buffer_codigo, tipo_codigo
        codigo = "\n".join(buffer_codigo)
        if tipo_codigo == "mermaid" and codigo.strip().startswith("flowchart"):
            story.append(FlowchartBasico(codigo, titulo="Diagrama de flujo"))
            story.append(Spacer(1, 8))
        elif tipo_codigo == "mermaid" and codigo.strip().startswith("sequenceDiagram"):
            story.append(SequenceBasico(codigo))
            story.append(Spacer(1, 8))
        else:
            story.append(Preformatted(codigo, s["code"]))
        buffer_codigo = []
        tipo_codigo = ""

    for linea in lineas:
        if linea.startswith("```"):
            if not en_codigo:
                en_codigo = True
                tipo_codigo = linea.strip("`").strip()
                buffer_codigo = []
            else:
                en_codigo = False
                volcar_codigo()
            continue

        if en_codigo:
            buffer_codigo.append(linea)
            continue

        if not linea.strip():
            story.append(Spacer(1, 2))
            continue

        if linea.startswith("# "):
            story.append(Paragraph(limpiar_parrafo(linea[2:]), s["titulo"]))
        elif linea.startswith("## "):
            if linea.startswith("## 18. Diagrama de secuencia completo"):
                story.append(PageBreak())
            story.append(Paragraph(limpiar_parrafo(linea[3:]), s["h1"]))
        elif linea.startswith("### "):
            story.append(Paragraph(limpiar_parrafo(linea[4:]), s["h2"]))
        elif linea.strip().startswith("- "):
            story.append(Paragraph(f"- {limpiar_parrafo(linea.strip()[2:])}", s["bullet"]))
        else:
            story.append(Paragraph(limpiar_parrafo(linea), s["body"]))
    return story


def pie_pagina(canvas, doc, titulo: str):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(PALETA["gris"])
    canvas.drawString(doc.leftMargin, 1.15 * cm, titulo)
    canvas.drawRightString(A4[0] - doc.rightMargin, 1.15 * cm, f"Pagina {doc.page}")
    canvas.setStrokeColor(PALETA["borde"])
    canvas.line(doc.leftMargin, 1.45 * cm, A4[0] - doc.rightMargin, 1.45 * cm)
    canvas.restoreState()


def generar_pdf(path: Path, story: list, titulo_pie: str) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=1.55 * cm,
        leftMargin=1.55 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        title=path.stem,
    )
    doc.build(
        story,
        onFirstPage=lambda canvas, d: pie_pagina(canvas, d, titulo_pie),
        onLaterPages=lambda canvas, d: pie_pagina(canvas, d, titulo_pie),
    )


def main() -> None:
    generar_pdf(PDF_GUIA, construir_guia(), "Guia desde cero - Extractor PDF")
    generar_pdf(PDF_TECNICO, construir_tecnico(), "Documentacion tecnica - Raloe-CRONO")
    print(PDF_GUIA)
    print(PDF_TECNICO)


if __name__ == "__main__":
    main()
