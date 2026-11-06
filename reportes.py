"""
Reportes y estadísticas - sólo administradora.

Con un rango de fechas y una agrupación (diaria, semanal o mensual):
 * Ingresos, cantidad de ventas, ticket promedio y ganancia estimada
   (ingresos - costo de los productos vendidos al momento de la venta).
 * Gráficos con Matplotlib: ventas por período y productos más vendidos.
 * Tablas: ventas por período, ranking, stock bajo y movimientos.
 * Exportación a Excel y PDF.
"""

from datetime import date
from tkinter import filedialog

import customtkinter as ctk
from matplotlib.ticker import FuncFormatter

import exportar
from componentes import (
    SelectorFechas, Tabla, advertir, crear_grafico, ejecutar_seguro, encabezado, estilo_eje,
    fecha_texto, fila_tarjetas, formato_dinero, formato_eje_dinero, formato_fecha, informar,
    nombre_persona, panel,
)
from config import AZUL, FONDO, FUENTE, GRIS, VERDE, VERDE_CLARO, VERDE_OSCURO
from database import ErrorSistema, hoy
from servicios import operaciones, reportes

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


class ReportesFrame(ctk.CTkFrame):
    def __init__(self, master, app=None):
        super().__init__(master, fg_color=FONDO, corner_radius=0)
        self.app = app
        self.datos = {"periodos": [], "top": [], "stock": [], "movimientos": [], "totales": {}}

        encabezado(self, "Reportes y estadísticas", "Analizá las ventas y la rentabilidad del negocio.",
                   [("Exportar PDF", self.exportar_pdf, "oscuro"),
                    ("Exportar Excel", self.exportar_excel, "primario")]).pack(fill="x", padx=22, pady=(16, 8))

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=22, pady=(0, 10))
        self.fechas = SelectorFechas(filtros, self.actualizar)
        self.fechas.establecer(hoy().replace(day=1), hoy())
        self.fechas.pack(side="left")
        self.agrupacion = ctk.CTkSegmentedButton(
            filtros, values=list(reportes.AGRUPACIONES), height=32, selected_color=VERDE,
            selected_hover_color=VERDE_OSCURO, font=(FUENTE, 12, "bold"), command=lambda _v: self.actualizar())
        self.agrupacion.set("Diaria")
        self.agrupacion.pack(side="right")
        ctk.CTkLabel(filtros, text="Agrupar:", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(
            side="right", padx=6)

        fila, tarjetas = fila_tarjetas(self, [
            ("Ingresos totales", "$"),
            ("Cantidad de ventas", "◉"),
            ("Ticket promedio", "≈", AZUL, "#DBEAFE"),
            ("Ganancia estimada", "▲", VERDE_OSCURO, VERDE_CLARO),
        ])
        self.t_ingresos, self.t_ventas, self.t_ticket, self.t_ganancia = tarjetas
        fila.pack(fill="x", padx=22, pady=(0, 10))

        self.pestanas = ctk.CTkTabview(
            self, fg_color=FONDO, segmented_button_selected_color=VERDE,
            segmented_button_selected_hover_color=VERDE_OSCURO, segmented_button_font=(FUENTE, 12, "bold"))
        self.pestanas.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        for nombre in ("Ventas por período", "Más vendidos", "Stock bajo", "Movimientos de inventario"):
            self.pestanas.add(nombre)

        self._crear_ventas(self.pestanas.tab("Ventas por período"))
        self._crear_top(self.pestanas.tab("Más vendidos"))
        self.tabla_stock = Tabla(self.pestanas.tab("Stock bajo"), [
            ("codigo", "Código", 110, "w"), ("nombre", "Producto", 240, "w"), ("categoria", "Categoría", 140, "w"),
            ("stock", "Stock", 70, "center"), ("minimo", "Mínimo", 70, "center"), ("faltante", "A reponer", 90, "center"),
        ], altura=12)
        self.tabla_stock.pack(fill="both", expand=True)
        self.tabla_movimientos = Tabla(self.pestanas.tab("Movimientos de inventario"), [
            ("fecha", "Fecha", 125, "center"), ("producto", "Producto", 200, "w"), ("tipo", "Tipo", 80, "center"),
            ("cantidad", "Cantidad", 70, "center"), ("motivo", "Motivo", 230, "w"), ("usuario", "Usuario", 120, "w"),
        ], altura=12)
        self.tabla_movimientos.pack(fill="both", expand=True)

        self.actualizar()

    # ------------------------------------------------------------------

    def _crear_ventas(self, tab):
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)
        grafico = panel(tab)
        grafico.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.figura_ventas, self.eje_ventas, lienzo = crear_grafico(grafico, alto=2.6)
        self.lienzo_ventas = lienzo
        lienzo.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        self.tabla_periodos = Tabla(tab, [
            ("periodo", "Período", 110, "w"), ("ventas", "Ventas", 60, "center"),
            ("ingresos", "Ingresos", 100, "e"), ("ganancia", "Ganancia", 100, "e"),
        ], altura=10)
        self.tabla_periodos.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    def _crear_top(self, tab):
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)
        grafico = panel(tab)
        grafico.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.figura_top, self.eje_top, lienzo = crear_grafico(grafico, alto=2.6)
        self.lienzo_top = lienzo
        lienzo.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        self.tabla_top = Tabla(tab, [
            ("pos", "#", 35, "center"), ("nombre", "Producto", 170, "w"), ("cantidad", "Unid.", 60, "center"),
            ("ingresos", "Ingresos", 95, "e"), ("ganancia", "Ganancia", 95, "e"),
        ], altura=10)
        self.tabla_top.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    # ------------------------------------------------------------------

    def _etiqueta_periodo(self, valor):
        dia = date.fromisoformat(str(valor)[:10])
        agrupacion = self.agrupacion.get()
        if agrupacion == "Mensual":
            return f"{MESES[dia.month - 1]} {dia.year}"
        if agrupacion == "Semanal":
            return f"Sem. {dia:%d/%m}"
        return f"{dia:%d/%m}"

    def actualizar(self):
        try:
            desde, hasta = self.fechas.obtener()
        except ErrorSistema as error:
            advertir(str(error))
            return
        self.desde, self.hasta = desde, hasta
        agrupacion = reportes.AGRUPACIONES[self.agrupacion.get()]

        def consultar():
            return {
                "periodos": reportes.ventas_por_periodo(desde, hasta, agrupacion),
                "top": reportes.mas_vendidos(desde, hasta, 10),
                "stock": reportes.stock_bajo(),
                "movimientos": operaciones.listar_movimientos_inventario(desde, hasta),
            }

        correcto, datos = ejecutar_seguro(consultar, titulo_error="No se pudo generar el reporte")
        if not correcto:
            return
        datos["totales"] = reportes.totales(datos["periodos"])
        self.datos = datos
        self._mostrar()

    def _mostrar(self):
        t = self.datos["totales"]
        self.t_ingresos.actualizar(formato_dinero(t["ingresos"]))
        self.t_ventas.actualizar(t["ventas"])
        self.t_ticket.actualizar(formato_dinero(t["ticket_promedio"]))
        self.t_ganancia.actualizar(formato_dinero(t["ganancia"]),
                                   titulo=f"Ganancia estimada · margen {t['margen']:.0f} %")

        periodos = self.datos["periodos"]
        self.tabla_periodos.cargar([
            (i, [self._etiqueta_periodo(p["periodo"]), p["cantidad_ventas"], formato_dinero(p["ingresos"]),
                 formato_dinero(p["ganancia"])])
            for i, p in enumerate(periodos)
        ], "Sin ventas en el período.")

        top = self.datos["top"]
        self.tabla_top.cargar([
            (i, [i + 1, p["nombre"], p["cantidad"], formato_dinero(p["ingresos"]), formato_dinero(p["ganancia"])])
            for i, p in enumerate(top)
        ], "Sin ventas en el período.")

        self.tabla_stock.cargar([
            (p["id"], [p["codigo"], p["nombre"], p["categoria"], p["stock"], p["stock_minimo"], p["faltante"]],
             ["alerta"] if p["stock"] <= 0 else ["aviso"])
            for p in self.datos["stock"]
        ], "✓ No hay productos con stock bajo.")

        self.tabla_movimientos.cargar([
            (m["id"], [formato_fecha(m["fecha"]), (m.get("productos") or {}).get("nombre", "-"), m["tipo"],
                       m["cantidad"], m["motivo"], nombre_persona(m.get("perfiles"))])
            for m in self.datos["movimientos"]
        ], "Sin movimientos en el período.")

        self._grafico_ventas(periodos)
        self._grafico_top(top)

    def _grafico_ventas(self, periodos):
        eje = self.eje_ventas
        eje.clear()
        estilo_eje(eje)
        if periodos:
            etiquetas = [self._etiqueta_periodo(p["periodo"]) for p in periodos]
            ingresos = [float(p["ingresos"]) for p in periodos]
            ganancias = [float(p["ganancia"]) for p in periodos]
            posiciones = range(len(etiquetas))
            eje.bar([x - 0.2 for x in posiciones], ingresos, width=0.4, color=VERDE, label="Ingresos")
            eje.bar([x + 0.2 for x in posiciones], ganancias, width=0.4, color="#86C59A", label="Ganancia")
            eje.set_xticks(list(posiciones))
            eje.set_xticklabels(etiquetas, rotation=45 if len(etiquetas) > 10 else 0, ha="right" if len(etiquetas) > 10 else "center")
            eje.yaxis.set_major_formatter(FuncFormatter(formato_eje_dinero))
            eje.legend(fontsize=8, frameon=False)
        else:
            eje.text(0.5, 0.5, "Sin ventas en el período", ha="center", va="center", color=GRIS,
                     transform=eje.transAxes)
        eje.set_title("Ingresos y ganancia por período", fontsize=10, color=VERDE_OSCURO, loc="left")
        self.figura_ventas.tight_layout(pad=1.0)
        self.lienzo_ventas.draw_idle()

    def _grafico_top(self, top):
        eje = self.eje_top
        eje.clear()
        estilo_eje(eje)
        eje.grid(axis="x", color="#EEF3EF")
        eje.grid(axis="y", visible=False)
        if top:
            nombres = [p["nombre"][:22] for p in reversed(top)]
            cantidades = [int(p["cantidad"]) for p in reversed(top)]
            barras = eje.barh(nombres, cantidades, color=VERDE)
            eje.bar_label(barras, padding=3, fontsize=8, color=GRIS)
        else:
            eje.text(0.5, 0.5, "Sin ventas en el período", ha="center", va="center", color=GRIS,
                     transform=eje.transAxes)
        eje.set_title("Unidades vendidas", fontsize=10, color=VERDE_OSCURO, loc="left")
        self.figura_top.tight_layout(pad=1.0)
        self.lienzo_top.draw_idle()

    # ------------------------------------------------------------------
    # EXPORTACIÓN
    # ------------------------------------------------------------------

    def _contenido_exportable(self):
        t = self.datos["totales"]
        periodo = f"{fecha_texto(self.desde)} al {fecha_texto(self.hasta)}"
        resumen = [
            ("Ingresos totales", formato_dinero(t["ingresos"])),
            ("Cantidad de ventas", t["ventas"]),
            ("Ticket promedio", formato_dinero(t["ticket_promedio"])),
            ("Costo de lo vendido", formato_dinero(t["costo"])),
            ("Ganancia estimada", formato_dinero(t["ganancia"])),
            ("Margen", f"{t['margen']:.1f} %"),
        ]
        secciones = [
            (f"Ventas por período ({self.agrupacion.get().lower()})",
             ["Período", "Ventas", "Ingresos", "Costo", "Ganancia"],
             [[self._etiqueta_periodo(p["periodo"]), p["cantidad_ventas"], formato_dinero(p["ingresos"]),
               formato_dinero(p["costo"]), formato_dinero(p["ganancia"])] for p in self.datos["periodos"]]),
            ("Productos más vendidos", ["#", "Código", "Producto", "Unidades", "Ingresos", "Ganancia"],
             [[i + 1, p["codigo"], p["nombre"], p["cantidad"], formato_dinero(p["ingresos"]),
               formato_dinero(p["ganancia"])] for i, p in enumerate(self.datos["top"])]),
            ("Productos con stock bajo", ["Código", "Producto", "Categoría", "Stock", "Mínimo", "A reponer"],
             [[p["codigo"], p["nombre"], p["categoria"], p["stock"], p["stock_minimo"], p["faltante"]]
              for p in self.datos["stock"]]),
            ("Movimientos de inventario", ["Fecha", "Producto", "Tipo", "Cantidad", "Motivo", "Usuario"],
             [[formato_fecha(m["fecha"]), (m.get("productos") or {}).get("nombre", "-"), m["tipo"], m["cantidad"],
               m["motivo"], nombre_persona(m.get("perfiles"))] for m in self.datos["movimientos"]]),
        ]
        return periodo, resumen, secciones

    def _ruta(self, extension, descripcion):
        return filedialog.asksaveasfilename(
            parent=self, title="Guardar reporte", defaultextension=extension,
            initialfile=f"reporte_{self.desde:%Y%m%d}_{self.hasta:%Y%m%d}{extension}",
            filetypes=[(descripcion, f"*{extension}")])

    def exportar_excel(self):
        ruta = self._ruta(".xlsx", "Excel")
        if not ruta:
            return
        periodo, resumen, secciones = self._contenido_exportable()
        hojas = [(titulo.split(" (")[0], encabezados, filas) for titulo, encabezados, filas in secciones]
        if ejecutar_seguro(exportar.a_excel, ruta, "Reporte de ventas", periodo, resumen, hojas,
                           titulo_error="No se pudo exportar")[0]:
            informar(f"Reporte exportado a Excel:\n{ruta}")

    def exportar_pdf(self):
        ruta = self._ruta(".pdf", "PDF")
        if not ruta:
            return
        periodo, resumen, secciones = self._contenido_exportable()
        if ejecutar_seguro(exportar.a_pdf, ruta, "Reporte de ventas", periodo, resumen, secciones,
                           figura=self.figura_ventas, titulo_error="No se pudo exportar")[0]:
            informar(f"Reporte exportado a PDF:\n{ruta}")
