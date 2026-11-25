---
tipo: bitacora-clase
curso: IAG y Sistemas Inteligentes (electiva VI)
periodo: EAM-2026II
equipo: Equipo_SebastiánCruz
corte: 3
semana: 12 - 14
clase: "12"
fecha: 2026_11_25
estado: finalizada
tags:
  - ai
  - bitacora
---

# Bitácora — Entrega final

## 1. Datos de la sesión

| Campo    | Registro                                                                                                                                                                                                 |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tema     | Aplicación web del asistente normativo con Gradio, historial por usuario en Supabase y corpus reproducible                                                                                               |
| Objetivo | Migrar a la carpeta `app/` el agente con RAG y servidores MCP validado en los notebooks previos, para que una persona pueda iniciar sesión, consultar y recuperar sus conversaciones sin ejecutar celdas |
| Proyecto | Asistente normativo                                                                                                                                                                                      |
| Inicio   | N/A                                                                                                                                                                                                      |
| Cierre   | N/A                                                                                                                                                                                                      |

## 2. Participación y responsabilidades

| Integrante             | Asistió | Rol de la clase | Responsabilidad asumida      | Aporte verificable                                                                                            |
| ---------------------- | :-----: | --------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Sebastián Cruz Cardona |   Sí    | Estudiante      | Desarrollar la entrega final | Commits `de6266c` a `9b1cb74` del repositorio https://github.com/sebastiancruzcardona/IAG_asistente_normativo |

## 3. Reto aplicado al proyecto

### Funcionalidad trabajada

La entrega final convierte el notebook de la clase 11 ([`notebooks/asistente_normativo_RAG_agente_MCP.ipynb`](notebooks/asistente_normativo_RAG_agente_MCP.ipynb)) en una aplicación web que se ejecuta en local. El código se migró a [`app/sistema.py`](app/sistema.py) con la menor cantidad de cambios posible, y solo se adaptó lo necesario para una aplicación multiusuario. Así, el contrato `Decision`, las validaciones, los límites, la fusión RRF, el ciclo de decisión del agente y las funciones de los dos MCP se conservan tal como estaban. El detalle de cada cambio está en [`cambios-decisiones.md`](cambios-decisiones.md).

Cada persona inicia sesión con Supabase Auth y cada solicitud usa un cliente creado con su propio token. Las conversaciones se guardan en Supabase, en tablas protegidas con RLS, de modo que sobreviven al cierre del navegador y al reinicio de la aplicación, y ningún usuario puede ver el historial de otro. Además, el corpus dejó de depender del prototipo del corte 2 en Colab, porque ahora se construye desde el código en [`app/corpus.py`](app/corpus.py) y genera una versión nueva por sí solo cuando cambia el texto. Finalmente, las pruebas que antes eran celdas del notebook pasaron a pytest, en [`app/pruebas/`](app/pruebas/).

Cuando alguien escribe una pregunta, `atender_mensaje()` valida su token, crea o carga la conversación después de comprobar que le pertenece y arma la memoria con los últimos cuatro turnos completados. Luego el agente decide paso a paso, ejecuta las herramientas dentro de los límites y, al terminar, `guardar_turno()` guarda la pregunta y la respuesta en una sola inserción, con su estado, sus citas, las fuentes citadas y la traza. En la prueba de recorrido final, los siete casos terminaron en el estado esperado y quedaron guardados en Supabase.

### Parámetros generales vigentes

Estos parámetros se definieron en los notebooks desarrollados durante el semestre y la aplicación los conserva sin cambios.

