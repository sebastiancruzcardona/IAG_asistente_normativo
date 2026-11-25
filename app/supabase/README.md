# Corpus compartido con historial privado

## Instalación en un proyecto nuevo de Supabase

Todo se hace desde el panel de Supabase, sin instalar nada. Cada script se ejecuta **una sola vez** y **en este orden**: abre el archivo, copia todo su contenido, pégalo en **SQL Editor → New query** y pulsa **Run**.

1. **`Clase_08_Supabase_Setup.sql`** (en esta carpeta): crea la tabla del corpus, sus políticas y la búsqueda semántica.
2. **`migraciones/001_historial_conversaciones.sql`:** crea el historial privado de cada usuario.
3. **`migraciones/002_corpus_compartido.sql`:** permite que varios usuarios lean el mismo corpus.
4. **`migraciones/003_administradores_corpus.sql`:** permite que la app comparta versiones nuevas del corpus.
5. **Crea las cuentas** en **Authentication → Users → Add user**, marcando **Auto Confirm User**:
   - La cuenta dueña del corpus.
   - Una cuenta por cada persona que usará la app.
6. **Registra la cuenta dueña como administradora del corpus.** Pega esto en el SQL Editor, cambia el correo y pulsa **Run**:

   ```sql
   insert into public.administradores_corpus (usuario_id)
   select id from auth.users where email = 'correo-de-la-cuenta-duena@ejemplo.com';
   ```

7. **Completa `app/.env`** a partir de `app/.env.ejemplo`:
   - `SUPABASE_URL` y `SUPABASE_PUBLISHABLE_KEY` del proyecto.
   - `CORPUS_EMAIL` y `CORPUS_PASSWORD`, con la cuenta del paso 6.
   - Deja vacíos `CORPUS_ID` y `EMBEDDINGS_REVISION`.
8. **Arranca la app** con `python app/app.py`. La primera vez construye el corpus, lo carga en Supabase, lo comparte y escribe `CORPUS_ID` y `EMBEDDINGS_REVISION` en `app/.env`.

Si un script falla a la mitad, revisa el mensaje antes de volver a ejecutarlo: varios crean políticas que no pueden crearse dos veces.

## Punto de partida

Supabase tenía solo la tabla `clase08_fragmentos`, con el corpus del RAG. Sus políticas RLS eran por propietario (`owner_id = auth.uid()`): solo la cuenta que cargó el corpus podía leerlo. Con un segundo usuario, la búsqueda le devolvía cero fragmentos.

### Script original del docente

`Clase_08_Supabase_Setup.sql` es el script que entregó el docente en la clase 8, **tal cual, sin modificar**. Se ejecuta en el SQL Editor de un proyecto de práctica y crea la base del RAG:

- **Extensión `vector`:** en el esquema `extensions`, para guardar embeddings.
- **Tabla `clase08_fragmentos`:** una fila por fragmento, con `owner_id`, `corpus_id`, `chunk_id`, `content`, `metadata`, `configuracion` (modelo y revisión de embeddings) y `embedding` de 384 dimensiones. La clave primaria es `(owner_id, corpus_id, chunk_id)`.
- **RLS por propietario:** tres políticas (`clase08_select_own`, `clase08_insert_own` y `clase08_update_own`) que solo dejan leer, insertar y actualizar las filas cuyo `owner_id` es el usuario autenticado. Se revoca todo acceso a `public` y `anon`.
- **Función `clase08_buscar_fragmentos`:** búsqueda semántica exacta (sin índice HNSW ni IVFFlat, porque el corpus es pequeño) que devuelve los `match_count` fragmentos más similares, entre 1 y 10. Filtra por propietario, corpus, modelo y revisión. Es `security invoker`, así que RLS aplica al usuario que consulta.
- **Comprobaciones finales:** tres consultas que verifican la extensión, que RLS esté activo y cuántos fragmentos hay (al inicio, cero).

Es el punto de partida descrito arriba. Las migraciones `001`, `002` y `003` se aplican después y no modifican el script: lo extienden.

## Objetivo

- **Corpus:** uno solo, que leen todos los usuarios autenticados.
- **Historial:** cada usuario ve únicamente sus propias conversaciones.
- **Notas:** sin desactivar RLS, sin duplicar el corpus y sin clave administrativa en la app (solo la clave publicable).

## Flujo

El corpus sigue existiendo una sola vez, en la misma tabla y con el mismo dueño, pero ahora, además de su dueño, puede leerlo cualquier usuario con sesión iniciada, siempre que el corpus esté en la lista de corpus compartidos. Cuando alguien inicia sesión, la app usa la sesión de esa persona para traer el corpus a memoria una sola vez y armar el índice de búsqueda por palabras (BM25), que luego reutilizan todos los usuarios mientras la app esté encendida. Cuando el agente busca en el corpus, la búsqueda por significado (embeddings) la hace `buscar_fragmentos_compartidos`. A pesar del nombre, no es una copia del corpus, ni virtual ni en memoria, es una copia de la consulta original (`clase08_buscar_fragmentos`) sin el filtro de dueño, que busca directamente en la tabla de siempre, con los permisos de quien pregunta. 

Por otra parte, en cuando al historial, cada pregunta y su respuesta se guardan en conversaciones propias, marcadas con el usuario que las hizo, y la base de datos solo se las muestra a esa persona. Así, dos usuarios consultan los mismos documentos, pero ninguno ve lo que el otro ha preguntado.

## Cómo se hizo

