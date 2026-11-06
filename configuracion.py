"""
Configuración del sistema.

 * Mi sesión: datos de la sesión, cambio de contraseña y cierre de sesión.
 * Negocio: datos que aparecen en los comprobantes (editables por la
   administradora; la cajera sólo los consulta).
 * Usuarios (sólo administradora): alta de usuarios, rol y activación.
"""

import customtkinter as ctk

import sesion
from componentes import (
    Tabla, boton, campo, cambiar_opciones, ejecutar_seguro, elegir_opcion, encabezado, escribir,
    formato_fecha, informar, panel, selector,
)
from config import (
    FONDO, FUENTE, GRIS, NOMBRE_NEGOCIO, PERMISOS, ROL_ADMIN, ROL_CAJERA, SECCIONES, TEXTO, VERDE,
    VERDE_OSCURO, VERDE_SUAVE, VERSION,
)
from servicios import autenticacion, reportes

ROLES = {"Administradora": ROL_ADMIN, "Cajera": ROL_CAJERA}


class ConfiguracionFrame(ctk.CTkFrame):
    def __init__(self, master, app=None):
        super().__init__(master, fg_color=FONDO, corner_radius=0)
        self.app = app
        self.usuario = sesion.actual()
        self.usuarios = []
        self.usuario_editado = None

        encabezado(self, "Configuración", "Datos del negocio, tu sesión y usuarios del sistema.").pack(
            fill="x", padx=22, pady=(16, 6))

        self.pestanas = ctk.CTkTabview(
            self, fg_color=FONDO, segmented_button_selected_color=VERDE,
            segmented_button_selected_hover_color=VERDE_OSCURO, segmented_button_font=(FUENTE, 13, "bold"))
        self.pestanas.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.pestanas.add("Mi sesión")
        self.pestanas.add("Negocio")
        if self.usuario.es_admin:
            self.pestanas.add("Usuarios")

        self._crear_sesion(self.pestanas.tab("Mi sesión"))
        self._crear_negocio(self.pestanas.tab("Negocio"))
        if self.usuario.es_admin:
            self._crear_usuarios(self.pestanas.tab("Usuarios"))
            self.cargar_usuarios()

    # ==================================================================
    # MI SESIÓN
    # ==================================================================

    def _crear_sesion(self, tab):
        tab.grid_columnconfigure((0, 1), weight=1, uniform="sesion")
        tab.grid_rowconfigure(0, weight=1)

        datos = panel(tab, "Datos de la sesión")
        datos.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        filas = [
            ("Nombre", self.usuario.nombre),
            ("Usuario", self.usuario.usuario),
            ("Correo", self.usuario.email),
            ("Rol", self.usuario.rol_legible),
            ("Sesión iniciada", self.usuario.inicio.strftime("%d/%m/%Y %H:%M")),
        ]
        rejilla = ctk.CTkFrame(datos, fg_color="transparent")
        rejilla.pack(fill="x", padx=16, pady=(4, 8))
        for indice, (titulo, valor) in enumerate(filas):
            ctk.CTkLabel(rejilla, text=titulo, font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO).grid(
                row=indice, column=0, sticky="w", pady=4, padx=(0, 16))
            ctk.CTkLabel(rejilla, text=valor, font=(FUENTE, 12), text_color=TEXTO).grid(
                row=indice, column=1, sticky="w", pady=4)

        secciones = [nombre for nombre, _ in SECCIONES if nombre in PERMISOS[self.usuario.rol]]
        ctk.CTkLabel(datos, text="Secciones habilitadas para tu rol:\n" + " · ".join(secciones),
                     font=(FUENTE, 12), text_color=VERDE_OSCURO, fg_color=VERDE_SUAVE, corner_radius=10,
                     wraplength=380, justify="left").pack(fill="x", padx=16, pady=8, ipady=8)
        ctk.CTkLabel(datos, text=f"{NOMBRE_NEGOCIO} · Versión {VERSION}", font=(FUENTE, 11),
                     text_color=GRIS).pack(anchor="w", padx=16, pady=(4, 4))
        boton(datos, "Cerrar sesión", self.app.cerrar_sesion if self.app else None, "peligro").pack(
            anchor="w", padx=16, pady=(8, 16))

        clave = panel(tab, "Cambiar contraseña", "Mínimo 6 caracteres.")
        clave.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        c, self.clave_actual = campo(clave, "Contraseña actual", mostrar="*")
        c.pack(fill="x", padx=16, pady=4)
        c, self.clave_nueva = campo(clave, "Nueva contraseña", mostrar="*")
        c.pack(fill="x", padx=16, pady=4)
        c, self.clave_repetir = campo(clave, "Repetir nueva contraseña", mostrar="*")
        c.pack(fill="x", padx=16, pady=4)
        self.clave_repetir.bind("<Return>", lambda _e: self.cambiar_contrasena())
        boton(clave, "Actualizar contraseña", self.cambiar_contrasena, "primario").pack(
            fill="x", padx=16, pady=(14, 16))

    def cambiar_contrasena(self):
        correcto, _ = ejecutar_seguro(autenticacion.cambiar_contrasena, self.clave_actual.get(),
                                      self.clave_nueva.get(), self.clave_repetir.get())
        for entrada in (self.clave_actual, self.clave_nueva, self.clave_repetir):
            escribir(entrada, "")
        if correcto:
            informar("Tu contraseña fue actualizada correctamente.")

    # ==================================================================
    # NEGOCIO
    # ==================================================================

    def _crear_negocio(self, tab):
        contenedor = panel(tab, "Información del negocio",
                           "Estos datos se muestran en los comprobantes de venta."
                           if self.usuario.es_admin else "Sólo la administradora puede modificar estos datos.")
        contenedor.pack(fill="both", expand=True)
        rejilla = ctk.CTkFrame(contenedor, fg_color="transparent")
        rejilla.pack(fill="x", padx=10)
        rejilla.grid_columnconfigure((0, 1), weight=1)

        self.campos_negocio = {}
        definiciones = [
            ("nombre", "Nombre del negocio"), ("telefono", "Teléfono"),
            ("direccion", "Dirección"), ("email", "Correo electrónico"),
            ("cuit", "CUIT"), ("mensaje_comprobante", "Mensaje al pie del comprobante"),
        ]
        for indice, (clave, titulo) in enumerate(definiciones):
            c, entrada = campo(rejilla, titulo)
            c.grid(row=indice // 2, column=indice % 2, sticky="ew", padx=6, pady=5)
            self.campos_negocio[clave] = entrada

        correcto, negocio = ejecutar_seguro(reportes.obtener_negocio)
        if correcto:
            for clave, entrada in self.campos_negocio.items():
                escribir(entrada, negocio.get(clave) or "")
            if negocio.get("actualizado_en"):
                ctk.CTkLabel(contenedor, text=f"Última actualización: {formato_fecha(negocio['actualizado_en'])}",
                             font=(FUENTE, 11), text_color=GRIS).pack(anchor="w", padx=16, pady=(6, 0))

        if self.usuario.es_admin:
            boton(contenedor, "Guardar datos del negocio", self.guardar_negocio, "primario", ancho=220).pack(
                anchor="w", padx=16, pady=16)
        else:
            for entrada in self.campos_negocio.values():
                entrada.configure(state="disabled")

    def guardar_negocio(self):
        valores = {clave: entrada.get() for clave, entrada in self.campos_negocio.items()}
        correcto, _ = ejecutar_seguro(
            reportes.guardar_negocio, valores["nombre"], valores["direccion"], valores["telefono"],
            valores["email"], valores["cuit"], valores["mensaje_comprobante"])
        if correcto:
            informar("Datos del negocio actualizados.")

    # ==================================================================
    # USUARIOS (administradora)
    # ==================================================================

    def _crear_usuarios(self, tab):
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2, minsize=320)
        tab.grid_rowconfigure(0, weight=1)

        listado = panel(tab, "Usuarios del sistema")
        listado.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.tabla_usuarios = Tabla(listado, [
            ("nombre", "Nombre", 150, "w"), ("usuario", "Usuario", 110, "w"), ("email", "Correo", 190, "w"),
            ("rol", "Rol", 110, "center"), ("estado", "Estado", 80, "center"),
        ], altura=12, al_seleccionar=self.seleccionar_usuario)
        self.tabla_usuarios.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        ctk.CTkLabel(listado, text="Las contraseñas las guarda Supabase Auth cifradas (bcrypt); "
                                   "nadie puede verlas, ni siquiera la administradora.",
                     font=(FUENTE, 11), text_color=GRIS, wraplength=360, justify="left").pack(
            anchor="w", padx=16, pady=(0, 12))

        formulario = panel(tab)
        formulario.grid(row=0, column=1, sticky="nsew")
        self.titulo_usuario = ctk.CTkLabel(formulario, text="Nuevo usuario", font=(FUENTE, 17, "bold"),
                                           text_color=VERDE_OSCURO)
        self.titulo_usuario.pack(anchor="w", padx=16, pady=(14, 4))
        rejilla = ctk.CTkFrame(formulario, fg_color="transparent")
        rejilla.pack(fill="x", padx=10)
        rejilla.grid_columnconfigure((0, 1), weight=1)

        c, self.u_nombre = campo(rejilla, "Nombre y apellido")
        c.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=3)
        c, self.u_usuario = campo(rejilla, "Usuario", "ej.: angie")
        c.grid(row=1, column=0, sticky="ew", padx=6, pady=3)
        c, self.u_rol = selector(rejilla, "Rol", list(ROLES))
        c.grid(row=1, column=1, sticky="ew", padx=6, pady=3)
        elegir_opcion(self.u_rol, "Cajera")
        self.contenedor_email, self.u_email = campo(rejilla, "Correo electrónico")
        self.contenedor_email.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=3)
        self.contenedor_clave, self.u_clave = campo(rejilla, "Contraseña", mostrar="*")
        self.contenedor_clave.grid(row=3, column=0, sticky="ew", padx=6, pady=3)
        self.contenedor_repetir, self.u_repetir = campo(rejilla, "Repetir contraseña", mostrar="*")
        self.contenedor_repetir.grid(row=3, column=1, sticky="ew", padx=6, pady=3)
        self.u_activo = ctk.CTkSwitch(formulario, text="Usuario activo", progress_color=VERDE,
                                      font=(FUENTE, 12, "bold"), text_color=VERDE_OSCURO)
        self.u_activo.pack(anchor="w", padx=16, pady=(8, 4))

        botones = ctk.CTkFrame(formulario, fg_color="transparent")
        botones.pack(fill="x", padx=16, pady=(8, 14))
        botones.grid_columnconfigure((0, 1), weight=1)
        self.boton_usuario = boton(botones, "Crear usuario", self.guardar_usuario, "primario")
        self.boton_usuario.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        boton(botones, "Nuevo / limpiar", self.limpiar_usuario, "secundario").grid(
            row=0, column=1, sticky="ew", padx=(4, 0))
        self.limpiar_usuario()

    def cargar_usuarios(self):
        correcto, usuarios = ejecutar_seguro(autenticacion.listar_usuarios)
        if not correcto:
            return
        self.usuarios = usuarios
        self.tabla_usuarios.cargar([
            (u["id"], [u.get("nombre") or "-", u.get("usuario") or "-", u.get("email") or "-",
                       "Administradora" if u["rol"] == ROL_ADMIN else "Cajera",
                       "Activo" if u.get("activo") else "Inactivo"],
             [] if u.get("activo") else ["inactivo"])
            for u in usuarios
        ], "No hay usuarios.")

    def seleccionar_usuario(self):
        identificador = self.tabla_usuarios.seleccionado()
        usuario = next((u for u in self.usuarios if u["id"] == identificador), None)
        if not usuario:
            return
        self.usuario_editado = usuario
        escribir(self.u_nombre, usuario.get("nombre") or "")
        escribir(self.u_usuario, usuario.get("usuario") or "")
        elegir_opcion(self.u_rol, "Administradora" if usuario["rol"] == ROL_ADMIN else "Cajera")
        (self.u_activo.select if usuario.get("activo") else self.u_activo.deselect)()
        for contenedor in (self.contenedor_email, self.contenedor_clave, self.contenedor_repetir):
            contenedor.grid_remove()
        self.titulo_usuario.configure(text=f"Editar: {usuario.get('email') or usuario.get('usuario')}")
        self.boton_usuario.configure(text="Guardar cambios")

    def limpiar_usuario(self):
        self.usuario_editado = None
        for entrada in (self.u_nombre, self.u_usuario, self.u_email, self.u_clave, self.u_repetir):
            escribir(entrada, "")
        cambiar_opciones(self.u_rol, list(ROLES), "Cajera")
        self.u_activo.select()
        for contenedor in (self.contenedor_email, self.contenedor_clave, self.contenedor_repetir):
            contenedor.grid()
        self.titulo_usuario.configure(text="Nuevo usuario")
        self.boton_usuario.configure(text="Crear usuario")
        self.tabla_usuarios.arbol.selection_remove(self.tabla_usuarios.arbol.selection())

    def guardar_usuario(self):
        rol = ROLES[self.u_rol.get()]
        if self.usuario_editado is None:
            correcto, confirmado = ejecutar_seguro(
                autenticacion.crear_usuario, self.u_nombre.get(), self.u_usuario.get(), self.u_email.get(),
                self.u_clave.get(), self.u_repetir.get(), rol, titulo_error="No se creó el usuario")
            if not correcto:
                return
            mensaje = "Usuario creado y habilitado correctamente."
            if not confirmado:
                mensaje += ("\n\nSupabase tiene activada la confirmación por correo: el usuario debe "
                            "confirmar su correo antes de ingresar (o desactivá «Confirm email» en "
                            "Supabase > Authentication > Providers > Email).")
            informar(mensaje)
        else:
            correcto, _ = ejecutar_seguro(
                autenticacion.actualizar_usuario, self.usuario_editado["id"], self.u_nombre.get(),
                self.u_usuario.get(), rol, bool(self.u_activo.get()))
            if not correcto:
                return
            informar("Usuario actualizado correctamente.")
        self.limpiar_usuario()
        self.cargar_usuarios()


