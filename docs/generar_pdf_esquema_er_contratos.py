from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "esquema_er_contratos_extractor.pdf"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = _styles()
    story = [
        Paragraph("Esquema E-R - Contratos Extractor PDF", styles["doc_title"]),
        Paragraph(
            "Diseno propuesto para APIExtractor + SQL Server. La base de datos usa nombres en castellano; "
            "el DTO entregado al motor Python conserva los nombres actuales del contrato JSON.",
            styles["er_body"],
        ),
        Spacer(1, 6 * mm),
        _tabla_resumen_decisiones(styles),
        PageBreak(),
        Paragraph("Diagrama E-R", styles["er_h1"]),
        Spacer(1, 3 * mm),
        _diagrama_placeholder(),
        PageBreak(),
        Paragraph("Tablas Principales", styles["er_h1"]),
        _tabla_entidades_principales(styles),
        PageBreak(),
        Paragraph("Reglas Programadas y Parametros", styles["er_h1"]),
        _tabla_reglas(styles),
        Spacer(1, 5 * mm),
        Paragraph("Contrato Vacio y Metadata", styles["er_h1"]),
        _tabla_contrato_metadata(styles),
    ]

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(OUTPUT)


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="doc_title",
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="er_h1",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="er_body",
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="er_small",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="er_box_title",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="er_box_text",
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
        )
    )
    return styles


def _tabla_resumen_decisiones(styles):
    data = [
        ["Decision", "Criterio"],
        ["API_CS", "API generica de empresa: entidades crudas y repositorios corporativos."],
        ["APIExtractor", "Aplicacion privada: reglas de negocio, DTOs y composicion de contratos."],
        ["Python ExtractorPDF", "Motor PDF/OCR. Consume contratos resueltos desde APIExtractor."],
        ["Nombres", "Tablas y dominio C# en castellano; contrato JSON hacia Python conserva aliases, reglas, modo, etc."],
        ["Campos", "Reutilizables solo como concepto. La configuracion vive en CampoPlantilla."],
        ["Secciones", "Catalogo reutilizable. La plantilla decide orden, roles y campos."],
        ["Subsecciones", "Configuracion opcional por seccion de plantilla. No obligatoria para campos nuevos."],
        ["Contrato vacio", "Se genera desde CampoPlantilla.valor_inicial, permitiendo constantes por plantilla."],
        ["Version formulario", "La detecta el sistema. Version actual de raloe_crono: 0."],
    ]
    return _styled_table(data, [55 * mm, 210 * mm], styles)


def _diagrama_placeholder():
    return ErDiagramFlowable()


