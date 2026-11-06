"""
Mini Service Gris y Angie - Sistema de gestión comercial.

Punto de entrada del programa:  python main.py

Arma la ventana principal con el menú lateral fijo, muestra el login
y, según el rol del usuario, habilita las secciones permitidas. Cada
sección es una clase en su propio archivo (ventas.py, productos.py...)
que se carga recién cuando el usuario la abre.
"""

import importlib
import sys
import traceback

import customtkinter as ctk

try:
    import supabase_config  # noqa: F401  (valida el archivo .env al iniciar)
except ValueError as error_configuracion:
    import tkinter
    from tkinter import messagebox

    raiz = tkinter.Tk()
    raiz.withdraw()
    messagebox.showerror(
        "Falta la configuración",
        f"{error_configuracion}.\n\nCopiá el archivo .env.example como .env y completá "
        "SUPABASE_URL y SUPABASE_KEY (clave pública anon).",
    )
    sys.exit(1)

import sesion
from componentes import FUENTE_ICONOS, advertir, aplicar_tema, confirmar, configurar_estilos
from config import (
    BLANCO, FONDO, FUENTE, GRIS, NOMBRE_NEGOCIO, ROJO, SECCIONES, VERDE,
    VERDE_MENU, VERDE_OSCURO, VERSION,
)
from login import LoginFrame
from servicios import autenticacion

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")
aplicar_tema()

# Sección -> (archivo, clase)
MODULOS = {
    "Inicio": ("inicio", "InicioFrame"),
    "Ventas": ("ventas", "VentasFrame"),
    "Caja": ("caja", "CajaFrame"),
    "Productos": ("productos", "ProductosFrame"),
    "Categorías": ("categorias", "CategoriasFrame"),
    "Inventario": ("inventario", "InventarioFrame"),
    "Proveedores": ("proveedores", "ProveedoresFrame"),
    "Reportes": ("reportes", "ReportesFrame"),
    "Configuración": ("configuracion", "ConfiguracionFrame"),
}

ANCHO_MENU = 230
ANCHO_MENU_COMPACTO = 76


