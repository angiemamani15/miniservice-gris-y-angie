"""Validaciones reutilizables para los formularios."""

import re
from datetime import date, datetime

from database import ErrorSistema

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def texto_obligatorio(valor, campo, minimo=1, maximo=120):
    valor = (valor or "").strip()
    if len(valor) < minimo:
        raise ErrorSistema(f"Completá el campo «{campo}».")
    if len(valor) > maximo:
        raise ErrorSistema(f"«{campo}» no puede superar {maximo} caracteres.")
    return valor


def texto_opcional(valor, maximo=200):
    valor = (valor or "").strip()
    if len(valor) > maximo:
        raise ErrorSistema(f"El texto no puede superar {maximo} caracteres.")
    return valor or None


def decimal(valor, campo, minimo=0.0, permitir_cero=True):
    """Convierte '1.234,50' o '1234.50' a número. Valida el mínimo."""
    texto = str(valor or "").strip().replace("$", "").replace(" ", "")
    if not texto:
        raise ErrorSistema(f"Ingresá un valor para «{campo}».")
    if "," in texto:
        # Formato argentino: punto de miles y coma decimal.
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = round(float(texto), 2)
    except ValueError:
        raise ErrorSistema(f"«{campo}» debe ser un número válido.") from None
    if numero < minimo or (not permitir_cero and numero == 0):
        condicion = "mayor a cero" if not permitir_cero else f"mayor o igual a {minimo:g}"
        raise ErrorSistema(f"«{campo}» debe ser {condicion}.")
    if numero > 9_999_999_999:
        raise ErrorSistema(f"«{campo}» es demasiado grande.")
    return numero


def entero(valor, campo, minimo=0):
    texto = str(valor or "").strip()
    if not texto:
        raise ErrorSistema(f"Ingresá un valor para «{campo}».")
    try:
        numero = int(texto)
    except ValueError:
        raise ErrorSistema(f"«{campo}» debe ser un número entero.") from None
    if numero < minimo:
        raise ErrorSistema(f"«{campo}» debe ser mayor o igual a {minimo}.")
    if numero > 1_000_000:
        raise ErrorSistema(f"«{campo}» es demasiado grande.")
    return numero


def email(valor, obligatorio=False):
    valor = (valor or "").strip().lower()
    if not valor:
        if obligatorio:
            raise ErrorSistema("Ingresá un correo electrónico.")
        return None
    if not PATRON_EMAIL.match(valor):
        raise ErrorSistema("El correo electrónico no tiene un formato válido.")
    return valor


def telefono(valor):
    valor = (valor or "").strip()
    if valor and not re.fullmatch(r"[0-9+()\-\s]{6,25}", valor):
        raise ErrorSistema("El teléfono sólo puede contener números, espacios, +, - y paréntesis.")
    return valor or None


def fecha(valor, campo="Fecha"):
    """Acepta DD/MM/AAAA o AAAA-MM-DD."""
    texto = (valor or "").strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ErrorSistema(f"«{campo}» debe tener el formato DD/MM/AAAA.")


def rango_fechas(desde: date, hasta: date):
    if desde > hasta:
        raise ErrorSistema("La fecha «Desde» no puede ser posterior a «Hasta».")
    return desde, hasta


def contrasena(valor, confirmacion=None):
    if len(valor or "") < 6:
        raise ErrorSistema("La contraseña debe tener al menos 6 caracteres.")
    if confirmacion is not None and valor != confirmacion:
        raise ErrorSistema("Las contraseñas no coinciden.")
    return valor


def nombre_usuario(valor):
    valor = (valor or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9._]{3,30}", valor):
        raise ErrorSistema(
            "El usuario debe tener entre 3 y 30 caracteres: letras, números, punto o guion bajo."
        )
    return valor
