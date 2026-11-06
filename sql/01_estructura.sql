-- =====================================================================
-- Mini Service Gris y Angie
-- 01_estructura.sql
--
-- Crea las tablas que faltan y completa las existentes SIN borrar datos.
-- Es "idempotente": se puede ejecutar más de una vez sin duplicar nada.
--   * CREATE TABLE IF NOT EXISTS  -> crea la tabla sólo si no existe.
--   * ADD COLUMN IF NOT EXISTS    -> agrega columnas faltantes.
--   * Las restricciones se agregan sólo si no existen.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Funciones auxiliares temporales (sólo viven durante esta ejecución)
-- ---------------------------------------------------------------------

-- Agrega una restricción CHECK/UNIQUE si todavía no existe.
-- Se crea como NOT VALID para no fallar con datos viejos; luego intenta validarla.
create or replace function pg_temp.agregar_check(p_tabla regclass, p_nombre text, p_def text)
returns void language plpgsql as $$
begin
  if not exists (select 1 from pg_constraint where conrelid = p_tabla and conname = p_nombre) then
    execute format('alter table %s add constraint %I %s not valid', p_tabla, p_nombre, p_def);
    begin
      execute format('alter table %s validate constraint %I', p_tabla, p_nombre);
    exception when others then
      raise notice 'Restricción % creada pero hay datos antiguos que no la cumplen: %', p_nombre, sqlerrm;
    end;
  end if;
end $$;

-- Agrega una clave foránea si la columna todavía no referencia a esa tabla.
create or replace function pg_temp.agregar_fk(
  p_tabla regclass, p_columna text, p_referencia regclass, p_nombre text, p_al_borrar text default 'no action')
returns void language plpgsql as $$
declare
  v_attnum int2;
begin
  select attnum into v_attnum from pg_attribute
  where attrelid = p_tabla and attname = p_columna and not attisdropped;

  if not exists (
    select 1 from pg_constraint
    where conrelid = p_tabla and contype = 'f'
      and confrelid = p_referencia and conkey = array[v_attnum]
  ) then
    execute format(
      'alter table %s add constraint %I foreign key (%I) references %s(id) on delete %s not valid',
      p_tabla, p_nombre, p_columna, p_referencia, p_al_borrar);
    begin
      execute format('alter table %s validate constraint %I', p_tabla, p_nombre);
    exception when others then
      raise notice 'FK % creada pero hay datos antiguos inconsistentes: %', p_nombre, sqlerrm;
    end;
  end if;
end $$;

-- Crea un índice único si la columna no tiene ya uno.
create or replace function pg_temp.agregar_unico(p_tabla regclass, p_columna text, p_nombre text)
returns void language plpgsql as $$
declare
  v_attnum int2;
begin
  select attnum into v_attnum from pg_attribute
  where attrelid = p_tabla and attname = p_columna and not attisdropped;

  if not exists (
    select 1 from pg_index
    where indrelid = p_tabla and indisunique and indnatts = 1 and indkey[0] = v_attnum
  ) then
    begin
      execute format('create unique index %I on %s (%I)', p_nombre, p_tabla, p_columna);
    exception when others then
      raise notice 'No se pudo crear el índice único % (¿valores duplicados?): %', p_nombre, sqlerrm;
    end;
  end if;
end $$;

-- Quita las restricciones CHECK heredadas de una columna (salvo la nueva
-- p_excepto). Sólo borra la REGLA, nunca datos. Se usa antes de normalizar
-- valores viejos: si el CHECK anterior sólo admitía 'Efectivo', el UPDATE
-- a 'efectivo' fallaría mientras ese CHECK siga existiendo.
create or replace function pg_temp.quitar_checks(p_tabla regclass, p_columna text, p_excepto text)
returns void language plpgsql as $$
declare
  r record;
begin
  for r in
    select conname from pg_constraint
    where conrelid = p_tabla and contype = 'c'
      and pg_get_constraintdef(oid) ilike '%' || p_columna || '%'
      and conname <> p_excepto
  loop
    execute format('alter table %s drop constraint %I', p_tabla, r.conname);
  end loop;
end $$;