Partiendo del script del docente, se agregaron tres migraciones propias en `migraciones/`. En este proyecto se aplicaron con el MCP de Supabase (`historial_conversaciones`, `corpus_compartido` y `administradores_corpus`). En un proyecto nuevo se ejecutan en el SQL Editor, como se explica en la instalación.

### 1. Historial privado (`001_historial_conversaciones.sql`)

- **Tablas nuevas:** `conversaciones` y `mensajes`, separadas del corpus.
- **Dueño de cada fila:** `usuario_id` se llena solo con `auth.uid()`.
- **Conversaciones:** RLS deja leer, crear y actualizar solo las propias.
- **Mensajes:** se leen o insertan solo si son del usuario **y** pertenecen a una conversación suya. Conocer el id de una conversación ajena no da acceso.
- **Sin borrado:** no hay política para borrar.
- **Sin acceso anónimo:** se revoca todo permiso a `anon`.

### 2. Corpus compartido (`002_corpus_compartido.sql`)

- **Tabla `corpus_compartidos`:** lista los corpus que pueden leer todos los usuarios autenticados, en este caso solo `asistente_normativo-26748aae6375`.
- **Política de lectura adicional:** se agregó `clase08_select_compartido` a `clase08_fragmentos`. Permite leer cualquier fragmento cuyo corpus esté en esa lista. Las políticas originales de propietario se conservan, así que insertar o actualizar el corpus sigue reservado a su dueño.
- **Función `buscar_fragmentos_compartidos`:**
  - Es una copia de `clase08_buscar_fragmentos` sin el filtro por propietario.
  - Es `security invoker`: corre con los permisos de quien consulta, así que RLS sigue aplicando.
  - Solo la puede ejecutar el rol `authenticated`.

### 3. Versiones nuevas del corpus (`003_administradores_corpus.sql`)

Desde esta migración, `app/corpus.py` construye el corpus desde sus textos y `sistema.py` lo sincroniza al arrancar. Si los textos cambian, la app crea una versión nueva con otro `corpus_id` y la comparte sola, sin escribir otra migración.

- **Tabla `administradores_corpus`:**
  - Guarda las cuentas que pueden compartir corpus.
  - Cada usuario solo puede ver su propia fila, y nadie puede escribir en ella desde la app.
  - El administrador inicial es el dueño del corpus que ya estaba compartido.
- **Dueño en `corpus_compartidos`:**
  - La tabla ahora tiene una columna `owner_id`, que se llena sola con quien comparte.
  - Un administrador puede agregar un corpus a la tabla solo si tiene fragmentos propios con ese `corpus_id`.
- **Lectura más estricta:**
  - La política `clase08_select_compartido` de la `002` se reemplazó: ahora solo deja leer los fragmentos del mismo dueño que compartió el corpus.
  - Así, si otra cuenta cargara filas con el mismo `corpus_id`, no se mezclarían con el corpus compartido.

### 4. Cambios en la app

- **Cliente por usuario:** cada usuario inicia sesión con su cuenta, y la app crea un cliente con su token para cada solicitud.
- **Búsqueda:** la app lee el corpus (`CORPUS_ID` en `app/.env`) sin filtrar por `owner_id` y llama a `buscar_fragmentos_compartidos`.
- **Historial:** `almacenamiento.py` guarda y lee el historial. Además de RLS, verifica en el código que la conversación sea del usuario.
- **Corpus:** al arrancar, `sistema.py` inicia sesión con la cuenta dueña del corpus (`CORPUS_EMAIL` y `CORPUS_PASSWORD` en `app/.env`) y compara los textos de `corpus.py` con el corpus guardado.
  - Si son iguales, no cambia nada.
  - Si cambiaron, guarda la versión nueva, la comparte y actualiza `CORPUS_ID` y `EMBEDDINGS_REVISION` en `app/.env`.

## Resultado

| | Corpus (`clase08_fragmentos`) | Historial (`conversaciones`, `mensajes`) |
|---|---|---|
| Leer | Todos los autenticados, si el corpus y su dueño están en `corpus_compartidos` | Solo el dueño |
| Escribir | Solo el dueño del corpus | Solo el dueño, en sus propias conversaciones |
| Compartir | Solo un administrador, y solo corpus propios | No aplica |
| Anónimo | Sin acceso | Sin acceso |

## Agregar usuarios o corpus

- **Otro usuario:** se crea la cuenta en Supabase Auth (Authentication → Users). No se cambia nada en la base: ya lee el corpus y empieza con un historial vacío.
- **Otra versión del corpus:** se cambian los textos de `FUENTES` en `app/corpus.py` y se reinicia la app. La versión anterior no se borra.
- **Otro administrador:** se ejecuta el `insert` del paso 6 de la instalación con su correo.

La migración `002` registra el `corpus_id` de este proyecto. En un proyecto nuevo, ese registro no tiene fragmentos, y la `003` lo elimina.

## Cómo comprobarlo

`app/pruebas/test_almacenamiento_rls.py` usa dos cuentas de prueba (A y B, configuradas en `app/.env`). Comprueba que A recupera su historial con una sesión nueva, que B no puede listar, leer ni escribir el historial de A, y que B lee el corpus compartido:

```
cd app
pytest pruebas/test_almacenamiento_rls.py -v
```

`app/pruebas/test_corpus.py` comprueba que `corpus.py` reproduce los 63 fragmentos guardados (mismo texto y metadatos, y embeddings equivalentes) y que solo detecta cambios cuando cambia el texto.
