"""
Datos del usuario que inició sesión.

Se guarda en un único objeto compartido por todas las pantallas para
consultar el rol (permisos) y mostrar quién está operando el sistema.
"""

from dataclasses import dataclass
from datetime import datetime

from config import PERMISOS, ROL_ADMIN


@dataclass
class Usuario:
    id: str
    email: str
    nombre: str
    usuario: str
    rol: str
    inicio: datetime

    @property
    def es_admin(self):
        return self.rol == ROL_ADMIN

    @property
    def rol_legible(self):
        return "Administradora" if self.es_admin else "Cajera"

    def puede(self, seccion):
        return seccion in PERMISOS.get(self.rol, set())


usuario_actual: Usuario | None = None


def iniciar(usuario: Usuario):
    global usuario_actual
    usuario_actual = usuario


def cerrar():
    global usuario_actual
    usuario_actual = None


def actual() -> Usuario | None:
    return usuario_actual


def es_admin():
    return usuario_actual is not None and usuario_actual.es_admin
