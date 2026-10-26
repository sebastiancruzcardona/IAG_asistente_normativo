# Asistente normativo --- Corte 2

Prototipo integrado de un asistente normativo para apoyar a abogados que
trabajan en un juzgado en Colombia. Combina la clasificación de
solicitudes y la consulta de procesos ficticios del corte 1 con un
sistema de recuperación aumentada por generación (RAG), que busca
evidencia documental, genera respuestas con citas y permite comparar
estrategias de recuperación.

**Entrega:** prototipo integrado del corte 2.\
**Autor:** Sebastián Cruz Cardona.\
**Código:** 240220222010.\
**Programa:** Ingeniería de Software.\
**Institución:** Institución Universitaria EAM.

## 1. Problema y objetivo

Las consultas jurídicas requieren distinguir la intención de la persona,
identificar la información disponible y evitar respuestas que no cuenten
con respaldo suficiente. El prototipo explora cómo un asistente puede
apoyar este trabajo mediante la clasificación de solicitudes y la
búsqueda de evidencia en un corpus documental.

El objetivo del corte 2 es integrar el prototipo inicial con un flujo
RAG. El sistema recupera fragmentos de documentos, genera una respuesta
estructurada y presenta referencias para que una persona pueda
contrastarla con las fuentes. También compara tres estrategias de
recuperación para observar si la búsqueda híbrida o el reranking mejoran
los resultados.


## 2. Alcance

### Implementado

-   Clasificación de solicitudes normativas con un contrato estructurado
    validado mediante Pydantic.
-   Detección de solicitudes incompletas, fuera de alcance o que
    requieren revisión humana.
-   Consulta de solo lectura del estado de procesos ficticios mediante
    `consultar_estado_proceso`.
-   Preparación de un corpus documental, limpieza, fragmentación y
    generación de embeddings.
-   Persistencia de fragmentos y vectores en Supabase.
-   Recuperación semántica, búsqueda léxica BM25 y fusión de rankings
    con Reciprocal Rank Fusion (RRF).
-   Comparación de tres alternativas: A, búsqueda semántica; B, búsqueda
    híbrida con RRF; y C, búsqueda híbrida con reranking.
-   Generación de respuestas con Groq, validación estructural y
    presentación de citas.
-   Registro de trazas, métricas y evidencias de evaluación.
-   Interfaz al final del flujo principal para probar el RAG documental,
    la clasificación y las herramientas.
-   Anexo opcional para convertir archivos PDF, PDF escaneados, Excel y
    Word a Markdown.

### Fuera de alcance

-   Consulta o modificación de expedientes y sistemas institucionales
    reales.
-   Creación, actualización o eliminación de procesos judiciales.
-   Uso de las respuestas como asesoría jurídica definitiva.
-   Incorporación automática al corpus de los documentos convertidos en
    el anexo.
-   Certificación del rendimiento del sistema a partir de un conjunto
    pequeño de preguntas.

## 3. Arquitectura y flujo

El notebook integra dos recorridos relacionados:

``` text
RECORRIDO DE CLASIFICACIÓN Y HERRAMIENTAS
Texto de la persona
  → validación de entrada
  → clasificación estructurada con Groq o respuestas simuladas
  → validación con Pydantic y reglas de decisión
  → validación de la herramienta y sus argumentos
  → consulta de solo lectura a registros ficticios
  → respuesta y traza de ejecución

RECORRIDO RAG DOCUMENTAL
Documentos ficticios
  → limpieza y fragmentación
  → embeddings
  → índice local de la clase 7
  → fragmentos y vectores en Supabase
  → recuperación semántica (A), híbrida con BM25 + RRF (B)
    o híbrida con reranking (C)
  → generación con Groq
  → validación de la respuesta y sus citas
  → revisión humana y registro de evidencia
```

Supabase almacena los fragmentos y permite la búsqueda semántica. BM25,
RRF y el reranker se ejecutan en Colab. Groq genera las respuestas a
partir de la pregunta y los pasajes recuperados. Las credenciales de
Supabase no se envían al modelo generativo.

La estrategia B, búsqueda híbrida con RRF, queda seleccionada como
opción principal en la evaluación registrada: obtuvo las mismas métricas
de recuperación que C, con menor latencia de recuperación y menor tiempo
total en las pruebas documentadas. La interfaz conserva C para comparar
ambas alternativas.

## 4. Tecnologías utilizadas