| Parámetro                   | Valor                                                                                                                                                                                                    | Ubicación actual                                    |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Modelo generativo           | `openai/gpt-oss-120b` en Groq, configurable con `GROQ_MODEL`                                                                                                                                             | `app/sistema.py`, línea 104                         |
| Generación de cada decisión | `temperature=0`, `reasoning_effort="medium"`, `max_completion_tokens=1800` y salida en JSON                                                                                                              | `app/sistema.py`, líneas 1384 a 1390                |
| Contrato de decisión        | `Decision` estricto, sin campos adicionales, con siete acciones (`buscar_documentos`, `consultar_estado_proceso`, `buscar_jurisprudencia`, `linea_jurisprudencial`, `responder`, `aclarar` y `rechazar`) | `app/sistema.py`, línea 1021                        |
| Límites por turno           | 2 operaciones (`MAX_OPERACIONES`) y 3 decisiones (`MAX_DECISIONES`)                                                                                                                                      | `app/sistema.py`, línea 108                         |
| Memoria del agente          | Últimos 4 turnos completados (`MAX_TURNOS`)                                                                                                                                                              | `app/sistema.py`, línea 108                         |
| Tiempo y contexto           | 90 segundos (`MAX_SEGUNDOS`) y 24 000 caracteres (`MAX_CONTEXTO_CARACTERES`)                                                                                                                             | `app/sistema.py`, línea 112                         |
| Recuperación                | Estrategia B, híbrida con RRF. M = 10 candidatos semánticos y 10 de BM25, K = 3 fragmentos finales y constante RRF de 60                                                                                 | `app/sistema.py`, línea 121                         |
| BM25                        | `BM25Okapi` de `rank-bm25` 0.2.2 con sus valores por defecto (k1 = 1,5 y b = 0,75), con tokenización NFKC y casefold                                                                                     | `app/sistema.py`, líneas 331 a 343 y 498            |
| Modelo de embeddings        | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, de 384 dimensiones, normalizado, con similitud coseno y `max_seq_length` de 128, y la revisión fijada en `EMBEDDINGS_REVISION`            | `app/corpus.py`, línea 27                           |
| Fragmentación               | Ventanas de 95 tokens con solapamiento de 17, versión `1.0-implementacion`                                                                                                                               | `app/corpus.py`, líneas 29 a 36                     |
| MCP propio                  | `consultar_estado_proceso` sobre diez procesos ficticios, con código `P-` seguido de 11 dígitos y tiempo de lectura de 15 s                                                                              | `app/servidor_mcp.py` y `app/sistema.py`, línea 663 |
| MCP externo                 | `normativa-colombia-mcp` 1.16.1 con `FUENTES=corte`, solo `buscar_jurisprudencia` y `linea_jurisprudencial`, 3 resultados por defecto y 6 como máximo, y tiempo de lectura de 60 s                       | `app/sistema.py`, líneas 115, 696 a 700 y 826       |

### Criterios de aceptación

- [x] La aplicación permite hacer una solicitud nueva y ver el resultado desde Gradio, sin ejecutar celdas de un notebook.
- [x] El código del notebook validado se migró con la menor cantidad de cambios posible.
- [x] Cada persona inicia sesión con Supabase Auth y las operaciones usan su contexto autenticado.
- [x] Las conversaciones se guardan en Supabase y se recuperan después de cerrar el navegador o reiniciar la aplicación, y crear una nueva no borra las anteriores.
- [x] Un usuario no puede listar, leer ni escribir el historial de otro, aunque conozca su identificador.
- [x] La aplicación conserva el RAG, los contratos y las herramientas MCP de la entrega anterior.
- [x] El corpus se puede recuperar desde un clon limpio, sin ejecutar notebooks ni subir archivos.
- [x] Las pruebas cubren los controles, el historial con RLS, el corpus y el recorrido real con el modelo.
- [x] El README permite clonar, configurar y ejecutar la aplicación con credenciales propias.
- [x] Presentación en PDF (`app/presentacion_proyecto.pdf`).

### Archivos o componentes modificados

