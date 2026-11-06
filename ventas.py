"""
Ventas: punto de venta con carrito e historial de ventas.

Flujo de una venta:
 1. Se buscan productos (por nombre o código; con lector de código de
    barras, Enter agrega directamente el producto).
 2. Se arma el carrito: cantidades, quitar productos, total automático.
 3. Se elige el medio de pago (en efectivo se calcula el vuelto).
 4. Al confirmar se llama a registrar_venta() en PostgreSQL, que en UNA
    transacción guarda la venta, el detalle, descuenta el stock y registra
    el movimiento de inventario y de caja. Si algo falla, no se guarda nada.
 5. Se muestra el comprobante.
"""

import customtkinter as ctk

from comprobantes import mostrar_comprobante
from componentes import (
    SelectorFechas, Tabla, advertir, boton, confirmar, ejecutar_seguro, encabezado,
    escribir, formato_dinero, formato_fecha, nombre_persona, panel,
)
from config import (
    BLANCO, BORDE, FONDO, FUENTE, GRIS, METODOS_PAGO, ROJO, TEXTO, VERDE, VERDE_OSCURO, VERDE_SUAVE,
)
from database import ErrorSistema
from servicios import catalogo, operaciones, validaciones

MAX_RESULTADOS = 300


class VentasFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=FONDO, corner_radius=0)
        self.app = app
        self.productos = []           # productos activos (desde Supabase)
        self.carrito = {}             # producto_id -> item del carrito

        encabezado(self, "Ventas", "Registrá ventas, cobrá y consultá el historial.").pack(
            fill="x", padx=22, pady=(16, 6))

        self.pestanas = ctk.CTkTabview(
            self, fg_color=FONDO, segmented_button_selected_color=VERDE,
            segmented_button_selected_hover_color=VERDE_OSCURO,
            segmented_button_font=(FUENTE, 13, "bold"), command=self._cambio_pestana)
        self.pestanas.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.pestanas.add("Nueva venta")
        self.pestanas.add("Historial de ventas")

        self._crear_punto_venta(self.pestanas.tab("Nueva venta"))
        self._crear_historial(self.pestanas.tab("Historial de ventas"))

        self.cargar_productos()
        self.after(200, self.busqueda.focus_set)

    # ==================================================================
    # PUNTO DE VENTA
    # ==================================================================

    def _crear_punto_venta(self, tab):
        tab.grid_columnconfigure(0, weight=11, uniform="pv")
        tab.grid_columnconfigure(1, weight=10, uniform="pv")
        tab.grid_rowconfigure(0, weight=1)

        # ---------------- Productos ----------------
        izquierda = panel(tab, "Buscar productos", "Escribí el nombre o escaneá el código y presioná Enter.")
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        barra = ctk.CTkFrame(izquierda, fg_color="transparent")
        barra.pack(fill="x", padx=14, pady=(0, 8))
        self.busqueda = ctk.CTkEntry(barra, height=38, placeholder_text="Nombre o código de barras...",
                                     border_color=BORDE, fg_color=BLANCO)
        self.busqueda.pack(side="left", fill="x", expand=True)
        self.busqueda.bind("<KeyRelease>", self._al_escribir)
        self.busqueda.bind("<Return>", lambda _e: self._enter_busqueda())
        boton(barra, "↻", self.cargar_productos, "suave", ancho=42).pack(side="left", padx=(6, 0))

        self.tabla_productos = Tabla(izquierda, [
            ("codigo", "Código", 110, "w"),
            ("nombre", "Producto", 220, "w"),
            ("precio", "Precio", 95, "e"),
            ("stock", "Stock", 60, "center"),
        ], altura=12, al_doble_click=self.agregar_seleccionado)
        self.tabla_productos.pack(fill="both", expand=True, padx=14)

        agregar = ctk.CTkFrame(izquierda, fg_color="transparent")
        agregar.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(agregar, text="Cantidad", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(side="left")
        self.cantidad = ctk.CTkEntry(agregar, width=70, height=36, justify="center", border_color=BORDE)
        self.cantidad.pack(side="left", padx=8)
        escribir(self.cantidad, 1)
        self.cantidad.bind("<Return>", lambda _e: self.agregar_seleccionado())
        boton(agregar, "Agregar al carrito  ➜", self.agregar_seleccionado, "primario", ancho=180).pack(side="right")

        # ---------------- Carrito ----------------
        derecha = panel(tab, "Carrito")
        derecha.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.tabla_carrito = Tabla(derecha, [
            ("nombre", "Producto", 170, "w"),
            ("cantidad", "Cant.", 50, "center"),
            ("precio", "P. unit.", 85, "e"),
            ("subtotal", "Subtotal", 95, "e"),
        ], altura=6, al_doble_click=self.editar_cantidad)
        self.tabla_carrito.pack(fill="both", expand=True, padx=14)

        acciones = ctk.CTkFrame(derecha, fg_color="transparent")
        acciones.pack(fill="x", padx=14, pady=(6, 4))
        for texto, comando, tipo, ancho in (
            ("−", lambda: self.sumar(-1), "suave", 40),
            ("+", lambda: self.sumar(1), "suave", 40),
            ("Cantidad...", self.editar_cantidad, "suave", 95),
            ("Quitar", self.quitar, "peligro", 75),
        ):
            boton(acciones, texto, comando, tipo, ancho=ancho, alto=32).pack(side="left", padx=(0, 5))

        # Total
        caja_total = ctk.CTkFrame(derecha, fg_color=VERDE_OSCURO, corner_radius=12)
        caja_total.pack(fill="x", padx=14, pady=(4, 6))
        self.lbl_items = ctk.CTkLabel(caja_total, text="0 productos", font=(FUENTE, 12), text_color="#B8CFC0")
        self.lbl_items.pack(side="left", padx=14, pady=10)
        self.lbl_total = ctk.CTkLabel(caja_total, text=formato_dinero(0), font=(FUENTE, 26, "bold"),
                                      text_color=BLANCO)
        self.lbl_total.pack(side="right", padx=14, pady=8)

        # Pago
        pago = ctk.CTkFrame(derecha, fg_color="transparent")
        pago.pack(fill="x", padx=14)
        pago.grid_columnconfigure((0, 1), weight=1)
        self.metodo = ctk.CTkSegmentedButton(
            pago, values=list(METODOS_PAGO.values()), height=34, font=(FUENTE, 12, "bold"),
            selected_color=VERDE, selected_hover_color=VERDE_OSCURO, command=lambda _v: self._actualizar_pago())
        self.metodo.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.metodo.set("Efectivo")

        ctk.CTkLabel(pago, text="Monto recibido", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).grid(
            row=1, column=0, sticky="w")
        self.lbl_vuelto_titulo = ctk.CTkLabel(pago, text="Vuelto", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO)
        self.lbl_vuelto_titulo.grid(row=1, column=1, sticky="w", padx=(10, 0))
        self.recibido = ctk.CTkEntry(pago, height=36, placeholder_text="$ 0,00", border_color=BORDE)
        self.recibido.grid(row=2, column=0, sticky="ew")
        self.recibido.bind("<KeyRelease>", lambda _e: self._actualizar_pago())
        self.recibido.bind("<Return>", lambda _e: self.confirmar_venta())
        self.lbl_vuelto = ctk.CTkLabel(pago, text=formato_dinero(0), font=(FUENTE, 18, "bold"),
                                       text_color=VERDE, fg_color=VERDE_SUAVE, corner_radius=8, height=36)
        self.lbl_vuelto.grid(row=2, column=1, sticky="ew", padx=(10, 0))

        finales = ctk.CTkFrame(derecha, fg_color="transparent")
        finales.pack(fill="x", padx=14, pady=(10, 14))
        finales.grid_columnconfigure(0, weight=1)
        finales.grid_columnconfigure(1, weight=2)
        boton(finales, "Cancelar venta", self.cancelar_venta, "secundario", alto=44).grid(
            row=0, column=0, sticky="ew", padx=(0, 6))
        self.boton_confirmar = boton(finales, "✓  Confirmar venta", self.confirmar_venta, "primario", alto=44)
        self.boton_confirmar.grid(row=0, column=1, sticky="ew")

    # ------------------------------------------------------------------
    # Productos
    # ------------------------------------------------------------------

    def cargar_productos(self):
        correcto, productos = ejecutar_seguro(catalogo.listar_productos, solo_activos=True,
                                              titulo_error="No se pudieron cargar los productos")
        if correcto:
            self.productos = productos
            # Actualizar el stock disponible de lo que ya está en el carrito
            por_id = {p["id"]: p for p in productos}
            for item in self.carrito.values():
                if item["producto_id"] in por_id:
                    item["stock"] = por_id[item["producto_id"]]["stock"]
            self.filtrar()

    def _al_escribir(self, evento):
        if evento.keysym not in ("Return", "Up", "Down"):
            self.filtrar()

    def filtrar(self):
        texto = self.busqueda.get().strip().lower()
        filas = []
        for producto in self.productos:
            if texto and texto not in f"{producto['codigo']} {producto['nombre']}".lower():
                continue
            stock = int(producto.get("stock") or 0)
            etiquetas = ["alerta"] if stock <= 0 else (["aviso"] if stock <= int(producto.get("stock_minimo") or 0) else [])
            filas.append((producto["id"], [producto["codigo"], producto["nombre"],
                                           formato_dinero(producto["precio_venta"]), stock], etiquetas))
            if len(filas) >= MAX_RESULTADOS:
                break
        self.tabla_productos.cargar(filas, "No se encontraron productos.")
        if filas:
            self.tabla_productos.seleccionar(filas[0][0])

    def _enter_busqueda(self):
        """Enter en la búsqueda: si el código coincide exacto, se agrega directo (lector de barras)."""
        texto = self.busqueda.get().strip()
        exacto = next((p for p in self.productos if str(p["codigo"]).lower() == texto.lower()), None)
        if exacto:
            self._agregar(exacto, 1)
            escribir(self.busqueda, "")
            self.filtrar()
        else:
            self.agregar_seleccionado()

    def _producto(self, producto_id):
        return next((p for p in self.productos if str(p["id"]) == str(producto_id)), None)

    # ------------------------------------------------------------------
    # Carrito
    # ------------------------------------------------------------------

    def agregar_seleccionado(self):
        seleccionado = self.tabla_productos.seleccionado()
        if not seleccionado:
            advertir("Seleccioná un producto de la lista.")
            return
        try:
            cantidad = validaciones.entero(self.cantidad.get(), "Cantidad", minimo=1)
        except ErrorSistema as error:
            advertir(str(error))
            return
        self._agregar(self._producto(seleccionado), cantidad)
        escribir(self.cantidad, 1)

    def _agregar(self, producto, cantidad):
        if producto is None:
            return
        actual = self.carrito.get(producto["id"], {}).get("cantidad", 0)
        stock = int(producto.get("stock") or 0)
        if actual + cantidad > stock:
            advertir(f"Stock insuficiente para «{producto['nombre']}».\n"
                     f"Disponible: {stock} · En el carrito: {actual}.", "Stock insuficiente")
            return
        self.carrito[producto["id"]] = {
            "producto_id": producto["id"],
            "nombre": producto["nombre"],
            "precio": float(producto["precio_venta"]),
            "stock": stock,
            "cantidad": actual + cantidad,
        }
        self._mostrar_carrito(seleccionar=producto["id"])

    def _item_seleccionado(self):
        seleccionado = self.tabla_carrito.seleccionado()
        if not seleccionado:
            advertir("Seleccioná un producto del carrito.")
            return None
        return self.carrito.get(int(seleccionado))

    def sumar(self, delta):
        item = self._item_seleccionado()
        if not item:
            return
        nueva = item["cantidad"] + delta
        if nueva <= 0:
            self.quitar()
            return
        if nueva > item["stock"]:
            advertir(f"No hay más stock de «{item['nombre']}» (disponible: {item['stock']}).")
            return
        item["cantidad"] = nueva
        self._mostrar_carrito(seleccionar=item["producto_id"])

    def editar_cantidad(self):
        item = self._item_seleccionado()
        if not item:
            return
        dialogo = ctk.CTkInputDialog(title="Modificar cantidad",
                                     text=f"Nueva cantidad para «{item['nombre']}» (disponible: {item['stock']}):")
        respuesta = dialogo.get_input()
        if respuesta is None:
            return
        try:
            cantidad = validaciones.entero(respuesta, "Cantidad", minimo=1)
        except ErrorSistema as error:
            advertir(str(error))
            return
        if cantidad > item["stock"]:
            advertir(f"Stock insuficiente: disponible {item['stock']}.")
            return
        item["cantidad"] = cantidad
        self._mostrar_carrito(seleccionar=item["producto_id"])

    def quitar(self):
        item = self._item_seleccionado()
        if item:
            del self.carrito[item["producto_id"]]
            self._mostrar_carrito()

    def total(self):
        return round(sum(round(i["precio"] * i["cantidad"], 2) for i in self.carrito.values()), 2)

    def _mostrar_carrito(self, seleccionar=None):
        self.tabla_carrito.cargar([
            (i["producto_id"], [i["nombre"], i["cantidad"], formato_dinero(i["precio"]),
                                formato_dinero(i["precio"] * i["cantidad"])])
            for i in self.carrito.values()
        ], "El carrito está vacío.")
        if seleccionar is not None:
            self.tabla_carrito.seleccionar(seleccionar)
        unidades = sum(i["cantidad"] for i in self.carrito.values())
        self.lbl_items.configure(text=f"{len(self.carrito)} productos · {unidades} unidades")
        self.lbl_total.configure(text=formato_dinero(self.total()))
        self._actualizar_pago()

    # ------------------------------------------------------------------
    # Pago
    # ------------------------------------------------------------------

    def _metodo_codigo(self):
        visible = self.metodo.get()
        return next(codigo for codigo, texto in METODOS_PAGO.items() if texto == visible)

    def _actualizar_pago(self):
        efectivo = self._metodo_codigo() == "efectivo"
        self.recibido.configure(state="normal" if efectivo else "disabled",
                                fg_color=BLANCO if efectivo else FONDO)
        if not efectivo:
            self.lbl_vuelto_titulo.configure(text="Vuelto")
            self.lbl_vuelto.configure(text="No corresponde", text_color=GRIS, fg_color=FONDO)
            return
        texto = self.recibido.get().strip()
        if not texto:
            self.lbl_vuelto.configure(text=formato_dinero(0), text_color=VERDE, fg_color=VERDE_SUAVE)
            return
        try:
            recibido = validaciones.decimal(texto, "Monto recibido")
        except ErrorSistema:
            self.lbl_vuelto.configure(text="Monto inválido", text_color=ROJO, fg_color="#FDE8E8")
            return
        vuelto = recibido - self.total()
        if vuelto < 0:
            self.lbl_vuelto_titulo.configure(text="Falta")
            self.lbl_vuelto.configure(text=formato_dinero(-vuelto), text_color=ROJO, fg_color="#FDE8E8")
        else:
            self.lbl_vuelto_titulo.configure(text="Vuelto")
            self.lbl_vuelto.configure(text=formato_dinero(vuelto), text_color=VERDE, fg_color=VERDE_SUAVE)

    def cancelar_venta(self):
        if self.carrito and not confirmar("¿Cancelar la venta actual y vaciar el carrito?", "Cancelar venta"):
            return
        self._reiniciar()

    def _reiniciar(self):
        self.carrito.clear()
        escribir(self.recibido, "")
        self.metodo.set("Efectivo")
        self._mostrar_carrito()
        escribir(self.busqueda, "")
        self.filtrar()
        self.busqueda.focus_set()

    def confirmar_venta(self):
        if not self.carrito:
            advertir("Agregá productos al carrito antes de confirmar.")
            return
        metodo = self._metodo_codigo()
        total = self.total()
        mensaje = f"Total a cobrar: {formato_dinero(total)}\nForma de pago: {METODOS_PAGO[metodo]}"
        if metodo == "efectivo":
            try:
                recibido = validaciones.decimal(self.recibido.get(), "Monto recibido", permitir_cero=False)
            except ErrorSistema as error:
                advertir(str(error))
                self.recibido.focus_set()
                return
            if recibido < total:
                advertir(f"El monto recibido es menor al total ({formato_dinero(total)}).")
                return
            mensaje += f"\nRecibido: {formato_dinero(recibido)}\nVuelto: {formato_dinero(recibido - total)}"
        else:
            recibido = None

        if not confirmar(mensaje + "\n\n¿Confirmar la venta?", "Confirmar venta"):
            return

        self.boton_confirmar.configure(state="disabled", text="Registrando...")
        self.update_idletasks()
        correcto, resultado = ejecutar_seguro(
            operaciones.registrar_venta, list(self.carrito.values()), metodo, recibido,
            titulo_error="La venta no se registró")
        if not self.winfo_exists():
            return
        self.boton_confirmar.configure(state="normal", text="✓  Confirmar venta")

        if correcto:
            self._reiniciar()
            self.cargar_productos()  # stock actualizado
            mostrar_comprobante(self, resultado["venta_id"])
        else:
            # Puede haber cambiado el stock (otra caja vendió): se recarga.
            self.cargar_productos()

    # ==================================================================
    # HISTORIAL
    # ==================================================================

    def _crear_historial(self, tab):
        barra = ctk.CTkFrame(tab, fg_color="transparent")
        barra.pack(fill="x", pady=(4, 8))
        self.fechas = SelectorFechas(barra, self.cargar_historial, dias_iniciales=0)
        self.fechas.pack(side="left")
        boton(barra, "Ver comprobante", self.ver_detalle, "oscuro", ancho=150).pack(side="right")

        self.resumen_historial = ctk.CTkLabel(tab, text="", font=(FUENTE, 13, "bold"), text_color=TEXTO,
                                              anchor="w")
        self.resumen_historial.pack(fill="x", pady=(0, 6))

        self.tabla_historial = Tabla(tab, [
            ("id", "N° venta", 80, "center"),
            ("fecha", "Fecha y hora", 140, "center"),
            ("usuario", "Atendió", 150, "w"),
            ("pago", "Forma de pago", 120, "center"),
            ("items", "Ítems", 60, "center"),
            ("total", "Total", 120, "e"),
        ], altura=14, al_doble_click=self.ver_detalle)
        self.tabla_historial.pack(fill="both", expand=True)

    def _cambio_pestana(self):
        if self.pestanas.get() == "Historial de ventas":
            self.cargar_historial()
        else:
            self.busqueda.focus_set()

    def cargar_historial(self):
        try:
            desde, hasta = self.fechas.obtener()
        except ErrorSistema as error:
            advertir(str(error))
            return
        correcto, ventas = ejecutar_seguro(operaciones.listar_ventas, desde, hasta)
        if not correcto:
            return
        total = sum(float(v["total"]) for v in ventas)
        self.resumen_historial.configure(
            text=f"{len(ventas)} venta(s) en el período · Total: {formato_dinero(total)}")
        self.tabla_historial.cargar([
            (v["id"], [v["id"], formato_fecha(v["fecha"]), nombre_persona(v.get("perfiles")),
                       METODOS_PAGO.get(v["metodo_pago"], v["metodo_pago"]),
                       (v.get("detalle_ventas") or [{"count": 0}])[0].get("count", 0),
                       formato_dinero(v["total"])])
            for v in ventas
        ], "No hay ventas en el período seleccionado.")

    def ver_detalle(self):
        seleccionado = self.tabla_historial.seleccionado()
        if not seleccionado:
            advertir("Seleccioná una venta del historial.")
            return
        mostrar_comprobante(self, int(seleccionado))


