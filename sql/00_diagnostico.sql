-- =====================================================================
-- Mini Service Gris y Angie
-- 00_diagnostico.sql  (SOLO LECTURA - no modifica nada)
--
-- Ejecutalo primero en Supabase > SQL Editor para ver qué tablas,
-- columnas, restricciones y políticas ya existen en tu proyecto.
-- =====================================================================

-- 1) Tablas y columnas del esquema public
select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
order by table_name, ordinal_position;

-- 2) Restricciones (PK, FK, UNIQUE, CHECK)
select conrelid::regclass as tabla, conname as restriccion,
       contype as tipo, pg_get_constraintdef(oid) as definicion
from pg_constraint
where connamespace = 'public'::regnamespace
order by 1, 2;

-- 3) Políticas RLS existentes
select tablename, policyname, cmd, roles, qual, with_check
from pg_policies
where schemaname = 'public'
order by tablename, policyname;

-- 4) Triggers sobre auth.users (por ejemplo, creación automática de perfiles)
select tgname as trigger, tgrelid::regclass as tabla
from pg_trigger
where tgrelid = 'auth.users'::regclass and not tgisinternal;

-- 5) Usuarios de Supabase Auth y su perfil/rol (para revisar el login).
--    Muestra sólo correo, confirmación y rol: nunca contraseñas.
select u.email, u.email_confirmed_at is not null as correo_confirmado,
       p.id is not null as tiene_perfil, p.rol
from auth.users u
left join public.perfiles p on p.id = u.id
order by u.email;

-- 6) Cantidad de registros por tabla
select relname as tabla, n_live_tup as registros_aprox
from pg_stat_user_tables
where schemaname = 'public'
order by relname;
