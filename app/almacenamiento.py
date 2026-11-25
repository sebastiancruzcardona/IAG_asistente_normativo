"""
Guardado y recuperación de conversaciones en Supabase.

Todas las funciones reciben un cliente autenticado con el token del usuario
(sistema.cliente_usuario) y el usuario_id validado por Supabase Auth.
Cada operación comprueba el propietario en el código; las políticas RLS de
las tablas conversaciones y mensajes lo comprueban de nuevo en la base de datos.
No se usa ninguna clave administrativa.
"""

import re
from datetime import datetime, timezone

# Formato de los identificadores de conversación (UUID)
PATRON_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)

# Estados de la traza que representan un turno completado. Solo estos turnos
# forman la memoria del agente, igual que guardar_turno() en el notebook
ESTADOS_COMPLETADOS = {"RESPONDER", "ACLARAR", "RECHAZAR"}

# Límite de caracteres de los mensajes (coincide con la tabla mensajes)
MAX_CONTENIDO = 5000


class PermisoDenegado(Exception):
    """
    La conversación no existe o no pertenece al usuario autenticado.
    """
    pass


def _validar_ids(usuario_id, conversacion_id=None):
    """
    Valida el formato de los identificadores antes de consultar.
    """
    if not isinstance(usuario_id, str) or not PATRON_UUID.fullmatch(usuario_id):
        raise PermisoDenegado("Usuario no válido.")

    if conversacion_id is not None and (
        not isinstance(conversacion_id, str)
        or not PATRON_UUID.fullmatch(conversacion_id)
    ):
        raise PermisoDenegado("Conversación no válida.")


def titulo_desde_texto(texto):
    """
    Construye un título corto a partir de la primera pregunta.
    """
    titulo = " ".join(texto.split())
    return titulo if len(titulo) <= 80 else titulo[:77].rstrip() + "..."


def crear_conversacion(cliente, usuario_id, titulo):
    """
    Crea una conversación nueva del usuario. No borra las anteriores.
    """
    _validar_ids(usuario_id)

    titulo = titulo_desde_texto(titulo) or "Conversación"

    datos = (
        cliente.table("conversaciones")
        .insert({"usuario_id": usuario_id, "titulo": titulo})
        .execute()
        .data
    )

    if not datos or datos[0]["usuario_id"] != usuario_id:
        raise PermisoDenegado("No fue posible crear la conversación.")

    return datos[0]


def listar_conversaciones(cliente, usuario_id):
    """
    Lista las conversaciones del usuario, de la más reciente a la más antigua.
    """
    _validar_ids(usuario_id)

    return (
        cliente.table("conversaciones")
        .select("id,titulo,creada_en,actualizada_en")
        .eq("usuario_id", usuario_id)
        .order("actualizada_en", desc=True)
        .execute()
        .data
    )


def obtener_conversacion(cliente, usuario_id, conversacion_id):
    """
    Devuelve la conversación solo si pertenece al usuario.
    Conocer el UUID no concede acceso.
    """
    _validar_ids(usuario_id, conversacion_id)

    datos = (
        cliente.table("conversaciones")
        .select("id,usuario_id,titulo,creada_en,actualizada_en")
        .eq("id", conversacion_id)
        .eq("usuario_id", usuario_id)
        .limit(1)
        .execute()
        .data
    )

    if not datos or datos[0]["usuario_id"] != usuario_id:
        raise PermisoDenegado("La conversación no existe o no te pertenece.")

    return datos[0]


def cargar_mensajes(cliente, usuario_id, conversacion_id):
    """
    Carga los mensajes de una conversación del usuario en orden de creación.
    """
    obtener_conversacion(cliente, usuario_id, conversacion_id)

    return (
        cliente.table("mensajes")
        .select("id,rol,contenido,estado,citas,fuentes,traza,creado_en")
        .eq("conversacion_id", conversacion_id)
        .eq("usuario_id", usuario_id)
        .order("id")
        .execute()
        .data
    )


def guardar_turno(cliente, usuario_id, conversacion_id, texto, traza):
    """
    Guarda la pregunta del usuario y la respuesta del asistente con su
    estado, citas, fuentes citadas y traza. Actualiza la fecha de la
    conversación.
    """
    obtener_conversacion(cliente, usuario_id, conversacion_id)

    # Fuentes citadas en la respuesta (la traza conserva el catálogo completo)
    fuentes = {
        etiqueta: traza["fuentes"][etiqueta]
        for etiqueta in traza.get("citas", [])
        if etiqueta in traza.get("fuentes", {})
    }

    respuesta = traza.get("respuesta") or "Sin respuesta."

    # Las dos filas llevan las mismas columnas: en una inserción de varias
    # filas, las columnas que faltan se envían como NULL, no con su valor por defecto
    filas = [
        {
            "conversacion_id": conversacion_id,
            "usuario_id": usuario_id,
            "rol": "usuario",
            "contenido": texto[:MAX_CONTENIDO],
            "estado": None,
            "citas": [],
            "fuentes": {},
            "traza": None
        },
        {
            "conversacion_id": conversacion_id,
            "usuario_id": usuario_id,
            "rol": "asistente",
            "contenido": respuesta[:MAX_CONTENIDO],
            "estado": traza.get("estado"),
            "citas": traza.get("citas", []),
            "fuentes": fuentes,
            "traza": traza
        }
    ]

    # Una sola inserción mantiene el orden y evita turnos incompletos
    cliente.table("mensajes").insert(filas).execute()

    (
        cliente.table("conversaciones")
        .update({"actualizada_en": datetime.now(timezone.utc).isoformat()})
        .eq("id", conversacion_id)
        .eq("usuario_id", usuario_id)
        .execute()
    )


def historial_para_modelo(mensajes, max_turnos):
    """
    Convierte los mensajes guardados en la memoria que usa el agente:
    lista de {"usuario", "respuesta"} con los últimos max_turnos turnos
    completados. Todos los mensajes siguen guardados; solo se envían
    al modelo los pertinentes.
    """
    turnos = []
    pendiente = None

    for mensaje in mensajes:
        if mensaje["rol"] == "usuario":
            pendiente = mensaje["contenido"]

        elif pendiente is not None:
            if mensaje.get("estado") in ESTADOS_COMPLETADOS:
                turnos.append(
                    {
                        "usuario": pendiente,
                        "respuesta": mensaje["contenido"]
                    }
                )
            pendiente = None

    return turnos[-max_turnos:] if max_turnos > 0 else []
