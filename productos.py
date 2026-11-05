
import customtkinter as ctk
from tkinter import ttk, messagebox
from supabase_config import supabase

# COLORES
VERDE_OSCURO = "#18392B"
VERDE = "#166534"
FONDO = "#F4F8F5"
BLANCO = "#FFFFFF"
GRIS = "#64756B"
ROJO = "#B91C1C"


class ProductosFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=FONDO)

        self.producto_id = None
        self.categorias = {}
        self.productos = []

        # ENCABEZADO
        encabezado = ctk.CTkFrame(self, fg_color="transparent")
        encabezado.pack(fill="x", padx=22, pady=(16, 8))

        ctk.CTkLabel(
            encabezado,
            text="Gestión de productos",
            font=("Arial", 25, "bold"),
            text_color=VERDE_OSCURO
        ).pack(anchor="w")

        ctk.CTkLabel(
            encabezado,
            text="Registrá, buscá y administrá la mercadería.",
            font=("Arial", 12),
            text_color=GRIS
        ).pack(anchor="w", pady=(3, 0))

        # PESTAÑAS
        self.pestanas = ctk.CTkTabview(
            self,
            fg_color=BLANCO,
            segmented_button_selected_color=VERDE,
            segmented_button_selected_hover_color=VERDE_OSCURO
        )
        self.pestanas.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=(0, 16)
        )

        self.pestanas.add("Registrar producto")
        self.pestanas.add("Lista de productos")

        self.crear_formulario()
        self.crear_listado()

        self.cargar_categorias()
        self.cargar_productos()

    # ----------------------------------------
    # CREAR CAMPO
    # ----------------------------------------

    def crear_campo(self, padre, texto, fila, columna):
        contenedor = ctk.CTkFrame(
            padre,
            fg_color="transparent"
        )
        contenedor.grid(
            row=fila,
            column=columna,
            sticky="ew",
            padx=8,
            pady=7
        )

        ctk.CTkLabel(
            contenedor,
            text=texto,
            text_color=VERDE_OSCURO,
            font=("Arial", 12, "bold")
        ).pack(anchor="w", pady=(0, 4))

        entrada = ctk.CTkEntry(
            contenedor,
            height=37,
            border_color="#D7E3DA"
        )
        entrada.pack(fill="x")

        return entrada

    # ----------------------------------------
    # FORMULARIO
    # ----------------------------------------

    def crear_formulario(self):
        tab = self.pestanas.tab("Registrar producto")

        contenido = ctk.CTkFrame(
            tab,
            fg_color="transparent"
        )
        contenido.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=8
        )

        self.titulo_formulario = ctk.CTkLabel(
            contenido,
            text="Registrar nuevo producto",
            font=("Arial", 18, "bold"),
            text_color=VERDE_OSCURO
        )
        self.titulo_formulario.pack(
            anchor="w",
            padx=8,
            pady=(4, 12)
        )

        formulario = ctk.CTkFrame(
            contenido,
            fg_color="transparent"
        )
        formulario.pack(fill="x")

        formulario.grid_columnconfigure(0, weight=1)
        formulario.grid_columnconfigure(1, weight=1)

        # FILA 1
        self.codigo = self.crear_campo(
            formulario, "Código del producto", 0, 0
        )

        self.nombre = self.crear_campo(
            formulario, "Nombre del producto", 0, 1
        )

        # FILA 2 - CATEGORÍA
        contenedor_categoria = ctk.CTkFrame(
            formulario,
            fg_color="transparent"
        )
        contenedor_categoria.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=8,
            pady=7
        )

        ctk.CTkLabel(
            contenedor_categoria,
            text="Categoría",
            font=("Arial", 12, "bold"),
            text_color=VERDE_OSCURO
        ).pack(anchor="w", pady=(0, 4))

        self.categoria = ctk.CTkComboBox(
            contenedor_categoria,
            values=["Cargando categorías..."],
            state="readonly",
            height=37
        )
        self.categoria.pack(fill="x")
        self.categoria.set("Cargando categorías...")

        self.precio_venta = self.crear_campo(
            formulario, "Precio de venta ($)", 1, 1
        )

        # FILA 3
        self.precio_compra = self.crear_campo(
            formulario, "Precio de compra ($)", 2, 0
        )

        self.stock = self.crear_campo(
            formulario, "Cantidad en stock", 2, 1
        )

        # FILA 4
        self.stock_minimo = self.crear_campo(
            formulario, "Stock mínimo", 3, 0
        )

        self.stock.insert(0, "0")
        self.stock_minimo.insert(0, "5")

        # BOTONES
        botones = ctk.CTkFrame(
            contenido,
            fg_color="transparent"
        )
        botones.pack(
            fill="x",
            padx=8,
            pady=(20, 8)
        )

        self.boton_guardar = ctk.CTkButton(
            botones,
            text="Guardar producto",
            fg_color=VERDE,
            hover_color=VERDE_OSCURO,
            height=42,
            width=180,
            font=("Arial", 13, "bold"),
            command=self.guardar_producto
        )
        self.boton_guardar.pack(
            side="left",
            padx=(0, 10)
        )

        ctk.CTkButton(
            botones,
            text="Limpiar",
            fg_color=GRIS,
            hover_color="#4B5B51",
            height=42,
            width=110,
            command=self.limpiar
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            botones,
            text="Actualizar categorías",
            fg_color=VERDE_OSCURO,
            hover_color=VERDE,
            height=42,
            width=160,
            command=self.cargar_categorias
        ).pack(side="left")

    # ----------------------------------------
    # LISTA DE PRODUCTOS
    # ----------------------------------------

    def crear_listado(self):
        tab = self.pestanas.tab("Lista de productos")

        barra = ctk.CTkFrame(
            tab,
            fg_color="transparent"
        )
        barra.pack(fill="x", padx=10, pady=10)

        self.buscar = ctk.CTkEntry(
            barra,
            placeholder_text="Buscar por nombre o código...",
            height=38
        )
        self.buscar.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        self.buscar.bind(
            "<KeyRelease>",
            lambda evento: self.filtrar()
        )

        ctk.CTkButton(
            barra,
            text="Actualizar lista",
            width=120,
            fg_color=VERDE,
            hover_color=VERDE_OSCURO,
            command=self.cargar_productos
        ).pack(side="right")

        # ESTILO DE TABLA
        estilo = ttk.Style()
        estilo.configure(
            "Productos.Treeview",
            rowheight=31,
            font=("Arial", 10)
        )
        estilo.configure(
            "Productos.Treeview.Heading",
            font=("Arial", 10, "bold")
        )

        contenedor = ctk.CTkFrame(
            tab,
            fg_color=BLANCO
        )
        contenedor.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        columnas = (
            "id",
            "codigo",
            "nombre",
            "categoria",
            "precio",
            "stock"
        )

        self.tabla = ttk.Treeview(
            contenedor,
            columns=columnas,
            show="headings",
            selectmode="browse",
            style="Productos.Treeview"
        )

        encabezados = {
            "id": "ID",
            "codigo": "Código",
            "nombre": "Producto",
            "categoria": "Categoría",
            "precio": "Precio venta",
            "stock": "Stock"
        }

        for columna in columnas:
            self.tabla.heading(
                columna,
                text=encabezados[columna]
            )
            self.tabla.column(
                columna,
                width=145 if columna == "nombre" else 100,
                anchor="center"
            )

        self.tabla.column("id", width=50)

        self.tabla.pack(
            side="left",
            fill="both",
            expand=True
        )

        scroll = ttk.Scrollbar(
            contenedor,
            orient="vertical",
            command=self.tabla.yview
        )
        scroll.pack(side="right", fill="y")

        self.tabla.configure(
            yscrollcommand=scroll.set
        )

        # DOBLE CLIC PARA EDITAR
        self.tabla.bind(
            "<Double-1>",
            lambda evento: self.editar_producto()
        )

        acciones = ctk.CTkFrame(
            tab,
            fg_color="transparent"
        )
        acciones.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            acciones,
            text="Editar seleccionado",
            fg_color=VERDE,
            hover_color=VERDE_OSCURO,
            height=38,
            command=self.editar_producto
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            acciones,
            text="Eliminar seleccionado",
            fg_color=ROJO,
            hover_color="#991B1B",
            height=38,
            command=self.eliminar_producto
        ).pack(side="left")

    # ----------------------------------------
    # CARGAR CATEGORÍAS DESDE SUPABASE
    # ----------------------------------------

    def cargar_categorias(self):
        try:
            respuesta = (
                supabase.table("categorias")
                .select("id,nombre")
                .order("nombre")
                .execute()
            )

            self.categorias = {
                fila["nombre"]: fila["id"]
                for fila in (respuesta.data or [])
            }

            nombres = list(self.categorias.keys())

            if nombres:
                self.categoria.configure(
                    state="normal",
                    values=nombres
                )
                self.categoria.set(nombres[0])
                self.categoria.configure(
                    state="readonly"
                )
            else:
                self.categoria.configure(
                    state="normal",
                    values=["Sin categorías"]
                )
                self.categoria.set("Sin categorías")
                self.categoria.configure(
                    state="readonly"
                )

        except Exception as error:
            print("ERROR AL CARGAR CATEGORÍAS:", error)
            self.categorias = {}

            self.categoria.configure(
                state="normal",
                values=["Error al cargar"]
            )
            self.categoria.set("Error al cargar")
            self.categoria.configure(
                state="readonly"
            )

            messagebox.showerror(
                "Error de categorías",
                str(error)
            )

    # ----------------------------------------
    # CARGAR PRODUCTOS
    # ----------------------------------------

    def cargar_productos(self):
        try:
            respuesta = (
                supabase.table("productos")
                .select("*")
                .order("id", desc=True)
                .execute()
            )

            self.productos = respuesta.data or []
            self.filtrar()

        except Exception as error:
            print("ERROR AL CARGAR PRODUCTOS:", error)
            messagebox.showerror(
                "Error al cargar productos",
                str(error)
            )

    # ----------------------------------------
    # BUSCAR PRODUCTOS
    # ----------------------------------------

    def filtrar(self):
        texto = self.buscar.get().lower().strip()

        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        categorias_por_id = {
            identificador: nombre
            for nombre, identificador in self.categorias.items()
        }

        for producto in self.productos:
            codigo = str(producto.get("codigo") or "")
            nombre = str(producto.get("nombre") or "")

            if texto not in (codigo + " " + nombre).lower():
                continue

            precio = float(
                producto.get("precio_venta") or 0
            )

            self.tabla.insert(
                "",
                "end",
                values=(
                    producto["id"],
                    codigo,
                    nombre,
                    categorias_por_id.get(
                        producto.get("categoria_id"),
                        "Sin categoría"
                    ),
                    f"$ {precio:,.2f}",
                    producto.get("stock", 0)
                )
            )

    # ----------------------------------------
    # GUARDAR O ACTUALIZAR PRODUCTO
    # ----------------------------------------

    def guardar_producto(self):
        try:
            codigo = self.codigo.get().strip()
            nombre = self.nombre.get().strip()
            categoria = self.categoria.get()

            if not codigo or not nombre:
                messagebox.showwarning(
                    "Datos incompletos",
                    "Ingresá el código y el nombre."
                )
                return

            if categoria not in self.categorias:
                messagebox.showwarning(
                    "Categoría",
                    "Seleccioná una categoría válida."
                )
                return

            compra = float(
                self.precio_compra.get().replace(",", ".")
            )
            venta = float(
                self.precio_venta.get().replace(",", ".")
            )
            stock = int(self.stock.get())
            minimo = int(self.stock_minimo.get())

            if min(compra, venta, stock, minimo) < 0:
                raise ValueError("Valores negativos")

            datos = {
                "codigo": codigo,
                "nombre": nombre,
                "categoria_id": self.categorias[categoria],
                "precio_compra": compra,
                "precio_venta": venta,
                "stock": stock,
                "stock_minimo": minimo
            }

            if self.producto_id is None:
                (
                    supabase.table("productos")
                    .insert(datos)
                    .execute()
                )
                mensaje = "Producto registrado correctamente."
            else:
                (
                    supabase.table("productos")
                    .update(datos)
                    .eq("id", self.producto_id)
                    .execute()
                )
                mensaje = "Producto actualizado correctamente."

            messagebox.showinfo("Éxito", mensaje)

            self.limpiar()
            self.cargar_productos()
            self.pestanas.set("Lista de productos")

        except ValueError:
            messagebox.showerror(
                "Datos incorrectos",
                "Revisá precios y cantidades. Usá números válidos."
            )

        except Exception as error:
            print("ERROR AL GUARDAR:", error)
            messagebox.showerror(
                "Error al guardar",
                str(error)
            )

    # ----------------------------------------
    # PRODUCTO SELECCIONADO
    # ----------------------------------------

    def producto_seleccionado(self):
        seleccion = self.tabla.selection()

        if not seleccion:
            messagebox.showwarning(
                "Seleccionar producto",
                "Primero seleccioná un producto de la lista."
            )
            return None

        producto_id = int(
            self.tabla.item(
                seleccion[0], "values"
            )[0]
        )

        return next(
            (
                producto
                for producto in self.productos
                if producto["id"] == producto_id
            ),
            None
        )

    # ----------------------------------------
    # EDITAR PRODUCTO
    # ----------------------------------------

    def editar_producto(self):
        producto = self.producto_seleccionado()

        if not producto:
            return

        self.limpiar()
        self.producto_id = producto["id"]

        campos = [
            (self.codigo, producto.get("codigo") or ""),
            (self.nombre, producto.get("nombre") or ""),
            (self.precio_compra, producto.get("precio_compra") or 0),
            (self.precio_venta, producto.get("precio_venta") or 0),
            (self.stock, producto.get("stock") or 0),
            (self.stock_minimo, producto.get("stock_minimo") or 0)
        ]

        for entrada, valor in campos:
            entrada.delete(0, "end")
            entrada.insert(0, str(valor))

        for nombre, identificador in self.categorias.items():
            if identificador == producto.get("categoria_id"):
                self.categoria.configure(state="normal")
                self.categoria.set(nombre)
                self.categoria.configure(state="readonly")
                break

        self.titulo_formulario.configure(
            text="Editar producto"
        )
        self.boton_guardar.configure(
            text="Guardar cambios"
        )

        self.pestanas.set("Registrar producto")

    # ----------------------------------------
    # ELIMINAR PRODUCTO
    # ----------------------------------------

    def eliminar_producto(self):
        producto = self.producto_seleccionado()

        if not producto:
            return

        confirmar = messagebox.askyesno(
            "Eliminar producto",
            f"¿Querés eliminar '{producto['nombre']}'?"
        )

        if not confirmar:
            return

        try:
            (
                supabase.table("productos")
                .delete()
                .eq("id", producto["id"])
                .execute()
            )

            self.cargar_productos()

            messagebox.showinfo(
                "Éxito",
                "Producto eliminado correctamente."
            )

        except Exception as error:
            print("ERROR AL ELIMINAR:", error)
            messagebox.showerror(
                "Error al eliminar",
                str(error)
            )

    # ----------------------------------------
    # LIMPIAR FORMULARIO
    # ----------------------------------------

    def limpiar(self):
        self.producto_id = None

        for entrada in (
            self.codigo,
            self.nombre,
            self.precio_compra,
            self.precio_venta,
            self.stock,
            self.stock_minimo
        ):
            entrada.delete(0, "end")

        self.stock.insert(0, "0")
        self.stock_minimo.insert(0, "5")

        if self.categorias:
            primer_nombre = next(iter(self.categorias))
            self.categoria.configure(state="normal")
            self.categoria.set(primer_nombre)
            self.categoria.configure(state="readonly")

        self.titulo_formulario.configure(
            text="Registrar nuevo producto"
        )
        self.boton_guardar.configure(
            text="Guardar producto"
        )
