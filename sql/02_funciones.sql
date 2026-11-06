-- =====================================================================
-- Mini Service Gris y Angie
-- 02_funciones.sql
--
-- Funciones y triggers de PostgreSQL. Las operaciones que modifican
-- varias tablas a la vez (venta, compra, movimiento de inventario)
-- se ejecutan como UNA transacción: si cualquier paso falla, PostgreSQL
-- deshace todo (no quedan ventas incompletas ni stock mal descontado).
--
-- Se pueden ejecutar varias veces (CREATE OR REPLACE).
-- =====================================================================


-- =====================================================================
-- 1. AUXILIARES DE FECHA Y ROLES
-- =====================================================================

-- Inicio de un día en la hora local del negocio (Argentina).
create or replace function public.inicio_dia_local(p_dia date)
returns timestamptz
language sql stable
set search_path = public
as $$
  select p_dia::timestamp at time zone 'America/Argentina/Buenos_Aires'
$$;

-- Fecha local de un instante.
create or replace function public.fecha_local(p_instante timestamptz)
returns date
language sql stable
set search_path = public
as $$
  select (p_instante at time zone 'America/Argentina/Buenos_Aires')::date
$$;

-- Rol del usuario autenticado (null si no tiene perfil activo).
-- SECURITY DEFINER: lee perfiles sin depender de las políticas RLS
-- (evita recursión en las políticas de la propia tabla perfiles).
create or replace function public.rol_actual()
returns text
language sql stable security definer
set search_path = public
as $$
  select p.rol from public.perfiles p
  where p.id = auth.uid() and p.activo
$$;

create or replace function public.es_usuario_activo()
returns boolean
language sql stable security definer
set search_path = public
as $$
  select exists (select 1 from public.perfiles p where p.id = auth.uid() and p.activo)
$$;

create or replace function public.es_admin()
returns boolean
language sql stable security definer
set search_path = public
as $$
  select exists (
    select 1 from public.perfiles p
    where p.id = auth.uid() and p.activo and p.rol = 'administradora'
  )
$$;

-- Corta la operación si el usuario no tiene uno de los roles indicados.
-- Devuelve el id del usuario para registrarlo en la operación.
create or replace function public.exigir_rol(p_roles text[])
returns uuid
language plpgsql stable security definer
set search_path = public
as $$
declare
  v_rol text := public.rol_actual();
begin
  if v_rol is null or not (v_rol = any (p_roles)) then
    raise exception 'No tenés permisos para realizar esta operación.'
      using errcode = '42501';
  end if;
  return auth.uid();
end $$;


-- =====================================================================
-- 2. TRIGGERS DE INTEGRIDAD
-- =====================================================================

-- 2.a Productos: fecha de actualización y protección del stock.
-- El stock sólo cambia mediante las funciones de inventario/venta/compra,
-- que dejan registro en movimientos_inventario.
create or replace function public.tg_productos_antes_actualizar()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.actualizado_en := now();

  if new.stock is distinct from old.stock
     and coalesce(current_setting('app.movimiento_stock', true), '') <> 'si'
     and auth.uid() is not null then
    raise exception 'El stock sólo puede modificarse desde Inventario, Ventas o Compras.';
  end if;

  return new;
end $$;

drop trigger if exists trg_productos_antes_actualizar on public.productos;
create trigger trg_productos_antes_actualizar
  before update on public.productos
  for each row execute function public.tg_productos_antes_actualizar();

-- 2.b Productos: el stock inicial queda registrado como movimiento.
create or replace function public.tg_productos_stock_inicial()
returns trigger
language plpgsql security definer
set search_path = public
as $$
begin
  if new.stock > 0 then
    insert into public.movimientos_inventario
      (producto_id, usuario_id, tipo, cantidad, motivo, stock_anterior, stock_nuevo)
    values
      (new.id, auth.uid(), 'Entrada', new.stock, 'Stock inicial al registrar el producto', 0, new.stock);
  end if;
  return new;