class Aplicacion(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{NOMBRE_NEGOCIO} | Sistema de Gestión")
        self.configure(fg_color=FONDO)
        self.minsize(820, 600)
        self._centrar()
        configurar_estilos()

        self.pantalla_login = None
        self.seccion_actual = None
        self.menu_compacto = None
        self.ajuste_pendiente = None
        self.botones_menu = {}

        self._crear_menu()
        self.contenido = ctk.CTkFrame(self, fg_color=FONDO, corner_radius=0)

        self.bind("<Configure>", self._programar_adaptacion)
        self.protocol("WM_DELETE_WINDOW", self.salir)
        self.mostrar_login()

    def _ancho_logico(self):
        # Con el escalado de Windows (125 %, 150 %) winfo_width() devuelve
        # píxeles reales; CustomTkinter trabaja en unidades sin escalar.
        return self._reverse_window_scaling(self.winfo_width())

    def _centrar(self):
        escala = self._get_window_scaling()
        pantalla_ancho, pantalla_alto = self.winfo_screenwidth(), self.winfo_screenheight()
        ancho = min(1366, int(pantalla_ancho / escala) - 40)
        alto = min(800, int(pantalla_alto / escala) - 90)
        x = max((pantalla_ancho - int(ancho * escala)) // 2, 0)
        y = max((pantalla_alto - int(alto * escala)) // 2 - 20, 0)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    # ------------------------------------------------------------------
    # MENÚ LATERAL
    # ------------------------------------------------------------------

    def _crear_menu(self):
        self.menu = ctk.CTkFrame(self, width=ANCHO_MENU, corner_radius=0, fg_color=VERDE_OSCURO)
        self.menu.pack_propagate(False)

        self.cabecera_menu = ctk.CTkFrame(self.menu, fg_color="transparent")
        self.cabecera_menu.pack(fill="x", padx=14, pady=(18, 10))

        self.logo = ctk.CTkFrame(self.cabecera_menu, width=50, height=50, corner_radius=14, fg_color=VERDE_MENU)
        self.logo.pack(side="left")
        self.logo.pack_propagate(False)
        ctk.CTkLabel(self.logo, text="G&A", font=(FUENTE, 17, "bold"), text_color=BLANCO).place(
            relx=0.5, rely=0.5, anchor="center")

        self.titulo_menu = ctk.CTkLabel(
            self.cabecera_menu, text="Mini Service\nGris y Angie", font=(FUENTE, 16, "bold"),
            text_color=BLANCO, justify="left")
        self.titulo_menu.pack(side="left", padx=(10, 0))

        self.subtitulo_menu = ctk.CTkLabel(
            self.menu, text="MENÚ PRINCIPAL", font=(FUENTE, 11, "bold"), text_color="#B8CFC0")
        self.subtitulo_menu.pack(anchor="w", padx=23, pady=(6, 4))

        self.contenedor_botones = ctk.CTkFrame(self.menu, fg_color="transparent")
        self.contenedor_botones.pack(fill="both", expand=True, padx=10)

        for nombre, icono in SECCIONES:
            self.botones_menu[nombre] = ctk.CTkButton(
                self.contenedor_botones, text=f"  {icono}    {nombre}", height=38, corner_radius=10,
                fg_color="transparent", hover_color=VERDE_MENU, text_color=BLANCO, anchor="w",
                font=(FUENTE, 13), command=lambda s=nombre: self.mostrar_seccion(s),
            )

        self.pie_menu = ctk.CTkFrame(self.menu, fg_color="transparent")
        self.pie_menu.pack(fill="x", padx=10, pady=(5, 12))

        self.etiqueta_usuario = ctk.CTkLabel(
            self.pie_menu, text="", font=(FUENTE, 12, "bold"), text_color=BLANCO)
        self.etiqueta_usuario.pack()
        self.etiqueta_rol = ctk.CTkLabel(
            self.pie_menu, text="", font=(FUENTE, 11), text_color="#B8CFC0")
        self.etiqueta_rol.pack(pady=(0, 8))

        self.boton_cerrar = ctk.CTkButton(
            self.pie_menu, text="Cerrar sesión", height=36, fg_color=VERDE_MENU,
            hover_color="#366D50", text_color=BLANCO, command=self.cerrar_sesion)
        self.boton_cerrar.pack(fill="x")

        self.etiqueta_version = ctk.CTkLabel(
            self.pie_menu, text=f"Gris y Angie | Versión {VERSION}", font=(FUENTE, 10),
            text_color="#B8CFC0")
        self.etiqueta_version.pack(pady=(8, 0))

    def _programar_adaptacion(self, _evento=None):
        if self.ajuste_pendiente is not None:
            self.after_cancel(self.ajuste_pendiente)
        self.ajuste_pendiente = self.after(120, self._adaptar_menu)

    def _adaptar_menu(self, forzar=False):
        """En ventanas angostas el menú muestra sólo íconos."""
        self.ajuste_pendiente = None
        usuario = sesion.actual()
        if usuario is None:
            return

        compacto = self._ancho_logico() < 1000
        if compacto == self.menu_compacto and not forzar:
            return
        self.menu_compacto = compacto

        self.menu.configure(width=ANCHO_MENU_COMPACTO if compacto else ANCHO_MENU)
        if compacto:
            self.titulo_menu.pack_forget()
            self.subtitulo_menu.pack_forget()
            self.etiqueta_version.pack_forget()
            self.etiqueta_rol.pack_forget()
            self.etiqueta_usuario.configure(text="Admin" if usuario.es_admin else "Caja",
                                            font=(FUENTE, 10, "bold"))
            self.boton_cerrar.configure(text="Salir")
        else:
            self.titulo_menu.pack(side="left", padx=(10, 0))
            self.subtitulo_menu.pack(after=self.cabecera_menu, anchor="w", padx=23, pady=(6, 4))
            self.etiqueta_usuario.configure(text=usuario.nombre, font=(FUENTE, 12, "bold"))
            self.etiqueta_rol.pack(after=self.etiqueta_usuario, pady=(0, 8))
            self.etiqueta_rol.configure(text=f"Rol: {usuario.rol_legible}")
            self.etiqueta_version.pack(pady=(8, 0))
            self.boton_cerrar.configure(text="Cerrar sesión")

        for nombre, icono in SECCIONES:
            self.botones_menu[nombre].configure(
                text=icono if compacto else f"  {icono}    {nombre}",
                anchor="center" if compacto else "w",
                font=(FUENTE_ICONOS, 18) if compacto else (FUENTE, 13),
            )

    # ------------------------------------------------------------------
    # NAVEGACIÓN
    # ------------------------------------------------------------------

    def mostrar_seccion(self, nombre):
        usuario = sesion.actual()
        if usuario is None:
            return
        if not usuario.puede(nombre):
            advertir(f"Tu rol ({usuario.rol_legible}) no tiene acceso a {nombre}.", "Acceso restringido")
            return

        self.seccion_actual = nombre
        for widget in self.contenido.winfo_children():
            widget.destroy()

        for seccion, boton in self.botones_menu.items():
            boton.configure(fg_color=VERDE if seccion == nombre else "transparent")

        archivo, clase = MODULOS[nombre]
        try:
            modulo = importlib.import_module(archivo)
            pantalla = getattr(modulo, clase)(self.contenido, self)
            pantalla.pack(fill="both", expand=True)
        except Exception as error:
            # Un error en una sección no cierra el programa.
            traceback.print_exc()
            for widget in self.contenido.winfo_children():
                widget.destroy()
            self._mostrar_error_seccion(nombre, error)

    def _mostrar_error_seccion(self, nombre, error):
        ctk.CTkLabel(self.contenido, text=f"No se pudo abrir {nombre}", font=(FUENTE, 23, "bold"),
                     text_color=ROJO).pack(pady=(60, 15))
        ctk.CTkLabel(self.contenido, text=str(error), font=(FUENTE, 13), text_color=GRIS,
                     wraplength=520).pack()
        ctk.CTkButton(self.contenido, text="Reintentar", fg_color=VERDE,
                      command=lambda: self.mostrar_seccion(nombre)).pack(pady=20)

    def refrescar(self):
        """Vuelve a abrir la sección actual (por ejemplo, tras una operación)."""
        if self.seccion_actual:
            self.mostrar_seccion(self.seccion_actual)

    # ------------------------------------------------------------------
    # SESIÓN
    # ------------------------------------------------------------------

    def mostrar_login(self):
        self.pantalla_login = LoginFrame(self, on_login=self.abrir_sistema)
        self.pantalla_login.pack(fill="both", expand=True)

    def abrir_sistema(self, usuario):
        if self.pantalla_login is not None:
            self.pantalla_login.destroy()
            self.pantalla_login = None

        self.menu.pack(side="left", fill="y")
        self.contenido.pack(side="left", fill="both", expand=True)

        for nombre, boton in self.botones_menu.items():
            boton.pack_forget()
            if usuario.puede(nombre):
                boton.pack(fill="x", pady=2, padx=3)

        self.menu_compacto = None
        self._adaptar_menu(forzar=True)
        self.mostrar_seccion("Inicio")

    def cerrar_sesion(self, preguntar=True):
        if preguntar and not confirmar("¿Querés cerrar la sesión actual?", "Cerrar sesión"):
            return
        autenticacion.cerrar_sesion()
        self.seccion_actual = None
        for widget in self.contenido.winfo_children():
            widget.destroy()
        self.menu.pack_forget()
        self.contenido.pack_forget()
        self.mostrar_login()

    def salir(self):
        # Al cerrar la ventana también se cierra la sesión en Supabase
        # (y se detiene la renovación automática del token).
        autenticacion.cerrar_sesion()
        self.destroy()


def main():
    app = Aplicacion()
    app.mainloop()


if __name__ == "__main__":
    main()
