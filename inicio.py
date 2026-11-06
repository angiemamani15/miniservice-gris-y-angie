"""
Panel principal: resumen del negocio con datos reales de Supabase.

Toda la información llega en una sola consulta (función resumen_panel)
y se actualiza al entrar, con el botón "Actualizar" y cada 60 segundos.
"""

from datetime import date

import customtkinter as ctk
from matplotlib.ticker import FuncFormatter

import sesion
from componentes import (
    Tabla, boton, crear_grafico, encabezado, estilo_eje, fila_tarjetas, formato_dinero,
    formato_eje_dinero, formato_fecha, panel,
)
from config import (
    AMARILLO, AMARILLO_CLARO, FONDO, FUENTE, GRIS, METODOS_PAGO, ROJO,
    ROJO_CLARO, VERDE, VERDE_CLARO, VERDE_OSCURO,
)
from database import ErrorSistema, hoy
from servicios import reportes

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
INTERVALO_ACTUALIZACION = 60_000  # milisegundos


class InicioFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=FONDO, corner_radius=0)
        self.app = app
        self.usuario = sesion.actual()
        self.tarea = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        titulo = "Panel de administración" if self.usuario.es_admin else "Panel de caja"
        dia = hoy()
        subtitulo = f"Bienvenida, {self.usuario.nombre} · {DIAS[dia.weekday()]} {dia:%d/%m/%Y}"
        encabezado(self, titulo, subtitulo, [("↻ Actualizar", self.actualizar, "suave")]).grid(
            row=0, column=0, sticky="ew", padx=22, pady=(18, 12))

        fila, (self.t_productos, self.t_ventas, self.t_ingresos, self.t_bajo) = fila_tarjetas(self, [
            ("Productos registrados", "▣"),
            ("Ventas de hoy", "◉"),
            ("Ingresos del día", "$"),
            ("Productos con stock bajo", "!", ROJO, ROJO_CLARO),
        ])
        fila.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 12))

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.grid(row=2, column=0, sticky="nsew", padx=22, pady=(0, 18))
        cuerpo.grid_columnconfigure(0, weight=3, uniform="cuerpo")
        cuerpo.grid_columnconfigure(1, weight=2, uniform="cuerpo")
        cuerpo.grid_rowconfigure(0, weight=5)
        cuerpo.grid_rowconfigure(1, weight=4)

        # Gráfico de ventas de la semana
        p_grafico = panel(cuerpo, "Ventas de los últimos 7 días")
        p_grafico.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        self.figura, self.eje, self.lienzo = crear_grafico(p_grafico, alto=2.4)
        self.lienzo.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Más vendidos
        p_top = panel(cuerpo, "Más vendidos (últimos 30 días)")
        p_top.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 6))
        self.tabla_top = Tabla(p_top, [
            ("nombre", "Producto", 170, "w"),
            ("cantidad", "Unid.", 60, "center"),
            ("importe", "Importe", 100, "e"),
        ], altura=5)
        self.tabla_top.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Últimas ventas
        p_ultimas = panel(cuerpo, "Últimas ventas")
        p_ultimas.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(6, 0))
        self.tabla_ultimas = Tabla(p_ultimas, [
            ("id", "N°", 60, "center"),
            ("fecha", "Fecha", 130, "center"),
            ("vendedor", "Atendió", 120, "w"),
            ("pago", "Pago", 110, "center"),
            ("total", "Total", 110, "e"),
        ], altura=4)
        self.tabla_ultimas.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Accesos rápidos y alertas
        p_accesos = panel(cuerpo, "Accesos rápidos")
        p_accesos.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(6, 0))
        self._crear_accesos(p_accesos)

        self.actualizar()

    def _crear_accesos(self, contenedor):
        rejilla = ctk.CTkFrame(contenedor, fg_color="transparent")
        rejilla.pack(fill="x", padx=14)
        rejilla.grid_columnconfigure((0, 1), weight=1)

        opciones = [("◉  Nueva venta", "Ventas"), ("$  Caja del día", "Caja")]
        if self.usuario.es_admin:
            opciones += [("▤  Inventario", "Inventario"), ("▥  Reportes", "Reportes")]
        else:
            opciones += [("▤  Consultar stock", "Inventario")]

        for indice, (texto, seccion) in enumerate(opciones):
            boton(rejilla, texto, lambda s=seccion: self.app.mostrar_seccion(s),
                  "primario" if indice == 0 else "suave", ancho=120).grid(
                row=indice // 2, column=indice % 2, sticky="ew", padx=4, pady=4)

        self.alerta = ctk.CTkLabel(
            contenedor, text="", font=(FUENTE, 12, "bold"), corner_radius=10,
            wraplength=300, justify="left", anchor="w")
        self.alerta.pack(fill="x", padx=18, pady=(10, 14))

    # ------------------------------------------------------------------

    def actualizar(self):
        if self.tarea is not None:
            self.after_cancel(self.tarea)
            self.tarea = None
        try:
            datos = reportes.resumen_panel()
        except ErrorSistema as error:
            self._mostrar_error(str(error))
        except Exception as error:
            self._mostrar_error(f"Error inesperado: {error}")
        else:
            self._mostrar(datos)
        if self.winfo_exists():
            self.tarea = self.after(INTERVALO_ACTUALIZACION, self.actualizar)

    def destroy(self):
        if self.tarea is not None:
            try:
                self.after_cancel(self.tarea)
            except Exception:
                pass
        super().destroy()

    def _mostrar_error(self, mensaje):
        for tarjeta in (self.t_productos, self.t_ventas, self.t_ingresos, self.t_bajo):
            tarjeta.actualizar("—")
        self.alerta.configure(text=f"No se pudieron cargar los datos.\n{mensaje}",
                              fg_color=ROJO_CLARO, text_color=ROJO)

    def _mostrar(self, datos):
        bajo = int(datos.get("stock_bajo") or 0)
        self.t_productos.actualizar(datos.get("total_productos", 0))
        self.t_ventas.actualizar(datos.get("ventas_hoy", 0))
        self.t_ingresos.actualizar(formato_dinero(datos.get("ingresos_hoy")))
        self.t_bajo.actualizar(bajo, ROJO if bajo else None)

        if bajo:
            self.alerta.configure(
                text=f"⚠  Hay {bajo} producto(s) con stock bajo. Revisalos en Inventario.",
                fg_color=AMARILLO_CLARO, text_color=AMARILLO)
        else:
            self.alerta.configure(text="✓  El stock de todos los productos está en niveles normales.",
                                  fg_color=VERDE_CLARO, text_color=VERDE_OSCURO)

        self.tabla_top.cargar([
            (i, [p["nombre"], p["cantidad"], formato_dinero(p["importe"])])
            for i, p in enumerate(datos.get("mas_vendidos") or [])
        ], "Todavía no hay ventas en los últimos 30 días.")

        self.tabla_ultimas.cargar([
            (v["id"], [v["id"], formato_fecha(v["fecha"]), v.get("vendedor") or "-",
                       METODOS_PAGO.get(v["metodo_pago"], v["metodo_pago"]), formato_dinero(v["total"])])
            for v in datos.get("ultimas_ventas") or []
        ], "Todavía no se registraron ventas.")

        self._dibujar_grafico(datos.get("ventas_semana") or [])

    def _dibujar_grafico(self, semana):
        self.eje.clear()
        estilo_eje(self.eje)
        etiquetas, totales = [], []
        for dia in semana:
            fecha = date.fromisoformat(str(dia["fecha"])[:10])
            etiquetas.append(f"{DIAS[fecha.weekday()]}\n{fecha:%d/%m}")
            totales.append(float(dia.get("total") or 0))

        if etiquetas:
            colores = [VERDE] * len(totales)
            colores[-1] = VERDE_OSCURO  # hoy
            barras = self.eje.bar(etiquetas, totales, color=colores, width=0.6)
            self.eje.yaxis.set_major_formatter(FuncFormatter(formato_eje_dinero))
            maximo = max(totales) if totales else 0
            for barra, total in zip(barras, totales):
                if total > 0:
                    self.eje.annotate(formato_eje_dinero(total), (barra.get_x() + barra.get_width() / 2, total),
                                      ha="center", va="bottom", fontsize=8, color=GRIS,
                                      xytext=(0, 2), textcoords="offset points")
            self.eje.set_ylim(0, maximo * 1.18 if maximo else 1)
        self.figura.tight_layout(pad=1.0)
        self.lienzo.draw_idle()