-- Reemplaza las restricciones CHECK de una columna por una nueva (se usa
-- en tablas heredadas cuyo CHECK sólo admitía 'Entrada'/'Salida').
create or replace function pg_temp.reemplazar_check(p_tabla regclass, p_columna text, p_nombre text, p_def text)
returns void language plpgsql as $$
begin
  perform pg_temp.quitar_checks(p_tabla, p_columna, p_nombre);
  perform pg_temp.agregar_check(p_tabla, p_nombre, p_def);
end $$;


-- =====================================================================
-- 1. PERFILES (usuarios del sistema)
--    La autenticación (correo + contraseña cifrada con bcrypt) la maneja
--    Supabase Auth en auth.users. Aquí guardamos rol y datos visibles.
-- =====================================================================
create table if not exists public.perfiles (
  id  uuid primary key references auth.users(id) on delete cascade,
  rol text not null default 'cajera'
);
alter table public.perfiles add column if not exists nombre    text;
alter table public.perfiles add column if not exists usuario   text;
alter table public.perfiles add column if not exists email     text;
-- Los perfiles existentes quedan activos; los nuevos nacen inactivos
-- hasta que la administradora los habilita.
alter table public.perfiles add column if not exists activo    boolean not null default true;
alter table public.perfiles alter column activo set default false;
alter table public.perfiles add column if not exists creado_en timestamptz not null default now();

-- Normalizar roles cargados a mano con mayúsculas o espacios
-- ('Administradora ', 'CAJERA'...). Sólo se corrigen esos dos valores;
-- cualquier otro rol queda como está y ese usuario no podrá ingresar.
update public.perfiles set rol = lower(btrim(rol))
where rol <> lower(btrim(rol))
  and lower(btrim(rol)) in ('administradora', 'cajera');

create unique index if not exists perfiles_usuario_unico
  on public.perfiles (lower(usuario)) where usuario is not null;

-- Copiar el correo de Supabase Auth (sólo para mostrarlo en Configuración).
update public.perfiles p set email = u.email
from auth.users u where u.id = p.id and p.email is distinct from u.email;

-- Completar nombre de usuario de perfiles antiguos a partir del correo.
do $$
declare
  r record;
  v_base text;
begin
  for r in
    select p.id, u.email from public.perfiles p
    join auth.users u on u.id = p.id
    where p.usuario is null
  loop
    v_base := lower(split_part(r.email, '@', 1));
    begin
      update public.perfiles set usuario = v_base,
             nombre = coalesce(nombre, v_base)
      where id = r.id;
    exception when unique_violation then
      update public.perfiles set usuario = v_base || '_' || left(r.id::text, 4),
             nombre = coalesce(nombre, v_base)
      where id = r.id;
    end;
  end loop;
end $$;

-- La regla de roles se agrega DESPUÉS de completar los datos: si hubiera
-- un perfil viejo con otro rol, la restricción queda "NOT VALID" (no lo
-- borra ni lo cambia), y si se agregara antes, los UPDATE de arriba
-- fallarían al tocar esa fila y abortarían todo el script.
select pg_temp.agregar_check('public.perfiles', 'perfiles_rol_valido',
  $c$check (rol in ('administradora', 'cajera'))$c$);


-- =====================================================================
-- 2. CATEGORÍAS
-- =====================================================================
create table if not exists public.categorias (
  id     bigint generated by default as identity primary key,
  nombre text not null
);
alter table public.categorias add column if not exists descripcion text;
alter table public.categorias add column if not exists creado_en   timestamptz not null default now();

select pg_temp.agregar_check('public.categorias', 'categorias_nombre_no_vacio',
  $c$check (length(btrim(nombre)) > 0)$c$);

do $$ begin
  create unique index if not exists categorias_nombre_unico
    on public.categorias (lower(btrim(nombre)));
exception when others then
  raise notice 'Hay categorías con nombre repetido; no se creó el índice único: %', sqlerrm;
end $$;

-- Categorías iniciales (sólo se agregan las que no existen)
insert into public.categorias (nombre)
select v.nombre
from (values ('Bebidas'), ('Almacén'), ('Golosinas'), ('Snacks'), ('Galletitas'),
             ('Lácteos'), ('Limpieza'), ('Higiene personal'), ('Otros')) as v(nombre)