end $$;

drop trigger if exists trg_productos_stock_inicial on public.productos;
create trigger trg_productos_stock_inicial
  after insert on public.productos
  for each row execute function public.tg_productos_stock_inicial();

-- 2.c Perfiles: siempre debe quedar al menos una administradora activa.
create or replace function public.tg_perfiles_proteger_admin()
returns trigger
language plpgsql security definer
set search_path = public
as $$
begin
  if old.rol = 'administradora' and old.activo
     and (new.rol <> 'administradora' or not new.activo) then
    if not exists (
      select 1 from public.perfiles
      where id <> old.id and rol = 'administradora' and activo
    ) then
      raise exception 'Debe quedar al menos una administradora activa.';
    end if;
  end if;
  return new;
end $$;

drop trigger if exists trg_perfiles_proteger_admin on public.perfiles;
create trigger trg_perfiles_proteger_admin
  before update on public.perfiles
  for each row execute function public.tg_perfiles_proteger_admin();

-- 2.d Nuevo usuario de Supabase Auth -> perfil INACTIVO con rol cajera.
-- Así, aunque alguien se registre con la clave pública, no obtiene acceso:
-- la administradora debe activarlo y asignarle el rol.
create or replace function public.tg_crear_perfil_usuario()
returns trigger
language plpgsql security definer
set search_path = public
as $$
declare
  v_nombre  text := nullif(btrim(new.raw_user_meta_data ->> 'nombre'), '');
  v_usuario text := nullif(lower(btrim(new.raw_user_meta_data ->> 'usuario')), '');
begin
  begin
    insert into public.perfiles (id, nombre, usuario, email, rol, activo)
    values (new.id, v_nombre, v_usuario, new.email, 'cajera', false)
    on conflict (id) do nothing;
  exception when unique_violation then
    insert into public.perfiles (id, nombre, usuario, email, rol, activo)
    values (new.id, v_nombre, null, new.email, 'cajera', false)
    on conflict (id) do nothing;
  end;
  return new;
end $$;

drop trigger if exists trg_crear_perfil_usuario on auth.users;
create trigger trg_crear_perfil_usuario
  after insert on auth.users
  for each row execute function public.tg_crear_perfil_usuario();


-- =====================================================================
-- 3. LOGIN CON NOMBRE DE USUARIO
-- Devuelve el correo asociado a un nombre de usuario activo, para que
-- Supabase Auth valide la contraseña. Nunca devuelve contraseñas.
-- =====================================================================
create or replace function public.email_para_login(p_usuario text)
returns text
language sql stable security definer
set search_path = public, auth
as $$
  select u.email::text
  from auth.users u
  join public.perfiles p on p.id = u.id
  where lower(p.usuario) = lower(btrim(p_usuario)) and p.activo
  limit 1
$$;


-- =====================================================================
-- 4. REGISTRAR VENTA (transacción atómica)
--
-- p_items: [{"producto_id": 1, "cantidad": 2}, ...]
-- Los precios se toman de la base de datos (no del programa), para que
-- nadie pueda alterar el importe desde el cliente.
--
-- Control de concurrencia: SELECT ... FOR UPDATE bloquea las filas de
-- los productos vendidos hasta que termina la transacción. Si dos cajas
-- venden el mismo producto a la vez, la segunda espera y luego ve el
-- stock ya descontado, por lo que nunca se vende stock inexistente.
-- Los productos se bloquean ordenados por id para evitar interbloqueos.
-- =====================================================================
create or replace function public.registrar_venta(
  p_items          jsonb,
  p_metodo_pago    text,
  p_monto_recibido numeric default null
)
returns jsonb
language plpgsql security definer
set search_path = public
as $$
declare
  v_usuario  uuid := public.exigir_rol(array['administradora', 'cajera']);
  v_item     record;
  v_producto record;
  v_total    numeric(12,2) := 0;
  v_recibido numeric(12,2);
  v_vuelto   numeric(12,2) := 0;
  v_venta_id bigint;
  v_fecha    timestamptz;
