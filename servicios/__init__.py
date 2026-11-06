"""
Servicios: lógica de negocio y consultas a Supabase.

Las pantallas (archivos de la raíz como productos.py o ventas.py) sólo
manejan la interfaz y llaman a estas funciones. Así cada parte tiene una
responsabilidad clara:

    Pantalla (CustomTkinter)  ->  Servicio (validaciones + consultas)  ->  Supabase
"""
