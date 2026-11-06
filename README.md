# Mini Service Gris y Angie — Sistema de gestión comercial

Aplicación de escritorio para administrar un miniservice (pequeño supermercado):
ventas con carrito y comprobante, caja, productos, categorías, inventario,
proveedores y compras, reportes con gráficos y exportación, y usuarios con roles.

**Tecnologías:** Python · CustomTkinter (interfaz) · Supabase/PostgreSQL (base de datos) ·
Matplotlib (gráficos) · openpyxl (Excel) · reportlab (PDF) · python-dotenv (credenciales).

---

## 1. Instalación

```bash
pip install -r requirements.txt
```

Copiá `.env.example` como `.env` y completá los datos de **Supabase > Project Settings > API**:

```
SUPABASE_URL=https://TU-PROYECTO.supabase.co
SUPABASE_KEY=tu_clave_anon_publica
```

> Usá siempre la clave pública **anon / publishable**. Nunca la clave `service_role`:
> la seguridad la aplica la base de datos con políticas RLS.

## 2. Preparar la base de datos (una sola vez)

En **Supabase > SQL Editor** ejecutá, en este orden, los archivos de la carpeta `sql/`:

| Archivo | Qué hace |
|---|---|
| `00_diagnostico.sql` | (Opcional, sólo lectura) muestra las tablas, restricciones y políticas actuales. |
| `01_estructura.sql` | Crea las tablas que faltan y completa las existentes **sin borrar datos**. Carga las categorías iniciales. |
| `02_funciones.sql` | Funciones transaccionales (venta, compra, inventario, caja, reportes) y triggers de integridad. |
| `03_seguridad.sql` | Activa RLS y define qué puede hacer cada rol. **Reemplaza las políticas RLS anteriores** de estas tablas. |

Los scripts se pueden volver a ejecutar sin duplicar nada.

**Usuarios:** los perfiles que ya existían quedan activos con su rol. Si el proyecto
es nuevo, creá el primer usuario en *Authentication > Users > Add user* y luego ejecutá:

```sql
update public.perfiles set rol = 'administradora', activo = true, usuario = 'gris', nombre = 'Gris'
where email = 'correo@ejemplo.com';
```

Desde ese momento la administradora puede crear más usuarios en **Configuración > Usuarios**.
Si en *Authentication > Providers > Email* está activado **Confirm email**, cada usuario nuevo
deberá confirmar su correo antes de ingresar (para un uso local conviene desactivarlo).

Para verificar la conexión: `python probar_supabase.py`

## 3. Ejecutar

```bash
python main.py
```

Se ingresa con **nombre de usuario o correo** y contraseña.

| Sección | Administradora | Cajera |
|---|:---:|:---:|
| Inicio (panel) | ✔ | ✔ |
| Ventas e historial | ✔ | ✔ |
| Caja | ✔ | ✔ |
| Inventario | ✔ (registrar) | ✔ (sólo consulta) |
| Productos, Categorías, Proveedores, Reportes | ✔ | ✖ |
| Configuración | ✔ (incluye usuarios) | ✔ (su sesión y contraseña) |

---

## 4. Estructura del código

```
main.py            Ventana principal, menú lateral, navegación y permisos
login.py           Pantalla de inicio de sesión
inicio.py          Panel principal (tarjetas, gráfico, últimas ventas, más vendidos)
ventas.py          Punto de venta (carrito, pago, vuelto) e historial
comprobantes.py    Comprobante de venta (pantalla y PDF)
caja.py            Resumen diario, ingresos/egresos y arqueo
productos.py       CRUD de productos
categorias.py      CRUD de categorías
inventario.py      Existencias, historial de movimientos y entradas/salidas/ajustes
proveedores.py     Proveedores, productos suministrados, compras e historial
reportes.py        Reportes, gráficos y exportación
configuracion.py   Sesión, contraseña, datos del negocio y usuarios
exportar.py        Generación de Excel y PDF
componentes.py     Piezas visuales reutilizables (tablas, tarjetas, campos, fechas)
config.py          Colores, roles, permisos y constantes
sesion.py          Usuario que inició sesión
database.py        Acceso a Supabase: ejecutar consultas, paginar y traducir errores
supabase_config.py Conexión con Supabase (lee el .env)
servicios/         Lógica de negocio y consultas (una capa por tema)
sql/               Scripts de la base de datos
```

El código está en capas: **pantalla → servicio → Supabase**. Las pantallas sólo manejan
la interfaz; los servicios validan los datos y hacen las consultas; la base de datos
vuelve a validar con restricciones y controla los permisos.

