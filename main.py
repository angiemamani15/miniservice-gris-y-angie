
import customtkinter as ctk
from tkinter import messagebox
from datetime import date

from database import conectar, crear_base_datos
from login import LoginFrame
from supabase_config import supabase

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

BLANCO = "#FFFFFF"
FONDO = "#F4F8F5"
VERDE_OSCURO = "#18392B"
VERDE_PRINCIPAL = "#166534"
VERDE_HOVER = "#15803D"
VERDE_CLARO = "#DCEFE2"
VERDE_SUAVE = "#EAF5ED"
TEXTO = "#18392B"
GRIS = "#64756B"
BORDE = "#DFEAE2"
ROJO = "#B91C1C"

crear_base_datos()

ROL_ACTUAL = None
pantalla_login = None
seccion_actual = "Inicio"
menu_compacto = False
ajuste_pendiente = None

PERMISOS = {
    "administradora": {
        "Inicio", "Productos", "Inventario",
        "Ventas", "Proveedores", "Caja", "Reportes"
    },
    "cajera": {
        "Inicio", "Ventas", "Caja"
    }
}

SECCIONES = [
    ("Inicio", "⌂"),
    ("Productos", "▣"),
    ("Inventario", "▤"),
    ("Ventas", "◉"),
    ("Proveedores", "♧"),
    ("Caja", "$"),
    ("Reportes", "▥")
]

# ==========================================
# VENTANA PRINCIPAL
# ==========================================

ventana = ctk.CTk()
ventana.title("MiniService Gris y Angie | Sistema de Gestión")
ventana.geometry("1200x720")
ventana.minsize(600, 450)
ventana.configure(fg_color=FONDO)

# ==========================================
# MENÚ LATERAL
# ==========================================

menu = ctk.CTkFrame(
    ventana,
    width=230,
    corner_radius=0,
    fg_color=VERDE_OSCURO
)
menu.pack_propagate(False)

logo = ctk.CTkFrame(
    menu,
    width=65,
    height=65,
    corner_radius=15,
    fg_color="#285943"
)
logo.pack(pady=(20, 10))
logo.pack_propagate(False)

ctk.CTkLabel(
    logo,
    text="G&A",
    font=("Arial", 21, "bold"),
    text_color=BLANCO
).place(relx=0.5, rely=0.5, anchor="center")

titulo_menu = ctk.CTkLabel(
    menu,
    text="MiniService\nGris y Angie",
    font=("Arial", 19, "bold"),
    text_color=BLANCO,
    justify="center"
)
titulo_menu.pack(pady=(5, 15))

subtitulo_menu = ctk.CTkLabel(
    menu,
    text="MENÚ PRINCIPAL",
    font=("Arial", 11, "bold"),
    text_color="#B8CFC0"
)
subtitulo_menu.pack(anchor="w", padx=23, pady=(0, 10))

contenedor_botones = ctk.CTkScrollableFrame(
    menu,
    fg_color="transparent"
)
contenedor_botones.pack(
    fill="both",
    expand=True,
    padx=10
)

contenido = ctk.CTkFrame(
    ventana,
    fg_color=FONDO,
    corner_radius=0
)

botones_menu = {}

# ==========================================
# FUNCIONES GENERALES
# ==========================================

def formato_dinero(valor):
    return (
        f"$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def obtener_estadisticas():
    conexion = conectar()

    try:
        cursor = conexion.cursor()

        cursor.execute("SELECT COUNT(*) FROM productos")
        productos = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM productos
            WHERE stock <= stock_minimo
        """)
        stock_bajo = cursor.fetchone()[0]

        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(total), 0)
            FROM ventas
            WHERE DATE(fecha, 'localtime') = ?
        """, (date.today().isoformat(),))

        ventas, ingresos = cursor.fetchone()

        return productos, stock_bajo, ventas, ingresos

    finally:
        conexion.close()


# ==========================================
# TARJETAS
# ==========================================

