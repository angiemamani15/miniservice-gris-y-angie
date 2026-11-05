
from supabase_config import supabase

try:
    resultado = supabase.auth.get_session()

    print("Cliente de Supabase configurado correctamente.")
    print("La aplicación está preparada para autenticarse.")

except Exception as error:
    print("Ocurrió un error:")
    print(error)
