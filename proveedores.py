"""
Proveedores y compras de mercadería - sólo administradora.

 * Proveedores: alta, edición, baja (o desactivación si tiene compras).
 * Productos suministrados: qué productos provee cada proveedor.
 * Nueva compra: se cargan los productos recibidos con cantidad y costo.
   Al confirmar, la función registrar_compra de PostgreSQL guarda la
   compra y su detalle, suma el stock, registra el movimiento de
   inventario, actualiza el costo y (opcional) descuenta de la caja,
   todo en una única transacción.
 * Historial de compras con detalle.
"""

import customtkinter as ctk

from componentes import (
    SelectorFechas, Tabla, advertir, boton, campo, cambiar_opciones, confirmar, ejecutar_seguro,
    encabezado, escribir, formato_dinero, formato_fecha, informar, nombre_persona,
    numero_editable, panel, ventana_modal,
)
from config import FONDO, FUENTE, GRIS, TEXTO, VERDE, VERDE_HOVER, VERDE_OSCURO
from database import ErrorSistema
from servicios import catalogo, validaciones
from servicios import proveedores as servicio

SIN_PROVEEDORES = "No hay proveedores activos"


class ProveedoresFrame(ctk.CTkFrame):
    def __init__(self, master, app=None):
        super().__init__(master, fg_color=FONDO, corner_radius=0)
        self.app = app
        self.proveedores = []
        self.productos = []
        self.proveedor_id = None
        self.items_compra = {}

        encabezado(self, "Proveedores y compras",
                   "Administrá proveedores y registrá el ingreso de mercadería.").pack(
            fill="x", padx=22, pady=(16, 6))

        self.pestanas = ctk.CTkTabview(
            self, fg_color=FONDO, segmented_button_selected_color=VERDE,
            segmented_button_selected_hover_color=VERDE_OSCURO, segmented_button_font=(FUENTE, 13, "bold"),
            command=self._cambio_pestana)
        self.pestanas.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        for nombre in ("Proveedores", "Productos suministrados", "Nueva compra", "Historial de compras"):
            self.pestanas.add(nombre)

        self._crear_proveedores(self.pestanas.tab("Proveedores"))
        self._crear_suministros(self.pestanas.tab("Productos suministrados"))
        self._crear_compra(self.pestanas.tab("Nueva compra"))
        self._crear_historial(self.pestanas.tab("Historial de compras"))

        self.cargar_proveedores()
        self.cargar_productos()

    def _cambio_pestana(self):
        pestana = self.pestanas.get()
        if pestana == "Productos suministrados":
            self.cargar_suministros()
        elif pestana == "Historial de compras":
            self.cargar_historial()

    # ==================================================================
    # DATOS COMPARTIDOS
    # ==================================================================

    def cargar_proveedores(self):
        correcto, proveedores = ejecutar_seguro(servicio.listar_proveedores)
        if not correcto:
            return
        self.proveedores = proveedores
        self.mostrar_proveedores()
        activos = [p["nombre_comercial"] for p in proveedores if p.get("activo", True)] or [SIN_PROVEEDORES]
        cambiar_opciones(self.selector_suministro, activos, self.selector_suministro.get())
        cambiar_opciones(self.selector_compra, activos, self.selector_compra.get())

    def cargar_productos(self):
        correcto, productos = ejecutar_seguro(catalogo.listar_productos, solo_activos=True)
        if correcto:
            self.productos = productos
            self.filtrar_productos_compra()

    def _proveedor_por_nombre(self, nombre):
        return next((p for p in self.proveedores if p["nombre_comercial"] == nombre), None)

    def _producto(self, identificador):
        return next((p for p in self.productos if str(p["id"]) == str(identificador)), None)

    # ==================================================================
    # PESTAÑA 1: PROVEEDORES
    # ==================================================================

    def _crear_proveedores(self, tab):
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2, minsize=300)
        tab.grid_rowconfigure(0, weight=1)

        listado = panel(tab, "Proveedores registrados")
        listado.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.buscar_proveedor = ctk.CTkEntry(listado, placeholder_text="Buscar proveedor...", height=36)
        self.buscar_proveedor.pack(fill="x", padx=14, pady=(0, 8))
        self.buscar_proveedor.bind("<KeyRelease>", lambda _e: self.mostrar_proveedores())
        self.tabla_proveedores = Tabla(listado, [
            ("nombre", "Nombre comercial", 180, "w"),
            ("telefono", "Teléfono", 110, "w"),
            ("email", "Correo", 170, "w"),
            ("productos", "Productos", 80, "center"),
            ("estado", "Estado", 80, "center"),
        ], altura=12, al_seleccionar=self.seleccionar_proveedor)
        self.tabla_proveedores.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        formulario = panel(tab)
        formulario.grid(row=0, column=1, sticky="nsew")
        self.titulo_proveedor = ctk.CTkLabel(formulario, text="Nuevo proveedor", font=(FUENTE, 18, "bold"),
                                             text_color=VERDE_OSCURO)
        self.titulo_proveedor.pack(anchor="w", padx=16, pady=(14, 6))
        c, self.p_nombre = campo(formulario, "Nombre comercial", "Ej.: Distribuidora Norte")
        c.pack(fill="x", padx=16, pady=3)
        c, self.p_telefono = campo(formulario, "Teléfono", "Ej.: 387 4123456")
        c.pack(fill="x", padx=16, pady=3)
        c, self.p_email = campo(formulario, "Correo electrónico", "ventas@proveedor.com")
        c.pack(fill="x", padx=16, pady=3)
        c, self.p_direccion = campo(formulario, "Dirección", "Calle y número, ciudad")
        c.pack(fill="x", padx=16, pady=3)
        self.p_activo = ctk.CTkSwitch(formulario, text="Proveedor activo", progress_color=VERDE,
                                      font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO)
        self.p_activo.pack(anchor="w", padx=16, pady=(8, 4))
        self.p_activo.select()

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=16, pady=(8, 14))
        botones.grid_columnconfigure((0, 1, 2), weight=1)
        self.boton_guardar_proveedor = boton(botones, "Guardar", self.guardar_proveedor, "primario", ancho=80)
        self.boton_guardar_proveedor.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        boton(botones, "Limpiar", self.limpiar_proveedor, "secundario", ancho=80).grid(row=0, column=1, sticky="ew", padx=4)
        self.boton_eliminar_proveedor = boton(botones, "Eliminar", self.eliminar_proveedor, "peligro", ancho=80)
        self.boton_eliminar_proveedor.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        self.limpiar_proveedor()

    def mostrar_proveedores(self):
        texto = self.buscar_proveedor.get().strip().lower()
        self.tabla_proveedores.cargar([
            (p["id"], [p["nombre_comercial"], p.get("telefono") or "-", p.get("email") or "-",
                       p["cantidad_productos"], "Activo" if p.get("activo", True) else "Inactivo"],
             [] if p.get("activo", True) else ["inactivo"])
            for p in self.proveedores if texto in p["nombre_comercial"].lower()
        ], "No hay proveedores registrados.")

    def seleccionar_proveedor(self):
        identificador = self.tabla_proveedores.seleccionado()
        proveedor = next((p for p in self.proveedores if str(p["id"]) == identificador), None)
        if not proveedor:
            return
        self.proveedor_id = proveedor["id"]
        escribir(self.p_nombre, proveedor["nombre_comercial"])
        escribir(self.p_telefono, proveedor.get("telefono"))
        escribir(self.p_email, proveedor.get("email"))
        escribir(self.p_direccion, proveedor.get("direccion"))
        (self.p_activo.select if proveedor.get("activo", True) else self.p_activo.deselect)()
        self.titulo_proveedor.configure(text="Editar proveedor")
        self.boton_eliminar_proveedor.configure(state="normal")

    def limpiar_proveedor(self):
        self.proveedor_id = None
        for entrada in (self.p_nombre, self.p_telefono, self.p_email, self.p_direccion):
            escribir(entrada, "")
        self.p_activo.select()
        self.titulo_proveedor.configure(text="Nuevo proveedor")
        self.boton_eliminar_proveedor.configure(state="disabled")

    def guardar_proveedor(self):
        datos = (self.p_nombre.get(), self.p_telefono.get(), self.p_email.get(), self.p_direccion.get())
        if self.proveedor_id is None:
            correcto, _ = ejecutar_seguro(servicio.crear_proveedor, *datos)
            mensaje = "Proveedor registrado correctamente."
        else:
            correcto, _ = ejecutar_seguro(servicio.actualizar_proveedor, self.proveedor_id, *datos,
                                          activo=bool(self.p_activo.get()))
            mensaje = "Proveedor actualizado correctamente."
        if correcto:
            informar(mensaje)
            self.limpiar_proveedor()
            self.cargar_proveedores()

    def eliminar_proveedor(self):
        if self.proveedor_id is None:
            return
        nombre = self.p_nombre.get()
        if not confirmar(f"¿Eliminar el proveedor «{nombre}»?"):
            return
        correcto, _ = ejecutar_seguro(servicio.eliminar_proveedor, self.proveedor_id,
                                      titulo_error="No se puede eliminar")
        if correcto:
            informar("Proveedor eliminado.")
            self.limpiar_proveedor()
            self.cargar_proveedores()

    # ==================================================================
    # PESTAÑA 2: PRODUCTOS SUMINISTRADOS
    # ==================================================================

    def _crear_suministros(self, tab):
        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(barra, text="Proveedor", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(side="left")
        self.selector_suministro = ctk.CTkComboBox(barra, values=[SIN_PROVEEDORES], state="readonly", width=280,
                                                   height=36,
                                                   command=lambda _v: self.cargar_suministros())
        self.selector_suministro.pack(side="left", padx=8)
        ctk.CTkLabel(barra, text="Los productos también se vinculan automáticamente al registrar una compra.",
                     font=(FUENTE, 11), text_color=GRIS).pack(side="left", padx=8)

        cuerpo = ctk.CTkFrame(tab, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True)
        cuerpo.grid_columnconfigure(0, weight=1)
        cuerpo.grid_columnconfigure(2, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)

        asignados = panel(cuerpo, "Productos que suministra")
        asignados.grid(row=0, column=0, sticky="nsew")
        self.tabla_asignados = Tabla(asignados, [
            ("codigo", "Código", 100, "w"), ("nombre", "Producto", 200, "w"), ("costo", "Costo", 90, "e"),
        ], altura=12, al_doble_click=self.quitar_suministro)
        self.tabla_asignados.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        medio = ctk.CTkFrame(cuerpo, fg_color="transparent")
        medio.grid(row=0, column=1, padx=10)
        boton(medio, "← Asignar", self.asignar_suministro, "primario", ancho=110).pack(pady=6)
        boton(medio, "Quitar →", self.quitar_suministro, "peligro", ancho=110).pack(pady=6)

        otros = panel(cuerpo, "Otros productos")
        otros.grid(row=0, column=2, sticky="nsew")
        self.buscar_otros = ctk.CTkEntry(otros, placeholder_text="Buscar producto...", height=34)
        self.buscar_otros.pack(fill="x", padx=14, pady=(0, 8))
        self.buscar_otros.bind("<KeyRelease>", lambda _e: self._mostrar_otros())
        self.tabla_otros = Tabla(otros, [
            ("codigo", "Código", 100, "w"), ("nombre", "Producto", 200, "w"), ("categoria", "Categoría", 110, "w"),
        ], altura=11, al_doble_click=self.asignar_suministro)
        self.tabla_otros.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.ids_asignados = set()

    def _proveedor_suministro(self):
        return self._proveedor_por_nombre(self.selector_suministro.get())

    def cargar_suministros(self):
        proveedor = self._proveedor_suministro()
        if not proveedor:
            self.tabla_asignados.cargar([], "Registrá un proveedor primero.")
            self.ids_asignados = set()
            self._mostrar_otros()
            return
        correcto, productos = ejecutar_seguro(servicio.productos_del_proveedor, proveedor["id"])
        if not correcto:
            return
        self.ids_asignados = {p["id"] for p in productos}
        self.tabla_asignados.cargar([
            (p["id"], [p.get("codigo"), p.get("nombre"), formato_dinero(p.get("precio_compra"))]) for p in productos
        ], "Este proveedor todavía no tiene productos asignados.")
        self._mostrar_otros()

    def _mostrar_otros(self):
        texto = self.buscar_otros.get().strip().lower()
        self.tabla_otros.cargar([
            (p["id"], [p["codigo"], p["nombre"], p["categoria"]])
            for p in self.productos
            if p["id"] not in self.ids_asignados and texto in f"{p['codigo']} {p['nombre']}".lower()
        ], "No hay más productos para asignar.")

    def asignar_suministro(self):
        proveedor = self._proveedor_suministro()
        producto_id = self.tabla_otros.seleccionado()
        if not proveedor or not producto_id:
            advertir("Seleccioná un proveedor y un producto de «Otros productos».")
            return
        if ejecutar_seguro(servicio.asignar_producto, proveedor["id"], int(producto_id))[0]:
            self.cargar_suministros()
            self.cargar_proveedores()

    def quitar_suministro(self):
        proveedor = self._proveedor_suministro()
        producto_id = self.tabla_asignados.seleccionado()
        if not proveedor or not producto_id:
            advertir("Seleccioná un producto de la lista del proveedor.")
            return
        if ejecutar_seguro(servicio.quitar_producto, proveedor["id"], int(producto_id))[0]:
            self.cargar_suministros()
            self.cargar_proveedores()

    # ==================================================================
    # PESTAÑA 3: NUEVA COMPRA
    # ==================================================================

    def _crear_compra(self, tab):
        tab.grid_columnconfigure(0, weight=1, uniform="compra")
        tab.grid_columnconfigure(1, weight=1, uniform="compra")
        tab.grid_rowconfigure(1, weight=1)

        cabecera = ctk.CTkFrame(tab, fg_color="transparent")
        cabecera.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(4, 8))
        ctk.CTkLabel(cabecera, text="Proveedor", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(side="left")
        self.selector_compra = ctk.CTkComboBox(cabecera, values=[SIN_PROVEEDORES], state="readonly", width=260,
                                               height=36)
        self.selector_compra.pack(side="left", padx=8)
        ctk.CTkLabel(cabecera, text="Observación", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(
            side="left", padx=(12, 0))
        self.observacion = ctk.CTkEntry(cabecera, height=36, placeholder_text="N° de factura o remito (opcional)")
        self.observacion.pack(side="left", fill="x", expand=True, padx=8)

        # Productos
        izquierda = panel(tab, "Productos")
        izquierda.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.buscar_compra = ctk.CTkEntry(izquierda, placeholder_text="Buscar por nombre o código...", height=34)
        self.buscar_compra.pack(fill="x", padx=14, pady=(0, 6))
        self.buscar_compra.bind("<KeyRelease>", lambda _e: self.filtrar_productos_compra())
        self.tabla_productos_compra = Tabla(izquierda, [
            ("codigo", "Código", 100, "w"), ("nombre", "Producto", 190, "w"),
            ("costo", "Costo actual", 95, "e"), ("stock", "Stock", 55, "center"),
        ], altura=9, al_seleccionar=self._sugerir_costo, al_doble_click=self.agregar_item_compra)
        self.tabla_productos_compra.pack(fill="both", expand=True, padx=14)
        carga = ctk.CTkFrame(izquierda, fg_color="transparent")
        carga.pack(fill="x", padx=8, pady=8)
        carga.grid_columnconfigure((0, 1), weight=1)
        c, self.cantidad_compra = campo(carga, "Cantidad", "0")
        c.grid(row=0, column=0, sticky="ew", padx=6)
        c, self.costo_compra = campo(carga, "Costo unitario ($)", "0,00")
        c.grid(row=0, column=1, sticky="ew", padx=6)
        self.costo_compra.bind("<Return>", lambda _e: self.agregar_item_compra())
        boton(carga, "Agregar  ➜", self.agregar_item_compra, "primario", ancho=110).grid(
            row=0, column=2, sticky="s", padx=6)

        # Detalle
        derecha = panel(tab, "Detalle de la compra")
        derecha.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        self.tabla_items = Tabla(derecha, [
            ("nombre", "Producto", 180, "w"), ("cantidad", "Cant.", 55, "center"),
            ("costo", "Costo", 90, "e"), ("subtotal", "Subtotal", 100, "e"),
        ], altura=7)
        self.tabla_items.pack(fill="both", expand=True, padx=14)
        acciones = ctk.CTkFrame(derecha, fg_color="transparent")
        acciones.pack(fill="x", padx=14, pady=6)
        boton(acciones, "Quitar", self.quitar_item_compra, "peligro", ancho=90, alto=32).pack(side="left")
        self.lbl_total_compra = ctk.CTkLabel(acciones, text="Total: " + formato_dinero(0),
                                             font=(FUENTE, 18, "bold"), text_color=TEXTO)
        self.lbl_total_compra.pack(side="right")

        self.pagada_caja = ctk.CTkCheckBox(derecha, text="Pagada en efectivo con dinero de la caja",
                                           fg_color=VERDE, hover_color=VERDE_HOVER, font=(FUENTE, 12))
        self.pagada_caja.pack(anchor="w", padx=14, pady=2)
        self.actualizar_costo = ctk.CTkCheckBox(derecha, text="Actualizar el precio de compra de los productos",
                                                fg_color=VERDE, hover_color=VERDE_HOVER, font=(FUENTE, 12))
        self.actualizar_costo.pack(anchor="w", padx=14, pady=2)
        self.actualizar_costo.select()

        finales = ctk.CTkFrame(derecha, fg_color="transparent")
        finales.pack(fill="x", padx=14, pady=(8, 14))
        finales.grid_columnconfigure((0, 1), weight=1)
        boton(finales, "Cancelar", self.cancelar_compra, "secundario").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        boton(finales, "✓ Confirmar compra", self.confirmar_compra, "primario").grid(
            row=0, column=1, sticky="ew", padx=(4, 0))

    def filtrar_productos_compra(self):
        texto = self.buscar_compra.get().strip().lower()
        self.tabla_productos_compra.cargar([
            (p["id"], [p["codigo"], p["nombre"], formato_dinero(p.get("precio_compra")), p["stock"]])
            for p in self.productos if texto in f"{p['codigo']} {p['nombre']}".lower()
        ], "No se encontraron productos.")

    def _sugerir_costo(self):
        producto = self._producto(self.tabla_productos_compra.seleccionado())
        if producto:
            escribir(self.costo_compra, numero_editable(producto.get("precio_compra")))

    def agregar_item_compra(self):
        producto = self._producto(self.tabla_productos_compra.seleccionado())
        if not producto:
            advertir("Seleccioná un producto de la lista.")
            return
        try:
            cantidad = validaciones.entero(self.cantidad_compra.get(), "Cantidad", minimo=1)
            costo = validaciones.decimal(self.costo_compra.get(), "Costo unitario")
        except ErrorSistema as error:
            advertir(str(error))
            return
        item = self.items_compra.get(producto["id"])
        if item:
            item["cantidad"] += cantidad
            item["costo_unitario"] = costo
        else:
            self.items_compra[producto["id"]] = {"producto_id": producto["id"], "nombre": producto["nombre"],
                                                 "cantidad": cantidad, "costo_unitario": costo}
        escribir(self.cantidad_compra, "")
        self._mostrar_items()
        self.buscar_compra.focus_set()

    def quitar_item_compra(self):
        seleccionado = self.tabla_items.seleccionado()
        if not seleccionado:
            advertir("Seleccioná un producto del detalle.")
            return
        self.items_compra.pop(int(seleccionado), None)
        self._mostrar_items()

    def _mostrar_items(self):
        self.tabla_items.cargar([
            (i["producto_id"], [i["nombre"], i["cantidad"], formato_dinero(i["costo_unitario"]),
                                formato_dinero(i["cantidad"] * i["costo_unitario"])])
            for i in self.items_compra.values()
        ], "Agregá productos a la compra.")
        total = sum(i["cantidad"] * i["costo_unitario"] for i in self.items_compra.values())
        self.lbl_total_compra.configure(text="Total: " + formato_dinero(total))

    def cancelar_compra(self):
        if self.items_compra and not confirmar("¿Descartar la compra en curso?"):
            return
        self._reiniciar_compra()

    def _reiniciar_compra(self):
        self.items_compra.clear()
        escribir(self.observacion, "")
        self.pagada_caja.deselect()
        self.actualizar_costo.select()
        self._mostrar_items()

    def confirmar_compra(self):
        proveedor = self._proveedor_por_nombre(self.selector_compra.get())
        if not proveedor:
            advertir("Seleccioná un proveedor (registralo en la pestaña «Proveedores»).")
            return
        if not self.items_compra:
            advertir("Agregá al menos un producto a la compra.")
            return
        total = sum(i["cantidad"] * i["costo_unitario"] for i in self.items_compra.values())
        if not confirmar(f"Proveedor: {proveedor['nombre_comercial']}\nProductos: {len(self.items_compra)}\n"
                         f"Total: {formato_dinero(total)}\n\n¿Confirmar la compra? El stock se sumará automáticamente."):
            return
        correcto, resultado = ejecutar_seguro(
            servicio.registrar_compra, proveedor["id"], list(self.items_compra.values()),
            self.observacion.get(), bool(self.pagada_caja.get()), bool(self.actualizar_costo.get()),
            titulo_error="La compra no se registró")
        if correcto:
            informar(f"Compra N° {resultado['compra_id']} registrada por {formato_dinero(resultado['total'])}.\n"
                     "El stock fue actualizado.")
            self._reiniciar_compra()
            self.cargar_productos()
            self.cargar_proveedores()

    # ==================================================================
    # PESTAÑA 4: HISTORIAL DE COMPRAS
    # ==================================================================

    def _crear_historial(self, tab):
        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=(4, 8))
        self.fechas = SelectorFechas(barra, self.cargar_historial, dias_iniciales=29)
        self.fechas.pack(side="left")
        boton(barra, "Ver detalle", self.ver_compra, "oscuro", ancho=120).pack(side="right")
        self.resumen_compras = ctk.CTkLabel(tab, text="", font=(FUENTE, 13, "bold"), text_color=TEXTO, anchor="w")
        self.resumen_compras.pack(fill="x", pady=(0, 6))
        self.tabla_compras = Tabla(tab, [
            ("id", "N°", 60, "center"), ("fecha", "Fecha", 130, "center"),
            ("proveedor", "Proveedor", 190, "w"), ("items", "Ítems", 60, "center"),
            ("total", "Total", 110, "e"), ("caja", "Pagada con caja", 110, "center"),
            ("usuario", "Registró", 120, "w"),
        ], altura=13, al_doble_click=self.ver_compra)
        self.tabla_compras.pack(fill="both", expand=True)

    def cargar_historial(self):
        try:
            desde, hasta = self.fechas.obtener()
        except ErrorSistema as error:
            advertir(str(error))
            return
        correcto, compras = ejecutar_seguro(servicio.listar_compras, desde, hasta)
        if not correcto:
            return
        total = sum(float(c["total"]) for c in compras)
        self.resumen_compras.configure(text=f"{len(compras)} compra(s) · Total invertido: {formato_dinero(total)}")
        self.tabla_compras.cargar([
            (c["id"], [c["id"], formato_fecha(c["fecha"]), (c.get("proveedores") or {}).get("nombre_comercial", "-"),
                       (c.get("detalle_compras") or [{"count": 0}])[0].get("count", 0), formato_dinero(c["total"]),
                       "Sí" if c.get("pagada_desde_caja") else "No", nombre_persona(c.get("perfiles"))])
            for c in compras
        ], "No hay compras en el período seleccionado.")

    def ver_compra(self):
        seleccionado = self.tabla_compras.seleccionado()
        if not seleccionado:
            advertir("Seleccioná una compra del historial.")
            return
        correcto, compra = ejecutar_seguro(servicio.obtener_compra, int(seleccionado))
        if not correcto:
            return
        ventana = ventana_modal(self, f"Compra N° {compra['id']}", ancho=640, alto=480)
        info = panel(ventana)
        info.pack(fill="x", padx=16, pady=(16, 8))
        datos = [
            ("Proveedor", (compra.get("proveedores") or {}).get("nombre_comercial", "-")),
            ("Fecha", formato_fecha(compra["fecha"])),
            ("Registró", nombre_persona(compra.get("perfiles"))),
            ("Observación", compra.get("observacion") or "-"),
            ("Pagada con caja", "Sí" if compra.get("pagada_desde_caja") else "No"),
        ]
        for fila, (titulo, valor) in enumerate(datos):
            ctk.CTkLabel(info, text=titulo, font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).grid(
                row=fila, column=0, sticky="w", padx=(16, 10), pady=2)
            ctk.CTkLabel(info, text=str(valor), font=(FUENTE, 12), text_color=TEXTO).grid(
                row=fila, column=1, sticky="w", pady=2)
        tabla = Tabla(ventana, [
            ("codigo", "Código", 100, "w"), ("nombre", "Producto", 200, "w"),
            ("cantidad", "Cant.", 60, "center"), ("costo", "Costo", 90, "e"), ("subtotal", "Subtotal", 100, "e"),
        ], altura=6)
        tabla.pack(fill="both", expand=True, padx=16)
        tabla.cargar([
            (i, [(d.get("productos") or {}).get("codigo", ""), (d.get("productos") or {}).get("nombre", ""),
                 d["cantidad"], formato_dinero(d["costo_unitario"]), formato_dinero(d["subtotal"])])
            for i, d in enumerate(compra.get("detalle_compras") or [])
        ])
        pie = ctk.CTkFrame(ventana, fg_color="transparent")
        pie.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(pie, text="Total: " + formato_dinero(compra["total"]), font=(FUENTE, 18, "bold"),
                     text_color=TEXTO).pack(side="left")
        boton(pie, "Cerrar", ventana.destroy, "secundario", ancho=100).pack(side="right")


