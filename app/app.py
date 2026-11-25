"""
Interfaz Gradio del asistente normativo.

Presenta el inicio de sesión, las conversaciones del usuario, el chat, las
fuentes, el resultado de las herramientas y el recorrido de cada respuesta.
Gestiona el estado de cada sesión (gr.State) y llama a las funciones de
sistema.py sin duplicar su lógica.
"""

import asyncio
import html
import json
import os

import gradio as gr

import sistema

# Presentación de cada estado final de la traza
ESTADOS = {
    "RESPONDER": ("Respuesta", None),
    "ACLARAR": ("Aclaración solicitada", "El asistente necesita un dato adicional."),
    "RECHAZAR": ("Solicitud rechazada", "La solicitud está fuera del alcance o de los permisos del asistente."),
    "ERROR_VALIDACION": ("Error de validación", "La propuesta del modelo no superó los controles del sistema. Reformula la pregunta."),
    "ERROR_TECNICO": ("Error técnico", "No pudimos completar una consulta o una llamada al modelo. Esto no indica falta de evidencia."),
    "ERROR_PERMISO": ("Sin permiso", "La conversación no existe o no te pertenece."),
    "LIMITE_TIEMPO": ("Tiempo agotado", "El recorrido superó el tiempo de espera."),
    "LIMITE_DECISIONES": ("Recorrido detenido", "Se alcanzó el máximo de decisiones."),
    "LIMITE_OPERACIONES": ("Recorrido detenido", "Se alcanzó el máximo de operaciones."),
    "LIMITE_CONTEXTO": ("Recorrido detenido", "El contexto superó el límite permitido."),
    "REPETICION_SIN_AVANCE": ("Recorrido detenido", "El agente intentó repetir una operación sin avance.")
}

# Estados en los que se muestra la respuesta del agente tal cual
ESTADOS_CON_RESPUESTA = {"RESPONDER", "ACLARAR", "RECHAZAR"}

# Nombre visible de cada operación del agente
OPERACIONES = {
    "buscar_documentos": "RAG · corpus documental",
    "consultar_estado_proceso": "MCP propio · consultar_estado_proceso",
    "buscar_jurisprudencia": "MCP externo · buscar_jurisprudencia",
    "linea_jurisprudencial": "MCP externo · linea_jurisprudencial"
}

# Máximo de caracteres del resultado de jurisprudencia en el panel
MAX_TEXTO_HERRAMIENTA = 4000

# gr.Chatbot no tiene opción para quitar el botón de limpiar el chat; se oculta
# por su etiqueta (en inglés y en español, según el idioma del navegador).
# Limpiar el chat no borra la conversación guardada, así que no tiene uso aquí
CSS = """
#chat button[aria-label="Clear"], #chat button[title="Clear"],
#chat button[aria-label="Limpiar chat"], #chat button[title="Limpiar chat"] {
    display: none !important;
}
"""


# ---------- Presentación ----------

def contenido_mostrado(respuesta, estado):
    """
    Texto del asistente en el chat según el estado final.
    Los errores muestran un aviso general; el detalle queda en el recorrido.
    """
    if estado in ESTADOS_CON_RESPUESTA:
        return respuesta

    titulo, explicacion = ESTADOS.get(estado, ("Recorrido incompleto", respuesta))
    return f"⚠️ **{titulo}.** {explicacion or respuesta}"


def formatear_fuentes(fuentes, citas):
    """
    Markdown con las fuentes citadas: fragmentos del corpus [F] y
    registros del MCP propio [T].
    """
    if not citas:
        return "_Esta respuesta no cita fuentes del corpus ni de procesos._"

    bloques = []

    for etiqueta in citas:
        fuente = (fuentes or {}).get(etiqueta)

        if fuente is None:
            continue

        if etiqueta.startswith("F"):
            meta = fuente.get("fuente", {})
            extracto = " ".join(fuente.get("texto", "").split())
            extracto = extracto if len(extracto) <= 500 else extracto[:500] + "…"
            bloques.append(
                f"**[{etiqueta}] {meta.get('source', 'Documento')}**  \n"
                f"Sección: {meta.get('section', '—')} · Versión: {meta.get('version', '—')}  \n"
                f"> {extracto}"
            )

        else:
            registro = fuente.get("registro") or {}
            if fuente.get("encontrado"):
                detalle = (
                    f"Categoría: {registro.get('categoria')} · Estado: {registro.get('estado')} · "
                    f"Decisión: {registro.get('decision')} · Terminación: {registro.get('terminacion')}  \n"
                    f"{registro.get('detalle', '')}"
                )
            else:
                detalle = "El proceso no figura en los registros disponibles."

            bloques.append(
                f"**[{etiqueta}] Proceso {fuente.get('codigo_proceso')}** "
                f"(MCP propio · {fuente.get('fuente')})  \n{detalle}"
            )

    return "\n\n".join(bloques) or "_No hay fuentes para mostrar._"