def crear_tarjeta(padre, titulo, valor, simbolo):
    tarjeta = ctk.CTkFrame(
        padre,
        fg_color=BLANCO,
        corner_radius=15,
        border_width=1,
        border_color=BORDE
    )

    encabezado = ctk.CTkFrame(
        tarjeta,
        fg_color="transparent"
    )
    encabezado.pack(
        fill="x",
        padx=15,
        pady=(15, 5)
    )

    ctk.CTkLabel(
        encabezado,
        text=titulo,
        font=("Arial", 12),
        text_color=GRIS,
        wraplength=170
    ).pack(side="left", anchor="w")

    ctk.CTkLabel(
        encabezado,
        text=simbolo,
        font=("Arial", 19, "bold"),
        text_color=VERDE_PRINCIPAL
    ).pack(side="right")

    ctk.CTkLabel(
        tarjeta,
        text=str(valor),
        font=("Arial", 24, "bold"),
        text_color=TEXTO
    ).pack(
        anchor="w",
        padx=15,
        pady=(0, 15)
    )

    return tarjeta


# ==========================================
# INICIO RESPONSIVE
# ==========================================

def mostrar_inicio():
    panel = ctk.CTkScrollableFrame(
        contenido,
        fg_color="transparent"
    )
    panel.pack(
        fill="both",
        expand=True,
        padx=15,
        pady=12
    )

    ctk.CTkLabel(
        panel,
        text=(
            "Panel de administración"
            if ROL_ACTUAL == "administradora"
            else "Panel de caja"
        ),
        font=("Arial", 26, "bold"),
        text_color=TEXTO
    ).pack(anchor="w", pady=(5, 5))

    ctk.CTkLabel(
        panel,
        text="Bienvenida a MiniService Gris y Angie",
        font=("Arial", 13),
        text_color=GRIS
    ).pack(anchor="w", pady=(0, 8))

    ctk.CTkLabel(
        panel,
        text=f"Sesión iniciada como: {ROL_ACTUAL.capitalize()}",
        font=("Arial", 12, "bold"),
        text_color=VERDE_PRINCIPAL
    ).pack(anchor="w", pady=(0, 15))

    try:
        productos, stock_bajo, ventas, ingresos = (
            obtener_estadisticas()
        )
    except Exception as error:
        print("Error al cargar estadísticas:", error)
        productos = 0
        stock_bajo = 0
        ventas = 0
        ingresos = 0

    estadisticas = ctk.CTkFrame(
        panel,
        fg_color="transparent"
    )
    estadisticas.pack(fill="x", pady=5)

    datos = [
        ("Productos registrados", productos, "▣"),
        ("Ventas de hoy", ventas, "◉"),
        ("Ingresos del día", formato_dinero(ingresos), "$"),
        ("Productos con stock bajo", stock_bajo, "!")
    ]

    tarjetas = []

    for titulo, valor, simbolo in datos:
        tarjeta = crear_tarjeta(
            estadisticas, titulo, valor, simbolo
        )
        tarjetas.append(tarjeta)

    accesos = ctk.CTkFrame(
        panel,
        fg_color=BLANCO,
        corner_radius=15,
        border_width=1,
        border_color=BORDE
    )
    accesos.pack(fill="x", pady=(20, 10))

    ctk.CTkLabel(
        accesos,
        text="Accesos rápidos",
        font=("Arial", 19, "bold"),
        text_color=TEXTO
    ).pack(anchor="w", padx=15, pady=(15, 10))

    accesos_botones = ctk.CTkFrame(
        accesos,
        fg_color="transparent"
    )
    accesos_botones.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    if ROL_ACTUAL == "administradora":
        opciones = [
            ("Nueva venta", "Ventas"),
            ("Productos", "Productos"),
            ("Inventario", "Inventario")
        ]
    else:
        opciones = [
            ("Nueva venta", "Ventas"),
            ("Caja", "Caja")
        ]

    botones_acceso = []

    for texto, seccion in opciones:
        boton = ctk.CTkButton(
            accesos_botones,
            text=texto,
            height=42,
            fg_color=VERDE_CLARO,
            hover_color="#C8E8D1",
            text_color=VERDE_OSCURO,
            font=("Arial", 12, "bold"),
            command=lambda s=seccion: mostrar_seccion(s)
        )
        botones_acceso.append(boton)

    informacion = ctk.CTkFrame(
        panel,
        fg_color=VERDE_SUAVE,
        corner_radius=12
    )
    informacion.pack(fill="x", pady=(10, 10))

    ctk.CTkLabel(
        informacion,
        text="MiniService Gris y Angie",
        font=("Arial", 15, "bold"),
        text_color=VERDE_OSCURO
    ).pack(anchor="w", padx=15, pady=(12, 5))

    ctk.CTkLabel(
        informacion,
        text=(
            "Administrá las operaciones del negocio "
            "de forma sencilla y organizada."
        ),
        font=("Arial", 12),
        text_color=GRIS,
        wraplength=320,
        justify="left"
    ).pack(anchor="w", padx=15, pady=(0, 12))

    def reorganizar_inicio(evento=None):
        if not estadisticas.winfo_exists():
            return

        ancho = estadisticas.winfo_width()
        columnas = 2 if ancho >= 440 else 1

        for tarjeta in tarjetas:
            tarjeta.grid_forget()

        for columna in range(2):
            estadisticas.grid_columnconfigure(
                columna,
                weight=1 if columna < columnas else 0
            )

        for indice, tarjeta in enumerate(tarjetas):
            tarjeta.grid(
                row=indice // columnas,
                column=indice % columnas,
                sticky="ew",
                padx=5,
                pady=5
            )

        ancho_accesos = accesos_botones.winfo_width()
        columnas_acceso = (
            len(botones_acceso)
            if ancho_accesos >= 440
            else 1
        )

        for boton in botones_acceso:
            boton.grid_forget()

        for columna in range(len(botones_acceso)):
            accesos_botones.grid_columnconfigure(
                columna,
                weight=1 if columna < columnas_acceso else 0
            )

        for indice, boton in enumerate(botones_acceso):
            boton.grid(
                row=indice // columnas_acceso,
                column=indice % columnas_acceso,
                sticky="ew",
                padx=4,
                pady=4
            )

    estadisticas.bind("<Configure>", reorganizar_inicio)
    accesos_botones.bind("<Configure>", reorganizar_inicio)
    panel.after(100, reorganizar_inicio)


