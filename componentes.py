"""
Componentes visuales reutilizables.

Todas las pantallas usan estas piezas (tablas, tarjetas, campos, botones,
selector de fechas, ventanas de detalle) para mantener un diseño
consistente y no repetir código.
"""

import traceback
from datetime import date, timedelta
from tkinter import messagebox, ttk

import customtkinter as ctk

from config import (
    AMARILLO, BLANCO, BORDE, FONDO, FUENTE, GRIS, GRIS_HOVER, ROJO, ROJO_CLARO,
    ROJO_HOVER, TEXTO, VERDE, VERDE_CLARO, VERDE_HOVER, VERDE_OSCURO, VERDE_SUAVE,
)
from database import ErrorSistema, a_fecha_local, hoy
from servicios import validaciones

# ======================================================================
# FORMATOS
# ======================================================================

def formato_dinero(valor):
    """1234.5 -> '$ 1.234,50' (formato argentino)."""
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        numero = 0.0
    texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {texto}"


def formato_fecha(valor, con_hora=True):
    instante = a_fecha_local(valor)
    if instante is None:
        return "-"
    return instante.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")


def fecha_texto(dia: date):
    return dia.strftime("%d/%m/%Y")


def nombre_persona(perfil):
    perfil = perfil or {}
    return perfil.get("nombre") or perfil.get("usuario") or "-"


# ======================================================================
# MENSAJES Y MANEJO DE ERRORES
# ======================================================================

def informar(mensaje, titulo="Operación exitosa"):
    messagebox.showinfo(titulo, mensaje)


def advertir(mensaje, titulo="Atención"):
    messagebox.showwarning(titulo, mensaje)


def mostrar_error(mensaje, titulo="No se pudo completar la operación"):
    messagebox.showerror(titulo, mensaje)


def confirmar(mensaje, titulo="Confirmar"):
    return messagebox.askyesno(titulo, mensaje)


def ejecutar_seguro(funcion, *argumentos, titulo_error="No se pudo completar la operación", **opciones):
    """Ejecuta una función y muestra cualquier error en un mensaje claro.

    Devuelve (True, resultado) si salió bien o (False, None) si falló.
    Así un error de conexión o de validación nunca cierra el programa.
    """
    try:
        return True, funcion(*argumentos, **opciones)
    except ErrorSistema as error:
        mostrar_error(str(error), titulo_error)
    except Exception as error:  # Error inesperado: se informa y se registra.
        traceback.print_exc()
        mostrar_error(f"Ocurrió un error inesperado:\n{error}", titulo_error)
    return False, None


# ======================================================================
# ESTILO DE TABLAS (ttk.Treeview)
# ======================================================================

_estilos_listos = False
FUENTE_ICONOS = "Segoe UI Symbol"


def aplicar_tema():
    """Adapta el tema de CustomTkinter a la paleta del negocio.

    Debe llamarse antes de crear widgets (lo hace main.py al iniciar).
    """
    tema = ctk.ThemeManager.theme
    tema["CTkSegmentedButton"].update({
        "fg_color": ["#6B9479", "#6B9479"],
        "selected_color": [VERDE_OSCURO, VERDE_OSCURO],
        "selected_hover_color": [VERDE, VERDE],
        "unselected_color": ["#6B9479", "#6B9479"],
        "unselected_hover_color": ["#5C8569", "#5C8569"],
        "text_color": [BLANCO, BLANCO],
    })
    tema["CTkComboBox"].update({
        "button_color": [VERDE_CLARO, VERDE_CLARO],
        "button_hover_color": ["#C8E8D1", "#C8E8D1"],
        "border_color": [BORDE, BORDE],
        "text_color": [TEXTO, TEXTO],
    })
    tema["CTkEntry"].update({"border_color": [BORDE, BORDE]})