def resumir_resultado(operacion, resultado):
    """
    Markdown con el resultado que devolvió una herramienta.
    """
    if operacion == "buscar_documentos":
        lineas = [
            f"- [{r.get('etiqueta')}] {r.get('fuente', {}).get('source', 'Documento')} · "
            f"{r.get('fuente', {}).get('section', '—')}"
            for r in resultado or []
        ]
        return "\n".join(lineas) or "_La búsqueda no devolvió fragmentos._"

    if operacion == "consultar_estado_proceso":
        if not resultado.get("encontrado"):
            return f"[{resultado.get('etiqueta')}] El proceso no figura en los registros disponibles."

        registro = resultado.get("registro") or {}
        return (
            f"[{resultado.get('etiqueta')}] Estado: {registro.get('estado')} · "
            f"Decisión: {registro.get('decision')} · Terminación: {registro.get('terminacion')}"
        )

    # Jurisprudencia: texto del servidor en un bloque sin interpretar como Markdown
    texto = resultado.get("texto", "")
    if len(texto) > MAX_TEXTO_HERRAMIENTA:
        texto = texto[:MAX_TEXTO_HERRAMIENTA] + "\n[…] Resultado recortado en la vista."
    texto = texto.replace("```", "'''")
    nota = f"\n\n_{resultado['nota']}_" if resultado.get("nota") else ""
    return f"```text\n{texto}\n```{nota}"


def formatear_herramientas(traza):
    """
    Markdown con las herramientas que usó el agente: operación, argumentos
    y resultado, o el error si la operación no terminó.
    """
    eventos = (traza or {}).get("eventos") or []
    iniciadas = [e for e in eventos if e.get("etapa") == "OPERACION_INICIADA"]

    if not iniciadas:
        return "_Esta respuesta no usó herramientas._"

    recibidos = {
        (e.get("paso"), e.get("operacion")): e
        for e in eventos if e.get("etapa") == "RESULTADO_RECIBIDO"
    }

    bloques = []

    for evento in iniciadas:
        operacion = evento.get("operacion")
        argumentos = json.dumps(evento.get("argumentos"), ensure_ascii=False)
        recibido = recibidos.get((evento.get("paso"), operacion))

        if recibido is None:
            error = traza.get("tipo_error") or traza.get("estado")
            detalle = f"⚠️ La operación no devolvió resultado ({error})."
        elif "resultado" not in recibido:
            detalle = "_Resultado no registrado en el historial._"
        else:
            detalle = resumir_resultado(operacion, recibido["resultado"])

        bloques.append(
            f"**{OPERACIONES.get(operacion, operacion)}**  \n"
            f"Argumentos: `{argumentos}`\n\n{detalle}"
        )

    return "\n\n---\n\n".join(bloques)


def formatear_estado(info):
    """
    Resumen del estado, operaciones y guardado de una respuesta.
    """
    if not info:
        return ""

    estado = info.get("estado", "")
    titulo, _ = ESTADOS.get(estado, (estado, None))
    partes = [f"**Estado:** {titulo} (`{estado}`)"]

    traza = info.get("traza") or {}
    if traza:
        partes.append(
            f"**Operaciones:** {traza.get('operaciones', 0)} · "
            f"**Duración:** {traza.get('duracion_ms', '—')} ms"
        )

    if info.get("guardado") is False:
        partes.append("⚠️ **Este turno no se guardó en el historial.**")

    return "  \n".join(partes)