# ==========================================
# MENSAJES Y SECCIONES
# ==========================================

def mostrar_error(nombre, error):
    ctk.CTkLabel(
        contenido,
        text=f"No se pudo abrir {nombre}",
        font=("Arial", 23, "bold"),
        text_color=ROJO
    ).pack(pady=(50, 15))

    ctk.CTkLabel(
        contenido,
        text=str(error),
        font=("Arial", 13),
        text_color=GRIS,
        wraplength=350
    ).pack()


def mostrar_pendiente(nombre):
    ctk.CTkLabel(
        contenido,
        text=nombre,
        font=("Arial", 26, "bold"),
        text_color=TEXTO
    ).pack(pady=(50, 15))

    ctk.CTkLabel(
        contenido,
        text="Esta sección se encuentra en desarrollo.",
        font=("Arial", 13),
        text_color=GRIS
    ).pack()


# ==========================================
# NAVEGACIÓN
# ==========================================

def mostrar_seccion(nombre):
    global seccion_actual

    if ROL_ACTUAL is None:
        return

    if nombre not in PERMISOS.get(ROL_ACTUAL, set()):
        messagebox.showwarning(
            "Acceso restringido",
            "No tenés permiso para acceder a esta sección."
        )
        return

    seccion_actual = nombre

    for widget in contenido.winfo_children():
        widget.destroy()

    for seccion, boton in botones_menu.items():
        boton.configure(
            fg_color=(
                VERDE_PRINCIPAL
                if seccion == nombre
                else "transparent"
            ),
            text_color=BLANCO
        )

    if nombre == "Inicio":
        mostrar_inicio()
        return

    try:
        if nombre == "Productos":
            from productos import ProductosFrame
            modulo = ProductosFrame(contenido)

        elif nombre == "Inventario":
            from inventario import InventarioFrame
            modulo = InventarioFrame(contenido)

        elif nombre == "Ventas":
            from ventas import VentasFrame
            modulo = VentasFrame(contenido)

        else:
            mostrar_pendiente(nombre)
            return

        modulo.pack(fill="both", expand=True)

    except Exception as error:
        mostrar_error(nombre, error)


# ==========================================
# BOTONES DEL MENÚ
# ==========================================

for nombre, icono in SECCIONES:
    boton = ctk.CTkButton(
        contenedor_botones,
        text=f"  {icono}    {nombre}",
        height=44,
        corner_radius=10,
        fg_color="transparent",
        hover_color="#285943",
        text_color=BLANCO,
        anchor="w",
        font=("Arial", 13),
        command=lambda s=nombre: mostrar_seccion(s)
    )
    botones_menu[nombre] = boton


# ==========================================
# PIE DEL MENÚ
# ==========================================

pie_menu = ctk.CTkFrame(
    menu,
    fg_color="transparent"
)
pie_menu.pack(fill="x", padx=10, pady=(5, 10))