def configurar_estilos():
    global _estilos_listos
    if _estilos_listos:
        return
    estilo = ttk.Style()
    estilo.theme_use("clam")
    estilo.configure(
        "Sistema.Treeview",
        background=BLANCO, fieldbackground=BLANCO, foreground=TEXTO,
        rowheight=30, font=(FUENTE, 10), borderwidth=0,
    )
    estilo.configure(
        "Sistema.Treeview.Heading",
        background=VERDE_OSCURO, foreground=BLANCO, font=(FUENTE, 10, "bold"),
        relief="flat", padding=(6, 7),
    )
    estilo.map("Sistema.Treeview.Heading", background=[("active", VERDE)])
    estilo.map(
        "Sistema.Treeview",
        background=[("selected", VERDE_CLARO)],
        foreground=[("selected", VERDE_OSCURO)],
    )
    estilo.configure(
        "Sistema.Vertical.TScrollbar",
        background=VERDE_CLARO, troughcolor=FONDO, bordercolor=FONDO,
        arrowcolor=VERDE_OSCURO, relief="flat",
    )
    _estilos_listos = True


class Tabla(ctk.CTkFrame):
    """Tabla profesional con encabezado verde, filas alternadas y scroll.

    columnas: lista de tuplas (clave, título, ancho, alineación)
    """

    def __init__(self, master, columnas, altura=10, al_doble_click=None, al_seleccionar=None):
        super().__init__(master, fg_color=BLANCO, corner_radius=10, border_width=1, border_color=BORDE)
        configurar_estilos()

        self.claves = [c[0] for c in columnas]
        self.arbol = ttk.Treeview(
            self, columns=self.claves, show="headings", height=altura,
            selectmode="browse", style="Sistema.Treeview",
        )
        for clave, titulo, ancho, alineacion in columnas:
            self.arbol.heading(clave, text=titulo, anchor=alineacion)
            self.arbol.column(clave, width=ancho, minwidth=40, anchor=alineacion, stretch=True)

        barra = ttk.Scrollbar(self, orient="vertical", command=self.arbol.yview,
                              style="Sistema.Vertical.TScrollbar")
        self.arbol.configure(yscrollcommand=barra.set)

        self.arbol.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        barra.pack(side="right", fill="y", padx=(0, 4), pady=4)

        self.arbol.tag_configure("par", background="#F7FBF8")
        self.arbol.tag_configure("alerta", foreground=ROJO)
        self.arbol.tag_configure("aviso", foreground=AMARILLO)
        self.arbol.tag_configure("inactivo", foreground="#9CA3AF")
        self.arbol.tag_configure("positivo", foreground=VERDE)

        self.vacio = ctk.CTkLabel(self, text="", text_color=GRIS, font=(FUENTE, 12), fg_color=BLANCO)

        if al_doble_click:
            self.arbol.bind("<Double-1>", lambda _e: al_doble_click())
            self.arbol.bind("<Return>", lambda _e: al_doble_click())
        if al_seleccionar:
            self.arbol.bind("<<TreeviewSelect>>", lambda _e: al_seleccionar())

    def cargar(self, filas, mensaje_vacio="No hay registros para mostrar."):
        """filas: lista de (id, [valores], [etiquetas])."""
        self.arbol.delete(*self.arbol.get_children())
        for indice, fila in enumerate(filas):
            identificador, valores = fila[0], fila[1]
            etiquetas = list(fila[2]) if len(fila) > 2 and fila[2] else []
            if indice % 2:
                etiquetas.append("par")
            self.arbol.insert("", "end", iid=str(identificador), values=valores, tags=etiquetas)
        if filas:
            self.vacio.place_forget()
        else:
            self.vacio.configure(text=mensaje_vacio)
            self.vacio.place(relx=0.5, rely=0.55, anchor="center")

    def seleccionado(self):
        seleccion = self.arbol.selection()
        return seleccion[0] if seleccion else None

    def seleccionar(self, identificador):
        identificador = str(identificador)
        if self.arbol.exists(identificador):
            self.arbol.selection_set(identificador)
            self.arbol.see(identificador)

    def limpiar(self):
        self.cargar([], "")


# ======================================================================
# BLOQUES DE DISEÑO
# ======================================================================