def recorrido(traza):
    """
    Parte de la traza útil para revisar el recorrido, sin la entrada repetida.
    Los resultados de las herramientas se muestran en su propio panel.
    """
    if not traza:
        return None

    resumen = {
        clave: traza.get(clave)
        for clave in (
            "estado", "eventos", "operaciones", "duracion_ms",
            "uso_tokens", "tipo_error", "detalle_error", "respuesta"
        )
        if traza.get(clave) not in (None, "", [])
    }

    if "eventos" in resumen:
        resumen["eventos"] = [
            {clave: valor for clave, valor in evento.items() if clave != "resultado"}
            for evento in resumen["eventos"]
        ]

    return resumen


def mensajes_a_chat(mensajes):
    """
    Convierte los mensajes guardados en mensajes de gr.Chatbot y una lista
    paralela con la información de fuentes de cada mensaje.
    """
    chat, info = [], []

    for mensaje in mensajes:
        if mensaje["rol"] == "usuario":
            chat.append({"role": "user", "content": mensaje["contenido"]})
            info.append(None)
        else:
            chat.append(
                {
                    "role": "assistant",
                    "content": contenido_mostrado(mensaje["contenido"], mensaje.get("estado"))
                }
            )
            info.append(
                {
                    "estado": mensaje.get("estado"),
                    "citas": mensaje.get("citas") or [],
                    "fuentes": mensaje.get("fuentes") or {},
                    "traza": mensaje.get("traza"),
                    "guardado": True
                }
            )

    return chat, info


def opciones_conversaciones(conversaciones):
    """
    Opciones (título, id) para el selector.
    """
    return [(c["titulo"], c["id"]) for c in conversaciones]


def paneles(info):
    """
    Valores del panel lateral para una respuesta:
    estado, fuentes, herramientas y recorrido.
    """
    if not info:
        return "", "", "", None

    return (
        formatear_estado(info),
        formatear_fuentes(info.get("fuentes"), info.get("citas")),
        formatear_herramientas(info.get("traza")),
        recorrido(info.get("traza"))
    )


# ---------- Vistas ----------

def vista_inicio(mensaje=""):
    """
    Restablece el estado de la sesión y muestra el inicio de sesión.
    Orden: sesion, conversacion, info, pendiente, vista_login, vista_chat,
    boton_salir, usuario, selector, chatbot, estado, fuentes, herramientas,
    recorrido, aviso, mensaje_login.
    """
    return (
        None, None, [], "",
        gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
        "", gr.update(choices=[], value=None), [],
        "", "", "", None, "", mensaje
    )


# ---------- Eventos ----------

async def iniciar(email, password):
    try:
        sesion = await asyncio.to_thread(sistema.iniciar_sesion, email, password)
    except ValueError as error:
        return (*vista_inicio(f"⚠️ {error}"), gr.update())
    except Exception:
        return (*vista_inicio("⚠️ No pudimos conectar con Supabase. Intenta de nuevo."), gr.update())

    try:
        # El corpus se carga al iniciar sesión, fuera de la atención de preguntas
        sesion = await asyncio.to_thread(sistema.preparar_corpus, sesion)
        sesion, conversaciones = await asyncio.to_thread(sistema.listar_conversaciones, sesion)
    except sistema.SesionInvalida as error:
        return (*vista_inicio(f"⚠️ {error}"), gr.update())
    except Exception:
        return (*vista_inicio("⚠️ No pudimos cargar el corpus o las conversaciones. Intenta de nuevo."), gr.update())

    return (
        sesion, None, [], "",
        gr.update(visible=False), gr.update(visible=True), gr.update(visible=True),
        # HTML y no Markdown: Markdown convierte el correo en un enlace
        f"<p><strong>Usuario:</strong> {html.escape(sesion['email'])}</p>",
        gr.update(choices=opciones_conversaciones(conversaciones), value=None),
        [], "", "", "", None, "", "",
        ""  # Limpiar la contraseña
    )


async def salir(sesion):
    await asyncio.to_thread(sistema.cerrar_sesion, sesion)
    return vista_inicio("Sesión cerrada.")


def nueva_conversacion():
    """
    Prepara una conversación nueva. Se crea en Supabase con la primera pregunta;
    las anteriores no se borran.
    """
    return None, [], [], gr.update(value=None), "", "", "", None, ""


