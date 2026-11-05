
import sqlite3
from pathlib import Path

# Ubicación de la base de datos
DB_PATH = Path(__file__).resolve().parent / "minisuper.db"


def conectar():
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_base_datos():
    conexion = conectar()
    cursor = conexion.cursor()

    # 1. Categorías
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)

    # 2. Productos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            categoria_id INTEGER,
            precio_compra REAL NOT NULL DEFAULT 0,
            precio_venta REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 5,
            FOREIGN KEY (categoria_id)
                REFERENCES categorias(id)
        )
    """)

    # 3. Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            email TEXT,
            direccion TEXT
        )
    """)

    # 4. Proveedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            email TEXT,
            direccion TEXT
        )
    """)

    # 5. Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'cajero'
        )
    """)

    # 6. Ventas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            total REAL NOT NULL,
            metodo_pago TEXT NOT NULL,
            FOREIGN KEY (cliente_id)
                REFERENCES clientes(id)
        )
    """)

    # 7. Detalle de ventas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (venta_id)
                REFERENCES ventas(id),
            FOREIGN KEY (producto_id)
                REFERENCES productos(id)
        )
    """)

    # 8. Movimientos de caja
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_caja (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL,
            concepto TEXT NOT NULL,
            monto REAL NOT NULL
        )
    """)

    # 9. Movimientos de inventario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL CHECK (
                tipo IN ('Entrada', 'Salida')
            ),
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            motivo TEXT NOT NULL,
            FOREIGN KEY (producto_id)
                REFERENCES productos(id)
        )
    """)

    # 10. Categorías iniciales del supermercado
    categorias = [
        ("Almacén",),
        ("Bebidas",),
        ("Lácteos",),
        ("Limpieza",),
        ("Higiene personal",),
        ("Golosinas y snacks",),
        ("Panadería",),
        ("Congelados",),
        ("Frutas y verduras",),
        ("Carnicería",),
        ("Otros",)
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO categorias (nombre)
        VALUES (?)
    """, categorias)

    # Guardar los cambios
    conexion.commit()
    conexion.close()

    print("Base de datos creada correctamente")
    print("Categorías del supermercado cargadas correctamente")


if __name__ == "__main__":
    crear_base_datos()