- `app/sistema.py`: lógica del notebook de referencia, con la configuración desde `app/.env`, la identidad por usuario, la sincronización del corpus y el recorrido `atender_mensaje()`.
- `app/almacenamiento.py`: creación y listado de conversaciones, carga de mensajes, guardado de turnos y memoria del agente.
- `app/corpus.py`: construcción del corpus, desde los textos hasta su carga en Supabase, y creación de versiones nuevas.
- `app/servidor_mcp.py`: servidor MCP propio, que antes era un texto escrito a disco desde el notebook.
- `app/app.py`: interfaz Gradio, que solo presenta y llama a las funciones de `sistema.py`.
- `app/supabase/migraciones/001_historial_conversaciones.sql`, `002_corpus_compartido.sql` y `003_administradores_corpus.sql`: historial por usuario, corpus compartido y administradores del corpus.
- `app/pruebas/`: pruebas de controles, historial y RLS, corpus y recorrido.
- `app/requirements.txt`, `app/.env.ejemplo` y `app/pytest.ini`: dependencias, plantilla de configuración y configuración de pytest.

## 4. Decisiones técnicas

### Migración del notebook a `sistema.py`

| Decisión                                                                                                                                                                                                        | Razón                                                                                                                                                  | Alternativa descartada                                                     |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Leer la configuración de `app/.env` con `variable()` y guardar `CORPUS_ID`, `EMBEDDINGS_MODELO` y `EMBEDDINGS_REVISION` como variables, con las mismas validaciones.                                            | Fuera de Colab no hay secretos ni subida de archivos, y así la configuración queda separada del código.                                                | `secreto()` con los secretos de Colab y el JSON subido con `files.upload`. |
| Instalar las dependencias desde `app/requirements.txt` en un entorno `.venv`.                                                                                                                                   | Quien clone el repositorio instala todo en su propio entorno virtual.                                                                                  | Instalar con `pip` dentro del notebook.                                    |
| Crear un cliente de Supabase por solicitud con el token del usuario, mediante `iniciar_sesion()` y `cliente_usuario()`.                                                                                         | Cada persona entra con su cuenta, y un cliente autenticado compartido mezclaría identidades.                                                           | Un inicio de sesión único con `SUPABASE_EMAIL` y un cliente global.        |
| Leer el corpus sin filtrar por `owner_id`, con la función `buscar_fragmentos_compartidos`.                                                                                                                      | Con RLS por propietario, solo el dueño podía leer el corpus.                                                                                           | `clase08_buscar_fragmentos` con filtro de propietario.                     |
| Cargar el corpus y construir BM25 en `asegurar_corpus()`, una sola vez y con un bloqueo, cuando el primer usuario inicia sesión.                                                                                | RLS exige un usuario autenticado para leer el corpus, y la carga queda fuera de la atención de preguntas.                                              | Una celda que cargaba el corpus al ejecutarse el notebook.                 |
| Cargar el modelo de embeddings al arrancar con `cargar_modelo_embeddings()`, y pasar `cliente_db` a `buscar_documentos`.                                                                                        | El modelo se prepara una sola vez para todos y la búsqueda usa el cliente del usuario.                                                                 | Cargarlo en una celda y buscar con el cliente global.                      |
| Convertir el servidor MCP propio en el archivo `app/servidor_mcp.py`, con logs en `app/logs/`.                                                                                                                  | Es un archivo fijo del proyecto y los logs quedan fuera de Git.                                                                                        | El texto `SERVIDOR_MCP` escrito a disco desde el notebook.                 |
| Instalar `normativa-colombia-mcp@1.16.1` dentro de `.venv` con el Node.js de `nodejs-wheel`, mediante `preparar_normativa()`.                                                                                   | Todas las dependencias viven en el entorno virtual y no dependen del Node del sistema.                                                                 | Instalarlo solo en Colab con el Node del entorno.                          |
| Descubrir los MCP en `preparar_mcp()` y `preparar()`, al arrancar la aplicación.                                                                                                                                | Un módulo no admite `await` a nivel superior, y la preparación debe ocurrir antes de atender preguntas.                                                | `await` a nivel de celda.                                                  |
| Reemplazar `MEMORIA`, `guardar_turno()` y `reiniciar_conversacion()` por `almacenamiento.py`, de modo que `atender()` recibe el historial y `atender_mensaje()` guarda el turno.                                | La guía exige guardar el historial en Supabase, y una conversación nueva cumple el papel de reiniciar sin borrar las anteriores.                       | Memoria en un diccionario de Python.                                       |
| Validar el id de conversación como UUID.                                                                                                                                                                        | Ahora los genera Supabase.                                                                                                                             | El patrón `[A-Za-z0-9_-]{1,40}`.                                           |
| Eliminar `EJECUCIONES` y guardar la traza con cada mensaje.                                                                                                                                                     | En una aplicación web mezclaría las trazas de todos los usuarios.                                                                                      | Una lista global de ejecuciones.                                           |
| Incluir `resultado` en el evento `RESULTADO_RECIBIDO` de la traza.                                                                                                                                              | La interfaz debe mostrar el resultado de las herramientas.                                                                                             | Una traza sin los resultados.                                              |
| Llevar `mostrar()`, `display()` y las celdas de prueba a `app.py`, `pruebas/test_controles.py` y `pruebas/test_recorrido.py`.                                                                                   | La interacción, las pruebas y la evidencia ya no dependen de ejecutar celdas.                                                                          | Probar desde celdas del notebook.                                          |
| Agregar al prompt dos reglas en RESULTADOS y ajustar dos en CITAS, para que el agente diga que el corpus no contiene el tema y cite los fragmentos revisados, o responda la parte cubierta e indique qué falta. | `buscar_documentos` siempre devuelve tres fragmentos, y ante preguntas fuera del corpus el modelo declaraba citas que no escribía.                     | Relajar la validación de citas.                                            |
| Pedir en el prompt que cada etiqueta vaya entre corchetes junto al dato, y guardar en la traza la decisión rechazada (`decision_rechazada`).                                                                    | El modelo declaraba `T1` sin escribir `[T1]`, y no se podía ver qué había propuesto cuando fallaba la validación.                                      | Mostrar solo el mensaje genérico de error.                                 |
| Mover la construcción del corpus del prototipo del corte 2 a `app/corpus.py`, y sincronizarlo al arrancar con `sincronizar_corpus()` y la cuenta dueña del corpus.                                              | El corpus solo existía en Supabase y dependía de ejecutar el prototipo en Colab. Ahora el proyecto puede recrearlo y versionarlo.                      | Cargar el corpus desde el notebook.                                        |
| Quitar `guia_uso.md` del corpus y ampliar la Constitución a los artículos 1 a 94, cada uno con título `## Artículo N`.                                                                                          | El corpus se centra en el conocimiento constitucional, y el título de nivel 2 es necesario porque la fragmentación solo abre una sección en ese nivel. | Mantener la guía de uso dentro del corpus.                                 |

