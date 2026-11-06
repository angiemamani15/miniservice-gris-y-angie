"""
Pantalla de inicio de sesión.

Se puede ingresar con el nombre de usuario o con el correo. La
contraseña la valida Supabase Auth (nunca se compara en Python ni se
guarda en texto plano). Luego se lee el rol desde la tabla perfiles.
"""

import customtkinter as ctk

from componentes import ejecutar_seguro
from config import BLANCO, FONDO, FUENTE, GRIS, NOMBRE_NEGOCIO, VERDE, VERDE_HOVER, VERDE_OSCURO
from servicios import autenticacion


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login):
        super().__init__(master, fg_color=FONDO)

        self.on_login = on_login

        tarjeta = ctk.CTkFrame(self, width=420, fg_color=BLANCO, corner_radius=20)
        tarjeta.place(relx=0.5, rely=0.5, anchor="center")

        encabezado = ctk.CTkFrame(tarjeta, fg_color=VERDE_OSCURO, corner_radius=15)
        encabezado.pack(fill="x", padx=15, pady=(15, 20))

        ctk.CTkLabel(encabezado, text="G&A", font=(FUENTE, 34, "bold"),
                     text_color="white").pack(pady=(25, 10))
        ctk.CTkLabel(encabezado, text=NOMBRE_NEGOCIO, font=(FUENTE, 21, "bold"),
                     text_color="white").pack(padx=15, pady=(0, 8))
        ctk.CTkLabel(encabezado, text="SISTEMA DE GESTIÓN", font=(FUENTE, 12),
                     text_color="#DCEFE2").pack(pady=(0, 25))

        ctk.CTkLabel(tarjeta, text="Iniciar sesión", font=(FUENTE, 23, "bold"),
                     text_color=VERDE_OSCURO).pack(pady=(0, 20))

        self.usuario = ctk.CTkEntry(tarjeta, width=340, height=45,
                                    placeholder_text="Usuario o correo electrónico")
        self.usuario.pack(padx=30, pady=8)

        self.contrasena = ctk.CTkEntry(tarjeta, width=340, height=45,
                                       placeholder_text="Contraseña", show="*")
        self.contrasena.pack(padx=30, pady=8)

        self.ver = ctk.CTkCheckBox(
            tarjeta, text="Mostrar contraseña", font=(FUENTE, 12), text_color=GRIS,
            fg_color=VERDE, hover_color=VERDE_HOVER, checkbox_width=18, checkbox_height=18,
            command=self.alternar_contrasena,
        )
        self.ver.pack(anchor="w", padx=40, pady=(2, 0))

        self.boton = ctk.CTkButton(
            tarjeta, text="Ingresar al sistema", width=340, height=45,
            fg_color=VERDE, hover_color=VERDE_HOVER, font=(FUENTE, 15, "bold"),
            command=self.iniciar_sesion,
        )
        self.boton.pack(pady=(18, 30))

        self.usuario.bind("<Return>", lambda _e: self.contrasena.focus_set())
        self.contrasena.bind("<Return>", lambda _e: self.iniciar_sesion())
        self.after(150, self.usuario.focus_set)

    def alternar_contrasena(self):
        self.contrasena.configure(show="" if self.ver.get() else "*")

    def iniciar_sesion(self):
        self.boton.configure(state="disabled", text="Verificando...")
        self.update_idletasks()

        correcto, usuario = ejecutar_seguro(
            autenticacion.iniciar_sesion,
            self.usuario.get(),
            self.contrasena.get(),
            titulo_error="Error de inicio de sesión",
        )

        if not self.winfo_exists():
            return
        self.boton.configure(state="normal", text="Ingresar al sistema")

        if correcto:
            self.on_login(usuario)
        else:
            self.contrasena.delete(0, "end")
            self.contrasena.focus_set()
