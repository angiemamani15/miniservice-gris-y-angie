"""
Inicio de sesión, cierre de sesión, cambio de contraseña y usuarios.

Las contraseñas NUNCA se guardan en nuestras tablas: Supabase Auth las
almacena cifradas con bcrypt. Nuestra tabla "perfiles" sólo guarda el
nombre, el usuario, el rol y si la cuenta está activa.
"""

import sys
from datetime import datetime

import sesion
from config import ROL_ADMIN, ROL_CAJERA, ZONA_HORARIA
from database import ErrorSistema, ejecutar, llamar_funcion, patron_exacto, tabla, traducir_error
from servicios import validaciones
from supabase_config import crear_cliente_temporal, supabase

CAMPOS_PERFIL = "id,nombre,usuario,email,rol,activo,creado_en"


def iniciar_sesion(identificador, contrasena):
    """Valida usuario/correo y contraseña. Devuelve el Usuario de la sesión."""
    identificador = (identificador or "").strip()
    if not identificador or not contrasena:
        raise ErrorSistema("Ingresá tu usuario (o correo) y tu contraseña.")

    # Se puede ingresar con el nombre de usuario o con el correo.
    if "@" in identificador:
        correo = identificador.lower()
    else:
        correo = llamar_funcion("email_para_login", {"p_usuario": identificador})
        if not correo:
            raise ErrorSistema("Usuario o contraseña incorrectos.")

    try:
        respuesta = supabase.auth.sign_in_with_password(
            {"email": correo, "password": contrasena}
        )
    except Exception as error:
        raise ErrorSistema(traducir_error(error)) from error

    if not respuesta.user:
        raise ErrorSistema("Usuario o contraseña incorrectos.")

    # A partir de acá Supabase ya aceptó la contraseña y el cliente guarda
    # el token. Si algo falla (perfil inexistente, rol no autorizado, base
    # sin actualizar, sin conexión), se cierra esa sesión antes de avisar:
    # nunca queda una sesión abierta sin haber validado el rol.
    try:
        perfil = _perfil_autorizado(respuesta.user.id)
    except Exception:
        _cerrar_sesion_silenciosa()
        raise

    usuario = sesion.Usuario(
        id=perfil["id"],
        email=correo,
        nombre=perfil.get("nombre") or perfil.get("usuario") or correo,
        usuario=perfil.get("usuario") or correo.split("@")[0],
        rol=perfil["rol"],
        inicio=datetime.now(ZONA_HORARIA),
    )
    sesion.iniciar(usuario)
    return usuario


def _perfil_autorizado(id_usuario):
    """Lee el perfil del usuario autenticado y verifica que pueda entrar.

    El rol sale SIEMPRE de la tabla perfiles (protegida por RLS), nunca de
    lo que se escribe en el formulario.
    """
    perfiles = ejecutar(
        tabla("perfiles").select(CAMPOS_PERFIL).eq("id", id_usuario)
    )
    perfil = perfiles[0] if perfiles else None

    if not perfil:
        raise ErrorSistema(
            "Tu cuenta existe pero no tiene un perfil en el sistema. "
            "Pedile a la administradora que la registre."
        )
    if not perfil.get("activo"):
        raise ErrorSistema(
            "Tu usuario no está habilitado. Pedile a la administradora que lo active."
        )
    if perfil.get("rol") not in (ROL_ADMIN, ROL_CAJERA):
        raise ErrorSistema(
            "Tu usuario no tiene un rol autorizado (administradora o cajera). "
            "Acceso denegado."
        )
    return perfil


def _cerrar_sesion_silenciosa():
    # scope "local": borra la sesión de este equipo aunque no haya internet
    # y detiene la renovación automática del token. La sesión local se borra
    # ANTES de avisar al servidor, así que si falla sólo esa notificación
    # (por ejemplo, sin internet) se registra el error y se sigue.
    try:
        supabase.auth.sign_out({"scope": "local"})
    except Exception as error:
        print(f"Aviso: no se pudo notificar el cierre de sesión a Supabase: {error}",
              file=sys.stderr)


def cerrar_sesion():
    """Cierra la sesión en Supabase y borra los datos locales."""
    _cerrar_sesion_silenciosa()
    sesion.cerrar()