> La versión anterior usaba también una base SQLite local (`database.py`) para el panel y
> el inventario, mientras productos estaba en Supabase. Ahora todo usa Supabase, así los
> datos son siempre los mismos en todas las pantallas.

---

## 5. Guía para la defensa

### ¿Cómo funciona Python en el sistema?
`main.py` crea la ventana (`ctk.CTk`) y el menú lateral. Cada sección es una **clase** que
hereda de `CTkFrame` en su propio archivo; al hacer clic en el menú, `mostrar_seccion()`
destruye la pantalla anterior y crea la nueva, por eso los datos se recargan al entrar.
Los errores se capturan con `try/except` (`ejecutar_seguro()` en `componentes.py`) y se
muestran en un mensaje: el programa no se cierra ante un error de conexión o de datos.

### ¿Cómo se conecta con Supabase?
`supabase_config.py` lee `SUPABASE_URL` y `SUPABASE_KEY` del `.env` con `python-dotenv`
y crea el cliente con `create_client()`. Al iniciar sesión, Supabase Auth devuelve un
**token (JWT)** y la librería lo envía en cada consulta. Con ese token PostgreSQL sabe
quién consulta y aplica las políticas RLS de su rol.

### ¿Cómo se almacenan los datos?
En PostgreSQL (Supabase) con tablas relacionadas por **claves foráneas**:
`categorias → productos → detalle_ventas ← ventas`, `proveedores → compras → detalle_compras`,
`movimientos_inventario` (historial de stock) y `movimientos_caja` (dinero).
Restricciones `CHECK` impiden precios o stock negativos, `UNIQUE` impide códigos repetidos.
Las contraseñas **no** están en nuestras tablas: Supabase Auth las guarda cifradas con bcrypt.

### ¿Cómo funcionan las operaciones CRUD?
Ejemplo en `servicios/catalogo.py`:
- **Create:** `tabla("productos").insert(datos)`
- **Read:** `tabla("productos").select("...,categorias(nombre)").order("nombre")`
- **Update:** `tabla("productos").update(datos).eq("id", id)`
- **Delete:** `tabla("productos").delete().eq("id", id)` — antes se verifica que no tenga
  ventas ni movimientos; si los tiene, se ofrece **desactivarlo** para no perder el historial.

### ¿Cómo se registra una venta?
1. La cajera arma el carrito (Python controla que no supere el stock que ve en pantalla).
2. Al confirmar, `servicios/operaciones.registrar_venta()` llama a la función SQL
   `registrar_venta()` (`sql/02_funciones.sql`), que en **una sola transacción**:
   - bloquea los productos con `SELECT ... FOR UPDATE` (control de concurrencia: si dos
     cajas venden lo mismo a la vez, la segunda espera y ve el stock actualizado);
   - verifica stock, toma los precios **de la base** (no del programa) y calcula el total;
   - valida el pago y el vuelto;
   - inserta la venta, el detalle (con el costo para calcular ganancias), descuenta el
     stock, registra el movimiento de inventario y el ingreso en caja.
3. Si cualquier paso falla, PostgreSQL **deshace todo** (no queda una venta a medias).
4. Se muestra el comprobante, que puede guardarse en PDF.

### ¿Cómo se actualiza el inventario?
El stock sólo cambia por funciones que dejan registro en `movimientos_inventario` con el
usuario, el motivo y el stock anterior/nuevo: ventas, compras y movimientos manuales
(entrada, salida, ajuste). Un **trigger** impide modificar el stock directamente desde la
tabla, y la restricción `stock >= 0` evita stock negativo.

### ¿Cómo se implementan los roles?
En dos niveles:
1. **Interfaz:** `config.PERMISOS` define qué secciones ve cada rol; el menú sólo muestra
   las permitidas y `mostrar_seccion()` vuelve a verificarlo.
2. **Base de datos (lo importante):** políticas RLS (`sql/03_seguridad.sql`). Por ejemplo,
   aunque alguien modificara el programa, una cajera no puede cambiar precios ni registrar
   compras, porque PostgreSQL lo rechaza. Los usuarios nuevos nacen **inactivos** hasta que
   la administradora los habilita.

### ¿Cómo se generan los reportes?
Las funciones SQL `reporte_ventas()` y `reporte_mas_vendidos()` agrupan las ventas reales
por día, semana o mes (`date_trunc`) y calculan ingresos, costo y ganancia estimada
(`subtotal − costo_unitario × cantidad`, con el costo guardado al momento de la venta).
Python recibe los totales, los muestra en tarjetas y tablas, dibuja los gráficos con
Matplotlib dentro de la ventana y los exporta a Excel (openpyxl) o PDF (reportlab).
