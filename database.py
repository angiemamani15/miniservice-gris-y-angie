"""
Capa de acceso a datos (Supabase / PostgreSQL).

La versión anterior de este archivo creaba una base SQLite local, pero
el sistema usa Supabase como base de datos principal; mantener las dos
provocaba que Inventario y el Panel mostraran datos distintos a los de
Productos. Ahora todo el sistema trabaja sobre Supabase y este módulo
reúne las utilidades comunes:

  * ejecutar(): ejecuta una consulta y traduce los errores a mensajes claros.
  * llamar_funcion(): llama a funciones SQL (RPC) como registrar_venta.
  * obtener_todos(): trae todas las filas paginando (Supabase devuelve
    como máximo 1000 filas por consulta).
  * rango_del_dia(): convierte fechas locales en instantes con zona horaria.

La estructura de la base se crea con los scripts de la carpeta sql/.
"""

from datetime import date, datetime, time, timedelta

import httpx
from postgrest.exceptions import APIError

from config import ZONA_HORARIA
from supabase_config import supabase

TAMANIO_PAGINA = 1000


class ErrorSistema(Exception):
    """Error con un mensaje listo para mostrar al usuario."""


# ----------------------------------------------------------------------
# Traducción de errores técnicos a mensajes comprensibles
# ----------------------------------------------------------------------

def traducir_error(error):
    if isinstance(error, ErrorSistema):
        return str(error)

    if isinstance(error, APIError):
        codigo = error.code or ""
        mensaje = error.message or ""
        texto = f"{mensaje} {error.details or ''}".lower()

        if codigo == "23505":
            if "codigo" in texto:
                return "Ya existe un producto con ese código."
            if "usuario" in texto:
                return "Ese nombre de usuario ya está en uso."
            return "Ya existe un registro con ese nombre o código."
        if codigo in ("23503", "23001"):
            return (
                "No se puede eliminar porque tiene registros asociados "
                "(ventas, compras, movimientos o productos)."
            )
        if codigo == "23514":
            return "Los datos no cumplen las reglas del sistema (revisá precios y cantidades)."
        if codigo == "42501":
            if mensaje.startswith("No tenés"):
                return mensaje
            return "No tenés permisos para realizar esta operación."
        if codigo in ("PGRST200", "PGRST202", "PGRST204", "PGRST205", "42P01", "42703", "42883"):
            return (
                "La base de datos no está actualizada. Ejecutá los scripts "
                f"de la carpeta sql/ en Supabase.\n\nDetalle: {mensaje}"
            )
        if codigo == "P0001" and mensaje:
            # Mensajes propios de nuestras funciones SQL (RAISE EXCEPTION)
            return mensaje
        if codigo.startswith("PGRST3") or "jwt" in texto:
            return "La sesión expiró. Cerrá sesión e ingresá nuevamente."
        return mensaje or str(error)

    if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)):
        return "No hay conexión con Supabase. Revisá tu conexión a internet."

    nombre = type(error).__name__
    if nombre in ("AuthApiError", "AuthRetryableError", "AuthInvalidCredentialsError"):
        texto = str(error).lower()
        if "invalid login" in texto or "invalid credentials" in texto:
            return "Usuario o contraseña incorrectos."
        if "not confirmed" in texto:
            return "El correo del usuario todavía no fue confirmado."
        if "already registered" in texto or "already exists" in texto:
            return "Ya existe un usuario registrado con ese correo."
        if "password" in texto and ("weak" in texto or "at least" in texto or "characters" in texto):
            return "La contraseña es muy débil (mínimo 6 caracteres)."
        if "rate limit" in texto:
            return "Demasiados intentos. Esperá unos minutos y volvé a intentar."
        return str(error)

    return str(error) or nombre


# ----------------------------------------------------------------------
# Ejecución de consultas
# ----------------------------------------------------------------------

def tabla(nombre):
    """Inicia una consulta sobre una tabla."""
    return supabase.table(nombre)


def ejecutar(consulta):
    """Ejecuta una consulta de Supabase y devuelve la lista de filas."""
    try:
        return consulta.execute().data or []
    except Exception as error:
        raise ErrorSistema(traducir_error(error)) from error


def llamar_funcion(nombre, parametros=None):
    """Llama a una función SQL (RPC) definida en sql/02_funciones.sql."""
    try:
        return supabase.rpc(nombre, parametros or {}).execute().data
    except Exception as error:
        raise ErrorSistema(traducir_error(error)) from error


def obtener_todos(crear_consulta):
    """Trae todas las filas de una consulta, página por página.

    crear_consulta: función que devuelve una consulta nueva cada vez
    (por ejemplo: lambda: tabla("productos").select("*").order("id")).
    """
    filas = []
    inicio = 0
    while True:
        pagina = ejecutar(
            crear_consulta().range(inicio, inicio + TAMANIO_PAGINA - 1)
        )
        filas.extend(pagina)
        if len(pagina) < TAMANIO_PAGINA:
            return filas
        inicio += TAMANIO_PAGINA


def patron_exacto(texto):
    """Escapa % y _ para comparar sin distinguir mayúsculas con ilike."""
    barra = "\\"
    return (
        str(texto)
        .replace(barra, barra * 2)
        .replace("%", barra + "%")
        .replace("_", barra + "_")
    )


# ----------------------------------------------------------------------
# Fechas
# ----------------------------------------------------------------------

def hoy():
    return datetime.now(ZONA_HORARIA).date()


def rango_del_dia(desde: date, hasta: date):
    """Devuelve (inicio, fin) en formato ISO para filtrar columnas fecha.

    Incluye todo el día "hasta": fin = medianoche del día siguiente.
    """
    inicio = datetime.combine(desde, time.min, tzinfo=ZONA_HORARIA)
    fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=ZONA_HORARIA)
    return inicio.isoformat(), fin.isoformat()


def a_fecha_local(valor):
    """Convierte el texto de fecha que devuelve Supabase a hora local."""
    if not valor:
        return None
    if isinstance(valor, datetime):
        instante = valor
    else:
        instante = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if instante.tzinfo is None:
        return instante
    return instante.astimezone(ZONA_HORARIA)