begin
  if p_metodo_pago is null or p_metodo_pago not in ('efectivo', 'transferencia', 'tarjeta') then
    raise exception 'Método de pago inválido.';
  end if;

  if p_items is null or jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
    raise exception 'El carrito está vacío.';
  end if;

  -- Paso 1: bloquear productos, validar stock y calcular el total.
  for v_item in
    select (e ->> 'producto_id')::bigint as producto_id,
           sum((e ->> 'cantidad')::integer) as cantidad
    from jsonb_array_elements(p_items) e
    group by 1
    order by 1
  loop
    if v_item.producto_id is null or v_item.cantidad is null or v_item.cantidad <= 0 then
      raise exception 'Hay un producto con cantidad inválida en el carrito.';
    end if;

    select id, nombre, precio_venta, stock, activo
      into v_producto
    from public.productos
    where id = v_item.producto_id
    for update;

    if not found then
      raise exception 'El producto con id % no existe.', v_item.producto_id;
    end if;
    if not v_producto.activo then
      raise exception 'El producto "%" está desactivado.', v_producto.nombre;
    end if;
    if v_producto.stock < v_item.cantidad then
      raise exception 'Stock insuficiente para "%": disponible %, solicitado %.',
        v_producto.nombre, v_producto.stock, v_item.cantidad;
    end if;

    v_total := v_total + round(v_producto.precio_venta::numeric * v_item.cantidad, 2);
  end loop;

  -- Paso 2: validar el pago.
  if p_metodo_pago = 'efectivo' then
    v_recibido := coalesce(p_monto_recibido, 0);
    if v_recibido < v_total then
      raise exception 'El monto recibido ($ %) es menor al total ($ %).', v_recibido, v_total;
    end if;
    v_vuelto := v_recibido - v_total;
  else
    v_recibido := v_total;
  end if;

  -- Paso 3: cabecera de la venta.
  insert into public.ventas (usuario_id, total, metodo_pago, monto_recibido, vuelto)
  values (v_usuario, v_total, p_metodo_pago, v_recibido, v_vuelto)
  returning id, fecha into v_venta_id, v_fecha;

  perform set_config('app.movimiento_stock', 'si', true);

  -- Paso 4: detalle, descuento de stock y movimiento de inventario.
  for v_item in
    select (e ->> 'producto_id')::bigint as producto_id,
           sum((e ->> 'cantidad')::integer) as cantidad
    from jsonb_array_elements(p_items) e
    group by 1
    order by 1
  loop
    select id, precio_venta, precio_compra, stock
      into v_producto
    from public.productos
    where id = v_item.producto_id;

    insert into public.detalle_ventas
      (venta_id, producto_id, cantidad, precio_unitario, costo_unitario, subtotal)
    values
      (v_venta_id, v_producto.id, v_item.cantidad, round(v_producto.precio_venta::numeric, 2),
       round(v_producto.precio_compra::numeric, 2), round(v_producto.precio_venta::numeric * v_item.cantidad, 2));

    update public.productos
       set stock = stock - v_item.cantidad
     where id = v_producto.id;

    insert into public.movimientos_inventario
      (producto_id, usuario_id, tipo, cantidad, motivo, stock_anterior, stock_nuevo, venta_id)
    values
      (v_producto.id, v_usuario, 'Venta', v_item.cantidad, 'Venta #' || v_venta_id,
       v_producto.stock, v_producto.stock - v_item.cantidad, v_venta_id);
  end loop;

  -- Paso 5: ingreso en caja.
  if v_total > 0 then
    insert into public.movimientos_caja (usuario_id, tipo, concepto, monto, metodo_pago, venta_id)
    values (v_usuario, 'Ingreso', 'Venta #' || v_venta_id, v_total, p_metodo_pago, v_venta_id);
  end if;

  return jsonb_build_object(
    'venta_id', v_venta_id,
    'fecha', v_fecha,
    'total', v_total,
    'monto_recibido', v_recibido,
    'vuelto', v_vuelto
  );
