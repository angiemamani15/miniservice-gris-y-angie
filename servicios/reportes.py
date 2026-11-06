"""
Reportes y estadísticas.

Los cálculos se hacen en PostgreSQL (funciones resumen_panel,
reporte_ventas, reporte_mas_vendidos, productos_stock_bajo) para que
sean exactos y rápidos aunque haya muchas ventas: Python sólo recibe el
resultado ya agregado.
"""

from datetime import date

from database import ejecutar, llamar_funcion, tabla
from servicios import validaciones

AGRUPACIONES = {"Diaria": "dia", "Semanal": "semana", "Mensual": "mes"}


def resumen_panel():
    return llamar_funcion("resumen_panel") or {}


def ventas_por_periodo(desde: date, hasta: date, agrupacion="dia"):
    validaciones.rango_fechas(desde, hasta)
    return llamar_funcion("reporte_ventas", {
        "p_desde": desde.isoformat(),
        "p_hasta": hasta.isoformat(),
        "p_agrupacion": agrupacion,
    }) or []


def mas_vendidos(desde: date, hasta: date, limite=10):
    validaciones.rango_fechas(desde, hasta)
    return llamar_funcion("reporte_mas_vendidos", {
        "p_desde": desde.isoformat(),
        "p_hasta": hasta.isoformat(),
        "p_limite": limite,
    }) or []


def stock_bajo():
    return llamar_funcion("productos_stock_bajo") or []


def totales(filas_periodo):
    """Suma las filas de ventas_por_periodo para las tarjetas del reporte."""
    ventas = sum(int(f.get("cantidad_ventas") or 0) for f in filas_periodo)
    ingresos = sum(float(f.get("ingresos") or 0) for f in filas_periodo)
    costo = sum(float(f.get("costo") or 0) for f in filas_periodo)
    return {
        "ventas": ventas,
        "ingresos": ingresos,
        "costo": costo,
        "ganancia": ingresos - costo,
        "ticket_promedio": ingresos / ventas if ventas else 0.0,
        "margen": ((ingresos - costo) / ingresos * 100) if ingresos else 0.0,
    }


# ----------------------------------------------------------------------
# Datos del negocio (Configuración)
# ----------------------------------------------------------------------

def obtener_negocio():
    filas = ejecutar(tabla("configuracion_negocio").select("*").eq("id", 1))
    return filas[0] if filas else {}


def guardar_negocio(nombre, direccion, telefono, email, cuit, mensaje):
    datos = {
        "nombre": validaciones.texto_obligatorio(nombre, "Nombre del negocio", 2, 80),
        "direccion": validaciones.texto_opcional(direccion, 150),
        "telefono": validaciones.telefono(telefono),
        "email": validaciones.email(email),
        "cuit": validaciones.texto_opcional(cuit, 20),
        "mensaje_comprobante": validaciones.texto_opcional(mensaje, 120),
    }
    return ejecutar(tabla("configuracion_negocio").update(datos).eq("id", 1))