async def seleccionar_conversacion(sesion, conversacion_id):
    if not conversacion_id:
        return (sesion, None, [], [], "", "", "", None, "")

    try:
        sesion, mensajes = await asyncio.to_thread(
            sistema.cargar_conversacion, sesion, conversacion_id
        )
    except sistema.SesionInvalida as error:
        return (sesion, None, [], [], "", "", "", None, f"⚠️ {error}")
    except sistema.almacenamiento.PermisoDenegado as error:
        return (sesion, None, [], [], "", "", "", None, f"⚠️ {error}")
    except Exception:
        return (sesion, None, [], [], "", "", "", None, "⚠️ No pudimos recuperar la conversación.")

    chat, info = mensajes_a_chat(mensajes)

    # Mostrar en el panel la última respuesta de la conversación
    ultima = next((i for i in reversed(info) if i), None)
    estado, fuentes, herramientas, traza = paneles(ultima)

    return sesion, conversacion_id, chat, info, estado, fuentes, herramientas, traza, ""


def preparar_envio(texto, chat, info):
    """
    Muestra la pregunta en el chat antes de que llegue la respuesta
    y bloquea la entrada mientras el agente trabaja.
    """
    texto = (texto or "").strip()

    if not texto:
        raise gr.Error("Escribe una pregunta.")

    if len(texto) > 1200:
        raise gr.Error("Escribe una entrada de hasta 1200 caracteres.")

    chat = (chat or []) + [{"role": "user", "content": texto}]
    info = (info or []) + [None]

    return (
        texto, chat, info,
        gr.update(value="", interactive=False),
        gr.update(interactive=False),
        "_Consultando…_"
    )


async def responder(sesion, conversacion_id, texto, chat, info):
    """
    Llama al sistema y agrega la respuesta con sus fuentes, herramientas y recorrido.
    """
    desbloquear = (gr.update(interactive=True), gr.update(interactive=True))

    try:
        resultado = await sistema.atender_mensaje(sesion, conversacion_id, texto)

    except sistema.SesionInvalida as error:
        chat = chat + [{"role": "assistant", "content": f"⚠️ {error}"}]
        return (
            sesion, conversacion_id, chat, info + [None], gr.update(),
            "", "", "", None, f"⚠️ {error} Cierra sesión e ingresa de nuevo.", *desbloquear
        )

    except Exception:
        chat = chat + [{"role": "assistant", "content": "⚠️ **Error técnico.** No pudimos procesar la solicitud."}]
        return (
            sesion, conversacion_id, chat, info + [None], gr.update(),
            "", "", "", None, "", *desbloquear
        )

    sesion = resultado["sesion"]
    traza = resultado["traza"]

    datos = {
        "estado": traza.get("estado"),
        "citas": traza.get("citas") or [],
        "fuentes": traza.get("fuentes") or {},
        "traza": traza,
        "guardado": resultado["guardado"]
    }

    chat = chat + [
        {"role": "assistant", "content": contenido_mostrado(traza.get("respuesta", ""), traza.get("estado"))}
    ]
    info = info + [datos]

    conversacion_id = resultado["conversacion_id"] or conversacion_id

    # Actualizar el selector con la conversación activa
    try:
        sesion, conversaciones = await asyncio.to_thread(sistema.listar_conversaciones, sesion)
        selector = gr.update(choices=opciones_conversaciones(conversaciones), value=conversacion_id)
    except Exception:
        selector = gr.update()

    estado, fuentes, herramientas, recorrido_traza = paneles(datos)
    aviso = "" if resultado["guardado"] else "⚠️ La respuesta se mostró, pero no se guardó en el historial."

    return (
        sesion, conversacion_id, chat, info, selector,
        estado, fuentes, herramientas, recorrido_traza, aviso, *desbloquear
    )


def mostrar_fuentes_mensaje(info, evento: gr.SelectData):
    """
    Al seleccionar una respuesta del chat, muestra sus fuentes, herramientas y recorrido.
    """
    indice = evento.index
    if isinstance(indice, (list, tuple)):
        indice = indice[0]

    if not isinstance(indice, int) or not 0 <= indice < len(info or []) or not info[indice]:
        return gr.update(), gr.update(), gr.update(), gr.update()

    return paneles(info[indice])


# ---------- Interfaz ----------

