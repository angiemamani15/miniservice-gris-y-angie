"""Proveedores, productos que suministran y compras de mercadería."""

from database import (
    ErrorSistema, ejecutar, llamar_funcion, obtener_todos, patron_exacto, rango_del_dia, tabla,
)
from servicios import validaciones

CAMPOS = "id,nombre_comercial,telefono,email,direccion,activo"


def listar_proveedores(solo_activos=False):
    q = tabla("proveedores").select(CAMPOS + ",proveedores_productos(count)").order("nombre_comercial")
    if solo_activos:
        q = q.eq("activo", True)
    filas = ejecutar(q)
    for fila in filas:
        conteo = fila.pop("proveedores_productos", None) or [{"count": 0}]
        fila["cantidad_productos"] = conteo[0].get("count", 0)
    return filas


def _validar(nombre, telefono, email, direccion):
    return {
        "nombre_comercial": validaciones.texto_obligatorio(nombre, "Nombre comercial", 2, 100),
        "telefono": validaciones.telefono(telefono),
        "email": validaciones.email(email),
        "direccion": validaciones.texto_opcional(direccion, 150),
    }


def _nombre_repetido(nombre, excluir_id=None):
    filas = ejecutar(tabla("proveedores").select("id").ilike("nombre_comercial", patron_exacto(nombre)))
    return any(fila["id"] != excluir_id for fila in filas)


def crear_proveedor(nombre, telefono, email, direccion):
    datos = _validar(nombre, telefono, email, direccion)
    if _nombre_repetido(datos["nombre_comercial"]):
        raise ErrorSistema("Ya existe un proveedor con ese nombre comercial.")
    return ejecutar(tabla("proveedores").insert(datos))


def actualizar_proveedor(id_proveedor, nombre, telefono, email, direccion, activo=True):
    datos = _validar(nombre, telefono, email, direccion)
    datos["activo"] = bool(activo)
    if _nombre_repetido(datos["nombre_comercial"], excluir_id=id_proveedor):
        raise ErrorSistema("Ya existe otro proveedor con ese nombre comercial.")
    return ejecutar(tabla("proveedores").update(datos).eq("id", id_proveedor))


def eliminar_proveedor(id_proveedor):
    if ejecutar(tabla("compras").select("id").eq("proveedor_id", id_proveedor).limit(1)):
        raise ErrorSistema(
            "El proveedor tiene compras registradas y no puede eliminarse. "
            "Podés marcarlo como inactivo."
        )
    ejecutar(tabla("proveedores").delete().eq("id", id_proveedor))


# ----------------------------------------------------------------------
# Productos suministrados
# ----------------------------------------------------------------------

def productos_del_proveedor(id_proveedor):
    filas = ejecutar(
        tabla("proveedores_productos")
        .select("producto_id,productos(codigo,nombre,precio_compra,stock)")
        .eq("proveedor_id", id_proveedor)
    )
    resultado = []
    for fila in filas:
        producto = fila.get("productos") or {}
        producto["id"] = fila["producto_id"]
        resultado.append(producto)
    return sorted(resultado, key=lambda p: (p.get("nombre") or "").lower())


def asignar_producto(id_proveedor, id_producto):
    ejecutar(tabla("proveedores_productos").upsert(
        {"proveedor_id": id_proveedor, "producto_id": id_producto},
        ignore_duplicates=True,
    ))


def quitar_producto(id_proveedor, id_producto):
    ejecutar(
        tabla("proveedores_productos").delete()
        .eq("proveedor_id", id_proveedor).eq("producto_id", id_producto)
    )


# ----------------------------------------------------------------------
# Compras
# ----------------------------------------------------------------------

def registrar_compra(id_proveedor, items, observacion="", pagada_desde_caja=False,
                     actualizar_costo=True):
    """items: lista de dicts con producto_id, cantidad y costo_unitario."""
    if id_proveedor is None:
        raise ErrorSistema("Seleccioná un proveedor.")
    if not items:
        raise ErrorSistema("Agregá al menos un producto a la compra.")
    return llamar_funcion("registrar_compra", {
        "p_proveedor_id": id_proveedor,
        "p_items": [
            {
                "producto_id": item["producto_id"],
                "cantidad": int(item["cantidad"]),
                "costo_unitario": float(item["costo_unitario"]),
            }
            for item in items
        ],
        "p_observacion": validaciones.texto_opcional(observacion, 200),
        "p_pagada_desde_caja": bool(pagada_desde_caja),
        "p_actualizar_costo": bool(actualizar_costo),
    })


def listar_compras(desde, hasta, id_proveedor=None):
    validaciones.rango_fechas(desde, hasta)
    inicio, fin = rango_del_dia(desde, hasta)

    def consulta():
        q = (
            tabla("compras")
            .select("id,fecha,total,observacion,pagada_desde_caja,proveedores(nombre_comercial),"
                    "perfiles(nombre,usuario),detalle_compras(count)")
            .gte("fecha", inicio)
            .lt("fecha", fin)
            .order("fecha", desc=True)
        )
        if id_proveedor:
            q = q.eq("proveedor_id", id_proveedor)
        return q

    return obtener_todos(consulta)


def obtener_compra(id_compra):
    filas = ejecutar(
        tabla("compras")
        .select("id,fecha,total,observacion,pagada_desde_caja,proveedores(nombre_comercial),"
                "perfiles(nombre,usuario),"
                "detalle_compras(cantidad,costo_unitario,subtotal,productos(codigo,nombre))")
        .eq("id", id_compra)
    )
    if not filas:
        raise ErrorSistema("No se encontró la compra.")
    return filas[0]