### Supabase y migraciones

| Decisión                                                                                                                                                                                                      | Razón                                                                                                                | Alternativa descartada                                     |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Usar el mismo proyecto de Supabase del RAG, con las tablas `conversaciones` y `mensajes` separadas de `clase08_fragmentos`.                                                                                   | La guía lo permite y así el historial no se mezcla con el corpus.                                                    | Crear otro proyecto de Supabase.                           |
| Dar a `usuario_id` el valor por defecto `auth.uid()` y usar una identidad para `mensajes.id` (001).                                                                                                           | Cada fila queda asociada a su dueño y los mensajes tienen un orden estable.                                          | Enviar el usuario desde la aplicación y ordenar por fecha. |
| Permitir que solo el dueño lea, cree o actualice una conversación, y que un mensaje solo se lea o inserte si es del usuario y pertenece a una conversación suya, sin borrados y sin acceso para `anon` (001). | Conocer un UUID no da acceso al historial de otra persona.                                                           | Filtrar por usuario solo en el código.                     |
| Crear la tabla `corpus_compartidos` y una política adicional de lectura sobre `clase08_fragmentos` para esos corpus (002).                                                                                    | Todos los usuarios leen el mismo corpus sin desactivar RLS ni duplicar datos, y escribir sigue reservado al dueño.   | Desactivar RLS o copiar el corpus a cada usuario.          |
| Crear `buscar_fragmentos_compartidos` como copia de la búsqueda de la clase 8 sin el filtro de propietario, con `security invoker`, `search_path ''` y ejecución solo para `authenticated` (002).             | La búsqueda vectorial respeta RLS del usuario que consulta y no amplía privilegios.                                  | Una función `security definer`.                            |
| Crear `administradores_corpus` y permitir que un administrador comparta solo corpus con fragmentos propios (003).                                                                                             | `corpus.py` comparte cada versión nueva sin escribir una migración por versión, y ningún otro usuario puede hacerlo. | Una migración manual por cada versión del corpus.          |

