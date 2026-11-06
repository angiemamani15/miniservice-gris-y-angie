"""
Operaciones que modifican stock o dinero: inventario, ventas y caja.

Todas se ejecutan mediante funciones SQL transaccionales (RPC) definidas
en sql/02_funciones.sql. Python arma los datos y valida lo básico; la
base de datos bloquea las filas, controla el stock y guarda todo junto.
"""

from config import METODOS_PAGO
from database import (
    ErrorSistema, ejecutar, llamar_funcion, obtener_todos, rango_del_dia, tabla,
)
from servicios import validaciones

TIPOS_INVENTARIO = ("Entrada", "Salida", "Ajuste")


# ----------------------------------------------------------------------
# INVENTARIO
# ----------------------------------------------------------------------

def registrar_movimiento_inventario(producto_id, tipo, cantidad, motivo):
    if producto_id is None:
        raise ErrorSistema("Seleccioná un producto.")
    if tipo not in TIPOS_INVENTARIO:
        raise ErrorSistema("Seleccioná un tipo de movimiento válido.")
    if tipo == "Ajuste":
        cantidad = validaciones.entero(cantidad, "Nuevo stock", minimo=0)
    else:
        cantidad = validaciones.entero(cantidad, "Cantidad", minimo=1)
    motivo = validaciones.texto_obligatorio(motivo, "Motivo", 3, 200)

    return llamar_funcion("registrar_movimiento_inventario", {
        "p_producto_id": producto_id,
        "p_tipo": tipo,
        "p_cantidad": cantidad,
        "p_motivo": motivo,
    })


def listar_movimientos_inventario(desde, hasta, producto_id=None, tipo=None):
    validaciones.rango_fechas(desde, hasta)
    inicio, fin = rango_del_dia(desde, hasta)

    def consulta():
        q = (
            tabla("movimientos_inventario")
            .select(
                "id,fecha,tipo,cantidad,motivo,stock_anterior,stock_nuevo,"
                "productos(codigo,nombre),perfiles(nombre,usuario)"
            )
            .gte("fecha", inicio)
            .lt("fecha", fin)
            .order("fecha", desc=True)
        )
        if producto_id:
            q = q.eq("producto_id", producto_id)
        if tipo:
            q = q.eq("tipo", tipo)
        return q

    return obtener_todos(consulta)


# ----------------------------------------------------------------------
# VENTAS
# ----------------------------------------------------------------------

def registrar_venta(carrito, metodo_pago, monto_recibido=None):
    """carrito: lista de dicts con producto_id y cantidad.

    Devuelve {venta_id, fecha, total, monto_recibido, vuelto}.
    """
    if not carrito:
        raise ErrorSistema("El carrito está vacío.")
    if metodo_pago not in METODOS_PAGO:
        raise ErrorSistema("Seleccioná un método de pago.")

    items = []
    for item in carrito:
        cantidad = int(item["cantidad"])
        if cantidad <= 0:
            raise ErrorSistema(f"La cantidad de «{item.get('nombre', '')}» debe ser mayor a cero.")
        items.append({"producto_id": item["producto_id"], "cantidad": cantidad})

    recibido = None
    if metodo_pago == "efectivo":
        recibido = validaciones.decimal(monto_recibido, "Monto recibido", permitir_cero=False)

    return llamar_funcion("registrar_venta", {
        "p_items": items,
        "p_metodo_pago": metodo_pago,
        "p_monto_recibido": recibido,
    })


def listar_ventas(desde, hasta):
    validaciones.rango_fechas(desde, hasta)
    inicio, fin = rango_del_dia(desde, hasta)
    return obtener_todos(lambda: (
        tabla("ventas")
        .select("id,fecha,total,metodo_pago,monto_recibido,vuelto,perfiles(nombre,usuario),detalle_ventas(count)")
        .gte("fecha", inicio)
        .lt("fecha", fin)
        .order("fecha", desc=True)
    ))


def obtener_venta(venta_id):
    filas = ejecutar(
        tabla("ventas")
        .select(
            "id,fecha,total,metodo_pago,monto_recibido,vuelto,perfiles(nombre,usuario),"
            "detalle_ventas(cantidad,precio_unitario,subtotal,productos(codigo,nombre))"
        )
        .eq("id", venta_id)
    )
    if not filas:
        raise ErrorSistema("No se encontró la venta.")
    return filas[0]


# ----------------------------------------------------------------------
# CAJA
# ----------------------------------------------------------------------

def resumen_caja(dia):
    return llamar_funcion("resumen_caja", {"p_dia": dia.isoformat()}) or {}


def listar_movimientos_caja(desde, hasta):
    validaciones.rango_fechas(desde, hasta)
    inicio, fin = rango_del_dia(desde, hasta)
    return obtener_todos(lambda: (
        tabla("movimientos_caja")
        .select("id,fecha,tipo,concepto,monto,metodo_pago,venta_id,compra_id,perfiles(nombre,usuario)")
        .gte("fecha", inicio)
        .lt("fecha", fin)
        .order("fecha", desc=True)
    ))


def registrar_movimiento_caja(tipo, concepto, monto):
    if tipo not in ("Ingreso", "Egreso"):
        raise ErrorSistema("Seleccioná si es un ingreso o un egreso.")
    concepto = validaciones.texto_obligatorio(concepto, "Concepto", 3, 150)
    monto = validaciones.decimal(monto, "Monto", permitir_cero=False)
    return llamar_funcion("registrar_movimiento_caja", {
        "p_tipo": tipo,
        "p_concepto": concepto,
        "p_monto": monto,
        "p_metodo_pago": "efectivo",
    })