def cambiar_contrasena(actual, nueva, confirmacion):
    usuario = sesion.actual()
    if usuario is None:
        raise ErrorSistema("No hay una sesión activa.")
    if not actual:
        raise ErrorSistema("Ingresá tu contraseña actual.")
    validaciones.contrasena(nueva, confirmacion)
    if nueva == actual:
        raise ErrorSistema("La nueva contraseña debe ser distinta de la actual.")

    try:
        # Verificar la contraseña actual volviendo a autenticar.
        supabase.auth.sign_in_with_password({"email": usuario.email, "password": actual})
    except Exception as error:
        mensaje = traducir_error(error)
        if "incorrectos" in mensaje:
            mensaje = "La contraseña actual no es correcta."
        raise ErrorSistema(mensaje) from error

    try:
        supabase.auth.update_user({"password": nueva})
    except Exception as error:
        raise ErrorSistema(traducir_error(error)) from error


# ----------------------------------------------------------------------
# Administración de usuarios (sólo administradora; lo controla RLS)
# ----------------------------------------------------------------------

def listar_usuarios():
    return ejecutar(tabla("perfiles").select(CAMPOS_PERFIL).order("nombre"))


def _usuario_en_uso(nombre_usuario, excluir_id=None):
    filas = ejecutar(tabla("perfiles").select("id").ilike("usuario", patron_exacto(nombre_usuario)))
    return any(fila["id"] != excluir_id for fila in filas)


def crear_usuario(nombre, nombre_usuario, correo, contrasena, confirmacion, rol):
    if not sesion.es_admin():
        raise ErrorSistema("Sólo la administradora puede crear usuarios.")

    nombre = validaciones.texto_obligatorio(nombre, "Nombre", 2, 80)
    nombre_usuario = validaciones.nombre_usuario(nombre_usuario)
    correo = validaciones.email(correo, obligatorio=True)
    validaciones.contrasena(contrasena, confirmacion)
    if rol not in (ROL_ADMIN, ROL_CAJERA):
        raise ErrorSistema("Seleccioná un rol válido.")
    if _usuario_en_uso(nombre_usuario):
        raise ErrorSistema("Ese nombre de usuario ya está en uso.")

    # Cliente temporal: así la sesión de la administradora no se reemplaza.
    cliente = crear_cliente_temporal()
    try:
        respuesta = cliente.auth.sign_up({
            "email": correo,
            "password": contrasena,
            "options": {"data": {"nombre": nombre, "usuario": nombre_usuario}},
        })
    except Exception as error:
        raise ErrorSistema(traducir_error(error)) from error

    nuevo = respuesta.user
    if nuevo is None or getattr(nuevo, "identities", None) == []:
        raise ErrorSistema("Ya existe un usuario registrado con ese correo.")

    # El trigger de la base creó el perfil inactivo; la administradora lo habilita.
    actualizados = ejecutar(
        tabla("perfiles").update({
            "nombre": nombre,
            "usuario": nombre_usuario,
            "email": correo,
            "rol": rol,
            "activo": True,
        }).eq("id", nuevo.id)
    )
    if not actualizados:
        raise ErrorSistema(
            "El usuario se registró en Supabase Auth pero no se encontró su perfil. "
            "Verificá que se haya ejecutado sql/02_funciones.sql."
        )

    confirmado = getattr(nuevo, "email_confirmed_at", None) or getattr(nuevo, "confirmed_at", None)
    return bool(confirmado)


def actualizar_usuario(id_usuario, nombre, nombre_usuario, rol, activo):
    if not sesion.es_admin():
        raise ErrorSistema("Sólo la administradora puede modificar usuarios.")

    nombre = validaciones.texto_obligatorio(nombre, "Nombre", 2, 80)
    nombre_usuario = validaciones.nombre_usuario(nombre_usuario)
    if rol not in (ROL_ADMIN, ROL_CAJERA):
        raise ErrorSistema("Seleccioná un rol válido.")

    actual = sesion.actual()
    if id_usuario == actual.id and (rol != ROL_ADMIN or not activo):
        raise ErrorSistema("No podés quitarte el rol de administradora ni desactivar tu propia cuenta.")
    if _usuario_en_uso(nombre_usuario, excluir_id=id_usuario):
        raise ErrorSistema("Ese nombre de usuario ya está en uso.")

    filas = ejecutar(
        tabla("perfiles").update({
            "nombre": nombre,
            "usuario": nombre_usuario,
            "rol": rol,
            "activo": bool(activo),
        }).eq("id", id_usuario)
    )
    if not filas:
        raise ErrorSistema("No se pudo actualizar el usuario (verificá tus permisos).")