### `almacenamiento.py`

| Decisión                                                                                                                                                    | Razón                                                                                                  | Alternativa descartada              |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| Guardar la pregunta y la respuesta en una sola inserción, con estado, citas, solo las fuentes citadas y la traza, y con las mismas columnas en ambas filas. | Mantiene el orden, evita turnos a medias y evita que el cliente envíe `NULL` en columnas obligatorias. | Dos inserciones independientes.     |
| Guardar todos los turnos, incluidos los errores, pero enviar al modelo solo los últimos cuatro completados (`RESPONDER`, `ACLARAR` o `RECHAZAR`).           | Guardar el historial y elegir el contexto del modelo son cosas distintas.                              | Enviar todo el historial al modelo. |

### Sesión y ejecución en `app.py`

| Decisión                                                                                                                                                                     | Razón                                                                                                           | Alternativa descartada                       |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Guardar en `gr.State` solo datos serializables de la sesión (`usuario_id`, correo y tokens), y crear el cliente de Supabase en cada solicitud, renovando el token si venció. | No se comparte un cliente autenticado entre usuarios y la sesión sobrevive al vencimiento del token.            | Guardar el cliente autenticado en el estado. |
| Restablecer todos los `gr.State` al cerrar sesión y cancelar la respuesta que siga en curso.                                                                                 | Una respuesta tardía volvería a escribir la sesión anterior aunque la pantalla ya mostrara el inicio de sesión. | Limpiar solo la pantalla.                    |
| Preparar el modelo de embeddings, Node.js y los MCP al arrancar, y cargar el corpus al iniciar sesión.                                                                       | La primera pregunta no espera ninguna carga.                                                                    | Prepararlos con la primera pregunta.         |
| Ejecutar en local, en `127.0.0.1:7860`, con `GRADIO_SERVER_NAME` y `PORT` configurables.                                                                                     | No era necesario hacer despliegue según indicación del docente.                                                 | Desplegar en un servicio de alojamiento.     |

### `corpus.py`

| Decisión                                                                                                                                                                | Razón                                                                                                                                                       | Alternativa descartada                                                 |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Detectar cambios comparando el `source_hash` de cada documento, la versión, el modelo, la estrategia, `max_tokens` y `solapamiento`, sin comparar la huella del índice. | La huella incluye los bytes de los vectores, que varían entre máquinas. Con los mismos 63 fragmentos dio `22712e2e669b` en local y `26748aae6375` en Colab. | Comparar la huella, que crearía una versión nueva en cada equipo.      |
| Solo cargar el modelo y consultar Hugging Face cuando hay cambios en el corpus.                                                                                         | No es necesario.                                                                                                                                            | Reconstruir el corpus en cada arranque.                                |
| Construir, guardar, compartir y después escribir `CORPUS_ID` y `EMBEDDINGS_REVISION` en `app/.env` con `dotenv.set_key`.                                                | Si compartir falla, la aplicación no apunta a un corpus que los demás no pueden leer, y el resto de `.env` se conserva.                                     | Actualizar `.env` antes de compartir o reescribir el archivo completo. |
| Usar `CORPUS_ID` sin sincronizar si faltan `CORPUS_EMAIL` o `CORPUS_PASSWORD`, con un aviso.                                                                            | Solo el dueño puede escribir el corpus, y sin esa cuenta la aplicación funciona igual.                                                                      | Detener la aplicación.                                                 |

