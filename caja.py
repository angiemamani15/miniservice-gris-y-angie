"""
Caja: resumen diario del dinero.

Cada venta registra automáticamente un ingreso en movimientos_caja.
Aquí también se cargan ingresos/egresos manuales (cambio inicial, pago
a un repartidor, etc.) y se hace el arqueo: se compara el efectivo
contado con el efectivo que el sistema calcula que debería haber.
"""

import customtkinter as ctk

from componentes import (
    Tabla, advertir, boton, campo, ejecutar_seguro, encabezado, escribir, fecha_texto, fila_tarjetas,
    formato_dinero, formato_fecha, informar, nombre_persona, panel,
)
from config import (
    AZUL, BORDE, FONDO, FUENTE, GRIS, METODOS_PAGO, ROJO, ROJO_CLARO, VERDE,
    VERDE_CLARO, VERDE_OSCURO,
)
from database import ErrorSistema, hoy
from servicios import operaciones, validaciones


class CajaFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=FONDO, corner_radius=0)
        self.app = app
        self.dia = hoy()
        self.esperado = 0.0

        cabecera = encabezado(self, "Caja", "Controlá el dinero del día y registrá ingresos o egresos.")
        cabecera.pack(fill="x", padx=22, pady=(16, 10))

        selector = ctk.CTkFrame(cabecera, fg_color="transparent")
        selector.pack(side="right")
        ctk.CTkLabel(selector, text="Día", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(side="left")
        self.entrada_dia = ctk.CTkEntry(selector, width=110, height=34, border_color=BORDE)
        self.entrada_dia.pack(side="left", padx=6)
        self.entrada_dia.bind("<Return>", lambda _e: self.cambiar_dia())
        boton(selector, "Ver", self.cambiar_dia, "primario", ancho=60, alto=34).pack(side="left")
        boton(selector, "Hoy", self.ir_a_hoy, "suave", ancho=60, alto=34).pack(side="left", padx=(6, 0))

        fila, tarjetas = fila_tarjetas(self, [
            ("Ventas en efectivo", "$"),
            ("Transferencias", "⇄", AZUL, "#DBEAFE"),
            ("Tarjetas", "▭", AZUL, "#DBEAFE"),
            ("Efectivo esperado en caja", "✓", VERDE_OSCURO, VERDE_CLARO),
        ])
        self.t_efectivo, self.t_transferencia, self.t_tarjeta, self.t_esperado = tarjetas
        fila.pack(fill="x", padx=22, pady=(0, 10))

        self.detalle = ctk.CTkLabel(self, text="", font=(FUENTE, 12), text_color=GRIS, anchor="w")
        self.detalle.pack(fill="x", padx=26, pady=(0, 6))

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=1, minsize=300)
        cuerpo.grid_rowconfigure(0, weight=1)

        izquierda = panel(cuerpo, "Movimientos de caja del día")
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.tabla = Tabla(izquierda, [
            ("hora", "Hora", 110, "center"),
            ("tipo", "Tipo", 80, "center"),
            ("concepto", "Concepto", 220, "w"),
            ("metodo", "Medio", 110, "center"),
            ("monto", "Monto", 110, "e"),
            ("usuario", "Usuario", 110, "w"),
        ], altura=12)
        self.tabla.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        derecha = ctk.CTkFrame(cuerpo, fg_color="transparent")
        derecha.grid(row=0, column=1, sticky="nsew")
        self._crear_formulario(derecha)
        self._crear_arqueo(derecha)

        self.ir_a_hoy()

    # ------------------------------------------------------------------

    def _crear_formulario(self, contenedor):
        formulario = panel(contenedor, "Registrar movimiento", "Ingresos o egresos de efectivo.")
        formulario.pack(fill="x", pady=(0, 8))
        self.tipo = ctk.CTkSegmentedButton(formulario, values=["Ingreso", "Egreso"], height=32,
                                           selected_color=VERDE, selected_hover_color=VERDE_OSCURO,
                                           font=(FUENTE, 12, "bold"))
        self.tipo.set("Egreso")
        self.tipo.pack(fill="x", padx=14, pady=(0, 6))
        c1, self.concepto = campo(formulario, "Concepto", "Ej.: Pago a repartidor")
        c1.pack(fill="x", padx=14, pady=3)
        c2, self.monto = campo(formulario, "Monto ($)", "0,00")
        c2.pack(fill="x", padx=14, pady=3)
        self.monto.bind("<Return>", lambda _e: self.registrar())
        boton(formulario, "Registrar", self.registrar, "primario").pack(fill="x", padx=14, pady=(8, 14))

    def _crear_arqueo(self, contenedor):
        arqueo = panel(contenedor, "Arqueo de caja", "Compará el efectivo contado con el esperado.")
        arqueo.pack(fill="x")
        c, self.contado = campo(arqueo, "Efectivo contado ($)", "0,00")
        c.pack(fill="x", padx=14, pady=3)
        self.contado.bind("<KeyRelease>", lambda _e: self.calcular_arqueo())
        self.diferencia = ctk.CTkLabel(arqueo, text="Ingresá el efectivo contado", font=(FUENTE, 13, "bold"),
                                       text_color=GRIS, fg_color=FONDO, corner_radius=8, height=38)
        self.diferencia.pack(fill="x", padx=14, pady=(8, 14))

    # ------------------------------------------------------------------

    def ir_a_hoy(self):
        escribir(self.entrada_dia, fecha_texto(hoy()))
        self.cambiar_dia()

    def cambiar_dia(self):
        try:
            self.dia = validaciones.fecha(self.entrada_dia.get(), "Día")
        except ErrorSistema as error:
            advertir(str(error))
            return
        self.actualizar()

    def actualizar(self):
        correcto, resumen = ejecutar_seguro(operaciones.resumen_caja, self.dia)
        if correcto:
            self.t_efectivo.actualizar(formato_dinero(resumen.get("ventas_efectivo")))
            self.t_transferencia.actualizar(formato_dinero(resumen.get("ventas_transferencia")))
            self.t_tarjeta.actualizar(formato_dinero(resumen.get("ventas_tarjeta")))
            self.esperado = float(resumen.get("efectivo_esperado") or 0)
            self.t_esperado.actualizar(formato_dinero(self.esperado))
            total_ventas = sum(float(resumen.get(k) or 0) for k in
                               ("ventas_efectivo", "ventas_transferencia", "ventas_tarjeta"))
            self.detalle.configure(text=(
                f"{fecha_texto(self.dia)} · {resumen.get('cantidad_ventas', 0)} venta(s) por "
                f"{formato_dinero(total_ventas)} · Otros ingresos en efectivo: "
                f"{formato_dinero(resumen.get('otros_ingresos'))} · Egresos: {formato_dinero(resumen.get('egresos'))}"))
            self.calcular_arqueo()

        correcto, movimientos = ejecutar_seguro(operaciones.listar_movimientos_caja, self.dia, self.dia)
        if correcto:
            filas = []
            for m in movimientos:
                ingreso = m["tipo"] == "Ingreso"
                filas.append((m["id"], [
                    formato_fecha(m["fecha"]), m["tipo"], m["concepto"],
                    METODOS_PAGO.get(m["metodo_pago"], m["metodo_pago"]),
                    ("+ " if ingreso else "− ") + formato_dinero(m["monto"]),
                    nombre_persona(m.get("perfiles")),
                ], ["positivo" if ingreso else "alerta"]))
            self.tabla.cargar(filas, "No hay movimientos de caja en este día.")

    def registrar(self):
        correcto, _ = ejecutar_seguro(operaciones.registrar_movimiento_caja,
                                      self.tipo.get(), self.concepto.get(), self.monto.get())
        if correcto:
            informar(f"{self.tipo.get()} registrado correctamente.")
            escribir(self.concepto, "")
            escribir(self.monto, "")
            if self.dia != hoy():
                escribir(self.entrada_dia, fecha_texto(hoy()))
                self.dia = hoy()
            self.actualizar()

    def calcular_arqueo(self):
        texto = self.contado.get().strip()
        if not texto:
            self.diferencia.configure(text="Ingresá el efectivo contado", text_color=GRIS, fg_color=FONDO)
            return
        try:
            contado = validaciones.decimal(texto, "Efectivo contado")
        except ErrorSistema:
            self.diferencia.configure(text="Monto inválido", text_color=ROJO, fg_color=ROJO_CLARO)
            return
        diferencia = round(contado - self.esperado, 2)
        if diferencia == 0:
            self.diferencia.configure(text="✓ La caja está correcta", text_color=VERDE, fg_color=VERDE_CLARO)
        elif diferencia > 0:
            self.diferencia.configure(text=f"Sobrante: {formato_dinero(diferencia)}", text_color=AZUL,
                                      fg_color="#DBEAFE")
        else:
            self.diferencia.configure(text=f"Faltante: {formato_dinero(-diferencia)}", text_color=ROJO,
                                      fg_color=ROJO_CLARO)
