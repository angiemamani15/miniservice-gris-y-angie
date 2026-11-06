"""
Categorías de productos (CRUD) - sólo administradora.

Una categoría sólo puede eliminarse si no tiene productos asociados
(lo verifica el programa y también la clave foránea en la base).
Los selectores de Productos leen las categorías desde Supabase cada vez
que se abre esa pantalla, por lo que los cambios se ven al instante.
"""

import customtkinter as ctk

from componentes import (
    Tabla, advertir, boton, campo, confirmar, ejecutar_seguro, encabezado, escribir, informar, panel,
)
from config import FONDO, FUENTE, GRIS, VERDE_OSCURO
from servicios import catalogo


class CategoriasFrame(ctk.CTkFrame):
    def __init__(self, master, app=None):
        super().__init__(master, fg_color=FONDO, corner_radius=0)
        self.app = app
        self.categorias = []
        self.categoria_id = None

        encabezado(self, "Categorías", "Organizá los productos del negocio por rubro.").pack(
            fill="x", padx=22, pady=(16, 12))

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=2, minsize=300)
        cuerpo.grid_rowconfigure(0, weight=1)

        # ---------------- Listado ----------------
        listado = panel(cuerpo, "Listado de categorías")
        listado.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.buscar = ctk.CTkEntry(listado, placeholder_text="Buscar categoría...", height=36)
        self.buscar.pack(fill="x", padx=14, pady=(0, 8))
        self.buscar.bind("<KeyRelease>", lambda _e: self.mostrar())
        self.tabla = Tabla(listado, [
            ("nombre", "Categoría", 180, "w"),
            ("descripcion", "Descripción", 260, "w"),
            ("productos", "Productos", 90, "center"),
        ], altura=14, al_seleccionar=self.seleccionar)
        self.tabla.pack(fill="both", expand=True, padx=14)
        self.resumen = ctk.CTkLabel(listado, text="", font=(FUENTE, 12), text_color=GRIS, anchor="w")
        self.resumen.pack(fill="x", padx=16, pady=8)

        # ---------------- Formulario ----------------
        formulario = panel(cuerpo)
        formulario.grid(row=0, column=1, sticky="nsew")
        self.titulo = ctk.CTkLabel(formulario, text="Nueva categoría", font=(FUENTE, 18, "bold"),
                                   text_color=VERDE_OSCURO)
        self.titulo.pack(anchor="w", padx=16, pady=(16, 10))
        c, self.nombre = campo(formulario, "Nombre", "Ej.: Panadería")
        c.pack(fill="x", padx=16, pady=4)
        c, self.descripcion = campo(formulario, "Descripción (opcional)", "Breve descripción")
        c.pack(fill="x", padx=16, pady=4)
        self.nombre.bind("<Return>", lambda _e: self.guardar())

        self.boton_guardar = boton(formulario, "Guardar categoría", self.guardar, "primario", alto=42)
        self.boton_guardar.pack(fill="x", padx=16, pady=(16, 6))
        boton(formulario, "Nueva / limpiar", self.limpiar, "secundario").pack(fill="x", padx=16, pady=6)
        self.boton_eliminar = boton(formulario, "Eliminar categoría", self.eliminar, "peligro")
        self.boton_eliminar.pack(fill="x", padx=16, pady=6)
        self.aviso = ctk.CTkLabel(
            formulario, text="Seleccioná una categoría del listado para editarla o eliminarla.\n"
                             "Sólo se pueden eliminar categorías sin productos.",
            font=(FUENTE, 11), text_color=GRIS, wraplength=260, justify="left")
        self.aviso.pack(anchor="w", padx=16, pady=(10, 16))

        self.limpiar()
        self.cargar()

    def cargar(self):
        correcto, categorias = ejecutar_seguro(catalogo.listar_categorias, con_cantidad=True)
        if correcto:
            self.categorias = categorias
            self.mostrar()

    def mostrar(self):
        texto = self.buscar.get().strip().lower()
        filas = [
            (c["id"], [c["nombre"], c.get("descripcion") or "", c["cantidad_productos"]])
            for c in self.categorias if texto in c["nombre"].lower()
        ]
        self.tabla.cargar(filas, "No hay categorías.")
        total = sum(c["cantidad_productos"] for c in self.categorias)
        self.resumen.configure(text=f"{len(self.categorias)} categorías · {total} productos asignados")

    def _seleccionada(self):
        identificador = self.tabla.seleccionado()
        return next((c for c in self.categorias if str(c["id"]) == identificador), None)

    def seleccionar(self):
        categoria = self._seleccionada()
        if not categoria:
            return
        self.categoria_id = categoria["id"]
        escribir(self.nombre, categoria["nombre"])
        escribir(self.descripcion, categoria.get("descripcion") or "")
        self.titulo.configure(text="Editar categoría")
        self.boton_guardar.configure(text="Guardar cambios")
        self.boton_eliminar.configure(state="normal")

    def limpiar(self):
        self.categoria_id = None
        escribir(self.nombre, "")
        escribir(self.descripcion, "")
        self.titulo.configure(text="Nueva categoría")
        self.boton_guardar.configure(text="Guardar categoría")
        self.boton_eliminar.configure(state="disabled")
        self.tabla.arbol.selection_remove(self.tabla.arbol.selection())

    def guardar(self):
        if self.categoria_id is None:
            correcto, _ = ejecutar_seguro(catalogo.crear_categoria, self.nombre.get(), self.descripcion.get())
            mensaje = "Categoría creada correctamente."
        else:
            correcto, _ = ejecutar_seguro(catalogo.actualizar_categoria, self.categoria_id,
                                          self.nombre.get(), self.descripcion.get())
            mensaje = "Categoría actualizada correctamente."
        if correcto:
            informar(mensaje)
            self.limpiar()
            self.cargar()

    def eliminar(self):
        categoria = self._seleccionada()
        if not categoria:
            advertir("Seleccioná una categoría del listado.")
            return
        if categoria["cantidad_productos"]:
            advertir(f"«{categoria['nombre']}» tiene {categoria['cantidad_productos']} producto(s) asociados.\n"
                     "Cambiá la categoría de esos productos antes de eliminarla.", "No se puede eliminar")
            return
        if not confirmar(f"¿Eliminar la categoría «{categoria['nombre']}»?"):
            return
        correcto, _ = ejecutar_seguro(catalogo.eliminar_categoria, categoria["id"])
        if correcto:
            informar("Categoría eliminada.")
            self.limpiar()
            self.cargar()