## 5. Problemas y soluciones

| Problema encontrado                                                                                                                                           | Causa identificada                                                                                     | Solución aplicada                                                                  | ¿Cómo se verificó?                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Un segundo usuario no podía leer el corpus.                                                                                                                   | Las políticas de la clase 8 filtraban los fragmentos por propietario.                                  | Migración 002 con `corpus_compartidos` y `buscar_fragmentos_compartidos`.          | `test_b_lee_el_corpus_compartido` en `app/pruebas/test_almacenamiento_rls.py`.                                               |
| Filas de otra cuenta con el mismo `corpus_id` podían mezclarse con el corpus compartido.                                                                      | La política de lectura compartida solo comparaba el `corpus_id`.                                       | Migración 003, que exige que coincidan el corpus y su dueño.                       | Pruebas de inserción en una transacción revertida en Supabase, con los tres casos esperados.                                 |
| Guardar un turno violaba el `NOT NULL` de `citas`.                                                                                                            | En una inserción de varias filas, el cliente envía como `NULL` las columnas que faltan en alguna fila. | Las dos filas llevan las mismas columnas.                                          | `test_a_recupera_sus_conversaciones_con_una_sesion_nueva` y la prueba de recorrido, con todos los turnos guardados.          |
| Las preguntas fuera del corpus terminaban en `ERROR_VALIDACION`.                                                                                              | El RAG siempre devuelve tres fragmentos y el modelo declaraba citas que no escribía.                   | Reglas nuevas en el prompt, sin cambiar la validación.                             | Caso `sin_evidencia` de la prueba de recorrido, que terminó en `RESPONDER` con [F1], [F2] y [F3].                            |
| La consulta de un proceso terminaba en `ERROR_VALIDACION`.                                                                                                    | El modelo declaraba `T1` sin escribir `[T1]` en el texto.                                              | Regla en el prompt con un ejemplo y registro de `decision_rechazada` en la traza.  | Caso `herramienta_mcp_propio` de la prueba de recorrido, que respondió con [T1], y `test_traza_conserva_decision_rechazada`. |
| Una respuesta que terminaba después del cierre de sesión podía volver a escribir en la sesión anterior, dejando datos residuales que no son del otro usuario. | El evento de respuesta seguía en curso al cerrar sesión.                                               | Cancelar las respuestas en curso con `cancels` y restablecer todos los `gr.State`. | Revisión manual al cerrar sesión durante una respuesta.                                                                      |

Aun con estas correcciones, el sistema se mantiene con limitaciones. Los procesos son ficticios, el corpus solo cubre los artículos 1 a 94 de la Constitución y la jurisprudencia se limita a la Corte Constitucional. Una cita con formato válido tampoco garantiza que el fragmento respalde la afirmación, por lo que la revisión humana sigue siendo necesaria, y el plan gratuito de Groq obliga a espaciar las consultas. El sistema tampoco tiene un módulo de registro, por lo que es necesario gestionar los usuarios desde Supabase. Asimismo, el sistema no permite a los usuarios borrar registros individuales de sus chats, ni eliminarlos todos, esto debe hacerse desde Supabase.

## 6. Evidencias

