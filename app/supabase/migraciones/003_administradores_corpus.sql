-- Versiones nuevas del corpus desde corpus.py (sistema.preparar()).
-- Un administrador de corpus puede compartir un corpus propio sin migraciones.
-- Leer el corpus compartido exige ahora que la fila sea del mismo dueño que
-- lo compartió: filas de otras cuentas con el mismo corpus_id no se mezclan.

-- Administradores: se agregan con migraciones o desde el SQL Editor
create table if not exists public.administradores_corpus (
  usuario_id uuid primary key references auth.users (id) on delete cascade
);

alter table public.administradores_corpus enable row level security;
revoke all on public.administradores_corpus from anon, authenticated;
grant select on public.administradores_corpus to authenticated;

-- Cada usuario solo puede comprobar si él mismo es administrador
create policy administradores_corpus_select_propio on public.administradores_corpus
  for select to authenticated
  using ((select auth.uid()) = usuario_id);

-- Administrador inicial: el dueño del corpus compartido actual
insert into public.administradores_corpus (usuario_id)
select distinct f.owner_id
from public.clase08_fragmentos f
where f.corpus_id in (select cc.corpus_id from public.corpus_compartidos cc)
on conflict do nothing;

-- Dueño de cada corpus compartido
alter table public.corpus_compartidos
  add column if not exists owner_id uuid references auth.users (id) on delete cascade;

update public.corpus_compartidos cc
set owner_id = (
  select f.owner_id from public.clase08_fragmentos f
  where f.corpus_id = cc.corpus_id
  limit 1
)
where cc.owner_id is null;

-- Registros sin fragmentos no comparten nada (por ejemplo, el corpus_id que
-- registra 002 cuando se ejecuta en un proyecto nuevo)
delete from public.corpus_compartidos where owner_id is null;

alter table public.corpus_compartidos
  alter column owner_id set default auth.uid(),
  alter column owner_id set not null;

-- Un administrador comparte solo corpus con fragmentos propios
grant insert on public.corpus_compartidos to authenticated;

create policy corpus_compartidos_insert_administrador on public.corpus_compartidos
  for insert to authenticated
  with check (
    owner_id = (select auth.uid())
    and exists (
      select 1 from public.administradores_corpus a
      where a.usuario_id = (select auth.uid())
    )
    and exists (
      select 1 from public.clase08_fragmentos f
      where f.corpus_id = corpus_compartidos.corpus_id
        and f.owner_id = (select auth.uid())
    )
  );

-- Reemplaza la política de lectura de la migración 002: corpus y dueño deben
-- coincidir con el registro compartido
drop policy if exists clase08_select_compartido on public.clase08_fragmentos;
create policy clase08_select_compartido on public.clase08_fragmentos
  for select to authenticated
  using (
    exists (
      select 1 from public.corpus_compartidos cc
      where cc.corpus_id = clase08_fragmentos.corpus_id
        and cc.owner_id = clase08_fragmentos.owner_id
    )
  );