where not exists (
  select 1 from public.categorias c where lower(btrim(c.nombre)) = lower(v.nombre)
);


-- =====================================================================
-- 3. PRODUCTOS
-- =====================================================================
create table if not exists public.productos (
  id            bigint generated by default as identity primary key,
  codigo        text not null,
  nombre        text not null,
  categoria_id  bigint,
  precio_compra numeric(12,2) not null default 0,
  precio_venta  numeric(12,2) not null default 0,
  stock         integer not null default 0,
  stock_minimo  integer not null default 5
);
alter table public.productos add column if not exists activo         boolean not null default true;
alter table public.productos add column if not exists creado_en      timestamptz not null default now();
alter table public.productos add column if not exists actualizado_en timestamptz not null default now();

select pg_temp.agregar_fk('public.productos', 'categoria_id', 'public.categorias', 'productos_categoria_fk');
select pg_temp.agregar_unico('public.productos', 'codigo', 'productos_codigo_unico');
select pg_temp.agregar_check('public.productos', 'productos_precios_validos',
  $c$check (precio_compra >= 0 and precio_venta >= 0)$c$);
select pg_temp.agregar_check('public.productos', 'productos_stock_no_negativo',
  $c$check (stock >= 0 and stock_minimo >= 0)$c$);

create index if not exists productos_nombre_idx    on public.productos (lower(nombre));
create index if not exists productos_categoria_idx on public.productos (categoria_id);


-- =====================================================================
-- 4. PROVEEDORES y productos que suministra cada uno
-- =====================================================================
create table if not exists public.proveedores (
  id               bigint generated by default as identity primary key,
  nombre_comercial text not null,
  telefono         text,
  email            text,
  direccion        text
);
alter table public.proveedores add column if not exists nombre_comercial text;
alter table public.proveedores add column if not exists telefono  text;
alter table public.proveedores add column if not exists email     text;
alter table public.proveedores add column if not exists direccion text;
alter table public.proveedores add column if not exists activo    boolean not null default true;
alter table public.proveedores add column if not exists creado_en timestamptz not null default now();

-- Si existía una versión anterior con columna "nombre", se copia.
do $$ begin
  if exists (select 1 from information_schema.columns
             where table_schema = 'public' and table_name = 'proveedores' and column_name = 'nombre') then
    execute 'update public.proveedores set nombre_comercial = nombre where nombre_comercial is null';
    -- El programa ahora sólo escribe nombre_comercial: si la columna vieja
    -- era obligatoria, los proveedores nuevos no se podrían guardar.
    -- Se quita sólo la obligación (los datos de "nombre" se conservan).
    execute 'alter table public.proveedores alter column nombre drop not null';
  end if;
end $$;

do $$ begin
  create unique index if not exists proveedores_nombre_unico
    on public.proveedores (lower(btrim(nombre_comercial)));
exception when others then
  raise notice 'Hay proveedores con nombre repetido: %', sqlerrm;
end $$;

create table if not exists public.proveedores_productos (
  proveedor_id bigint not null references public.proveedores(id) on delete cascade,
  producto_id  bigint not null references public.productos(id)   on delete cascade,
  primary key (proveedor_id, producto_id)
);
create index if not exists proveedores_productos_producto_idx on public.proveedores_productos (producto_id);


-- =====================================================================
-- 5. COMPRAS de mercadería
-- =====================================================================
create table if not exists public.compras (
  id                bigint generated by default as identity primary key,
  proveedor_id      bigint not null,
  usuario_id        uuid,
  fecha             timestamptz not null default now(),
  total             numeric(12,2) not null default 0,
  observacion       text,
  pagada_desde_caja boolean not null default false
);
select pg_temp.agregar_fk('public.compras', 'proveedor_id', 'public.proveedores', 'compras_proveedor_fk');
select pg_temp.agregar_fk('public.compras', 'usuario_id',   'public.perfiles',    'compras_usuario_fk');
select pg_temp.agregar_check('public.compras', 'compras_total_valido', $c$check (total >= 0)$c$);
create index if not exists compras_fecha_idx on public.compras (fecha desc);