| Tipo       | Descripción                                                                               | Enlace o ruta                                                                                                  |
| ---------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Commit     | Migración de la lógica del notebook a `sistema.py`                                        | `de6266c`                                                                                                      |
| Commit     | Directorio de Supabase con el script de la clase 8 y las migraciones para varios usuarios | `4c362ae`                                                                                                      |
| Commit     | Módulo `almacenamiento.py` para guardar y recuperar conversaciones                        | `e3a3e23`                                                                                                      |
| Commit     | Módulo `corpus.py` para construir y actualizar el corpus                                  | `95fb532`                                                                                                      |
| Commit     | Ajustes al prompt para preguntas fuera del corpus                                         | `6cf625a`                                                                                                      |
| Commit     | Evidencias de la prueba de recorrido de la versión final                                  | `a8c5771`                                                                                                      |
| Referencia | Políticas RLS de `conversaciones` y `mensajes`                                            | `app/supabase/migraciones/001_historial_conversaciones.sql`, líneas 42 a 75                                    |
| Referencia | Política que exige corpus y dueño coincidentes                                            | `app/supabase/migraciones/003_administradores_corpus.sql`, líneas 50 a 76                                      |
| Referencia | Sincronización del corpus al arrancar                                                     | `app/sistema.py`, líneas 1666 a 1730                                                                           |
| Referencia | Detección de cambios en el corpus                                                         | `app/corpus.py`, líneas 1053 a 1098                                                                            |
| Referencia | Guardado de un turno en una sola inserción                                                | `app/almacenamiento.py`, líneas 133 a 186                                                                      |
| Referencia | Pruebas de separación de historiales entre los usuarios A y B                             | `app/pruebas/test_almacenamiento_rls.py`, líneas 73 a 169                                                      |
| Referencia | Resultado de las pruebas                                                                  | `app/evidencia/Entrega_Final_Recorrido.json`                                                                   |
| Demo       | Prueba de recorrido con Groq real, siete casos                                            | [`app/pruebas/test_recorrido.py`](app/pruebas/test_recorrido.py), con `pytest -m recorrido -v -s` desde `app/` |
| Demo       | Pruebas manuales en la interfaz                                                           | [`preguntas-pruebas-manuales.md`](preguntas-pruebas-manuales.md)                                               |
| Código     | Recorrido completo de un mensaje desde la interfaz                                        | [`app/sistema.py`](app/sistema.py), líneas 1795 a 1862                                                         |
| Código     | Validación de decisiones y control de operaciones                                         | [`app/sistema.py`](app/sistema.py), líneas 1108 a 1235                                                         |
| Código     | Construcción y sincronización del corpus                                                  | [`app/corpus.py`](app/corpus.py), líneas 1099 a 1298                                                           |

### Pruebas de la entrega final

| Prueba                                                                 | Qué comprueba                                                                                                                                                                              | Resultado                                                                                      |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| [`test_controles.py`](app/pruebas/test_controles.py)                   | Catálogos y llamadas de los dos MCP, validación de decisiones y citas, repeticiones, límite de operaciones, fusión RRF, memoria desde el historial y conservación de la decisión rechazada | Test pasa correctamente.                                                                       |
| [`test_almacenamiento_rls.py`](app/pruebas/test_almacenamiento_rls.py) | A recupera sus conversaciones con una sesión nueva, B no puede listar, leer ni escribir el historial de A y B sí lee el corpus compartido                                                  | Test pasa correctamente.                                                                       |
| [`test_corpus.py`](app/pruebas/test_corpus.py)                         | `corpus.py` reproduce el corpus guardado, solo detecta cambios si cambia el texto y al actualizar `.env` conserva las demás líneas                                                         | Test pasa correctamente.                                                                       |
| [`test_recorrido.py`](app/pruebas/test_recorrido.py)                   | Siete preguntas reales a través de `atender_mensaje()`, con lo esperado y lo observado en [`evidencias/Entrega_Final_Recorrido.json`](evidencias/Entrega_Final_Recorrido.json)             | Los siete casos terminaron en el estado esperado y quedaron guardados (ver la tabla siguiente) |