end $$;


-- =====================================================================
-- 5. MOVIMIENTO MANUAL DE INVENTARIO (sólo administradora)
--   Entrada -> suma p_cantidad
--   Salida  -> resta p_cantidad (no permite stock negativo)
--   Ajuste  -> p_cantidad es el NUEVO stock real (conteo físico)
-- =====================================================================
create or replace function public.registrar_movimiento_inventario(
  p_producto_id bigint,
  p_tipo        text,
  p_cantidad    integer,
  p_motivo      text
)
returns jsonb
language plpgsql security definer
set search_path = public
as $$
declare
  v_usuario uuid := public.exigir_rol(array['administradora']);
  v_stock   integer;
  v_nombre  text;
  v_nuevo   integer;
  v_mov     integer;
begin
  if p_tipo is null or p_tipo not in ('Entrada', 'Salida', 'Ajuste') then
    raise exception 'Tipo de movimiento inválido.';
  end if;
  if p_motivo is null or length(btrim(p_motivo)) < 3 then
    raise exception 'Indicá el motivo del movimiento.';
  end if;
  if p_cantidad is null or p_cantidad < 0 or (p_tipo <> 'Ajuste' and p_cantidad = 0) then
    raise exception 'La cantidad debe ser un número entero mayor a cero.';
  end if;

  select stock, nombre into v_stock, v_nombre
  from public.productos
  where id = p_producto_id
  for update;

  if not found then
    raise exception 'El producto no existe.';
  end if;

  if p_tipo = 'Entrada' then
    v_nuevo := v_stock + p_cantidad;
    v_mov   := p_cantidad;
  elsif p_tipo = 'Salida' then
    if p_cantidad > v_stock then
      raise exception 'Stock insuficiente para "%": disponible %, solicitado %.', v_nombre, v_stock, p_cantidad;
    end if;
    v_nuevo := v_stock - p_cantidad;
    v_mov   := p_cantidad;
  else
    v_nuevo := p_cantidad;
    v_mov   := abs(p_cantidad - v_stock);
    if v_mov = 0 then
      raise exception 'El stock de "%" ya es %; no hay diferencia para ajustar.', v_nombre, v_stock;
    end if;
  end if;

  perform set_config('app.movimiento_stock', 'si', true);

  update public.productos set stock = v_nuevo where id = p_producto_id;

  insert into public.movimientos_inventario
    (producto_id, usuario_id, tipo, cantidad, motivo, stock_anterior, stock_nuevo)
  values
    (p_producto_id, v_usuario, p_tipo, v_mov, btrim(p_motivo), v_stock, v_nuevo);

  return jsonb_build_object('producto', v_nombre, 'stock_anterior', v_stock, 'stock_nuevo', v_nuevo);
end $$;


-- =====================================================================
-- 6. REGISTRAR COMPRA A PROVEEDOR (transacción atómica, administradora)
-- p_items: [{"producto_id": 1, "cantidad": 24, "costo_unitario": 850.50}, ...]
-- Suma stock, registra movimientos, actualiza el precio de compra y
-- vincula el producto con el proveedor.
-- =====================================================================
create or replace function public.registrar_compra(
  p_proveedor_id      bigint,
  p_items             jsonb,
  p_observacion       text    default null,
  p_pagada_desde_caja boolean default false,
  p_actualizar_costo  boolean default true
)
returns jsonb
language plpgsql security definer
set search_path = public
as $$
declare
  v_usuario   uuid := public.exigir_rol(array['administradora']);
  v_item      record;
  v_stock     integer;
  v_total     numeric(12,2) := 0;
  v_compra_id bigint;
  v_proveedor text;