create table if not exists public.detalle_compras (
  id             bigint generated by default as identity primary key,
  compra_id      bigint not null,
  producto_id    bigint not null,
  cantidad       integer not null,
  costo_unitario numeric(12,2) not null,
  subtotal       numeric(12,2) not null
);
select pg_temp.agregar_fk('public.detalle_compras', 'compra_id',   'public.compras',   'detalle_compras_compra_fk', 'cascade');
select pg_temp.agregar_fk('public.detalle_compras', 'producto_id', 'public.productos', 'detalle_compras_producto_fk');
select pg_temp.agregar_check('public.detalle_compras', 'detalle_compras_valores',
  $c$check (cantidad > 0 and costo_unitario >= 0 and subtotal >= 0)$c$);
create index if not exists detalle_compras_compra_idx   on public.detalle_compras (compra_id);
create index if not exists detalle_compras_producto_idx on public.detalle_compras (producto_id);


-- =====================================================================
-- 6. VENTAS
-- =====================================================================
create table if not exists public.ventas (
  id          bigint generated by default as identity primary key,
  fecha       timestamptz not null default now(),
  total       numeric(12,2) not null,
  metodo_pago text not null
);
alter table public.ventas add column if not exists usuario_id     uuid;
alter table public.ventas add column if not exists monto_recibido numeric(12,2);
alter table public.ventas add column if not exists vuelto         numeric(12,2) not null default 0;

-- Normalizar valores de versiones anteriores ('Efectivo' -> 'efectivo').
-- Primero se quita el CHECK viejo (si no, el UPDATE lo violaría).
select pg_temp.quitar_checks('public.ventas', 'metodo_pago', 'ventas_metodo_pago_valido');
update public.ventas set metodo_pago = lower(btrim(metodo_pago))
where metodo_pago <> lower(btrim(metodo_pago));

select pg_temp.agregar_fk('public.ventas', 'usuario_id', 'public.perfiles', 'ventas_usuario_fk');
select pg_temp.agregar_check('public.ventas', 'ventas_total_valido', $c$check (total >= 0 and vuelto >= 0)$c$);
select pg_temp.reemplazar_check('public.ventas', 'metodo_pago', 'ventas_metodo_pago_valido',
  $c$check (metodo_pago in ('efectivo', 'transferencia', 'tarjeta'))$c$);
create index if not exists ventas_fecha_idx   on public.ventas (fecha desc);
create index if not exists ventas_usuario_idx on public.ventas (usuario_id);

create table if not exists public.detalle_ventas (
  id              bigint generated by default as identity primary key,
  venta_id        bigint not null,
  producto_id     bigint not null,
  cantidad        integer not null,
  precio_unitario numeric(12,2) not null,
  subtotal        numeric(12,2) not null
);
-- Costo del producto al momento de la venta: permite calcular ganancias reales.
alter table public.detalle_ventas add column if not exists costo_unitario numeric(12,2) not null default 0;

select pg_temp.agregar_fk('public.detalle_ventas', 'venta_id',    'public.ventas',    'detalle_ventas_venta_fk', 'cascade');
select pg_temp.agregar_fk('public.detalle_ventas', 'producto_id', 'public.productos', 'detalle_ventas_producto_fk');
select pg_temp.agregar_check('public.detalle_ventas', 'detalle_ventas_valores',
  $c$check (cantidad > 0 and precio_unitario >= 0 and subtotal >= 0)$c$);
create index if not exists detalle_ventas_venta_idx    on public.detalle_ventas (venta_id);
create index if not exists detalle_ventas_producto_idx on public.detalle_ventas (producto_id);


