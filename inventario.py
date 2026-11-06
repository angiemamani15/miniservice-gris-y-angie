"""
Control de inventario.

 * Existencias: stock actual de cada producto y alertas de stock bajo.
 * Movimientos: historial (entradas, salidas, ajustes, ventas y compras)
   filtrable por fecha, producto y tipo, con el usuario que lo realizó.
 * Registrar (sólo administradora): entradas, salidas y ajustes con motivo.

Los movimientos se guardan con la función registrar_movimiento_inventario
de PostgreSQL, que bloquea el producto, impide stock negativo y registra
stock anterior/nuevo y usuario en una sola transacción.
La cajera puede consultar existencias y movimientos, pero no modificarlos.
"""

import customtkinter as ctk

import sesion
from componentes import (
    SelectorFechas, Tabla, advertir, boton, campo, cambiar_opciones, ejecutar_seguro, elegir_opcion,
    encabezado, escribir, fila_tarjetas, formato_fecha, informar, nombre_persona, panel,
)
from config import (
    AMARILLO, AMARILLO_CLARO, BLANCO, BORDE, FONDO, FUENTE, GRIS, ROJO, ROJO_CLARO, VERDE,
    VERDE_CLARO, VERDE_OSCURO,
)
from database import ErrorSistema
from servicios import catalogo, operaciones

TODOS_PRODUCTOS = "Todos los productos"
TODOS_TIPOS = "Todos los tipos"
TIPOS_HISTORIAL = ["Entrada", "Salida", "Ajuste", "Venta", "Compra"]
EXPLICACION_TIPO = {
    "Entrada": "Suma unidades al stock (reposición, devolución de cliente, etc.).",
    "Salida": "Resta unidades (vencimiento, rotura, consumo interno). No permite stock negativo.",
    "Ajuste": "Corrige el stock al valor contado físicamente. Ingresá el NUEVO stock total.",
}


