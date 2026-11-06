"""
Exportación de reportes a Excel (openpyxl) y PDF (reportlab).

Recibe los datos ya calculados por la pantalla de Reportes, así lo
exportado coincide exactamente con lo que se ve en pantalla.
"""

from io import BytesIO

from config import NOMBRE_NEGOCIO, VERDE, VERDE_OSCURO


def a_excel(ruta, titulo, periodo, resumen, hojas):
    """hojas: lista de (nombre_hoja, encabezados, filas)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Resumen"
    hoja["A1"] = f"{NOMBRE_NEGOCIO} - {titulo}"
    hoja["A1"].font = Font(size=14, bold=True, color=VERDE_OSCURO.strip("#"))
    hoja["A2"] = f"Período: {periodo}"
    for fila, (clave, valor) in enumerate(resumen, start=4):
        hoja.cell(row=fila, column=1, value=clave).font = Font(bold=True)
        hoja.cell(row=fila, column=2, value=valor)
    hoja.column_dimensions["A"].width = 30
    hoja.column_dimensions["B"].width = 22

    relleno = PatternFill("solid", fgColor=VERDE_OSCURO.strip("#"))
    for nombre, encabezados, filas in hojas:
        hoja = libro.create_sheet(nombre[:31])
        hoja.append(encabezados)
        for celda in hoja[1]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = relleno
            celda.alignment = Alignment(horizontal="center")
        for fila in filas:
            hoja.append(list(fila))
        for indice, encabezado in enumerate(encabezados, start=1):
            largo = max([len(str(encabezado))] + [len(str(f[indice - 1])) for f in filas] or [10])
            hoja.column_dimensions[get_column_letter(indice)].width = min(max(largo + 2, 10), 45)
        hoja.freeze_panes = "A2"
    libro.save(ruta)


def a_pdf(ruta, titulo, periodo, resumen, secciones, figura=None):
    """secciones: lista de (subtítulo, encabezados, filas)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    estilos = getSampleStyleSheet()
    estilos["Title"].textColor = colors.HexColor(VERDE_OSCURO)
    estilos["Heading2"].textColor = colors.HexColor(VERDE)
    documento = SimpleDocTemplate(ruta, pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                                  topMargin=1.4 * cm, bottomMargin=1.4 * cm, title=titulo)
    contenido = [
        Paragraph(f"{NOMBRE_NEGOCIO}", estilos["Title"]),
        Paragraph(f"{titulo} · Período: {periodo}", estilos["Normal"]),
        Spacer(1, 10),
    ]

    def tabla(datos, anchos=None):
        t = Table(datos, colWidths=anchos, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(VERDE_OSCURO)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F7F3")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DFEAE2")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    contenido.append(tabla([["Indicador", "Valor"]] + [[k, str(v)] for k, v in resumen], [8 * cm, 6 * cm]))
    contenido.append(Spacer(1, 12))

    if figura is not None:
        imagen = BytesIO()
        figura.savefig(imagen, format="png", dpi=150, bbox_inches="tight")
        imagen.seek(0)
        contenido.append(Image(imagen, width=17 * cm, height=6.5 * cm))
        contenido.append(Spacer(1, 8))

    for subtitulo, encabezados, filas in secciones:
        contenido.append(Paragraph(subtitulo, estilos["Heading2"]))
        if filas:
            contenido.append(tabla([encabezados] + [[str(c)[:45] for c in f] for f in filas[:500]]))
        else:
            contenido.append(Paragraph("Sin datos en el período.", estilos["Normal"]))
        contenido.append(Spacer(1, 10))

    documento.build(contenido)
