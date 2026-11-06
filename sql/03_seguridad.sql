-- =====================================================================
-- Mini Service Gris y Angie
-- 03_seguridad.sql
--
-- Seguridad a nivel de filas (RLS). La aplicación usa la clave pública
-- (anon key), así que la protección real está en la base de datos:
--
--   * Sin sesión iniciada (anon): no puede leer ni modificar tablas.
--   * Cajera: consulta productos/stock, ve ventas y caja; registra ventas
--     y movimientos de caja SOLO mediante funciones (registrar_venta...).
--   * Administradora: acceso completo a catálogos, compras, usuarios.
--
-- Las tablas de movimientos (ventas, compras, inventario, caja) NO tienen
-- políticas de INSERT/UPDATE/DELETE: sólo se escriben a través de las
-- funciones transaccionales, que validan el rol y registran el usuario.
--
-- IMPORTANTE: este script reemplaza las políticas RLS anteriores de estas
-- tablas (revisalas antes con 00_diagnostico.sql).
-- =====================================================================

-- 1. Activar RLS y eliminar políticas anteriores de las tablas del sistema
do $$
declare
  v_tabla text;
  r record;
begin
  foreach v_tabla in array array[
    'perfiles', 'categorias', 'productos', 'proveedores', 'proveedores_productos',
    'compras', 'detalle_compras', 'ventas', 'detalle_ventas',
    'movimientos_inventario', 'movimientos_caja', 'configuracion_negocio'
  ] loop
    execute format('alter table public.%I enable row level security', v_tabla);

    for r in select policyname from pg_policies
             where schemaname = 'public' and tablename = v_tabla loop
      execute format('drop policy %I on public.%I', r.policyname, v_tabla);
    end loop;

    -- El rol anónimo no accede a ninguna tabla del sistema.
    execute format('revoke all on public.%I from anon', v_tabla);
    execute format('grant select, insert, update, delete on public.%I to authenticated', v_tabla);
  end loop;
end $$;

-- 2. PERFILES
create policy perfiles_select on public.perfiles
  for select to authenticated
  using (id = auth.uid() or public.es_usuario_activo());

create policy perfiles_update_admin on public.perfiles
  for update to authenticated
  using (public.es_admin()) with check (public.es_admin());

-- 3. CATÁLOGOS: lectura para usuarios activos, escritura sólo administradora
create policy categorias_select on public.categorias
  for select to authenticated using (public.es_usuario_activo());
create policy categorias_admin on public.categorias
  for all to authenticated using (public.es_admin()) with check (public.es_admin());

create policy productos_select on public.productos
  for select to authenticated using (public.es_usuario_activo());
create policy productos_admin on public.productos
  for all to authenticated using (public.es_admin()) with check (public.es_admin());

create policy proveedores_admin on public.proveedores
  for all to authenticated using (public.es_admin()) with check (public.es_admin());

create policy proveedores_productos_admin on public.proveedores_productos
  for all to authenticated using (public.es_admin()) with check (public.es_admin());

create policy configuracion_select on public.configuracion_negocio
  for select to authenticated using (public.es_usuario_activo());
create policy configuracion_update_admin on public.configuracion_negocio
  for update to authenticated using (public.es_admin()) with check (public.es_admin());

-- 4. MOVIMIENTOS: sólo lectura (se escriben mediante funciones)
create policy ventas_select on public.ventas
  for select to authenticated using (public.es_usuario_activo());
create policy detalle_ventas_select on public.detalle_ventas
  for select to authenticated using (public.es_usuario_activo());
create policy movimientos_inventario_select on public.movimientos_inventario
  for select to authenticated using (public.es_usuario_activo());
create policy movimientos_caja_select on public.movimientos_caja
  for select to authenticated using (public.es_usuario_activo());
create policy compras_select on public.compras
  for select to authenticated using (public.es_admin());
create policy detalle_compras_select on public.detalle_compras
  for select to authenticated using (public.es_admin());

-- 5. PERMISOS DE EJECUCIÓN DE FUNCIONES
-- Por defecto PostgreSQL permite ejecutar funciones a cualquiera (PUBLIC).
-- Se restringe a usuarios autenticados; las propias funciones validan el rol.
do $$
declare
  v_funcion text;
begin
  foreach v_funcion in array array[
    'public.rol_actual()',
    'public.es_usuario_activo()',
    'public.es_admin()',
    'public.exigir_rol(text[])',
    'public.registrar_venta(jsonb, text, numeric)',
    'public.registrar_movimiento_inventario(bigint, text, integer, text)',
    'public.registrar_compra(bigint, jsonb, text, boolean, boolean)',
    'public.registrar_movimiento_caja(text, text, numeric, text)',
    'public.resumen_caja(date)',
    'public.resumen_panel()',
    'public.reporte_ventas(date, date, text)',
    'public.reporte_mas_vendidos(date, date, integer)',
    'public.productos_stock_bajo()'
  ] loop
    execute format('revoke all on function %s from public, anon', v_funcion);
    execute format('grant execute on function %s to authenticated', v_funcion);
  end loop;
end $$;

-- Las funciones de triggers no se llaman directamente desde la API.
revoke all on function public.tg_productos_antes_actualizar() from public, anon, authenticated;
revoke all on function public.tg_productos_stock_inicial()    from public, anon, authenticated;
revoke all on function public.tg_perfiles_proteger_admin()    from public, anon, authenticated;
revoke all on function public.tg_crear_perfil_usuario()       from public, anon, authenticated;

-- El login por nombre de usuario se usa ANTES de iniciar sesión.
revoke all on function public.email_para_login(text) from public;
grant execute on function public.email_para_login(text) to anon, authenticated;
