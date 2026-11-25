"""
Persistencia del historial y separación entre usuarios.

Requiere dos cuentas de prueba de Supabase Auth en app/.env:
PRUEBA_USUARIO_A_EMAIL/PASSWORD y PRUEBA_USUARIO_B_EMAIL/PASSWORD.
Si faltan, las pruebas se omiten. Las conversaciones de prueba quedan
guardadas (no hay política de borrado) con el título "[prueba] ...".
"""

import math
import os

import pytest

import almacenamiento
import sistema

CREDENCIALES = {
    usuario: (
        os.environ.get(f"PRUEBA_USUARIO_{usuario}_EMAIL", "").strip(),
        os.environ.get(f"PRUEBA_USUARIO_{usuario}_PASSWORD", "")
    )
    for usuario in ("A", "B")
}

pytestmark = pytest.mark.skipif(
    not all(email and clave for email, clave in CREDENCIALES.values()),
    reason="Faltan las cuentas de prueba PRUEBA_USUARIO_A/B en app/.env."
)


def ingresar(usuario):
    """
    Inicia sesión y devuelve (cliente, sesion) con un cliente nuevo.
    """
    sesion = sistema.iniciar_sesion(*CREDENCIALES[usuario])
    return sistema.cliente_usuario(sesion)


def traza_de_prueba(texto):
    return {
        "estado": "RESPONDER",
        "respuesta": f"Respuesta de prueba a: {texto}",
        "citas": [],
        "fuentes": {},
        "eventos": [],
        "operaciones": 0
    }


@pytest.fixture(scope="module")
def datos_a():
    """
    El usuario A crea dos conversaciones y guarda un turno en cada una.
    """
    cliente, sesion = ingresar("A")
    usuario_id = sesion["usuario_id"]

    conversaciones = []
    for numero in (1, 2):
        conversacion = almacenamiento.crear_conversacion(
            cliente, usuario_id, f"[prueba] Conversación {numero}"
        )
        texto = f"Pregunta de prueba {numero} P-20210010001"
        almacenamiento.guardar_turno(
            cliente, usuario_id, conversacion["id"], texto, traza_de_prueba(texto)
        )
        conversaciones.append(conversacion["id"])

    return {"usuario_id": usuario_id, "conversaciones": conversaciones}


def test_a_recupera_sus_conversaciones_con_una_sesion_nueva(datos_a):
    # Cliente y sesión nuevos: equivale a cerrar sesión y volver a ingresar
    cliente, sesion = ingresar("A")
    ids = {c["id"] for c in almacenamiento.listar_conversaciones(cliente, sesion["usuario_id"])}
    assert set(datos_a["conversaciones"]) <= ids

    for conversacion_id in datos_a["conversaciones"]:
        mensajes = almacenamiento.cargar_mensajes(cliente, sesion["usuario_id"], conversacion_id)
        assert [m["rol"] for m in mensajes] == ["usuario", "asistente"]
        assert mensajes[0]["id"] < mensajes[1]["id"]
        assert mensajes[1]["estado"] == "RESPONDER"


def test_b_no_lista_ni_lee_el_historial_de_a(datos_a):
    cliente, sesion = ingresar("B")
    usuario_b = sesion["usuario_id"]
    assert usuario_b != datos_a["usuario_id"]

    ids = {c["id"] for c in almacenamiento.listar_conversaciones(cliente, usuario_b)}
    assert not ids & set(datos_a["conversaciones"])

    conversacion_a = datos_a["conversaciones"][0]

    # Mediante almacenamiento.py, conociendo el UUID
    with pytest.raises(almacenamiento.PermisoDenegado):
        almacenamiento.cargar_mensajes(cliente, usuario_b, conversacion_a)

    # Consultas directas que dependen solo de RLS
    assert cliente.table("conversaciones").select("id").eq("id", conversacion_a).execute().data == []
    assert cliente.table("mensajes").select("id").eq("conversacion_id", conversacion_a).execute().data == []


def test_b_no_escribe_en_el_historial_de_a(datos_a):
    cliente, sesion = ingresar("B")
    usuario_b = sesion["usuario_id"]
    conversacion_a = datos_a["conversaciones"][0]

    # Mediante almacenamiento.py
    with pytest.raises(almacenamiento.PermisoDenegado):
        almacenamiento.guardar_turno(
            cliente, usuario_b, conversacion_a, "Intrusión", traza_de_prueba("Intrusión")
        )

    # Inserciones directas: RLS debe rechazarlas, con su id o con el de A
    for usuario_id in (usuario_b, datos_a["usuario_id"]):
        with pytest.raises(Exception):
            cliente.table("mensajes").insert(
                {
                    "conversacion_id": conversacion_a,
                    "usuario_id": usuario_id,
                    "rol": "usuario",
                    "contenido": "Intrusión"
                }
            ).execute()

    # Actualización directa: no afecta ninguna fila
    actualizadas = (
        cliente.table("conversaciones")
        .update({"titulo": "Intrusión"})
        .eq("id", conversacion_a)
        .execute()
        .data
    )
    assert actualizadas == []

    # A sigue viendo solo sus mensajes originales
    cliente_a, sesion_a = ingresar("A")
    mensajes = almacenamiento.cargar_mensajes(cliente_a, sesion_a["usuario_id"], conversacion_a)
    assert len(mensajes) == 2 and all("Intrusión" not in m["contenido"] for m in mensajes)


def test_b_lee_el_corpus_compartido():
    cliente, _ = ingresar("B")
    sistema.leer_configuracion()

    fragmentos = (
        cliente.table("clase08_fragmentos")
        .select("chunk_id")
        .eq("corpus_id", sistema.CORPUS_ID)
        .limit(5)
        .execute()
        .data
    )
    assert fragmentos

    vector = [1 / math.sqrt(384)] * 384
    resultados = cliente.rpc(
        "buscar_fragmentos_compartidos",
        {
            "query_embedding": vector,
            "p_corpus_id": sistema.CORPUS_ID,
            "p_modelo": sistema.configuracion["modelo"],
            "p_revision": sistema.configuracion["revision"],
            "match_count": 3
        }
    ).execute().data
    assert len(resultados) == 3
