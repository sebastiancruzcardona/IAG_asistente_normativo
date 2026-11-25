-- Corpus documental compartido para lectura entre usuarios autenticados.
-- El historial conversacional sigue siendo privado (001).
-- No se desactiva RLS ni se usa una clave administrativa.

create table if not exists public.corpus_compartidos (
  corpus_id text primary key check (length(btrim(corpus_id)) between 1 and 100)
);

alter table public.corpus_compartidos enable row level security;
revoke all on public.corpus_compartidos from anon;
grant select on public.corpus_compartidos to authenticated;

-- Solo lectura; se administra mediante migraciones
create policy corpus_compartidos_select on public.corpus_compartidos
  for select to authenticated
  using (true);

insert into public.corpus_compartidos (corpus_id)
values ('asistente_normativo-26748aae6375')
on conflict do nothing;

-- Lectura adicional del corpus compartido. Las políticas de propietario se conservan
create policy clase08_select_compartido on public.clase08_fragmentos
  for select to authenticated
  using (corpus_id in (select cc.corpus_id from public.corpus_compartidos cc));

-- Copia de clase08_buscar_fragmentos sin filtro por propietario.
-- security invoker: RLS sigue aplicando al usuario que consulta
create or replace function public.buscar_fragmentos_compartidos(
  query_embedding extensions.vector,
  p_corpus_id text,
  p_modelo text,
  p_revision text,
  match_count integer default 3
)
returns table (chunk_id text, content text, metadata jsonb, similitud double precision)
language sql
stable
security invoker
set search_path to ''
as $function$
  select d.chunk_id, d.content, d.metadata,
         1 - (d.embedding operator(extensions.<=>) query_embedding) as similitud
  from public.clase08_fragmentos as d
  where d.corpus_id = p_corpus_id
    and p_corpus_id in (select cc.corpus_id from public.corpus_compartidos cc)
    and d.configuracion ->> 'modelo' = p_modelo
    and d.configuracion ->> 'revision' = p_revision
  order by d.embedding operator(extensions.<=>) query_embedding, d.chunk_id
  limit least(greatest(coalesce(match_count, 3), 1), 10);
$function$;

revoke all on function public.buscar_fragmentos_compartidos(extensions.vector, text, text, text, integer) from public, anon;
grant execute on function public.buscar_fragmentos_compartidos(extensions.vector, text, text, text, integer) to authenticated;
