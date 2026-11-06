"""
Conexión con Supabase.

Las credenciales se leen del archivo .env (que NO se sube a GitHub).
Se usa la clave pública "anon": es segura para una app cliente porque
la base de datos protege cada tabla con políticas RLS según el usuario
que inició sesión. Nunca se debe usar aquí la clave "service_role".
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import ClientOptions, create_client

# Cargar las variables del archivo .env
RUTA_ENV = Path(__file__).resolve().parent / ".env"
load_dotenv(RUTA_ENV)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env"
    )

# Cliente principal: después del login, cada consulta viaja con el
# token del usuario, y Supabase aplica las reglas de su rol.
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def crear_cliente_temporal():
    """Crea un cliente independiente que no guarda sesión.

    Se usa para que la administradora registre usuarios nuevos sin que
    su propia sesión sea reemplazada por la del usuario creado.
    """
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(
            persist_session=False,
            auto_refresh_token=False,
        ),
    )