-   **Python**, ejecutado en Google Colab.
-   **Sentence Transformers:**
    `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, para
    generar embeddings.
-   **Supabase:** almacenamiento de fragmentos y vectores, autenticación
    y recuperación semántica.
-   **Groq:** generación de respuestas con el modelo
    `openai/gpt-oss-20b`.
-   **Pydantic:** validación de los contratos de clasificación y
    respuesta.
-   **rank-bm25:** recuperación léxica BM25.
-   **Cross-encoder multilingüe:** reordenamiento de candidatos en la
    estrategia C.
-   **NumPy, JSON y bibliotecas estándar de Python:** procesamiento,
    validación y exportación de evidencias.

Las versiones de las dependencias principales se fijan en las celdas de
preparación del notebook.

## 5. Requisitos previos

Para ejecutar la entrega se requiere:

1.  Una cuenta con acceso a **Google Colab** y conexión a Internet.

2.  Un proyecto de **Supabase** con la tabla `clase08_fragmentos`, la
    función RPC `clase08_buscar_fragmentos` y las políticas de acceso
    necesarias. El notebook utiliza esta infraestructura, pero no crea
    la tabla, la función ni las políticas.

3.  Un usuario de Supabase Auth habilitado para la práctica y con acceso
    limitado mediante las políticas configuradas.

4.  Los siguientes secretos guardados en la sección **Secrets** de
    Google Colab:

    -   `GROQ_API_KEY`
    -   `SUPABASE_URL`
    -   `SUPABASE_PUBLISHABLE_KEY`
    -   `SUPABASE_EMAIL`
    -   `SUPABASE_PASSWORD`

**No escriba los valores de estos secretos en el notebook**

## 6. Instalación y ejecución

### 6.1. Preparar el entorno

1.  Abra `prototipo_asistente_normativo_corte2.ipynb` en Google Colab.
2.  Configure los cinco secretos indicados en la sección anterior.
3.  Verifique que el proyecto de Supabase tenga la tabla, la función RPC
    y las políticas requeridas.
4.  Ejecute las celdas en orden, desde el inicio del notebook. La
    ejecución inicial descarga dependencias y el modelo de embeddings;
    puede tardar más que las ejecuciones posteriores.
5.  Si Colab solicita reiniciar el entorno después de instalar
    dependencias, reinicie y ejecute el notebook desde el principio.

### 6.2. Ejecutar el flujo integrado

El notebook conserva primero el recorrido de clasificación y
herramientas del corte 1 y, después, las secciones de las clases 6 a 9.

-   **Clase 7:** prepara el corpus, genera los fragmentos, calcula los
    embeddings y crea `Clase_07_Indice_y_Corpus.zip`.
-   **Clase 8:** lee el índice generado, carga los fragmentos y vectores
    en Supabase, permite recuperar evidencia y generar respuestas, y
    crea `Clase_08_Evidencia_RAG.json`.
-   **Clase 9:** compara las estrategias A, B y C, calcula métricas de
    recuperación, genera respuestas para las alternativas seleccionadas
    y registra la evaluación.
-   **Interfaz de usuario:** ubicada al final del flujo principal, antes del
    anexo opcional, permite escribir una pregunta y seleccionar el
    recorrido que se desea probar.

La interfaz solo funciona después de ejecutar en orden las celdas
anteriores, incluidas la conexión a Supabase y la preparación de las
funciones de recuperación y generación. **No es necesario ejecutar el
anexo opcional** para utilizarla.

### 6.3. Probar el asistente

En la celda **Interfaz del asistente normativo integrado**, escriba una
pregunta, seleccione un modo y ejecute la celda:

-   `RAG documental (B: híbrida con RRF)`: utiliza la estrategia
    principal seleccionada.
-   `RAG documental (C: con reranking)`: permite contrastar la
    alternativa con reranking.
-   `Clasificación y herramienta`: ejecuta el flujo inicial de
    clasificación y, cuando corresponde, la consulta de solo lectura a
    los registros ficticios.
-   `RAG + clasificación/herramienta`: ejecuta ambos recorridos para la
    misma pregunta y puede consumir más cuota de API.

Ejemplos de preguntas:

``` text
Si una ley contradice la Constitución, ¿cuál debe prevalecer?
¿Cómo se hace para consultar el estado de un proceso?
¿Cómo solicito una audiencia con el juez?
¿Cómo lo hago?
¿Cómo va el proceso P-20210010001?
¿Cómo va mi proceso?
```

El resultado depende de la evidencia disponible, de la clasificación y
de las respuestas del modelo. Si los documentos no respaldan una
respuesta, el sistema debe indicar que la evidencia es insuficiente o
pedir una aclaración, en lugar de inventar información.

## 7. Archivos generados y manejo de sesiones

El notebook crea varios archivos durante la ejecución:

  ------------------------------------------------------------------------------
  Archivo                                    Uso
  ------------------------------------------ -----------------------------------
  `Clase_07_Indice_y_Corpus.zip`             Copia del índice local con los
                                             registros, vectores y configuración
                                             de embeddings.

  `Clase_08_Evidencia_RAG.json`              Configuración del corpus, versión
                                             del prompt y trazas aceptadas del
                                             flujo RAG.

  `Clase_09_Evidencia_Evaluacion_RAG.json`   Evidencia estructurada de la
                                             evaluación del RAG.

  `Clase_09_Metricas_RAG.csv`                Métricas de evaluación en formato
                                             tabular.

  `Clase_09_Evidencia_Evaluacion_RAG.zip`    Paquete con las evidencias de
                                             evaluación de la clase 9.

  ZIP de evidencias de la clase 4            Prompts, esquemas, datos ficticios,
                                             evaluación y trazas del prototipo
                                             inicial.
  ------------------------------------------------------------------------------

En una misma sesión de Colab, el índice ZIP y el JSON de la clase 8 se
generan y reutilizan directamente; no hace falta descargarlos y
volverlos a subir. La descarga del índice es opcional y sirve como copia
de respaldo. La celda de evaluación de la clase 9 descarga el ZIP de
evidencias final.

**Si se reinicia o se pierde la sesión de Colab**, desaparecen las
variables y los archivos temporales. Vuelva a ejecutar las secciones
anteriores en orden para regenerarlos o cargue una copia de respaldo
cuando corresponda. La persistencia de los fragmentos en Supabase no
conserva las variables ni los archivos locales de Colab.

Antes de compartir un archivo de evidencia, revise su contenido. Aunque
el notebook evita exportar credenciales y tokens de acceso, las trazas
pueden conservar las preguntas introducidas y otros detalles de
ejecución.

## 8. Consumo de API

Las llamadas al modelo de Groq pueden consumir cuota. En esta versión,
algunos interruptores de pruebas están activados por defecto:

-   Las pruebas de continuidad del corte 1.
-   Las cinco pruebas breves de la clase 8.
-   La comparación de respuestas de la clase 9.
-   Las llamadas que se realicen desde la interfaz.

Revise los interruptores antes de ejecutar todas las celdas. Desactive
las pruebas que no necesite si desea reducir el consumo. La recuperación
semántica, BM25, RRF y el reranking no son llamadas generativas a Groq;
sin embargo, pueden requerir descargar modelos o ejecutar procesamiento
local en Colab.

## 9. Anexo de extracción de documentos

El anexo opcional permite extraer texto de archivos PDF con texto
seleccionable, PDF escaneados mediante OCR, hojas de Excel y documentos
Word. El resultado se guarda como Markdown local en
`corpus_extraido_clase08`.

La conversión **no incorpora automáticamente** los documentos al corpus,
no genera sus embeddings y no los carga en Supabase. Para consultarlos
mediante RAG, revise el Markdown contra el original y añádalo
explícitamente al proceso de ingestión de la clase 7. Después, vuelva a
generar el índice y ejecute la carga a Supabase de la clase 8.

Use únicamente documentos propios o autorizados. La extracción puede
omitir imágenes, elementos de formato o contenido de tablas; por ello,
es necesario verificar el resultado antes de usarlo como evidencia.

## 10. Validación y limitaciones

-   Pydantic valida la estructura de las respuestas, y las
    comprobaciones revisan que las etiquetas de cita existan y coincidan
    con el contrato.
-   Una cita con formato válido no garantiza que la afirmación esté
    respaldada semánticamente. Es necesaria una revisión humana de las
    fuentes.
-   La evaluación usa un conjunto pequeño de preguntas didácticas. Sus
    resultados ilustran el procedimiento, pero no certifican el
    desempeño en un entorno judicial real.
-   Los procesos y estados son ficticios; no existe conexión con
    expedientes institucionales.
-   El modo `mock` utiliza respuestas programadas y no mide el
    rendimiento del modelo real.
-   Las latencias registradas corresponden a ejecuciones puntuales, no a
    un estudio de rendimiento a gran escala.
-   Un error de API o de validación se registra como error técnico; no
    equivale a una respuesta jurídicamente correcta ni a evidencia
    insuficiente.
-   Los documentos convertidos por el anexo requieren una ingestión
    explícita antes de formar parte del corpus consultable.

## 11. Seguridad y privacidad

-   No incluya claves, contraseñas, tokens, archivos de secretos ni
    datos personales en el repositorio o en las salidas guardadas.
-   Utilice únicamente preguntas, documentos y registros ficticios o
    autorizados.
-   Mantenga las credenciales en los secretos de Colab y limite los
    permisos de Supabase mediante las políticas de acceso.
-   Revise las trazas y los archivos de evidencia antes de compartirlos,
    ya que pueden conservar las consultas introducidas.
-   No interprete la respuesta del prototipo como decisión judicial ni
    como sustituto de la revisión de un profesional.

## 12. Estructura de la entrega

La entrega principal es el notebook integrado:

``` text
C09_2026_10_14_Estrategias_de_Recuperación.md
Clase_07_Indice_y_Corpus.zip
Clase_08_Evidencia_RAG.json
Clase_09_Evidencia_Evaluacion_RAG.zip
presentación_corte2_asistente_normativo
prototipo_asistente_normativo_corte2.ipynb
README.md
```

Durante la ejecución se generan los archivos de índice y evidencia
descritos en la sección 7. Las copias descargadas son respaldos o
materiales para la evaluación; no todos son necesarios para continuar en
una misma sesión de Colab.

## 13. Referencia de ejecución

-   **Notebook principal:**
    `prototipo_asistente_normativo_corte2.ipynb`.
-   **Entorno recomendado:** Google Colab.
-   **Modelo generativo:** `openai/gpt-oss-20b` mediante Groq.
-   **Modelo de embeddings:**
    `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
-   **Almacenamiento y búsqueda semántica:** Supabase.
-   **Estrategia RAG principal:** búsqueda híbrida con BM25 y RRF (B).