def construir_interfaz():
    with gr.Blocks(title="Asistente normativo") as demo:
        sesion = gr.State(None)
        conversacion = gr.State(None)
        info_mensajes = gr.State([])
        pendiente = gr.State("")

        # Encabezado: título a la izquierda y cierre de sesión a la derecha,
        # alineado con el borde derecho del panel lateral
        with gr.Row():
            gr.Markdown(
                "# Asistente normativo\n"
                "Consultas sobre el corpus documental, procesos judiciales ficticios "
                "y jurisprudencia de la Corte Constitucional de Colombia."
            )
            boton_salir = gr.Button("Cerrar sesión", size="sm", scale=0, min_width=120, visible=False)

        # Inicio de sesión: columna central de la mitad del ancho
        with gr.Row(visible=True) as vista_login:
            gr.Column(scale=1, min_width=0)
            with gr.Column(scale=2, min_width=280):
                correo = gr.Textbox(label="Correo", max_lines=1)
                clave = gr.Textbox(label="Contraseña", type="password", max_lines=1)
                boton_login = gr.Button("Iniciar sesión", variant="primary")
                mensaje_login = gr.Markdown()
            gr.Column(scale=1, min_width=0)

        with gr.Row(visible=False) as vista_chat:
            with gr.Column(scale=1, min_width=220):
                usuario = gr.HTML()
                boton_nueva = gr.Button("Nueva conversación", variant="primary")
                selector = gr.Radio(label="Conversaciones", choices=[], value=None)

            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversación",
                    elem_id="chat",
                    height=560,
                    buttons=["copy"],
                    placeholder="Escribe una pregunta para comenzar una conversación."
                )
                with gr.Row():
                    entrada = gr.Textbox(
                        show_label=False,
                        placeholder="Ejemplo: ¿Cuál es el estado del proceso P-20210010001?",
                        max_lines=4,
                        scale=5
                    )
                    boton_enviar = gr.Button("Enviar", variant="primary", scale=1)
                aviso = gr.Markdown()

            with gr.Column(scale=2, min_width=260):
                estado = gr.Markdown()
                with gr.Accordion("Fuentes", open=True):
                    fuentes = gr.Markdown()
                with gr.Accordion("Herramientas", open=True):
                    herramientas = gr.Markdown()
                with gr.Accordion("Recorrido", open=False):
                    traza = gr.JSON(label="Traza")

        salida_vista = [
            sesion, conversacion, info_mensajes, pendiente,
            vista_login, vista_chat, boton_salir, usuario, selector, chatbot,
            estado, fuentes, herramientas, traza, aviso, mensaje_login
        ]

        # Inicio y cierre de sesión. Al iniciar, el chat aún está oculto: la
        # animación se muestra solo bajo el botón de inicio de sesión
        for disparador in (boton_login.click, clave.submit):
            disparador(
                iniciar, [correo, clave], salida_vista + [clave],
                show_progress_on=mensaje_login
            )

        boton_salir.click(salir, [sesion], salida_vista, show_progress_on=chatbot)

        # Conversaciones
        boton_nueva.click(
            nueva_conversacion, None,
            [conversacion, chatbot, info_mensajes, selector, estado, fuentes, herramientas, traza, aviso]
        )

        selector.input(
            seleccionar_conversacion, [sesion, selector],
            [sesion, conversacion, chatbot, info_mensajes, estado, fuentes, herramientas, traza, aviso],
            show_progress_on=chatbot
        )

        # Envío de la pregunta: primero se muestra, luego se responde.
        # La animación de carga se muestra solo en el chat
        for disparador in (boton_enviar.click, entrada.submit):
            disparador(
                preparar_envio, [entrada, chatbot, info_mensajes],
                [pendiente, chatbot, info_mensajes, entrada, boton_enviar, aviso],
                show_progress="hidden"
            ).success(
                responder, [sesion, conversacion, pendiente, chatbot, info_mensajes],
                [sesion, conversacion, chatbot, info_mensajes, selector,
                 estado, fuentes, herramientas, traza, aviso, entrada, boton_enviar],
                show_progress_on=chatbot
            )

        chatbot.select(mostrar_fuentes_mensaje, [info_mensajes], [estado, fuentes, herramientas, traza])

    return demo


if __name__ == "__main__":
    print("Preparando el sistema (modelo de embeddings, Node.js y servidores MCP)…")
    resumen = asyncio.run(sistema.preparar())
    print("Sistema preparado:", resumen)

    demo = construir_interfaz()
    demo.queue(default_concurrency_limit=4).launch(
        css=CSS,
        server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.environ.get("PORT", "7860"))
    )