-- =====================================================================
-- 7. MOVIMIENTOS DE INVENTARIO (historial de stock)
-- =====================================================================
create table if not exists public.movimientos_inventario (
  id          bigint generated by default as identity primary key,
  producto_id bigint not null,
  fecha       timestamptz not null default now(),
  tipo        text not null,
  cantidad    integer not null,
  motivo      text not null
);
alter table public.movimientos_inventario add column if not exists usuario_id     uuid;
alter table public.movimientos_inventario add column if not exists stock_anterior integer;
alter table public.movimientos_inventario add column if not exists stock_nuevo    integer;
alter table public.movimientos_inventario add column if not exists venta_id       bigint;
alter table public.movimientos_inventario add column if not exists compra_id      bigint;

select pg_temp.agregar_fk('public.movimientos_inventario', 'producto_id', 'public.productos', 'mov_inv_producto_fk');
select pg_temp.agregar_fk('public.movimientos_inventario', 'usuario_id',  'public.perfiles',  'mov_inv_usuario_fk');
select pg_temp.agregar_fk('public.movimientos_inventario', 'venta_id',    'public.ventas',    'mov_inv_venta_fk');
select pg_temp.agregar_fk('public.movimientos_inventario', 'compra_id',   'public.compras',   'mov_inv_compra_fk');
select pg_temp.reemplazar_check('public.movimientos_inventario', 'tipo', 'mov_inv_tipo_valido',
  $c$check (tipo in ('Entrada', 'Salida', 'Ajuste', 'Venta', 'Compra'))$c$);
select pg_temp.agregar_check('public.movimientos_inventario', 'mov_inv_cantidad_positiva',
  $c$check (cantidad > 0)$c$);
create index if not exists mov_inv_fecha_idx    on public.movimientos_inventario (fecha desc);
create index if not exists mov_inv_producto_idx on public.movimientos_inventario (producto_id, fecha desc);


-- =====================================================================
-- 8. MOVIMIENTOS DE CAJA
-- =====================================================================
create table if not exists public.movimientos_caja (
  id       bigint generated by default as identity primary key,
  fecha    timestamptz not null default now(),
  tipo     text not null,
  concepto text not null,
  monto    numeric(12,2) not null
);
alter table public.movimientos_caja add column if not exists usuario_id  uuid;
alter table public.movimientos_caja add column if not exists metodo_pago text not null default 'efectivo';
alter table public.movimientos_caja add column if not exists venta_id    bigint;
alter table public.movimientos_caja add column if not exists compra_id   bigint;

-- Igual que en ventas: quitar el CHECK viejo antes de normalizar ('ingreso' -> 'Ingreso').
select pg_temp.quitar_checks('public.movimientos_caja', 'tipo', 'mov_caja_tipo_valido');
update public.movimientos_caja set tipo = initcap(btrim(tipo))
where tipo <> initcap(btrim(tipo));

select pg_temp.agregar_fk('public.movimientos_caja', 'usuario_id', 'public.perfiles', 'mov_caja_usuario_fk');
select pg_temp.agregar_fk('public.movimientos_caja', 'venta_id',   'public.ventas',   'mov_caja_venta_fk');
select pg_temp.agregar_fk('public.movimientos_caja', 'compra_id',  'public.compras',  'mov_caja_compra_fk');
select pg_temp.reemplazar_check('public.movimientos_caja', 'tipo', 'mov_caja_tipo_valido',
  $c$check (tipo in ('Ingreso', 'Egreso'))$c$);
select pg_temp.agregar_check('public.movimientos_caja', 'mov_caja_monto_positivo', $c$check (monto > 0)$c$);
select pg_temp.agregar_check('public.movimientos_caja', 'mov_caja_metodo_valido',
  $c$check (metodo_pago in ('efectivo', 'transferencia', 'tarjeta'))$c$);
create index if not exists mov_caja_fecha_idx on public.movimientos_caja (fecha desc);


-- =====================================================================
-- 9. CONFIGURACIÓN DEL NEGOCIO (una sola fila)
-- =====================================================================
create table if not exists public.configuracion_negocio (
  id                  integer primary key default 1 check (id = 1),
  nombre              text not null default 'Mini Service Gris y Angie',
  direccion           text,
  telefono            text,
  email               text,
  cuit                text,
  mensaje_comprobante text default '¡Gracias por su compra!',
  actualizado_en      timestamptz not null default now()
);
insert into public.configuracion_negocio (id) values (1) on conflict (id) do nothing;
