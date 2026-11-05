
import sqlite3
import customtkinter as ctk
from tkinter import messagebox

from database import conectar


# ==========================================
# COLORES DEL MINISERVICE
# ==========================================

FONDO = "#F4F8F5"
BLANCO = "#FFFFFF"
VERDE_OSCURO = "#18392B"
VERDE = "#166534"
VERDE_HOVER = "#15803D"
VERDE_CLARO = "#DCEFE2"
GRIS = "#64756B"
BORDE = "#DFEAE2"
ROJO = "#B91C1C"
ROJO_CLARO = "#FDE8E8"


class InventarioFrame(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=FONDO,
            corner_radius=0
        )

        self.productos = {}
        self.datos_productos = []
        self.datos_movimientos = []
        self.vista_actual = "Existencias"
        self.botones = {}

        self.crear_interfaz()
        self.actualizar()

    # ==========================================
    # DISEÑO GENERAL
    # ==========================================

    def crear_interfaz(self):

        self.contenedor = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.contenedor.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=18
        )

        # Encabezado
        encabezado = ctk.CTkFrame(
            self.contenedor,
            fg_color="transparent"
        )
        encabezado.pack(fill="x", pady=(0, 18))

        ctk.CTkLabel(
            encabezado,
            text="Control de Inventario",
            font=("Arial", 27, "bold"),
            text_color=VERDE_OSCURO
        ).pack(anchor="w")

        ctk.CTkLabel(
            encabezado,
            text="Controlá la mercadería de MiniService Gris y Angie.",
            font=("Arial", 13),
            text_color=GRIS
        ).pack(anchor="w", pady=(4, 0))

        # ======================================
        # TARJETAS DE RESUMEN
        # ======================================

        resumen = ctk.CTkFrame(
            self.contenedor,
            fg_color="transparent"
        )
        resumen.pack(fill="x", pady=(0, 18))

        resumen.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="resumen"
        )

        self.valor_productos = self.crear_tarjeta_resumen(
            resumen,
            "Productos",
            "▣",
            0
        )

        self.valor_normales = self.crear_tarjeta_resumen(
            resumen,
            "Stock normal",
            "✓",
            1
        )

        self.valor_bajos = self.crear_tarjeta_resumen(
            resumen,
            "Stock bajo",
            "!",
            2,
            alerta=True
        )

        # ======================================
        # BOTONES DE NAVEGACIÓN
        # ======================================

        navegacion = ctk.CTkFrame(
            self.contenedor,
            fg_color=BLANCO,
            corner_radius=13,
            border_width=1,
            border_color=BORDE
        )
        navegacion.pack(fill="x", pady=(0, 15))

        navegacion.grid_columnconfigure(
            (0, 1, 2),
            weight=1
        )

        opciones = [
            ("Existencias", "▣"),
            ("Movimientos", "⇄"),
            ("Registrar", "+")
        ]

        for indice, (nombre, icono) in enumerate(opciones):

            boton = ctk.CTkButton(
                navegacion,
                text=f"{icono}  {nombre}",
                height=43,
                corner_radius=9,
                font=("Arial", 13, "bold"),
                fg_color="transparent",
                text_color=VERDE_OSCURO,
                hover_color=VERDE_CLARO,
                command=lambda n=nombre: self.mostrar_vista(n)
            )

            boton.grid(
                row=0,
                column=indice,
                sticky="ew",
                padx=5,
                pady=7
            )

            self.botones[nombre] = boton

        # ======================================
        # ÁREA DONDE CAMBIAN LAS VISTAS
        # ======================================

        self.area_vistas = ctk.CTkFrame(
            self.contenedor,
            fg_color="transparent"
        )
        self.area_vistas.pack(
            fill="both",
            expand=True
        )

    def crear_tarjeta_resumen(
        self,
        padre,
        titulo,
        simbolo,
        columna,
        alerta=False
    ):

        tarjeta = ctk.CTkFrame(
            padre,
            fg_color=BLANCO,
            corner_radius=14,
            border_width=1,
            border_color=BORDE
        )
        tarjeta.grid(
            row=0,
            column=columna,
            sticky="nsew",
            padx=5
        )

        ctk.CTkLabel(
            tarjeta,
            text=simbolo,
            font=("Arial", 22, "bold"),
            text_color=ROJO if alerta else VERDE
        ).pack(
            anchor="w",
            padx=17,
            pady=(13, 5)
        )

        ctk.CTkLabel(
            tarjeta,
            text=titulo,
            font=("Arial", 12),
            text_color=GRIS
        ).pack(
            anchor="w",
            padx=17
        )

        valor = ctk.CTkLabel(
            tarjeta,
            text="0",
            font=("Arial", 25, "bold"),
            text_color=ROJO if alerta else VERDE_OSCURO
        )
        valor.pack(
            anchor="w",
            padx=17,
            pady=(3, 15)
        )

        return valor

    # ==========================================
    # CAMBIAR ENTRE PANTALLAS
    # ==========================================

    def mostrar_vista(self, nombre):

        self.vista_actual = nombre

        for vista, boton in self.botones.items():

            if vista == nombre:
                boton.configure(
                    fg_color=VERDE,
                    text_color=BLANCO
                )
            else:
                boton.configure(
                    fg_color="transparent",
                    text_color=VERDE_OSCURO
                )

        for widget in self.area_vistas.winfo_children():
            widget.destroy()

        if nombre == "Existencias":
            self.mostrar_existencias()

        elif nombre == "Movimientos":
            self.mostrar_movimientos()

        elif nombre == "Registrar":
            self.mostrar_registrar()

    # ==========================================
    # VISTA 1: EXISTENCIAS
    # ==========================================

    def mostrar_existencias(self):

        panel = self.crear_panel("Existencias actuales")

        cabecera = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        cabecera.pack(
            fill="x",
            padx=18,
            pady=(0, 12)
        )

        ctk.CTkLabel(
            cabecera,
            text="Consultá el stock disponible de cada producto.",
            font=("Arial", 12),
            text_color=GRIS
        ).pack(side="left")

        ctk.CTkButton(
            cabecera,
            text="Actualizar",
            width=100,
            height=32,
            fg_color=VERDE_CLARO,
            hover_color="#C8E8D1",
            text_color=VERDE_OSCURO,
            command=self.actualizar
        ).pack(side="right")

        self.busqueda = ctk.CTkEntry(
            panel,
            placeholder_text="Buscar por nombre o código...",
            height=38,
            fg_color=FONDO,
            border_color=BORDE,
            text_color=VERDE_OSCURO
        )
        self.busqueda.pack(
            fill="x",
            padx=18,
            pady=(0, 12)
        )

        self.busqueda.bind(
            "<KeyRelease>",
            lambda evento: self.cargar_tarjetas_productos()
        )

        self.lista_productos = ctk.CTkScrollableFrame(
            panel,
            fg_color="transparent"
        )
        self.lista_productos.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 12)
        )

        self.cargar_tarjetas_productos()

    def cargar_tarjetas_productos(self):

        for widget in self.lista_productos.winfo_children():
            widget.destroy()

        filtro = self.busqueda.get().strip().lower()

        productos = [
            producto
            for producto in self.datos_productos
            if filtro in str(producto[1]).lower()
            or filtro in str(producto[2]).lower()
        ]

        if not productos:

            ctk.CTkLabel(
                self.lista_productos,
                text="No se encontraron productos.",
                font=("Arial", 14),
                text_color=GRIS
            ).pack(pady=35)

            return

        for id_producto, codigo, nombre, stock, minimo in productos:

            stock = int(stock or 0)
            minimo = int(minimo or 0)
            bajo = stock <= minimo

            tarjeta = ctk.CTkFrame(
                self.lista_productos,
                fg_color=FONDO,
                corner_radius=12,
                border_width=1,
                border_color=BORDE
            )
            tarjeta.pack(
                fill="x",
                padx=4,
                pady=5
            )

            informacion = ctk.CTkFrame(
                tarjeta,
                fg_color="transparent"
            )
            informacion.pack(
                side="left",
                fill="both",
                expand=True,
                padx=15,
                pady=12
            )

            ctk.CTkLabel(
                informacion,
                text=str(nombre),
                font=("Arial", 15, "bold"),
                text_color=VERDE_OSCURO
            ).pack(anchor="w")

            ctk.CTkLabel(
                informacion,
                text=f"Código: {codigo}  |  Mínimo: {minimo}",
                font=("Arial", 12),
                text_color=GRIS
            ).pack(anchor="w", pady=(5, 0))

            estado = ctk.CTkFrame(
                tarjeta,
                fg_color="transparent"
            )
            estado.pack(
                side="right",
                padx=15,
                pady=10
            )

            ctk.CTkLabel(
                estado,
                text=f"{stock} unidades",
                font=("Arial", 17, "bold"),
                text_color=ROJO if bajo else VERDE
            ).pack(anchor="e")

            ctk.CTkLabel(
                estado,
                text="Stock bajo" if bajo else "Normal",
                font=("Arial", 12, "bold"),
                text_color=ROJO if bajo else VERDE
            ).pack(anchor="e", pady=(4, 0))

    # ==========================================
    # VISTA 2: MOVIMIENTOS
    # ==========================================

    def mostrar_movimientos(self):

        panel = self.crear_panel("Últimos movimientos")

        ctk.CTkLabel(
            panel,
            text="Historial de entradas y salidas de mercadería.",
            font=("Arial", 12),
            text_color=GRIS
        ).pack(
            anchor="w",
            padx=18,
            pady=(0, 12)
        )

        lista = ctk.CTkScrollableFrame(
            panel,
            fg_color="transparent"
        )
        lista.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 12)
        )

        if not self.datos_movimientos:

            ctk.CTkLabel(
                lista,
                text="Todavía no hay movimientos registrados.",
                font=("Arial", 14),
                text_color=GRIS
            ).pack(pady=35)

            return

        for fecha, producto, tipo, cantidad, motivo in self.datos_movimientos:

            entrada = tipo == "Entrada"

            tarjeta = ctk.CTkFrame(
                lista,
                fg_color=FONDO,
                corner_radius=12,
                border_width=1,
                border_color=BORDE
            )
            tarjeta.pack(
                fill="x",
                padx=4,
                pady=5
            )

            icono = ctk.CTkLabel(
                tarjeta,
                text="↓" if entrada else "↑",
                width=43,
                height=43,
                corner_radius=10,
                fg_color=VERDE_CLARO if entrada else ROJO_CLARO,
                text_color=VERDE if entrada else ROJO,
                font=("Arial", 22, "bold")
            )
            icono.pack(
                side="left",
                padx=(12, 10),
                pady=12
            )

            detalles = ctk.CTkFrame(
                tarjeta,
                fg_color="transparent"
            )
            detalles.pack(
                side="left",
                fill="both",
                expand=True,
                pady=10
            )

            ctk.CTkLabel(
                detalles,
                text=str(producto),
                font=("Arial", 14, "bold"),
                text_color=VERDE_OSCURO
            ).pack(anchor="w")

            ctk.CTkLabel(
                detalles,
                text=f"{tipo}  |  {motivo}",
                font=("Arial", 12),
                text_color=GRIS,
                wraplength=400,
                justify="left"
            ).pack(anchor="w", pady=3)

            ctk.CTkLabel(
                detalles,
                text=str(fecha),
                font=("Arial", 11),
                text_color=GRIS
            ).pack(anchor="w")

            ctk.CTkLabel(
                tarjeta,
                text=f"{'+' if entrada else '-'}{cantidad}",
                font=("Arial", 18, "bold"),
                text_color=VERDE if entrada else ROJO
            ).pack(
                side="right",
                padx=18
            )

    # ==========================================
    # VISTA 3: REGISTRAR MOVIMIENTO
    # ==========================================

    def mostrar_registrar(self):

        panel = self.crear_panel("Registrar movimiento")

        ctk.CTkLabel(
            panel,
            text="Registrá ingresos o salidas de mercadería.",
            font=("Arial", 12),
            text_color=GRIS
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 18)
        )

        formulario = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        formulario.pack(
            fill="x",
            padx=20
        )

        formulario.grid_columnconfigure(
            (0, 1),
            weight=1
        )

        # Producto
        self.crear_etiqueta(
            formulario,
            "Producto",
            0,
            0
        )

        opciones = list(self.productos.keys())

        self.selector = ctk.CTkComboBox(
            formulario,
            values=opciones if opciones else ["Sin productos"],
            state="readonly",
            height=40,
            fg_color=BLANCO,
            border_color=BORDE,
            button_color=VERDE,
            button_hover_color=VERDE_HOVER,
            text_color=VERDE_OSCURO
        )
        self.selector.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=6,
            pady=(0, 16)
        )

        self.selector.set(
            opciones[0] if opciones else "Sin productos"
        )

        # Tipo
        self.crear_etiqueta(
            formulario,
            "Tipo de movimiento",
            0,
            1
        )

        self.tipo = ctk.CTkComboBox(
            formulario,
            values=["Entrada", "Salida"],
            state="readonly",
            height=40,
            fg_color=BLANCO,
            border_color=BORDE,
            button_color=VERDE,
            button_hover_color=VERDE_HOVER,
            text_color=VERDE_OSCURO
        )
        self.tipo.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=6,
            pady=(0, 16)
        )
        self.tipo.set("Entrada")

        # Cantidad
        self.crear_etiqueta(
            formulario,
            "Cantidad",
            2,
            0
        )

        self.cantidad = ctk.CTkEntry(
            formulario,
            placeholder_text="Ejemplo: 10",
            height=40,
            fg_color=BLANCO,
            border_color=BORDE,
            text_color=VERDE_OSCURO
        )
        self.cantidad.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=6,
            pady=(0, 16)
        )

        # Motivo
        self.crear_etiqueta(
            formulario,
            "Motivo",
            2,
            1
        )

        self.motivo = ctk.CTkEntry(
            formulario,
            placeholder_text="Ejemplo: Reposición de mercadería",
            height=40,
            fg_color=BLANCO,
            border_color=BORDE,
            text_color=VERDE_OSCURO
        )
        self.motivo.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=6,
            pady=(0, 16)
        )

        ctk.CTkButton(
            panel,
            text="Registrar movimiento",
            height=44,
            corner_radius=10,
            fg_color=VERDE,
            hover_color=VERDE_HOVER,
            font=("Arial", 14, "bold"),
            command=self.registrar_movimiento
        ).pack(
            fill="x",
            padx=26,
            pady=(10, 20)
        )

    def crear_etiqueta(self, padre, texto, fila, columna):

        ctk.CTkLabel(
            padre,
            text=texto,
            font=("Arial", 13, "bold"),
            text_color=VERDE_OSCURO
        ).grid(
            row=fila,
            column=columna,
            sticky="w",
            padx=6,
            pady=(0, 5)
        )

    # ==========================================
    # PANEL BLANCO REUTILIZABLE
    # ==========================================

    def crear_panel(self, titulo):

        panel = ctk.CTkFrame(
            self.area_vistas,
            fg_color=BLANCO,
            corner_radius=15,
            border_width=1,
            border_color=BORDE
        )
        panel.pack(
            fill="both",
            expand=True
        )

        ctk.CTkLabel(
            panel,
            text=titulo,
            font=("Arial", 19, "bold"),
            text_color=VERDE_OSCURO
        ).pack(
            anchor="w",
            padx=18,
            pady=(18, 8)
        )

        return panel

    # ==========================================
    # CARGAR DATOS DE SQLITE
    # ==========================================

    def actualizar(self):

        try:
            conexion = conectar()

            try:
                productos = conexion.execute("""
                    SELECT
                        id,
                        codigo,
                        nombre,
                        stock,
                        stock_minimo
                    FROM productos
                    ORDER BY nombre
                """).fetchall()

                movimientos = conexion.execute("""
                    SELECT
                        m.fecha,
                        p.nombre,
                        m.tipo,
                        m.cantidad,
                        m.motivo
                    FROM movimientos_inventario m
                    JOIN productos p
                        ON p.id = m.producto_id
                    ORDER BY m.id DESC
                    LIMIT 50
                """).fetchall()

            finally:
                conexion.close()

        except sqlite3.Error as error:
            messagebox.showerror(
                "Error de base de datos",
                str(error)
            )
            return

        self.datos_productos = productos
        self.datos_movimientos = movimientos

        self.productos = {
            f"{codigo} - {nombre}": id_producto
            for id_producto, codigo, nombre, stock, minimo
            in productos
        }

        total = len(productos)

        bajos = sum(
            1
            for _, _, _, stock, minimo in productos
            if (stock or 0) <= (minimo or 0)
        )

        normales = total - bajos

        self.valor_productos.configure(text=str(total))
        self.valor_normales.configure(text=str(normales))
        self.valor_bajos.configure(text=str(bajos))

        self.mostrar_vista(self.vista_actual)

    # ==========================================
    # GUARDAR ENTRADAS Y SALIDAS
    # ==========================================

    def registrar_movimiento(self):

        producto = self.selector.get()
        tipo = self.tipo.get()
        motivo = self.motivo.get().strip()

        if producto not in self.productos:
            messagebox.showwarning(
                "Atención",
                "Seleccioná un producto válido."
            )
            return

        if tipo not in ("Entrada", "Salida"):
            messagebox.showwarning(
                "Atención",
                "Seleccioná un tipo de movimiento válido."
            )
            return

        try:
            cantidad = int(self.cantidad.get())

            if cantidad <= 0:
                raise ValueError

        except ValueError:
            messagebox.showerror(
                "Cantidad incorrecta",
                "Ingresá una cantidad entera mayor a cero."
            )
            return

        if not motivo:
            messagebox.showwarning(
                "Atención",
                "Ingresá el motivo del movimiento."
            )
            return

        producto_id = self.productos[producto]
        cambio = cantidad if tipo == "Entrada" else -cantidad

        try:
            conexion = conectar()

            try:
                with conexion:

                    cursor = conexion.execute("""
                        UPDATE productos
                        SET stock = stock + ?
                        WHERE id = ?
                          AND stock + ? >= 0
                    """, (
                        cambio,
                        producto_id,
                        cambio
                    ))

                    if cursor.rowcount != 1:
                        raise ValueError(
                            "Stock insuficiente o producto inexistente."
                        )

                    conexion.execute("""
                        INSERT INTO movimientos_inventario
                        (
                            producto_id,
                            tipo,
                            cantidad,
                            motivo
                        )
                        VALUES (?, ?, ?, ?)
                    """, (
                        producto_id,
                        tipo,
                        cantidad,
                        motivo
                    ))

            finally:
                conexion.close()

        except (sqlite3.Error, ValueError) as error:
            messagebox.showerror(
                "Error",
                str(error)
            )
            return

        messagebox.showinfo(
            "Correcto",
            "Movimiento registrado correctamente."
        )

        self.actualizar()
