"""
Configuración general del sistema: identidad visual, roles y permisos.

Centralizar estos valores evita repetirlos en cada pantalla y permite
cambiar, por ejemplo, un color o un permiso en un solo lugar.
"""

from datetime import timedelta, timezone

# ----------------------------------------------------------------------
# Identidad del negocio
# ----------------------------------------------------------------------
NOMBRE_NEGOCIO = "Mini Service Gris y Angie"
VERSION = "2.0"

# Argentina usa UTC-3 todo el año. Se usa para filtrar "ventas del día".
ZONA_HORARIA = timezone(timedelta(hours=-3))

# ----------------------------------------------------------------------
# Paleta de colores (identidad visual original del proyecto)
# ----------------------------------------------------------------------
VERDE_OSCURO = "#18392B"
VERDE = "#166534"
VERDE_HOVER = "#15803D"
VERDE_MENU = "#285943"
VERDE_CLARO = "#DCEFE2"
VERDE_SUAVE = "#EAF5ED"
FONDO = "#F4F8F5"
BLANCO = "#FFFFFF"
GRIS = "#64756B"
GRIS_HOVER = "#4B5B51"
BORDE = "#DFEAE2"
TEXTO = "#18392B"
ROJO = "#B91C1C"
ROJO_HOVER = "#991B1B"
ROJO_CLARO = "#FDE8E8"
AMARILLO = "#B45309"
AMARILLO_CLARO = "#FEF3C7"
AZUL = "#1D4ED8"

FUENTE = "Arial"

# ----------------------------------------------------------------------
# Roles y permisos
# ----------------------------------------------------------------------
ROL_ADMIN = "administradora"
ROL_CAJERA = "cajera"

# Secciones del menú lateral: (nombre, icono)
SECCIONES = [
    ("Inicio", "⌂"),
    ("Ventas", "◉"),
    ("Caja", "$"),
    ("Productos", "▣"),
    ("Categorías", "☰"),
    ("Inventario", "▤"),
    ("Proveedores", "♧"),
    ("Reportes", "▥"),
    ("Configuración", "⚙"),
]

PERMISOS = {
    ROL_ADMIN: {nombre for nombre, _ in SECCIONES},
    # La cajera vende, maneja la caja y consulta stock (sin modificarlo).
    ROL_CAJERA: {"Inicio", "Ventas", "Caja", "Inventario", "Configuración"},
}

METODOS_PAGO = {
    "efectivo": "Efectivo",
    "transferencia": "Transferencia",
    "tarjeta": "Tarjeta",
}