def encabezado(master, titulo, subtitulo="", acciones=None):
    """Título de la sección con subtítulo y botones opcionales a la derecha."""
    marco = ctk.CTkFrame(master, fg_color="transparent")
    textos = ctk.CTkFrame(marco, fg_color="transparent")
    textos.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(textos, text=titulo, font=(FUENTE, 25, "bold"), text_color=VERDE_OSCURO).pack(anchor="w")
    if subtitulo:
        ctk.CTkLabel(textos, text=subtitulo, font=(FUENTE, 13), text_color=GRIS).pack(anchor="w", pady=(2, 0))
    for texto, comando, tipo in (acciones or []):
        boton(marco, texto, comando, tipo, ancho=120).pack(side="right", padx=(8, 0))
    return marco


def panel(master, titulo=None, subtitulo=None):
    """Tarjeta blanca con borde suave, usada para agrupar contenido."""
    marco = ctk.CTkFrame(master, fg_color=BLANCO, corner_radius=14, border_width=1, border_color=BORDE)
    if titulo:
        ctk.CTkLabel(marco, text=titulo, font=(FUENTE, 16, "bold"), text_color=VERDE_OSCURO).pack(
            anchor="w", padx=16, pady=(14, 0 if subtitulo else 8))
    if subtitulo:
        ctk.CTkLabel(marco, text=subtitulo, font=(FUENTE, 12), text_color=GRIS).pack(
            anchor="w", padx=16, pady=(0, 8))
    return marco


class TarjetaEstadistica(ctk.CTkFrame):
    """Tarjeta con título, ícono y valor grande (para paneles y reportes)."""

    def __init__(self, master, titulo, icono, color=VERDE, fondo_icono=VERDE_CLARO):
        super().__init__(master, fg_color=BLANCO, corner_radius=14, border_width=1, border_color=BORDE)
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self, text=icono, width=46, height=46, corner_radius=12,
            fg_color=fondo_icono, text_color=color, font=(FUENTE_ICONOS, 19, "bold"),
        ).grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=14)
        self.titulo = ctk.CTkLabel(self, text=titulo, font=(FUENTE, 12), text_color=GRIS, anchor="w")
        self.titulo.grid(row=0, column=1, sticky="sw", padx=(0, 10), pady=(14, 0))
        self.valor = ctk.CTkLabel(self, text="—", font=(FUENTE, 22, "bold"), text_color=TEXTO, anchor="w")
        self.valor.grid(row=1, column=1, sticky="nw", padx=(0, 10), pady=(0, 12))

    def actualizar(self, texto, color=None, titulo=None):
        self.valor.configure(text=str(texto), text_color=color or TEXTO)
        if titulo:
            self.titulo.configure(text=titulo)


def fila_tarjetas(master, definiciones):
    """Crea una fila de TarjetaEstadistica que se reparten el ancho."""
    marco = ctk.CTkFrame(master, fg_color="transparent")
    tarjetas = []
    for indice, definicion in enumerate(definiciones):
        marco.grid_columnconfigure(indice, weight=1, uniform="tarjetas")
        tarjeta = TarjetaEstadistica(marco, *definicion)
        tarjeta.grid(row=0, column=indice, sticky="nsew",
                     padx=(0 if indice == 0 else 6, 0 if indice == len(definiciones) - 1 else 6))
        tarjetas.append(tarjeta)
    return marco, tarjetas


COLORES_BOTON = {
    "primario": (VERDE, VERDE_HOVER, BLANCO),
    "oscuro": (VERDE_OSCURO, VERDE, BLANCO),
    "secundario": (GRIS, GRIS_HOVER, BLANCO),
    "peligro": (ROJO, ROJO_HOVER, BLANCO),
    "suave": (VERDE_CLARO, "#C8E8D1", VERDE_OSCURO),
}


def boton(master, texto, comando, tipo="primario", ancho=140, alto=38):
    color, hover, texto_color = COLORES_BOTON.get(tipo, COLORES_BOTON["primario"])
    return ctk.CTkButton(
        master, text=texto, command=comando, width=ancho, height=alto, corner_radius=9,
        fg_color=color, hover_color=hover, text_color=texto_color, font=(FUENTE, 13, "bold"),
    )


