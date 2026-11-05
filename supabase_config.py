
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

# Cargar las variables del archivo .env
RUTA_ENV = Path(__file__).resolve().parent / ".env"
load_dotenv(RUTA_ENV)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env"
    )

# Crear el cliente de Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