begin
  select nombre_comercial into v_proveedor
  from public.proveedores where id = p_proveedor_id and activo;
  if not found then
    raise exception 'El proveedor no existe o está inactivo.';
  end if;

  if p_items is null or jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
    raise exception 'La compra no tiene productos.';
  end if;

  insert into public.compras (proveedor_id, usuario_id, observacion, pagada_desde_caja)
  values (p_proveedor_id, v_usuario, nullif(btrim(p_observacion), ''), coalesce(p_pagada_desde_caja, false))
  returning id into v_compra_id;

  perform set_config('app.movimiento_stock', 'si', true);

  for v_item in
    select (e ->> 'producto_id')::bigint      as producto_id,
           (e ->> 'cantidad')::integer        as cantidad,
           round((e ->> 'costo_unitario')::numeric, 2) as costo
    from jsonb_array_elements(p_items) e
    order by 1
  loop
    if v_item.producto_id is null or v_item.cantidad is null or v_item.cantidad <= 0 then
      raise exception 'Hay un producto con cantidad inválida.';
    end if;
    if v_item.costo is null or v_item.costo < 0 then
      raise exception 'Hay un producto con costo inválido.';
    end if;

    select stock into v_stock from public.productos where id = v_item.producto_id for update;
    if not found then
      raise exception 'El producto con id % no existe.', v_item.producto_id;
    end if;

    insert into public.detalle_compras (compra_id, producto_id, cantidad, costo_unitario, subtotal)
    values (v_compra_id, v_item.producto_id, v_item.cantidad, v_item.costo,
            round(v_item.costo * v_item.cantidad, 2));

    update public.productos
       set stock = stock + v_item.cantidad,
           precio_compra = case when p_actualizar_costo then v_item.costo else precio_compra end
     where id = v_item.producto_id;

    insert into public.movimientos_inventario
      (producto_id, usuario_id, tipo, cantidad, motivo, stock_anterior, stock_nuevo, compra_id)
    values
      (v_item.producto_id, v_usuario, 'Compra', v_item.cantidad,
       'Compra #' || v_compra_id || ' - ' || v_proveedor, v_stock, v_stock + v_item.cantidad, v_compra_id);

    insert into public.proveedores_productos (proveedor_id, producto_id)
    values (p_proveedor_id, v_item.producto_id)
    on conflict do nothing;

    v_total := v_total + round(v_item.costo * v_item.cantidad, 2);
  end loop;

  update public.compras set total = v_total where id = v_compra_id;

  if coalesce(p_pagada_desde_caja, false) and v_total > 0 then
    insert into public.movimientos_caja (usuario_id, tipo, concepto, monto, metodo_pago, compra_id)
    values (v_usuario, 'Egreso', 'Compra #' || v_compra_id || ' - ' || v_proveedor, v_total, 'efectivo', v_compra_id);
  end if;

  return jsonb_build_object('compra_id', v_compra_id, 'total', v_total);
end $$;


-- =====================================================================
-- 7. CAJA
-- =====================================================================

-- Ingreso o egreso manual de dinero (ambos roles).
create or replace function public.registrar_movimiento_caja(
  p_tipo        text,
  p_concepto    text,
  p_monto       numeric,
  p_metodo_pago text default 'efectivo'
)
returns bigint
language plpgsql security definer
set search_path = public
as $$
declare
  v_usuario uuid := public.exigir_rol(array['administradora', 'cajera']);
  v_id      bigint;
begin
  if p_tipo not in ('Ingreso', 'Egreso') then
    raise exception 'Tipo de movimiento de caja inválido.';
  end if;
  if p_concepto is null or length(btrim(p_concepto)) < 3 then
    raise exception 'Indicá el concepto del movimiento.';
  end if;
  if p_monto is null or p_monto <= 0 then
    raise exception 'El monto debe ser mayor a cero.';
  end if;

  insert into public.movimientos_caja (usuario_id, tipo, concepto, monto, metodo_pago)
  values (v_usuario, p_tipo, btrim(p_concepto), round(p_monto, 2), coalesce(p_metodo_pago, 'efectivo'))
  returning id into v_id;

  return v_id;