etiqueta_rol = ctk.CTkLabel(
    pie_menu,
    text="",
    font=("Arial", 12, "bold"),
    text_color="#B8CFC0"
)
etiqueta_rol.pack(pady=(0, 8))

boton_cerrar = ctk.CTkButton(
    pie_menu,
    text="Cerrar sesión",
    height=38,
    fg_color="#285943",
    hover_color="#366D50",
    text_color=BLANCO,
    command=lambda: cerrar_sesion()
)
boton_cerrar.pack(fill="x")

etiqueta_version = ctk.CTkLabel(
    pie_menu,
    text="Gris y Angie | Versión 1.0",
    font=("Arial", 10),
    text_color="#B8CFC0"
)
etiqueta_version.pack(pady=(10, 0))


# ==========================================
# ADAPTACIÓN DEL MENÚ
# ==========================================

def adaptar_menu(evento=None):
    global menu_compacto, ajuste_pendiente

    if ROL_ACTUAL is None:
        return

    ancho = ventana.winfo_width()
    compacto = ancho < 950

    if compacto == menu_compacto:
        return

    menu_compacto = compacto

    menu.configure(width=75 if compacto else 230)

    if compacto:
        titulo_menu.pack_forget()
        subtitulo_menu.pack_forget()
        etiqueta_version.pack_forget()

        logo.configure(width=48, height=48)
        etiqueta_rol.configure(
            text="Admin" if ROL_ACTUAL == "administradora" else "Caja",
            font=("Arial", 10, "bold")
        )
        boton_cerrar.configure(text="Salir", width=55)

    else:
        titulo_menu.pack(
            after=logo,
            pady=(5, 15)
        )
        subtitulo_menu.pack(
            after=titulo_menu,
            anchor="w",
            padx=23,
            pady=(0, 10)
        )
        etiqueta_version.pack(pady=(10, 0))

        logo.configure(width=65, height=65)
        etiqueta_rol.configure(
            text=f"Rol: {ROL_ACTUAL.capitalize()}",
            font=("Arial", 12, "bold")
        )
        boton_cerrar.configure(text="Cerrar sesión")

    for nombre, icono in SECCIONES:
        boton = botones_menu[nombre]
        boton.configure(
            text=icono if compacto else f"  {icono}    {nombre}",
            anchor="center" if compacto else "w",
            font=("Arial", 17 if compacto else 13)
        )


def programar_adaptacion(evento=None):
    global ajuste_pendiente

    if ajuste_pendiente is not None:
        ventana.after_cancel(ajuste_pendiente)

    ajuste_pendiente = ventana.after(120, adaptar_menu)


ventana.bind("<Configure>", programar_adaptacion)


# ==========================================
# INICIAR SESIÓN
# ==========================================

def mostrar_login():
    global pantalla_login

    pantalla_login = LoginFrame(
        ventana,
        on_login=abrir_sistema
    )
    pantalla_login.pack(fill="both", expand=True)


def abrir_sistema(rol):
    global ROL_ACTUAL, pantalla_login

    if rol not in PERMISOS:
        messagebox.showerror(
            "Acceso denegado",
            "El usuario no tiene un rol autorizado."
        )
        return

    ROL_ACTUAL = rol

    if pantalla_login is not None:
        pantalla_login.destroy()
        pantalla_login = None

    menu.pack(side="left", fill="y")
    contenido.pack(side="left", fill="both", expand=True)

    etiqueta_rol.configure(
        text=f"Rol: {rol.capitalize()}"
    )

    for nombre, boton in botones_menu.items():
        boton.pack_forget()

        if nombre in PERMISOS[rol]:
            boton.pack(fill="x", pady=4, padx=3)

    adaptar_menu()
    mostrar_seccion("Inicio")


# ==========================================
# CERRAR SESIÓN
# ==========================================

def cerrar_sesion():
    global ROL_ACTUAL, menu_compacto

    confirmar = messagebox.askyesno(
        "Cerrar sesión",
        "¿Querés cerrar la sesión actual?"
    )

    if not confirmar:
        return

    try:
        supabase.auth.sign_out()

    except Exception as error:
        messagebox.showerror(
            "Error",
            f"No se pudo cerrar la sesión:\n{error}"
        )
        return

    ROL_ACTUAL = None
    menu_compacto = False

    for widget in contenido.winfo_children():
        widget.destroy()

    menu.pack_forget()
    contenido.pack_forget()

    mostrar_login()


# ==========================================
# INICIAR APLICACIÓN
# ==========================================

mostrar_login()
ventana.mainloop()
