"""
Prueba de conexión y diagnóstico de la base de datos en Supabase.

Uso:  python probar_supabase.py

1. Verifica que el archivo .env tenga las credenciales.
2. Comprueba que, SIN iniciar sesión, las tablas estén protegidas (RLS).
3. Pide usuario y contraseña, inicia sesión y verifica que existan todas
   las tablas y funciones que usa el sistema.
No modifica ningún dato.
"""

from getpass import getpass

TABLAS = [
    "perfiles", "categorias", "productos", "proveedores", "proveedores_productos", "compras",
    "detalle_compras", "ventas", "detalle_ventas", "movimientos_inventario", "movimientos_caja",
    "configuracion_negocio",
]


def main():
    print("=== Mini Service Gris y Angie - Diagnóstico de Supabase ===\n")
    try:
        from supabase_config import SUPABASE_URL
    except Exception as error:
        print("✗ No se pudo crear el cliente:", error)
        print("  Revisá que exista el archivo .env (copiá .env.example).")
        return
    print("✓ Cliente configurado para", SUPABASE_URL)

    from database import ErrorSistema, ejecutar, llamar_funcion, tabla

    # Sin sesión: la tabla productos no debería ser accesible.
    try:
        filas = ejecutar(tabla("productos").select("id").limit(1))
        if filas:
            print("⚠ Sin iniciar sesión se pueden leer productos: falta ejecutar sql/03_seguridad.sql")
        else:
            print("✓ Conexión correcta (sin sesión no se ven datos)")
    except ErrorSistema as error:
        if "permisos" in str(error):
            print("✓ Conexión correcta y tablas protegidas para usuarios sin sesión (RLS)")
        else:
            print("✗ Error de conexión:", error)
            return

    usuario = input("\nUsuario o correo para probar el login (Enter para omitir): ").strip()
    if not usuario:
        return
    contrasena = getpass("Contraseña: ")

    from servicios import autenticacion
    try:
        sesion = autenticacion.iniciar_sesion(usuario, contrasena)
    except ErrorSistema as error:
        print("✗ Login:", error)
        return
    print(f"✓ Sesión iniciada: {sesion.nombre} ({sesion.rol_legible})\n")

    for nombre in TABLAS:
        try:
            ejecutar(tabla(nombre).select("*").limit(1))
            print(f"  ✓ tabla {nombre}")
        except ErrorSistema as error:
            print(f"  ✗ tabla {nombre}: {error}")

    for funcion, parametros in [("resumen_panel", {}), ("productos_stock_bajo", {})]:
        try:
            llamar_funcion(funcion, parametros)
            print(f"  ✓ función {funcion}")
        except ErrorSistema as error:
            print(f"  ✗ función {funcion}: {error}")

    autenticacion.cerrar_sesion()
    print("\nDiagnóstico finalizado.")


if __name__ == "__main__":
    main()
