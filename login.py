
import customtkinter as ctk
from tkinter import messagebox

from supabase_config import supabase


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login):
        super().__init__(master, fg_color="#F4F8F5")

        self.on_login = on_login

        tarjeta = ctk.CTkFrame(
            self,
            width=420,
            fg_color="white",
            corner_radius=20
        )
        tarjeta.place(relx=0.5, rely=0.5, anchor="center")

        encabezado = ctk.CTkFrame(
            tarjeta,
            fg_color="#18392B",
            corner_radius=15
        )
        encabezado.pack(fill="x", padx=15, pady=(15, 20))

        ctk.CTkLabel(
            encabezado,
            text="G&A",
            font=("Arial", 34, "bold"),
            text_color="white"
        ).pack(pady=(25, 10))

        ctk.CTkLabel(
            encabezado,
            text="MiniService Gris y Angie",
            font=("Arial", 21, "bold"),
            text_color="white"
        ).pack(padx=15, pady=(0, 8))

        ctk.CTkLabel(
            encabezado,
            text="SISTEMA DE GESTIÓN",
            font=("Arial", 12),
            text_color="#DCEFE2"
        ).pack(pady=(0, 25))

        ctk.CTkLabel(
            tarjeta,
            text="Iniciar sesión",
            font=("Arial", 23, "bold"),
            text_color="#18392B"
        ).pack(pady=(0, 20))

        self.correo = ctk.CTkEntry(
            tarjeta,
            width=340,
            height=45,
            placeholder_text="Correo electrónico"
        )
        self.correo.pack(padx=30, pady=8)

        self.contrasena = ctk.CTkEntry(
            tarjeta,
            width=340,
            height=45,
            placeholder_text="Contraseña",
            show="*"
        )
        self.contrasena.pack(padx=30, pady=8)

        self.boton = ctk.CTkButton(
            tarjeta,
            text="Ingresar al sistema",
            width=340,
            height=45,
            fg_color="#166534",
            hover_color="#15803D",
            font=("Arial", 15, "bold"),
            command=self.iniciar_sesion
        )
        self.boton.pack(pady=(20, 30))

        self.contrasena.bind(
            "<Return>",
            lambda evento: self.iniciar_sesion()
        )

    def iniciar_sesion(self):
        correo = self.correo.get().strip()
        contrasena = self.contrasena.get()

        if not correo or not contrasena:
            messagebox.showwarning(
                "Atención",
                "Ingresá tu correo y contraseña."
            )
            return

        self.boton.configure(
            state="disabled",
            text="Verificando..."
        )
        self.update_idletasks()

        try:
            respuesta = supabase.auth.sign_in_with_password({
                "email": correo,
                "password": contrasena
            })

            if not respuesta.user:
                raise ValueError("No se pudo iniciar sesión.")

            perfil = (
                supabase.table("perfiles")
                .select("rol")
                .eq("id", respuesta.user.id)
                .single()
                .execute()
            )

            rol = perfil.data["rol"]

            if rol not in ("administradora", "cajera"):
                raise ValueError("Tu usuario no tiene un rol válido.")

            self.on_login(rol)

        except Exception as error:
            messagebox.showerror(
                "Error de inicio de sesión",
                f"No se pudo ingresar.\n\n{error}"
            )

        finally:
            self.boton.configure(
                state="normal",
                text="Ingresar al sistema"
            )
