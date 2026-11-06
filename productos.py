"""
Gestión de productos (CRUD) - sólo administradora.

 * Registrar: código/código de barras, nombre, categoría, precios y stock.
 * Listar, buscar por nombre o código y filtrar por categoría / estado.
 * Editar (doble clic o botón).
 * Eliminar con confirmación: si el producto tiene ventas, compras o
   movimientos, no se elimina (se perdería el historial) y se ofrece
   desactivarlo, para que deje de aparecer en Ventas.

El stock se carga sólo al registrar el producto (queda como "Stock
inicial" en el historial). Después se modifica desde Inventario.
"""

import customtkinter as ctk

from componentes import (
    Tabla, advertir, boton, campo, cambiar_opciones, confirmar, ejecutar_seguro, elegir_opcion,
    encabezado, escribir, formato_dinero, informar, numero_editable, panel, selector,
)
from config import BLANCO, FONDO, FUENTE, GRIS, ROJO, VERDE, VERDE_OSCURO, VERDE_SUAVE
from database import ErrorSistema
from servicios import catalogo, validaciones

TODAS = "Todas las categorías"
ESTADOS = ["Activos", "Inactivos", "Todos"]


class ProductosFrame(ctk.CTkFrame):
    def __init__(self, master, app=None):
        super().__init__(master, fg_color=FONDO)
        self.app = app

        self.producto_id = None
        self.categorias = {}   # nombre -> id
        self.productos = []

        encabezado(self, "Gestión de productos", "Registrá, buscá y administrá la mercadería.").pack(
            fill="x", padx=22, pady=(16, 6))

        self.pestanas = ctk.CTkTabview(
            self, fg_color=FONDO, segmented_button_selected_color=VERDE,
            segmented_button_selected_hover_color=VERDE_OSCURO, segmented_button_font=(FUENTE, 13, "bold"))
        self.pestanas.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.pestanas.add("Lista de productos")
        self.pestanas.add("Registrar producto")

        self.crear_listado()
        self.crear_formulario()

        self.cargar_categorias()
        self.cargar_productos()

    # ==================================================================
    # FORMULARIO
    # ==================================================================

    def crear_formulario(self):
        tab = self.pestanas.tab("Registrar producto")
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=1, minsize=260)
        tab.grid_rowconfigure(0, weight=1)

        contenido = panel(tab)
        contenido.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.titulo_formulario = ctk.CTkLabel(contenido, text="Registrar nuevo producto",
                                              font=(FUENTE, 18, "bold"), text_color=VERDE_OSCURO)
        self.titulo_formulario.pack(anchor="w", padx=18, pady=(16, 10))

        formulario = ctk.CTkFrame(contenido, fg_color="transparent")
        formulario.pack(fill="x", padx=10)
        formulario.grid_columnconfigure((0, 1), weight=1)

        def ubicar(widget, fila, columna):
            widget.grid(row=fila, column=columna, sticky="ew", padx=8, pady=6)

        c, self.codigo = campo(formulario, "Código / código de barras", "Ej.: 7790895000997")
        ubicar(c, 0, 0)
        c, self.nombre = campo(formulario, "Nombre del producto", "Ej.: Gaseosa cola 1,5 L")
        ubicar(c, 0, 1)
        c, self.categoria = selector(formulario, "Categoría", ["Cargando categorías..."])
        ubicar(c, 1, 0)
        c, self.precio_compra = campo(formulario, "Precio de compra ($)", "0,00")
        ubicar(c, 1, 1)
        c, self.precio_venta = campo(formulario, "Precio de venta ($)", "0,00")
        ubicar(c, 2, 0)
        c, self.stock = campo(formulario, "Stock inicial", "0")
        ubicar(c, 2, 1)
        c, self.stock_minimo = campo(formulario, "Stock mínimo (alerta)", "5")
        ubicar(c, 3, 0)

        self.nota_stock = ctk.CTkLabel(
            formulario, text="", font=(FUENTE, 11), text_color=GRIS, wraplength=300, justify="left")
        self.nota_stock.grid(row=3, column=1, sticky="w", padx=8)

        for entrada in (self.precio_compra, self.precio_venta):
            entrada.bind("<KeyRelease>", lambda _e: self.calcular_margen())

        escribir(self.stock, "0")
        escribir(self.stock_minimo, "5")

        botones = ctk.CTkFrame(contenido, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(18, 18))
        self.boton_guardar = boton(botones, "Guardar producto", self.guardar_producto, "primario", ancho=180, alto=42)
        self.boton_guardar.pack(side="left", padx=(0, 10))
        boton(botones, "Limpiar", self.limpiar, "secundario", ancho=110, alto=42).pack(side="left", padx=(0, 10))
        boton(botones, "Actualizar categorías", self.cargar_categorias, "oscuro", ancho=170, alto=42).pack(side="left")

        # Panel informativo con el margen de ganancia
        info = panel(tab, "Rentabilidad", "Se calcula con los precios ingresados.")
        info.grid(row=0, column=1, sticky="nsew")
        self.lbl_ganancia = ctk.CTkLabel(info, text=formato_dinero(0), font=(FUENTE, 26, "bold"),
                                         text_color=VERDE_OSCURO)
        self.lbl_ganancia.pack(anchor="w", padx=16, pady=(10, 0))
        ctk.CTkLabel(info, text="Ganancia por unidad", font=(FUENTE, 12), text_color=GRIS).pack(anchor="w", padx=16)
        self.lbl_margen = ctk.CTkLabel(info, text="0 %", font=(FUENTE, 26, "bold"), text_color=VERDE)
        self.lbl_margen.pack(anchor="w", padx=16, pady=(16, 0))
        ctk.CTkLabel(info, text="Margen sobre el precio de venta", font=(FUENTE, 12), text_color=GRIS).pack(
            anchor="w", padx=16)
        ctk.CTkLabel(
            info, text="Consejo: el stock mínimo genera la alerta de «stock bajo» en el Panel y en Inventario.",
            font=(FUENTE, 11), text_color=GRIS, wraplength=230, justify="left", fg_color=VERDE_SUAVE,
            corner_radius=10).pack(fill="x", padx=16, pady=(24, 16), ipady=8)

    def calcular_margen(self):
        try:
            compra = validaciones.decimal(self.precio_compra.get() or "0", "Precio de compra")
            venta = validaciones.decimal(self.precio_venta.get() or "0", "Precio de venta")
        except ErrorSistema:
            self.lbl_ganancia.configure(text="—")
            self.lbl_margen.configure(text="—")
            return
        ganancia = venta - compra
        margen = (ganancia / venta * 100) if venta else 0
        color = ROJO if ganancia < 0 else VERDE
        self.lbl_ganancia.configure(text=formato_dinero(ganancia), text_color=color)
        self.lbl_margen.configure(text=f"{margen:.1f} %", text_color=color)

    # ==================================================================
    # LISTA DE PRODUCTOS
    # ==================================================================

    def crear_listado(self):
        tab = self.pestanas.tab("Lista de productos")

        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=(4, 8))

        self.buscar = ctk.CTkEntry(barra, placeholder_text="Buscar por nombre o código...", height=38)
        self.buscar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.buscar.bind("<KeyRelease>", lambda _e: self.filtrar())

        self.filtro_categoria = ctk.CTkComboBox(
            barra, values=[TODAS], state="readonly", width=190, height=38,
            command=lambda _v: self.filtrar())
        self.filtro_categoria.pack(side="left", padx=(0, 8))
        elegir_opcion(self.filtro_categoria, TODAS)

        self.filtro_estado = ctk.CTkSegmentedButton(
            barra, values=ESTADOS, height=38, selected_color=VERDE, selected_hover_color=VERDE_OSCURO,
            command=lambda _v: self.filtrar())
        self.filtro_estado.set("Activos")
        self.filtro_estado.pack(side="left", padx=(0, 8))

        boton(barra, "+ Nuevo producto", self.nuevo_producto, "primario", ancho=150).pack(side="right")

        self.resumen = ctk.CTkLabel(tab, text="", font=(FUENTE, 12), text_color=GRIS, anchor="w")
        self.resumen.pack(fill="x", pady=(0, 4))

        self.tabla = Tabla(tab, [
            ("codigo", "Código", 120, "w"),
            ("nombre", "Producto", 230, "w"),
            ("categoria", "Categoría", 130, "w"),
            ("compra", "P. compra", 100, "e"),
            ("venta", "P. venta", 100, "e"),
            ("stock", "Stock", 65, "center"),
            ("minimo", "Mínimo", 65, "center"),
            ("estado", "Estado", 80, "center"),
        ], altura=14, al_doble_click=self.editar_producto)
        self.tabla.pack(fill="both", expand=True)

        acciones = ctk.CTkFrame(tab, fg_color="transparent")
        acciones.pack(fill="x", pady=(8, 2))
        boton(acciones, "Editar seleccionado", self.editar_producto, "primario", ancho=170).pack(side="left", padx=(0, 8))
        self.boton_estado = boton(acciones, "Activar / desactivar", self.alternar_estado, "oscuro", ancho=170)
        self.boton_estado.pack(side="left", padx=(0, 8))
        boton(acciones, "Eliminar seleccionado", self.eliminar_producto, "peligro", ancho=170).pack(side="left")
        boton(acciones, "↻ Actualizar lista", self.cargar_productos, "suave", ancho=150).pack(side="right")

    # ==================================================================
    # CARGA DE DATOS DESDE SUPABASE
    # ==================================================================

    def cargar_categorias(self):
        correcto, categorias = ejecutar_seguro(catalogo.listar_categorias,
                                               titulo_error="Error al cargar categorías")
        if not correcto:
            categorias = []
        self.categorias = {c["nombre"]: c["id"] for c in categorias}
        nombres = list(self.categorias) or ["Sin categorías"]
        cambiar_opciones(self.categoria, nombres, self.categoria.get())
        cambiar_opciones(self.filtro_categoria, [TODAS] + list(self.categorias), self.filtro_categoria.get())

    def cargar_productos(self):
        correcto, productos = ejecutar_seguro(catalogo.listar_productos,
                                              titulo_error="Error al cargar productos")
        if correcto:
            self.productos = productos
            self.filtrar()

    def filtrar(self):
        texto = self.buscar.get().lower().strip()
        categoria = self.filtro_categoria.get()
        estado = self.filtro_estado.get()

        filas = []
        for producto in self.productos:
            if texto and texto not in f"{producto['codigo']} {producto['nombre']}".lower():
                continue
            if categoria != TODAS and producto["categoria"] != categoria:
                continue
            activo = producto.get("activo", True)
            if (estado == "Activos" and not activo) or (estado == "Inactivos" and activo):
                continue
            stock = int(producto.get("stock") or 0)
            minimo = int(producto.get("stock_minimo") or 0)
            etiquetas = ["inactivo"] if not activo else (["alerta"] if stock <= minimo else [])
            filas.append((producto["id"], [
                producto["codigo"], producto["nombre"], producto["categoria"],
                formato_dinero(producto.get("precio_compra")), formato_dinero(producto.get("precio_venta")),
                stock, minimo, "Activo" if activo else "Inactivo",
            ], etiquetas))

        self.tabla.cargar(filas, "No se encontraron productos con esos filtros.")
        bajos = sum(1 for p in self.productos if p.get("activo", True)
                    and int(p.get("stock") or 0) <= int(p.get("stock_minimo") or 0))
        self.resumen.configure(
            text=f"Mostrando {len(filas)} de {len(self.productos)} productos · "
                 f"{bajos} con stock bajo (en rojo)")

    # ==================================================================
    # GUARDAR O ACTUALIZAR
    # ==================================================================

    def guardar_producto(self):
        es_nuevo = self.producto_id is None
        try:
            datos = catalogo.validar_producto(
                self.codigo.get(), self.nombre.get(), self.categorias.get(self.categoria.get()),
                self.precio_compra.get() or "0", self.precio_venta.get(),
                self.stock.get(), self.stock_minimo.get(), es_nuevo=es_nuevo,
            )
        except ErrorSistema as error:
            advertir(str(error), "Datos incorrectos")
            return

        if datos["precio_venta"] < datos["precio_compra"] and not confirmar(
                "El precio de venta es menor al precio de compra (se vendería con pérdida).\n"
                "¿Querés guardarlo igual?", "Precio por debajo del costo"):
            return

        if es_nuevo:
            correcto, _ = ejecutar_seguro(catalogo.crear_producto, datos, titulo_error="Error al guardar")
            mensaje = "Producto registrado correctamente."
        else:
            correcto, _ = ejecutar_seguro(catalogo.actualizar_producto, self.producto_id, datos,
                                          titulo_error="Error al guardar")
            mensaje = "Producto actualizado correctamente."

        if correcto:
            informar(mensaje)
            self.limpiar()
            self.cargar_productos()
            self.pestanas.set("Lista de productos")

    # ==================================================================
    # SELECCIÓN, EDICIÓN Y ELIMINACIÓN
    # ==================================================================

    def producto_seleccionado(self):
        seleccion = self.tabla.seleccionado()
        if not seleccion:
            advertir("Primero seleccioná un producto de la lista.", "Seleccionar producto")
            return None
        return next((p for p in self.productos if str(p["id"]) == seleccion), None)

    def nuevo_producto(self):
        self.limpiar()
        self.pestanas.set("Registrar producto")
        self.codigo.focus_set()

    def editar_producto(self):
        producto = self.producto_seleccionado()
        if not producto:
            return

        self.limpiar()
        self.producto_id = producto["id"]

        escribir(self.codigo, producto.get("codigo"))
        escribir(self.nombre, producto.get("nombre"))
        escribir(self.precio_compra, numero_editable(producto.get("precio_compra")))
        escribir(self.precio_venta, numero_editable(producto.get("precio_venta")))
        escribir(self.stock_minimo, producto.get("stock_minimo") or 0)
        escribir(self.stock, producto.get("stock") or 0)
        self.stock.configure(state="disabled", fg_color=FONDO)
        self.nota_stock.configure(text="El stock se modifica desde Inventario (entradas, salidas y ajustes) "
                                       "para que quede registrado en el historial.")

        if producto["categoria"] in self.categorias:
            elegir_opcion(self.categoria, producto["categoria"])

        self.titulo_formulario.configure(text=f"Editar producto: {producto['nombre']}")
        self.boton_guardar.configure(text="Guardar cambios")
        self.calcular_margen()
        self.pestanas.set("Registrar producto")

    def alternar_estado(self):
        producto = self.producto_seleccionado()
        if not producto:
            return
        activo = producto.get("activo", True)
        accion = "desactivar" if activo else "activar"
        detalle = ("Dejará de aparecer en Ventas, pero se conserva su historial."
                   if activo else "Volverá a estar disponible para la venta.")
        if not confirmar(f"¿Querés {accion} «{producto['nombre']}»?\n{detalle}"):
            return
        correcto, _ = ejecutar_seguro(catalogo.cambiar_estado_producto, producto["id"], not activo)
        if correcto:
            self.cargar_productos()

    def eliminar_producto(self):
        producto = self.producto_seleccionado()
        if not producto:
            return

        correcto, tiene_movimientos = ejecutar_seguro(catalogo.movimientos_asociados, producto["id"])
        if not correcto:
            return

        if tiene_movimientos:
            if producto.get("activo", True) and confirmar(
                    f"«{producto['nombre']}» tiene ventas, compras o movimientos de stock registrados "
                    "y no puede eliminarse sin perder el historial.\n\n"
                    "¿Querés desactivarlo para que no aparezca más en Ventas?", "No se puede eliminar"):
                if ejecutar_seguro(catalogo.cambiar_estado_producto, producto["id"], False)[0]:
                    informar("Producto desactivado.")
                    self.cargar_productos()
            elif not producto.get("activo", True):
                advertir("El producto tiene historial y no puede eliminarse. Ya se encuentra desactivado.")
            return

        if not confirmar(f"¿Querés eliminar definitivamente «{producto['nombre']}»?\n"
                         "Esta acción no se puede deshacer.", "Eliminar producto"):
            return

        correcto, _ = ejecutar_seguro(catalogo.eliminar_producto, producto["id"],
                                      titulo_error="Error al eliminar")
        if correcto:
            self.cargar_productos()
            informar("Producto eliminado correctamente.")

    # ==================================================================
    # LIMPIAR FORMULARIO
    # ==================================================================

    def limpiar(self):
        self.producto_id = None
        self.stock.configure(state="normal", fg_color=BLANCO)
        for entrada in (self.codigo, self.nombre, self.precio_compra, self.precio_venta,
                        self.stock, self.stock_minimo):
            escribir(entrada, "")
        escribir(self.stock, "0")
        escribir(self.stock_minimo, "5")
        self.nota_stock.configure(text="El stock inicial queda registrado en el historial de Inventario.")
        if self.categorias:
            elegir_opcion(self.categoria, next(iter(self.categorias)))
        self.titulo_formulario.configure(text="Registrar nuevo producto")
        self.boton_guardar.configure(text="Guardar producto")
        self.calcular_margen()