class ErDiagramFlowable(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 270 * mm
        self.height = 150 * mm

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        canv = self.canv
        styles = _styles()
        boxes = {
            "Perfiles": (8, 122, 45, 24, ["id", "clave", "nombre", "activo"]),
            "PlantillasFormulario": (68, 120, 58, 26, ["id", "perfil_id", "version", "activa", "por_defecto"]),
            "Secciones": (8, 72, 45, 24, ["id", "clave", "nombre", "activa"]),
            "SeccionesPlantilla": (68, 68, 58, 30, ["id", "plantilla_id", "seccion_id", "orden", "rol_pagina"]),
            "SubseccionesPlantilla": (68, 100, 58, 18, ["id", "seccion_plantilla_id", "clave"]),
            "Campos": (8, 28, 45, 24, ["id", "clave", "nombre", "activo"]),
            "CamposPlantilla": (68, 22, 58, 34, ["id", "seccion_plantilla_id", "campo_id", "nombre_salida", "tipo", "valor_inicial"]),
            "AliasCampo": (146, 38, 45, 24, ["id", "campo_plantilla_id", "alias", "orden"]),
            "ReglasCampoPlantilla": (146, 80, 58, 30, ["id", "campo_plantilla_id", "modo_regla_id", "orden", "activa"]),
            "ModosRegla": (224, 102, 45, 26, ["id", "clave", "origen", "bloqueado"]),
            "ParametrosModoRegla": (224, 62, 45, 28, ["id", "modo_regla_id", "clave", "tipo", "obligatorio"]),
            "ValoresParametroRegla": (146, 8, 58, 24, ["id", "regla_id", "parametro_id", "valor"]),
            "RolesPagina": (224, 24, 45, 24, ["id", "clave", "nombre"]),
        }

        def pt(v):
            return v * mm

        canv.saveState()
        _line(canv, boxes["Perfiles"], boxes["PlantillasFormulario"])
        _line(canv, boxes["PlantillasFormulario"], boxes["SeccionesPlantilla"])
        _line(canv, boxes["Secciones"], boxes["SeccionesPlantilla"])
        _line(canv, boxes["SeccionesPlantilla"], boxes["SubseccionesPlantilla"])
        _line(canv, boxes["SeccionesPlantilla"], boxes["CamposPlantilla"])
        _line(canv, boxes["Campos"], boxes["CamposPlantilla"])
        _line(canv, boxes["CamposPlantilla"], boxes["AliasCampo"])
        _line(canv, boxes["CamposPlantilla"], boxes["ReglasCampoPlantilla"])
        _line(canv, boxes["ReglasCampoPlantilla"], boxes["ModosRegla"])
        _line(canv, boxes["ModosRegla"], boxes["ParametrosModoRegla"])
        _line(canv, boxes["ReglasCampoPlantilla"], boxes["ValoresParametroRegla"])
        _line(canv, boxes["ParametrosModoRegla"], boxes["ValoresParametroRegla"])
        _line(canv, boxes["SeccionesPlantilla"], boxes["RolesPagina"])

        for name, (bx, by, bw, bh, fields) in boxes.items():
            if bh <= 0:
                continue
            _box(canv, pt(bx), pt(by), pt(bw), pt(bh), name, fields, styles)

        _note(canv, pt(133), pt(136), "APIExtractor compone el DTO con nombres del contrato actual: aliases, reglas, extraccion_pdf, modo.", styles)
        _note(canv, pt(133), pt(122), "Subseccion de busqueda opcional: sin valor, se busca en la seccion completa.", styles)
        canv.restoreState()


def _box(canv, x, y, w, h, title, fields, styles):
    canv.setStrokeColor(colors.HexColor("#2f5597"))
    canv.setFillColor(colors.HexColor("#eaf2f8"))
    canv.roundRect(x, y, w, h, 4, stroke=1, fill=1)
    canv.setFillColor(colors.HexColor("#1f3864"))
    canv.rect(x, y + h - 7 * mm, w, 7 * mm, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 7)
    canv.drawCentredString(x + w / 2, y + h - 4.8 * mm, title)
    canv.setFillColor(colors.black)
    canv.setFont("Helvetica", 6)
    top = y + h - 10 * mm
    for i, field in enumerate(fields):
        canv.drawString(x + 2 * mm, top - i * 3.8 * mm, field)


def _line(canv, a, b):
    ax, ay, aw, ah, _ = a
    bx, by, bw, bh, _ = b
    x1 = (ax + aw) * mm
    y1 = (ay + ah / 2) * mm
    x2 = bx * mm
    y2 = (by + bh / 2) * mm
    if bx < ax:
        x1 = ax * mm
        x2 = (bx + bw) * mm
    canv.setStrokeColor(colors.HexColor("#666666"))
    canv.setLineWidth(0.6)
    canv.line(x1, y1, x2, y2)


def _note(canv, x, y, text, styles):
    canv.setFillColor(colors.HexColor("#fff2cc"))
    canv.setStrokeColor(colors.HexColor("#d6b656"))
    canv.roundRect(x, y, 88 * mm, 10 * mm, 3, stroke=1, fill=1)
    canv.setFillColor(colors.black)
    canv.setFont("Helvetica", 6.8)
    canv.drawString(x + 2 * mm, y + 3.8 * mm, text)


def _tabla_entidades_principales(styles):
    data = [
        ["Tabla", "Responsabilidad", "Campos clave"],
        ["Perfiles", "Familias de extraccion.", "id, clave, nombre, activo"],
        ["PlantillasFormulario", "Versiones detectables de un perfil.", "id, perfil_id, version, nombre, activa, por_defecto"],
        ["Secciones", "Catalogo reutilizable de secciones.", "id, clave, nombre, descripcion, activo"],
        ["SeccionesPlantilla", "Secciones usadas por una plantilla concreta.", "id, plantilla_id, seccion_id, orden, activa, rol_pagina_id"],
        ["Campos", "Identidad conceptual reusable del campo.", "id, clave, nombre, descripcion, activo"],
        ["CamposPlantilla", "Configuracion del campo en una plantilla.", "id, seccion_plantilla_id, campo_id, nombre_salida, tipo, valor_inicial, valor_no_detectado"],
        ["AliasCampo", "Aliases editables por campo de plantilla.", "id, campo_plantilla_id, alias, orden, activo"],
        ["SubseccionesPlantilla", "Delimitadores opcionales dentro de una seccion.", "id, seccion_plantilla_id, clave, nombre, inicio, fin, orden"],
    ]
    return _styled_table(data, [45 * mm, 115 * mm, 110 * mm], styles)


def _tabla_reglas(styles):
    data = [
        ["Tabla", "Responsabilidad", "Notas"],
        ["ModosRegla", "Catalogo de modos programados en Python/C#.", "No editable ni borrable si bloqueado_sistema = true."],
        ["ParametrosModoRegla", "Parametros permitidos por cada modo.", "Define tipo, obligatorio y valor por defecto."],
        ["ReglasCampoPlantilla", "Seleccion de modo para un campo de plantilla.", "Ordena reglas PDF, OCR, normalizacion o validacion."],
        ["ValoresParametroRegla", "Valores concretos configurados en una regla.", "Ej.: distancia_maxima=95, tolerancia_y=18."],
        ["RolesPagina", "Catalogo de roles de pagina.", "Ej.: resumen, tecnica, opciones, premontada_botoneras."],
        ["ReglasDeteccionPagina", "Reglas seleccionables para detectar roles/version.", "Mismo patron que modos/parametros si se formaliza."],
    ]
    return _styled_table(data, [50 * mm, 120 * mm, 100 * mm], styles)


def _tabla_contrato_metadata(styles):
    data = [
        ["Elemento", "Decision"],
        ["Contrato vacio", "No necesita tabla propia: se genera desde CamposPlantilla.valor_inicial."],
        ["Valor no detectado", "CamposPlantilla.valor_no_detectado define que emitir si no se ve el campo."],
        ["Checks", "valor_no_marcado y valor_marcado viven en reglas/parametros, no como contrato vacio global."],
        ["Constantes por plantilla", "Se expresan con valor_inicial y, si aplica, valor_no_detectado."],
        ["Metadata universal", "profile_id, form_version detectada, status, warnings, filename, num_pedido."],
        ["Metadata de paginas", "Debe ser dinamica: pages = { rol_pagina: numero }. No atada a nombres fijos."],
        ["Version 0", "La version actual de raloe_crono se considera 0 y debe detectarse internamente."],
    ]
    return _styled_table(data, [55 * mm, 210 * mm], styles)


def _styled_table(data, col_widths, styles):
    table_data = []
    for row_idx, row in enumerate(data):
        table_data.append([
            Paragraph(str(cell), styles["er_small"] if row_idx else styles["er_box_title"])
            for cell in row
        ])
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fbfd")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b7c9d6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _footer(canv: canvas.Canvas, doc):
    canv.saveState()
    canv.setFont("Helvetica", 7)
    canv.setFillColor(colors.HexColor("#666666"))
    canv.drawString(12 * mm, 7 * mm, "ExtractorPDF - Esquema E-R contratos")
    canv.drawRightString(285 * mm, 7 * mm, f"Pagina {doc.page}")
    canv.restoreState()


if __name__ == "__main__":
    main()