end $$;

-- Resumen de caja de un día: ventas por medio de pago y efectivo esperado.
create or replace function public.resumen_caja(p_dia date)
returns jsonb
language plpgsql stable security invoker
set search_path = public
as $$
declare
  v_desde timestamptz := public.inicio_dia_local(p_dia);
  v_hasta timestamptz := public.inicio_dia_local(p_dia + 1);
  r jsonb;
begin
  perform public.exigir_rol(array['administradora', 'cajera']);

  select jsonb_build_object(
    'cantidad_ventas',      count(*) filter (where venta_id is not null),
    'ventas_efectivo',      coalesce(sum(monto) filter (where venta_id is not null and metodo_pago = 'efectivo'), 0),
    'ventas_transferencia', coalesce(sum(monto) filter (where venta_id is not null and metodo_pago = 'transferencia'), 0),
    'ventas_tarjeta',       coalesce(sum(monto) filter (where venta_id is not null and metodo_pago = 'tarjeta'), 0),
    'otros_ingresos',       coalesce(sum(monto) filter (where venta_id is null and tipo = 'Ingreso' and metodo_pago = 'efectivo'), 0),
    'egresos',              coalesce(sum(monto) filter (where tipo = 'Egreso' and metodo_pago = 'efectivo'), 0),
    'efectivo_esperado',    coalesce(sum(case when metodo_pago <> 'efectivo' then 0
                                              when tipo = 'Ingreso' then monto else -monto end), 0)
  ) into r
  from public.movimientos_caja
  where fecha >= v_desde and fecha < v_hasta;

  return r;
end $$;


-- =====================================================================
-- 8. PANEL PRINCIPAL Y REPORTES (leen datos reales con las reglas RLS)
-- =====================================================================

create or replace function public.resumen_panel()
returns jsonb
language plpgsql stable security invoker
set search_path = public
as $$
declare
  v_hoy   date := public.fecha_local(now());
  v_desde timestamptz := public.inicio_dia_local(v_hoy);
  v_hasta timestamptz := public.inicio_dia_local(v_hoy + 1);
begin
  perform public.exigir_rol(array['administradora', 'cajera']);

  return jsonb_build_object(
    'total_productos', (select count(*) from public.productos where activo),
    'stock_bajo',      (select count(*) from public.productos where activo and stock <= stock_minimo),
    'ventas_hoy',      (select count(*) from public.ventas where fecha >= v_desde and fecha < v_hasta),
    'ingresos_hoy',    (select coalesce(sum(total), 0) from public.ventas where fecha >= v_desde and fecha < v_hasta),

    'ventas_semana', (
      select coalesce(jsonb_agg(jsonb_build_object(
               'fecha', d.dia, 'total', coalesce(t.total, 0), 'cantidad', coalesce(t.cantidad, 0))
             order by d.dia), '[]'::jsonb)
      from (select (v_hoy - g)::date as dia from generate_series(0, 6) g) d
      left join (
        select public.fecha_local(fecha) as dia, sum(total) as total, count(*) as cantidad
        from public.ventas
        where fecha >= public.inicio_dia_local(v_hoy - 6)
        group by 1
      ) t on t.dia = d.dia
    ),

    'ultimas_ventas', (
      select coalesce(jsonb_agg(x order by x.fecha desc), '[]'::jsonb)
      from (
        select v.id, v.fecha, v.total, v.metodo_pago,
               coalesce(p.nombre, p.usuario, '-') as vendedor
        from public.ventas v
        left join public.perfiles p on p.id = v.usuario_id
        order by v.fecha desc
        limit 8
      ) x
    ),

    'mas_vendidos', (
      select coalesce(jsonb_agg(x order by x.cantidad desc), '[]'::jsonb)
      from (
        select pr.nombre, sum(dv.cantidad) as cantidad, sum(dv.subtotal) as importe
        from public.detalle_ventas dv
        join public.ventas v     on v.id = dv.venta_id
        join public.productos pr on pr.id = dv.producto_id
        where v.fecha >= public.inicio_dia_local(v_hoy - 29)
        group by pr.nombre
        order by 2 desc
        limit 5
      ) x
    )
  );