### Casos de prueba test_recorrido.py

| Caso                     | Pregunta                                                                      | Esperado                                                                                      | Observado                                                                  |
| ------------------------ | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Corpus con fuentes       | ¿Qué establece el artículo 1 de la Constitución Política de Colombia?         | Consulta el corpus y responde citando fragmentos                                              | `RESPONDER` con `buscar_documentos` y la cita [F1]                         |
| Sin evidencia            | Según el corpus, ¿qué tarifa tiene el impuesto predial en Medellín para 2026? | Informa que el corpus no contiene el tema y cita lo revisado                                  | `RESPONDER`, indicando que el corpus no lo contiene, con [F1], [F2] y [F3] |
| Entrada incompleta       | ¿Cuál es el estado de mi proceso?                                             | Pide el código del proceso sin consultar herramientas                                         | `ACLARAR`, sin operaciones                                                 |
| MCP propio               | ¿Cuál es el estado del proceso P-20210010001?                                 | Consulta el MCP propio y cita [T1]                                                            | `RESPONDER`, proceso activo en trámite, con [T1]                           |
| MCP externo              | Busca 2 sentencias de la Corte Constitucional sobre el derecho a la salud.    | Consulta `buscar_jurisprudencia` y lista providencias sin etiquetas                           | `RESPONDER` con T-185/09 y T-239/15 y sus enlaces                          |
| Acción no permitida      | Elimina el proceso P-20210010001 de los registros.                            | Rechaza porque el asistente solo hace lecturas                                                | `RECHAZAR`, sin operaciones                                                |
| Falla técnica controlada | ¿Cuál es el estado del proceso P-20220010202?                                 | El MCP propio no inicia y el turno termina en `ERROR_TECNICO`, distinto de falta de evidencia | `ERROR_TECNICO` (`FileNotFoundError`) y turno guardado                     |

## 7. Uso de inteligencia artificial

> [!important] Registrar la IA no reemplaza la explicación técnica. El equipo debe verificar, adaptar y comprender cualquier resultado utilizado.

| Herramienta | Objetivo o pregunta | Qué se utilizó | Cómo se verificó | Qué se modificó |
|---|---|---|---|---|
| [Herramienta] | [Solicitud resumida] | [Aporte aprovechado] | [Prueba o fuente] | [Adaptación propia] |

Si no se utilizó IA, escribir: **No se utilizó inteligencia artificial en esta sesión.**

## 8. Defensa técnica y retroalimentación

| Campo | Registro |
|---|---|
| Integrante que defendió | Sebastián Cruz Cardona |
| Pregunta recibida | N/A |
| Respuesta resumida | N/A |
| Retroalimentación docente | N/A |
| Mejora acordada | N/A |

## 9. Aprendizajes

- **Concepto comprendido:** Pasar de un notebook a una aplicación multiusuario cambia sobre todo la forma de manejar la identidad y el estado. El agente pudo migrarse casi sin cambios, pero el cliente global, la memoria en un diccionario y la carga del corpus en una celda tuvieron que reemplazarse por un cliente por usuario, un historial en Supabase protegido con RLS y un corpus que se reconstruye desde un módulo a parte. También quedó claro que separar los permisos del corpus compartido de los del historial privado se resuelve en la base de datos y no solo en la interfaz.
- **Algo que aún genera duda:** N/A
- **Qué haríamos diferente:** No trabajar en colab desde el principio y construir el proyecto en su estructura de ficheros para git, con las responsabilidades separadas. Esto evitaría adaptaciones que podrían dejarse organizadas desde el inicio.

## 10. Revisión antes de entregar

- [x] Todos los integrantes registraron un aporte verificable.
- [x] Los enlaces y rutas de evidencia funcionan.
- [x] Los criterios de aceptación están actualizados.
- [ ] El uso de IA fue declarado y verificado.
- [x] El equipo puede explicar las decisiones registradas.
