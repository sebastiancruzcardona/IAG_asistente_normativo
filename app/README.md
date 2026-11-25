# Aplicación del asistente normativo

Esta carpeta contiene la aplicación web del asistente normativo, es decir, todo lo necesario para ejecutarla en local, conectarla con Supabase y probarla. La instalación, la configuración y la ejecución paso a paso están en el [`README.md`](../README.md) de la raíz del proyecto, así que aquí solo se describe qué hay en cada archivo.

## Contenido

| Archivo o carpeta | Contenido |
|---|---|
| [`app.py`](app.py) | Interfaz de Gradio, con el inicio y cierre de sesión, la lista de conversaciones, el chat y el panel lateral. Solo presenta, y toda la lógica la delega en `sistema.py`. |
| [`sistema.py`](sistema.py) | Coordina el recorrido completo, con la configuración, la identidad por usuario, el RAG, los clientes MCP, el contrato `Decision`, las validaciones, los límites y el agente. Proviene del notebook `notebooks/asistente_normativo_RAG_agente_MCP.ipynb`. |
| [`almacenamiento.py`](almacenamiento.py) | Crea y lista conversaciones, carga sus mensajes y guarda cada turno en Supabase, siempre después de comprobar el propietario. |
| [`corpus.py`](corpus.py) | Contiene los textos del corpus y los convierte en fragmentos con embeddings. Además, crea y comparte una versión nueva cuando el texto cambia. |
| [`servidor_mcp.py`](servidor_mcp.py) | Servidor MCP propio, de solo lectura, con la herramienta `consultar_estado_proceso` sobre diez procesos ficticios. |
| [`supabase/`](supabase/) | Script SQL de la clase 8 y migraciones del historial y del corpus compartido. Su [`README.md`](supabase/README.md) explica el orden de ejecución y la estrategia de permisos. |
| [`pruebas/`](pruebas/) | Pruebas con pytest de los controles, el historial y RLS, el corpus y el recorrido con el modelo. Su [`README.md`](pruebas/README.md) explica cómo ejecutarlas. |
| [`requirements.txt`](requirements.txt) | Dependencias con sus versiones fijas, agrupadas por función. |
| [`.env.ejemplo`](.env.ejemplo) | Plantilla de las variables de entorno. A partir de ella se crea `app/.env`, que nunca se publica. |
| [`pytest.ini`](pytest.ini) | Configuración de pytest, por lo que las pruebas se ejecutan desde esta carpeta. |
| [`presentacion_proyecto.pdf`](presentacion_proyecto.pdf) | Presentación de la entrega final. |

Al ejecutarse, la aplicación crea además la carpeta `logs/`, con los registros de los dos servidores MCP. Esa carpeta, igual que `app/.env`, está excluida en `.gitignore`.

## Ejecución rápida

Con el entorno virtual creado y `app/.env` completo, primero se activa `.venv` y luego se inicia la aplicación desde la raíz del proyecto. Cuando termina de arrancar, queda disponible en **http://127.0.0.1:7860**.

```powershell
# Windows (PowerShell)
# Activar el entorno virtual
.\.venv\Scripts\Activate.ps1

# Iniciar la aplicación
python app/app.py
py app/app.py
```

```bash
# Linux o macOS
# Activar el entorno virtual
source .venv/bin/activate

# Iniciar la aplicación
python app/app.py
```
