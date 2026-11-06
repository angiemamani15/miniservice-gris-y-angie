"""
Productos y categorías (operaciones CRUD).

CRUD = Create (insert), Read (select), Update (update), Delete (delete).
Cada función valida los datos antes de enviarlos a Supabase; la base de
datos vuelve a validar con restricciones (UNIQUE, CHECK, claves foráneas).
"""

from database import ErrorSistema, ejecutar, obtener_todos, patron_exacto, tabla
from servicios import validaciones

CAMPOS_PRODUCTO = (
    "id,codigo,nombre,categoria_id,precio_compra,precio_venta,"
    "stock,stock_minimo,activo,categorias(nombre)"
)


# ----------------------------------------------------------------------
# CATEGORÍAS
# ----------------------------------------------------------------------

def listar_categorias(con_cantidad=False):
    campos = "id,nombre,descripcion"
    if con_cantidad:
        # productos(count): Supabase cuenta los productos de cada categoría.
        campos += ",productos(count)"
    filas = ejecutar(tabla("categorias").select(campos).order("nombre"))
    if con_cantidad:
        for fila in filas:
            conteo = fila.pop("productos", None) or [{"count": 0}]
            fila["cantidad_productos"] = conteo[0].get("count", 0)
    return filas


def _validar_categoria(nombre, descripcion):
    return {
        "nombre": validaciones.texto_obligatorio(nombre, "Nombre de la categoría", 2, 60),
        "descripcion": validaciones.texto_opcional(descripcion, 200),
    }


def _categoria_repetida(nombre, excluir_id=None):
    filas = ejecutar(tabla("categorias").select("id").ilike("nombre", patron_exacto(nombre)))
    return any(fila["id"] != excluir_id for fila in filas)


def crear_categoria(nombre, descripcion=""):
    datos = _validar_categoria(nombre, descripcion)
    if _categoria_repetida(datos["nombre"]):
        raise ErrorSistema("Ya existe una categoría con ese nombre.")
    return ejecutar(tabla("categorias").insert(datos))


def actualizar_categoria(id_categoria, nombre, descripcion=""):
    datos = _validar_categoria(nombre, descripcion)
    if _categoria_repetida(datos["nombre"], excluir_id=id_categoria):
        raise ErrorSistema("Ya existe una categoría con ese nombre.")
    return ejecutar(tabla("categorias").update(datos).eq("id", id_categoria))


def eliminar_categoria(id_categoria):
    asociados = ejecutar(
        tabla("productos").select("id").eq("categoria_id", id_categoria).limit(1)
    )
    if asociados:
        raise ErrorSistema(
            "No se puede eliminar la categoría porque tiene productos asociados. "
            "Cambiá la categoría de esos productos primero."
        )
    ejecutar(tabla("categorias").delete().eq("id", id_categoria))


# ----------------------------------------------------------------------
# PRODUCTOS
# ----------------------------------------------------------------------

def listar_productos(solo_activos=False):
    def consulta():
        q = tabla("productos").select(CAMPOS_PRODUCTO).order("nombre")
        if solo_activos:
            q = q.eq("activo", True)
        return q

    productos = obtener_todos(consulta)
    for producto in productos:
        categoria = producto.pop("categorias", None) or {}
        producto["categoria"] = categoria.get("nombre") or "Sin categoría"
    return productos


def codigo_en_uso(codigo, excluir_id=None):
    filas = ejecutar(tabla("productos").select("id").eq("codigo", codigo))
    return any(fila["id"] != excluir_id for fila in filas)


def validar_producto(codigo, nombre, categoria_id, precio_compra, precio_venta,
                     stock, stock_minimo, es_nuevo=True):
    codigo = validaciones.texto_obligatorio(codigo, "Código / código de barras", 1, 40)
    if " " in codigo:
        raise ErrorSistema("El código no puede contener espacios.")
    datos = {
        "codigo": codigo,
        "nombre": validaciones.texto_obligatorio(nombre, "Nombre del producto", 2, 120),
        "categoria_id": categoria_id,
        "precio_compra": validaciones.decimal(precio_compra, "Precio de compra"),
        "precio_venta": validaciones.decimal(precio_venta, "Precio de venta", permitir_cero=False),
        "stock_minimo": validaciones.entero(stock_minimo, "Stock mínimo"),
    }
    if categoria_id is None:
        raise ErrorSistema("Seleccioná una categoría.")
    if es_nuevo:
        datos["stock"] = validaciones.entero(stock, "Stock inicial")
    return datos


def crear_producto(datos):
    if codigo_en_uso(datos["codigo"]):
        raise ErrorSistema("Ya existe un producto con ese código.")
    return ejecutar(tabla("productos").insert(datos))


def actualizar_producto(id_producto, datos):
    # El stock no se edita aquí: se modifica desde Inventario para que
    # quede registrado en el historial de movimientos.
    datos = {clave: valor for clave, valor in datos.items() if clave != "stock"}
    if codigo_en_uso(datos["codigo"], excluir_id=id_producto):
        raise ErrorSistema("Ya existe otro producto con ese código.")
    return ejecutar(tabla("productos").update(datos).eq("id", id_producto))


def movimientos_asociados(id_producto):
    """Indica si el producto tiene ventas, compras o movimientos de stock."""
    for nombre_tabla in ("detalle_ventas", "detalle_compras", "movimientos_inventario"):
        if ejecutar(tabla(nombre_tabla).select("id").eq("producto_id", id_producto).limit(1)):
            return True
    return False


def eliminar_producto(id_producto):
    if movimientos_asociados(id_producto):
        raise ErrorSistema(
            "El producto tiene ventas, compras o movimientos de stock registrados, "
            "por lo que no puede eliminarse sin perder el historial."
        )
    ejecutar(tabla("productos").delete().eq("id", id_producto))


def cambiar_estado_producto(id_producto, activo):
    ejecutar(tabla("productos").update({"activo": bool(activo)}).eq("id", id_producto))
