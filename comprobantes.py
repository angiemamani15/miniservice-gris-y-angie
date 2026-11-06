"""
Comprobante de venta: vista en pantalla y exportación a PDF.

Es un comprobante interno sencillo (no es una factura electrónica AFIP).
"""

from tkinter import filedialog

import customtkinter as ctk

from componentes import (
    boton, ejecutar_seguro, formato_dinero, formato_fecha, informar, nombre_persona, ventana_modal,
)
from config import BLANCO, BORDE, METODOS_PAGO, NOMBRE_NEGOCIO, TEXTO
from servicios import operaciones, reportes

ANCHO_TICKET = 42  # caracteres por línea


def _linea(izquierda, derecha="", relleno=" "):
    espacio = ANCHO_TICKET - len(izquierda) - len(derecha)
    if espacio < 1:
        izquierda = izquierda[: ANCHO_TICKET - len(derecha) - 1]
        espacio = 1
    return izquierda + relleno * espacio + derecha


def _datos_negocio():
    try:
        return reportes.obtener_negocio() or {}
    except Exception:
        return {}


def texto_comprobante(venta, negocio):
    """Arma el comprobante como texto de ancho fijo (estilo ticket)."""
    separador = "-" * ANCHO_TICKET
    lineas = [(negocio.get("nombre") or NOMBRE_NEGOCIO).upper().center(ANCHO_TICKET)]
    for clave in ("direccion", "telefono"):
        if negocio.get(clave):
            lineas.append(str(negocio[clave]).center(ANCHO_TICKET))
    if negocio.get("cuit"):
        lineas.append(f"CUIT: {negocio['cuit']}".center(ANCHO_TICKET))
    lineas += [
        separador,
        "COMPROBANTE NO VÁLIDO COMO FACTURA".center(ANCHO_TICKET),
        separador,
        _linea(f"Venta N°: {venta['id']}", formato_fecha(venta["fecha"])),
        _linea("Atendió:", nombre_persona(venta.get("perfiles"))),
        separador,
        _linea("Cant x Precio", "Subtotal"),
    ]
    for item in venta.get("detalle_ventas") or []:
        producto = item.get("productos") or {}
        lineas.append((producto.get("nombre") or "Producto")[:ANCHO_TICKET])
        lineas.append(_linea(
            f"  {item['cantidad']} x {formato_dinero(item['precio_unitario'])}",
            formato_dinero(item["subtotal"]),
        ))
    lineas += [
        separador,
        _linea("TOTAL", formato_dinero(venta["total"])),
        _linea("Forma de pago", METODOS_PAGO.get(venta["metodo_pago"], venta["metodo_pago"])),
    ]
    if venta["metodo_pago"] == "efectivo":
        lineas.append(_linea("Recibido", formato_dinero(venta.get("monto_recibido"))))
        lineas.append(_linea("Vuelto", formato_dinero(venta.get("vuelto"))))
    lineas += [separador, (negocio.get("mensaje_comprobante") or "¡Gracias por su compra!").center(ANCHO_TICKET)]
    return "\n".join(lineas)


def guardar_pdf(ruta, texto):
    """Genera un PDF tipo ticket (80 mm de ancho) con el texto del comprobante."""
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    lineas = texto.split("\n")
    alto = (len(lineas) * 4.2 + 16) * mm
    pdf = canvas.Canvas(ruta, pagesize=(80 * mm, alto))
    pdf.setTitle("Comprobante de venta")
    pdf.setFont("Courier", 7.4)
    y = alto - 8 * mm
    for linea in lineas:
        pdf.drawString(4 * mm, y, linea)
        y -= 4.2 * mm
    pdf.showPage()
    pdf.save()


def mostrar_comprobante(master, venta_id, titulo="Comprobante de venta"):
    correcto, venta = ejecutar_seguro(operaciones.obtener_venta, venta_id)
    if not correcto:
        return
    texto = texto_comprobante(venta, _datos_negocio())

    ventana = ventana_modal(master, f"{titulo} N° {venta_id}", ancho=470, alto=640)
    caja = ctk.CTkTextbox(ventana, font=("Courier New", 12), fg_color=BLANCO, text_color=TEXTO,
                          border_width=1, border_color=BORDE, corner_radius=10, wrap="none")
    caja.pack(fill="both", expand=True, padx=16, pady=(16, 8))
    caja.insert("1.0", texto)
    caja.configure(state="disabled")

    botones = ctk.CTkFrame(ventana, fg_color="transparent")
    botones.pack(fill="x", padx=16, pady=(4, 16))

    def exportar():
        ruta = filedialog.asksaveasfilename(
            parent=ventana, title="Guardar comprobante", defaultextension=".pdf",
            initialfile=f"comprobante_venta_{venta_id}.pdf", filetypes=[("PDF", "*.pdf")])
        if ruta:
            correcto_pdf, _ = ejecutar_seguro(guardar_pdf, ruta, texto)
            if correcto_pdf:
                informar(f"Comprobante guardado en:\n{ruta}")

    boton(botones, "Cerrar", ventana.destroy, "secundario", ancho=110).pack(side="right")
    boton(botones, "Guardar PDF", exportar, "primario", ancho=130).pack(side="right", padx=8)
    return ventana