class InventarioFrame(ctk.CTkFrame):

    def __init__(self, master, app=None):
        super().__init__(master, fg_color=FONDO, corner_radius=0)
        self.app = app
        self.es_admin = sesion.es_admin()

        self.productos = {}          # "código - nombre" -> producto
        self.datos_productos = []
        self.vista_actual = "Existencias"
        self.botones = {}
        self.producto_preseleccionado = None

        self.crear_interfaz()
        self.actualizar()

    # ==========================================
    # DISEÑO GENERAL
    # ==========================================

    def crear_interfaz(self):
        self.contenedor = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor.pack(fill="both", expand=True, padx=22, pady=16)

        subtitulo = ("Controlá la mercadería de Mini Service Gris y Angie."
                     if self.es_admin else "Consultá el stock disponible y el historial de movimientos.")
        encabezado(self.contenedor, "Control de Inventario", subtitulo,
                   [("↻ Actualizar", self.actualizar, "suave")]).pack(fill="x", pady=(0, 12))

        fila, (self.valor_productos, self.valor_normales, self.valor_bajos, self.valor_sin) = fila_tarjetas(
            self.contenedor, [
                ("Productos activos", "▣"),
                ("Stock normal", "✓"),
                ("Stock bajo", "!", AMARILLO, AMARILLO_CLARO),
                ("Sin stock", "✕", ROJO, ROJO_CLARO),
            ])
        fila.pack(fill="x", pady=(0, 12))

        navegacion = ctk.CTkFrame(self.contenedor, fg_color=BLANCO, corner_radius=13,
                                  border_width=1, border_color=BORDE)
        navegacion.pack(fill="x", pady=(0, 12))

        opciones = [("Existencias", "▣"), ("Movimientos", "⇄")]
        if self.es_admin:
            opciones.append(("Registrar", "+"))
        for indice, (nombre, icono) in enumerate(opciones):
            navegacion.grid_columnconfigure(indice, weight=1)
            boton_vista = ctk.CTkButton(
                navegacion, text=f"{icono}  {nombre}", height=40, corner_radius=9,
                font=(FUENTE, 13, "bold"), fg_color="transparent", text_color=VERDE_OSCURO,
                hover_color=VERDE_CLARO, command=lambda n=nombre: self.mostrar_vista(n))
            boton_vista.grid(row=0, column=indice, sticky="ew", padx=5, pady=6)
            self.botones[nombre] = boton_vista

        self.area_vistas = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        self.area_vistas.pack(fill="both", expand=True)

    # ==========================================
    # CAMBIAR ENTRE VISTAS
    # ==========================================

    def mostrar_vista(self, nombre):
        self.vista_actual = nombre
        for vista, boton_vista in self.botones.items():
            activo = vista == nombre
            boton_vista.configure(fg_color=VERDE if activo else "transparent",
                                  text_color=BLANCO if activo else VERDE_OSCURO)

        for widget in self.area_vistas.winfo_children():
            widget.destroy()

        if nombre == "Existencias":
            self.mostrar_existencias()
        elif nombre == "Movimientos":
            self.mostrar_movimientos()
        elif nombre == "Registrar" and self.es_admin:
            self.mostrar_registrar()

    # ==========================================
    # CARGAR DATOS DESDE SUPABASE
    # ==========================================

    def actualizar(self):
        correcto, productos = ejecutar_seguro(catalogo.listar_productos, solo_activos=True,
                                              titulo_error="Error al cargar el inventario")
        if not correcto:
            productos = []
        self.datos_productos = productos
        self.productos = {f"{p['codigo']} - {p['nombre']}": p for p in productos}

        sin_stock = sum(1 for p in productos if int(p["stock"] or 0) <= 0)
        bajos = sum(1 for p in productos if 0 < int(p["stock"] or 0) <= int(p["stock_minimo"] or 0))
        self.valor_productos.actualizar(len(productos))
        self.valor_normales.actualizar(len(productos) - bajos - sin_stock)
        self.valor_bajos.actualizar(bajos, AMARILLO if bajos else None)
        self.valor_sin.actualizar(sin_stock, ROJO if sin_stock else None)

        self.mostrar_vista(self.vista_actual)

    # ==========================================
    # VISTA 1: EXISTENCIAS
    # ==========================================

    def mostrar_existencias(self):
        contenedor = panel(self.area_vistas)
        contenedor.pack(fill="both", expand=True)

        barra = ctk.CTkFrame(contenedor, fg_color="transparent")
        barra.pack(fill="x", padx=14, pady=(14, 8))
        self.busqueda = ctk.CTkEntry(barra, placeholder_text="Buscar por nombre o código...", height=36,
                                     fg_color=FONDO, border_color=BORDE)
        self.busqueda.pack(side="left", fill="x", expand=True)
        self.busqueda.bind("<KeyRelease>", lambda _e: self.cargar_existencias())
        self.solo_bajos = ctk.CTkSwitch(barra, text="Sólo stock bajo", progress_color=VERDE,
                                        font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO,
                                        command=self.cargar_existencias)
        self.solo_bajos.pack(side="left", padx=12)
        if self.es_admin:
            boton(barra, "Registrar movimiento", self._registrar_desde_existencias, "primario",
                  ancho=170).pack(side="right")

        self.tabla_existencias = Tabla(contenedor, [
            ("codigo", "Código", 120, "w"),
            ("nombre", "Producto", 240, "w"),
            ("categoria", "Categoría", 130, "w"),
            ("stock", "Stock actual", 95, "center"),
            ("minimo", "Mínimo", 80, "center"),
            ("estado", "Estado", 110, "center"),
        ], altura=12, al_doble_click=self._registrar_desde_existencias if self.es_admin else None)
        self.tabla_existencias.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.cargar_existencias()

    def cargar_existencias(self):
        filtro = self.busqueda.get().strip().lower()
        solo_bajos = bool(self.solo_bajos.get())
        filas = []
        for producto in self.datos_productos:
            if filtro and filtro not in f"{producto['codigo']} {producto['nombre']}".lower():
                continue
            stock, minimo = int(producto["stock"] or 0), int(producto["stock_minimo"] or 0)
            bajo = stock <= minimo
            if solo_bajos and not bajo:
                continue
            estado = "Sin stock" if stock <= 0 else ("Stock bajo" if bajo else "Normal")
            etiqueta = ["alerta"] if stock <= 0 else (["aviso"] if bajo else [])
            filas.append((producto["id"], [producto["codigo"], producto["nombre"], producto["categoria"],
                                           stock, minimo, estado], etiqueta))
        self.tabla_existencias.cargar(filas, "No se encontraron productos.")

    def _registrar_desde_existencias(self):
        seleccionado = self.tabla_existencias.seleccionado()
        self.producto_preseleccionado = next(
            (clave for clave, p in self.productos.items() if str(p["id"]) == seleccionado), None)
        self.mostrar_vista("Registrar")

    # ==========================================
    # VISTA 2: MOVIMIENTOS
    # ==========================================

    def mostrar_movimientos(self):
        contenedor = panel(self.area_vistas)
        contenedor.pack(fill="both", expand=True)

        filtros = ctk.CTkFrame(contenedor, fg_color="transparent")
        filtros.pack(fill="x", padx=14, pady=(14, 6))
        self.fechas = SelectorFechas(filtros, self.cargar_movimientos, dias_iniciales=6)
        self.fechas.pack(side="left")

        filtros2 = ctk.CTkFrame(contenedor, fg_color="transparent")
        filtros2.pack(fill="x", padx=14, pady=(0, 8))
        self.filtro_producto = ctk.CTkComboBox(
            filtros2, values=[TODOS_PRODUCTOS] + list(self.productos), width=320, height=34,
            state="readonly", command=lambda _v: self.cargar_movimientos())
        self.filtro_producto.pack(side="left")
        elegir_opcion(self.filtro_producto, TODOS_PRODUCTOS)
        self.filtro_tipo = ctk.CTkComboBox(
            filtros2, values=[TODOS_TIPOS] + TIPOS_HISTORIAL, width=160, height=34, state="readonly",
            command=lambda _v: self.cargar_movimientos())
        self.filtro_tipo.pack(side="left", padx=8)
        elegir_opcion(self.filtro_tipo, TODOS_TIPOS)
        self.resumen_movimientos = ctk.CTkLabel(filtros2, text="", font=(FUENTE, 12), text_color=GRIS)
        self.resumen_movimientos.pack(side="right")

        self.tabla_movimientos = Tabla(contenedor, [
            ("fecha", "Fecha", 125, "center"),
            ("producto", "Producto", 200, "w"),
            ("tipo", "Tipo", 75, "center"),
            ("cantidad", "Cant.", 60, "center"),
            ("stock", "Stock ant. → nuevo", 120, "center"),
            ("motivo", "Motivo", 200, "w"),
            ("usuario", "Usuario", 110, "w"),
        ], altura=11)
        self.tabla_movimientos.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.cargar_movimientos()

    def cargar_movimientos(self):
        try:
            desde, hasta = self.fechas.obtener()
        except ErrorSistema as error:
            advertir(str(error))
            return
        producto = self.productos.get(self.filtro_producto.get())
        tipo = self.filtro_tipo.get()
        correcto, movimientos = ejecutar_seguro(
            operaciones.listar_movimientos_inventario, desde, hasta,
            producto["id"] if producto else None, None if tipo == TODOS_TIPOS else tipo)
        if not correcto:
            return

        filas = []
        for m in movimientos:
            suma = m["tipo"] in ("Entrada", "Compra") or (
                m["tipo"] == "Ajuste" and (m.get("stock_nuevo") or 0) >= (m.get("stock_anterior") or 0))
            datos_producto = m.get("productos") or {}
            stock = "-" if m.get("stock_anterior") is None else f"{m['stock_anterior']} → {m['stock_nuevo']}"
            filas.append((m["id"], [
                formato_fecha(m["fecha"]), datos_producto.get("nombre", "-"), m["tipo"],
                f"{'+' if suma else '−'}{m['cantidad']}", stock, m["motivo"],
                nombre_persona(m.get("perfiles")),
            ], ["positivo" if suma else "alerta"]))
        self.tabla_movimientos.cargar(filas, "No hay movimientos con esos filtros.")
        self.resumen_movimientos.configure(text=f"{len(filas)} movimiento(s)")

    # ==========================================
    # VISTA 3: REGISTRAR MOVIMIENTO (administradora)
    # ==========================================

    def mostrar_registrar(self):
        contenedor = ctk.CTkFrame(self.area_vistas, fg_color="transparent")
        contenedor.pack(fill="both", expand=True)
        contenedor.grid_columnconfigure(0, weight=3)
        contenedor.grid_columnconfigure(1, weight=2, minsize=280)
        contenedor.grid_rowconfigure(0, weight=1)

        formulario = panel(contenedor, "Registrar movimiento", "Registrá ingresos, salidas o ajustes de mercadería.")
        formulario.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        c, self.buscar_producto = campo(formulario, "Buscar producto", "Escribí parte del nombre o código")
        c.pack(fill="x", padx=16, pady=4)
        self.buscar_producto.bind("<KeyRelease>", lambda _e: self._filtrar_selector())

        ctk.CTkLabel(formulario, text="Producto", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(
            anchor="w", padx=16, pady=(6, 3))
        opciones = list(self.productos) or ["Sin productos"]
        self.selector = ctk.CTkComboBox(formulario, values=opciones, state="readonly", height=36,
                                        command=lambda _v: self._mostrar_producto())
        self.selector.pack(fill="x", padx=16)
        elegir_opcion(self.selector, self.producto_preseleccionado or opciones[0])
        self.producto_preseleccionado = None

        ctk.CTkLabel(formulario, text="Tipo de movimiento", font=(FUENTE, 12, "bold"),
                     text_color=VERDE_OSCURO).pack(anchor="w", padx=16, pady=(10, 3))
        self.tipo = ctk.CTkSegmentedButton(formulario, values=list(EXPLICACION_TIPO), height=34,
                                           selected_color=VERDE, selected_hover_color=VERDE_OSCURO,
                                           font=(FUENTE, 12, "bold"), command=lambda _v: self._mostrar_producto())
        self.tipo.set("Entrada")
        self.tipo.pack(fill="x", padx=16)
        self.explicacion = ctk.CTkLabel(formulario, text="", font=(FUENTE, 11), text_color=GRIS, anchor="w",
                                        justify="left", wraplength=480)
        self.explicacion.pack(fill="x", padx=16, pady=(4, 4))

        fila = ctk.CTkFrame(formulario, fg_color="transparent")
        fila.pack(fill="x", padx=10)
        fila.grid_columnconfigure(0, weight=1)
        fila.grid_columnconfigure(1, weight=2)
        c, self.cantidad = campo(fila, "Cantidad", "Ej.: 10")
        c.grid(row=0, column=0, sticky="ew", padx=6)
        self.etiqueta_cantidad = c.etiqueta
        c, self.motivo = campo(fila, "Motivo", "Ej.: Reposición de mercadería")
        c.grid(row=0, column=1, sticky="ew", padx=6)
        self.cantidad.bind("<KeyRelease>", lambda _e: self._mostrar_producto())
        self.motivo.bind("<Return>", lambda _e: self.registrar_movimiento())

        boton(formulario, "Registrar movimiento", self.registrar_movimiento, "primario", alto=44).pack(
            fill="x", padx=16, pady=(16, 16))

        # Tarjeta con el stock del producto elegido
        info = panel(contenedor, "Producto seleccionado")
        info.grid(row=0, column=1, sticky="nsew")
        self.info_nombre = ctk.CTkLabel(info, text="", font=(FUENTE, 15, "bold"), text_color=VERDE_OSCURO,
                                        wraplength=250, justify="left")
        self.info_nombre.pack(anchor="w", padx=16, pady=(4, 10))
        self.info_stock = ctk.CTkLabel(info, text="", font=(FUENTE, 30, "bold"), text_color=VERDE)
        self.info_stock.pack(anchor="w", padx=16)
        ctk.CTkLabel(info, text="Stock actual", font=(FUENTE, 12), text_color=GRIS).pack(anchor="w", padx=16)
        self.info_minimo = ctk.CTkLabel(info, text="", font=(FUENTE, 12), text_color=GRIS)
        self.info_minimo.pack(anchor="w", padx=16, pady=(8, 0))
        self.info_resultado = ctk.CTkLabel(info, text="", font=(FUENTE, 13, "bold"), corner_radius=10,
                                           wraplength=240, justify="left")
        self.info_resultado.pack(fill="x", padx=16, pady=16, ipady=8)

        self._mostrar_producto()

    def _filtrar_selector(self):
        texto = self.buscar_producto.get().strip().lower()
        opciones = [clave for clave in self.productos if texto in clave.lower()] or ["Sin coincidencias"]
        cambiar_opciones(self.selector, opciones)
        self._mostrar_producto()

    def _mostrar_producto(self):
        tipo = self.tipo.get()
        self.explicacion.configure(text=EXPLICACION_TIPO[tipo])
        self.etiqueta_cantidad.configure(text="Nuevo stock total" if tipo == "Ajuste" else "Cantidad")

        producto = self.productos.get(self.selector.get())
        if not producto:
            self.info_nombre.configure(text="Seleccioná un producto")
            self.info_stock.configure(text="—")
            self.info_minimo.configure(text="")
            self.info_resultado.configure(text="", fg_color="transparent")
            return

        stock, minimo = int(producto["stock"] or 0), int(producto["stock_minimo"] or 0)
        self.info_nombre.configure(text=producto["nombre"])
        self.info_stock.configure(text=str(stock), text_color=ROJO if stock <= minimo else VERDE)
        self.info_minimo.configure(text=f"Stock mínimo: {minimo} · Código: {producto['codigo']}")

        try:
            cantidad = int(self.cantidad.get())
        except ValueError:
            self.info_resultado.configure(text="Ingresá la cantidad para ver el resultado.",
                                          fg_color=FONDO, text_color=GRIS)
            return
        nuevo = stock + cantidad if tipo == "Entrada" else (stock - cantidad if tipo == "Salida" else cantidad)
        if nuevo < 0 or cantidad < 0:
            self.info_resultado.configure(text="✕ El stock no puede quedar negativo.",
                                          fg_color=ROJO_CLARO, text_color=ROJO)
        else:
            self.info_resultado.configure(text=f"Stock después del movimiento: {nuevo}",
                                          fg_color=VERDE_CLARO, text_color=VERDE_OSCURO)

    def registrar_movimiento(self):
        producto = self.productos.get(self.selector.get())
        if not producto:
            advertir("Seleccioná un producto válido.")
            return
        correcto, resultado = ejecutar_seguro(
            operaciones.registrar_movimiento_inventario, producto["id"], self.tipo.get(),
            self.cantidad.get(), self.motivo.get(), titulo_error="No se registró el movimiento")
        if correcto:
            informar(f"Movimiento registrado correctamente.\n«{producto['nombre']}»: "
                     f"stock {resultado['stock_anterior']} → {resultado['stock_nuevo']}")
            self.producto_preseleccionado = self.selector.get()
            escribir(self.cantidad, "")
            escribir(self.motivo, "")
            self.actualizar()
