-- Historial conversacional por usuario (entrega final).
-- Separado del corpus documental (clase08_fragmentos).

create table if not exists public.conversaciones (
  id uuid primary key default gen_random_uuid(),
  usuario_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  titulo text not null check (length(btrim(titulo)) between 1 and 80),
  creada_en timestamptz not null default now(),
  actualizada_en timestamptz not null default now()
);

create table if not exists public.mensajes (
  -- identity: orden estable de creación
  id bigint generated always as identity primary key,
  conversacion_id uuid not null references public.conversaciones (id) on delete cascade,
  usuario_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  rol text not null check (rol in ('usuario', 'asistente')),
  contenido text not null check (length(btrim(contenido)) between 1 and 5000),
  estado text,
  citas jsonb not null default '[]'::jsonb,
  fuentes jsonb not null default '{}'::jsonb,
  traza jsonb,
  creado_en timestamptz not null default now()
);

create index if not exists conversaciones_usuario_fecha_idx
  on public.conversaciones (usuario_id, actualizada_en desc);
create index if not exists mensajes_conversacion_orden_idx
  on public.mensajes (conversacion_id, id);
create index if not exists mensajes_usuario_idx
  on public.mensajes (usuario_id);

alter table public.conversaciones enable row level security;
alter table public.mensajes enable row level security;

-- Solo usuarios autenticados; anon no tiene acceso
revoke all on public.conversaciones from anon;
revoke all on public.mensajes from anon;
grant select, insert, update on public.conversaciones to authenticated;
grant select, insert on public.mensajes to authenticated;

-- Conversaciones: solo su propietario
create policy conversaciones_select_propias on public.conversaciones
  for select to authenticated
  using ((select auth.uid()) = usuario_id);

create policy conversaciones_insert_propias on public.conversaciones
  for insert to authenticated
  with check ((select auth.uid()) = usuario_id);

create policy conversaciones_update_propias on public.conversaciones
  for update to authenticated
  using ((select auth.uid()) = usuario_id)
  with check ((select auth.uid()) = usuario_id);

-- Mensajes: propios y dentro de una conversación propia
create policy mensajes_select_propios on public.mensajes
  for select to authenticated
  using (
    (select auth.uid()) = usuario_id
    and exists (
      select 1 from public.conversaciones c
      where c.id = conversacion_id and c.usuario_id = (select auth.uid())
    )
  );

create policy mensajes_insert_propios on public.mensajes
  for insert to authenticated
  with check (
    (select auth.uid()) = usuario_id
    and exists (
      select 1 from public.conversaciones c
      where c.id = conversacion_id and c.usuario_id = (select auth.uid())
    )
  );