def campo(master, etiqueta, placeholder="", ancho=None, mostrar=None):
    """Etiqueta + entrada de texto. Devuelve (contenedor, entrada)."""
    contenedor = ctk.CTkFrame(master, fg_color="transparent")
    contenedor.etiqueta = ctk.CTkLabel(contenedor, text=etiqueta, font=(FUENTE, 12, "bold"),
                                       text_color=VERDE_OSCURO)
    contenedor.etiqueta.pack(anchor="w", pady=(0, 3))
    opciones = {"placeholder_text": placeholder, "height": 36, "border_color": BORDE,
                "fg_color": BLANCO, "text_color": TEXTO}
    if ancho:
        opciones["width"] = ancho
    if mostrar:
        opciones["show"] = mostrar
    entrada = ctk.CTkEntry(contenedor, **opciones)
    entrada.pack(fill="x")
    return contenedor, entrada


def selector(master, etiqueta, valores, ancho=None, comando=None):
    """Etiqueta + lista desplegable de sólo lectura. Devuelve (contenedor, combo)."""
    contenedor = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(contenedor, text=etiqueta, font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(
        anchor="w", pady=(0, 3))
    opciones = {"values": valores or [""], "state": "readonly", "height": 36,
                "fg_color": BLANCO, "dropdown_fg_color": BLANCO}
    if ancho:
        opciones["width"] = ancho
    if comando:
        opciones["command"] = comando
    combo = ctk.CTkComboBox(contenedor, **opciones)
    combo.pack(fill="x")
    if valores:
        combo.set(valores[0])
    return contenedor, combo


def cambiar_opciones(combo, valores, seleccion=None):
    """Actualiza las opciones de un CTkComboBox de sólo lectura."""
    valores = list(valores) or [""]
    combo.configure(values=valores)
    elegir_opcion(combo, seleccion if seleccion in valores else valores[0])


def elegir_opcion(combo, valor):
    combo.configure(state="normal")
    combo.set(valor)
    combo.configure(state="readonly")


def escribir(entrada, valor):
    """Reemplaza el texto de una entrada (respetando estado deshabilitado)."""
    estado = entrada.cget("state")
    entrada.configure(state="normal")
    entrada.delete(0, "end")
    if valor not in (None, ""):
        entrada.insert(0, str(valor))
    entrada.configure(state=estado)


def numero_editable(valor):
    """Muestra un número para editar: 1500.0 -> '1500', 99.9 -> '99.90'."""
    numero = float(valor or 0)
    return str(int(numero)) if numero.is_integer() else f"{numero:.2f}"


# ======================================================================
# SELECTOR DE RANGO DE FECHAS
# ======================================================================

class SelectorFechas(ctk.CTkFrame):
    """Campos Desde/Hasta con accesos rápidos (Hoy, 7 días, Mes)."""

    def __init__(self, master, al_cambiar, dias_iniciales=0):
        super().__init__(master, fg_color="transparent")
        self.al_cambiar = al_cambiar

        ctk.CTkLabel(self, text="Desde", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(side="left")
        self.desde = ctk.CTkEntry(self, width=105, height=34, border_color=BORDE, fg_color=BLANCO)
        self.desde.pack(side="left", padx=(6, 10))
        ctk.CTkLabel(self, text="Hasta", font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).pack(side="left")
        self.hasta = ctk.CTkEntry(self, width=105, height=34, border_color=BORDE, fg_color=BLANCO)
        self.hasta.pack(side="left", padx=(6, 10))

        for texto, dias in (("Hoy", 0), ("7 días", 6), ("Mes", None)):
            ctk.CTkButton(
                self, text=texto, width=62, height=32, corner_radius=8,
                fg_color=VERDE_CLARO, hover_color="#C8E8D1", text_color=VERDE_OSCURO,
                font=(FUENTE, 12, "bold"), command=lambda d=dias: self.rapido(d),
            ).pack(side="left", padx=2)

        boton(self, "Filtrar", self._aplicar, "primario", ancho=80, alto=32).pack(side="left", padx=(8, 0))

        for entrada in (self.desde, self.hasta):
            entrada.bind("<Return>", lambda _e: self._aplicar())

        self.establecer(hoy() - timedelta(days=dias_iniciales), hoy())

    def establecer(self, desde, hasta):
        escribir(self.desde, fecha_texto(desde))
        escribir(self.hasta, fecha_texto(hasta))

    def rapido(self, dias):
        fin = hoy()
        inicio = fin.replace(day=1) if dias is None else fin - timedelta(days=dias)
        self.establecer(inicio, fin)
        self._aplicar()

    def obtener(self):
        """Devuelve (desde, hasta) como date. Lanza ErrorSistema si no son válidas."""
        desde = validaciones.fecha(self.desde.get(), "Desde")
        hasta = validaciones.fecha(self.hasta.get(), "Hasta")
        return validaciones.rango_fechas(desde, hasta)

    def _aplicar(self):
        self.al_cambiar()


# ======================================================================
# VENTANAS EMERGENTES
# ======================================================================

def ventana_modal(master, titulo, ancho=560, alto=520):
    """Ventana secundaria centrada que bloquea la principal hasta cerrarse."""
    ventana = ctk.CTkToplevel(master)
    ventana.title(titulo)
    ventana.configure(fg_color=FONDO)
    raiz = master.winfo_toplevel()
    raiz.update_idletasks()
    # El tamaño se indica sin escalar; la posición, en píxeles reales.
    escala = ventana._get_window_scaling()
    ancho = min(ancho, int(raiz.winfo_screenwidth() / escala) - 40)
    alto = min(alto, int(raiz.winfo_screenheight() / escala) - 80)
    x = raiz.winfo_rootx() + max((raiz.winfo_width() - int(ancho * escala)) // 2, 0)
    y = raiz.winfo_rooty() + max((raiz.winfo_height() - int(alto * escala)) // 2, 0)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")
    ventana.minsize(min(420, ancho), min(360, alto))
    ventana.transient(raiz)
    # En Windows la ventana puede quedar detrás: se trae al frente.
    ventana.after(120, lambda: _activar_modal(ventana))
    return ventana


def _activar_modal(ventana):
    if not ventana.winfo_exists():
        return
    ventana.lift()
    ventana.focus_force()
    try:
        ventana.grab_set()
    except Exception:
        pass


def etiqueta_estado(master, texto, positivo=True):
    """Pequeña etiqueta de color (por ejemplo: Activo / Inactivo)."""
    return ctk.CTkLabel(
        master, text=f"  {texto}  ", corner_radius=8, font=(FUENTE, 11, "bold"),
        fg_color=VERDE_SUAVE if positivo else ROJO_CLARO,
        text_color=VERDE if positivo else ROJO,
    )


# ======================================================================
# GRÁFICOS (Matplotlib dentro de CustomTkinter)
# ======================================================================

def crear_grafico(master, alto=3.0):
    """Crea una figura de Matplotlib incrustada. Devuelve (figura, eje, lienzo)."""
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure

    figura = Figure(figsize=(6, alto), dpi=100, facecolor=BLANCO)
    eje = figura.add_subplot(111)
    lienzo = FigureCanvasTkAgg(figura, master=master)
    lienzo.get_tk_widget().configure(background=BLANCO, highlightthickness=0)
    return figura, eje, lienzo


def estilo_eje(eje):
    eje.set_facecolor(BLANCO)
    for lado in ("top", "right"):
        eje.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        eje.spines[lado].set_color(BORDE)
    eje.tick_params(colors=GRIS, labelsize=8)
    eje.grid(axis="y", color="#EEF3EF", linewidth=0.8)
    eje.set_axisbelow(True)


def formato_eje_dinero(valor, _posicion=None):
    if abs(valor) >= 1_000_000:
        return f"${valor / 1_000_000:.1f}M"
    if abs(valor) >= 1_000:
        return f"${valor / 1_000:.0f}k"
    return f"${valor:.0f}"