end $$;

-- Ventas agrupadas por día, semana o mes, con costo y ganancia estimada.
create or replace function public.reporte_ventas(
  p_desde      date,
  p_hasta      date,
  p_agrupacion text default 'dia'
)
returns table (periodo date, cantidad_ventas bigint, ingresos numeric, costo numeric, ganancia numeric)
language plpgsql stable security invoker
set search_path = public
as $$
#variable_conflict use_column
declare
  v_trunc text := case p_agrupacion when 'semana' then 'week' when 'mes' then 'month' else 'day' end;
begin
  perform public.exigir_rol(array['administradora']);

  return query
  with v as (
    select ve.id,
           date_trunc(v_trunc, ve.fecha at time zone 'America/Argentina/Buenos_Aires')::date as periodo,
           ve.total
    from public.ventas ve
    where ve.fecha >= public.inicio_dia_local(p_desde)
      and ve.fecha <  public.inicio_dia_local(p_hasta + 1)
  ),
  c as (
    select dv.venta_id, sum(dv.costo_unitario * dv.cantidad) as costo
    from public.detalle_ventas dv
    join v on v.id = dv.venta_id
    group by dv.venta_id
  )
  select v.periodo,
         count(*)::bigint,
         sum(v.total)::numeric,
         coalesce(sum(c.costo), 0)::numeric,
         (sum(v.total) - coalesce(sum(c.costo), 0))::numeric
  from v
  left join c on c.venta_id = v.id
  group by v.periodo
  order by v.periodo;
end $$;

-- Ranking de productos más vendidos en un rango de fechas.
create or replace function public.reporte_mas_vendidos(
  p_desde  date,
  p_hasta  date,
  p_limite integer default 10
)
returns table (producto_id bigint, codigo text, nombre text, cantidad bigint, ingresos numeric, ganancia numeric)
language plpgsql stable security invoker
set search_path = public
as $$
#variable_conflict use_column
begin
  perform public.exigir_rol(array['administradora']);

  return query
  select pr.id::bigint, pr.codigo::text, pr.nombre::text,
         sum(dv.cantidad)::bigint,
         sum(dv.subtotal)::numeric,
         sum(dv.subtotal - dv.costo_unitario * dv.cantidad)::numeric
  from public.detalle_ventas dv
  join public.ventas v     on v.id = dv.venta_id
  join public.productos pr on pr.id = dv.producto_id
  where v.fecha >= public.inicio_dia_local(p_desde)
    and v.fecha <  public.inicio_dia_local(p_hasta + 1)
  group by pr.id, pr.codigo, pr.nombre
  order by 4 desc, 5 desc
  limit greatest(coalesce(p_limite, 10), 1);
end $$;

-- Productos activos con stock igual o menor al mínimo.
create or replace function public.productos_stock_bajo()
returns table (id bigint, codigo text, nombre text, categoria text, stock integer, stock_minimo integer, faltante integer)
language plpgsql stable security invoker
set search_path = public
as $$
#variable_conflict use_column
begin
  perform public.exigir_rol(array['administradora', 'cajera']);

  return query
  select p.id::bigint, p.codigo::text, p.nombre::text, coalesce(c.nombre, 'Sin categoría')::text,
         p.stock::integer, p.stock_minimo::integer,
         greatest(p.stock_minimo - p.stock, 0)::integer
  from public.productos p
  left join public.categorias c on c.id = p.categoria_id
  where p.activo and p.stock <= p.stock_minimo
  order by (p.stock - p.stock_minimo), p.nombre;
end $$;
