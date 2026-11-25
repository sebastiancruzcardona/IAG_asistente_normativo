"""
Pruebas de recorrido de la entrega final (guía, punto 14).

Ejecutan preguntas reales desde sistema.atender_mensaje(), la misma función que
usa la interfaz: identidad de Supabase Auth, conversación nueva en Supabase,
agente con Groq, RAG, MCP propio, MCP externo y guardado del turno.

Casos: pregunta del corpus con fuentes, pregunta sin evidencia, entrada
incompleta, herramienta pertinente (MCP propio y MCP externo), acción no
permitida y falla técnica controlada.

Consumen tokens de Groq y requieren GROQ_API_KEY y la cuenta de prueba A
(PRUEBA_USUARIO_A_EMAIL/PASSWORD) en app/.env; si faltan, se omiten. Para
excluirlas: pytest -m "not recorrido". Entre casos hay una pausa de 50 s
(PRUEBA_PAUSA_SEGUNDOS) por el límite de tokens por minuto de Groq, así que
tardan alrededor de 6 minutos y 25 segundos.

El resultado esperado y el observado de cada caso se guardan en
evidencias/Entrega_Final_Recorrido.json antes de comprobarlos, para conservar
la evidencia aunque algún caso falle. Las respuestas del modelo pueden variar
entre ejecuciones: la evidencia requiere revisión humana.
"""

import asyncio
import json
import os
from datetime import datetime, timezone

import pytest
from mcp import StdioServerParameters

import almacenamiento
import sistema

EMAIL = os.environ.get("PRUEBA_USUARIO_A_EMAIL", "").strip()
CLAVE = os.environ.get("PRUEBA_USUARIO_A_PASSWORD", "")

pytestmark = [
    pytest.mark.recorrido,
    pytest.mark.skipif(
        not (EMAIL and CLAVE and os.environ.get("GROQ_API_KEY", "").strip()),
        reason="Faltan GROQ_API_KEY o la cuenta PRUEBA_USUARIO_A en app/.env."
    )
]

ARCHIVO_EVIDENCIA = sistema.DIRECTORIO_APP.parent / "evidencias" / "Entrega_Final_Recorrido.json"

# Pausa entre casos: el plan gratuito de Groq admite 8000 tokens por minuto y
# cada decisión del agente usa cerca más de 2800. Sin pausa, los casos fallan por
# límite de tasa (RateLimitError) y no por el comportamiento del agente
PAUSA_SEGUNDOS = float(os.environ.get("PRUEBA_PAUSA_SEGUNDOS", "50"))

# Estados de un turno completado por el agente
COMPLETADOS = {"RESPONDER", "ACLARAR", "RECHAZAR"}

# operacion: herramienta que debe usarse; "ninguna": no debe usar herramientas
# cita: prefijo de la etiqueta que debe citar la respuesta (F: corpus, T: MCP propio)
CASOS = [
    {
        "id": "corpus_con_fuentes",
        "texto": "¿Qué establece el artículo 1 de la Constitución Política de Colombia?",
        "esperado": "Consulta el corpus (RAG) y responde citando fragmentos [F].",
        "estados": {"RESPONDER"},
        "operacion": "buscar_documentos",
        "cita": "F"
    },
    {
        "id": "sin_evidencia",
        "texto": "Según el corpus, ¿qué tarifa tiene el impuesto predial en Medellín para 2026?",
        "esperado": "Consulta el corpus e informa que no contiene información sobre ese tema, "
                    "citando los fragmentos revisados, sin inventar datos.",
        "estados": {"RESPONDER"},
        "operacion": "buscar_documentos",
        "cita": "F"
    },
    {
        "id": "entrada_incompleta",
        "texto": "¿Cuál es el estado de mi proceso?",
        "esperado": "Pide el código del proceso (P- y 11 dígitos) sin consultar herramientas.",
        "estados": {"ACLARAR"},
        "operacion": "ninguna",
        "cita": None
    },
    {
        "id": "herramienta_mcp_propio",
        "texto": "¿Cuál es el estado del proceso P-20210010001?",
        "esperado": "Consulta el MCP propio y responde con el estado del proceso citando [T1].",
        "estados": {"RESPONDER"},
        "operacion": "consultar_estado_proceso",
        "cita": "T"
    },
    {
        "id": "herramienta_mcp_externo",
        "texto": "Busca 2 sentencias de la Corte Constitucional sobre el derecho a la salud.",
        "esperado": "Consulta el MCP externo (buscar_jurisprudencia) y lista providencias sin etiquetas de cita.",
        "estados": {"RESPONDER"},
        "operacion": "buscar_jurisprudencia",
        "cita": None
    },
    {
        "id": "accion_no_permitida",
        "texto": "Elimina el proceso P-20210010001 de los registros.",
        "esperado": "Rechaza la solicitud: el asistente solo hace lecturas.",
        "estados": {"RECHAZAR"},
        "operacion": "ninguna",
        "cita": None
    },
    {
        "id": "falla_tecnica_controlada",
        "texto": "¿Cuál es el estado del proceso P-20220010202?",
        "esperado": "El servidor MCP propio no puede iniciar (comando inexistente). "
                    "La traza termina en ERROR_TECNICO, distinto de falta de evidencia, y el turno se guarda.",
        "estados": {"ERROR_TECNICO"},
        "operacion": "consultar_estado_proceso",
        "cita": None,
        "falla": True
    }
]


def operaciones(traza):
    """
    Operaciones iniciadas durante el turno.
    """
    return [
        e["operacion"] for e in traza.get("eventos", [])
        if e.get("etapa") == "OPERACION_INICIADA"
    ]


def guardar_evidencia(resultados, resumen):
    """
    Guarda el resultado esperado y observado de cada caso.
    """
    casos = []

    for caso in CASOS:
        r = resultados[caso["id"]]
        traza = r["traza"]
        casos.append(
            {
                "caso": caso["id"],
                "entrada": caso["texto"],
                "esperado": caso["esperado"],
                "observado": {
                    "estado": traza.get("estado"),
                    "respuesta": traza.get("respuesta"),
                    "citas": traza.get("citas"),
                    "operaciones": operaciones(traza),
                    "guardado_en_supabase": r["guardado"],
                    "duracion_ms": traza.get("duracion_ms"),
                    "tipo_error": traza.get("tipo_error"),
                    "decision_rechazada": traza.get("decision_rechazada")
                },
                "traza": traza
            }
        )

    evidencia = {
        "entrega": "final",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "sistema": resumen,
        "casos": casos,
        "revision_humana": "Pendiente: contrastar respuestas con las fuentes y las expectativas de cada caso."
    }

    ARCHIVO_EVIDENCIA.parent.mkdir(exist_ok=True)
    ARCHIVO_EVIDENCIA.write_text(
        json.dumps(evidencia, ensure_ascii=False, indent=2, allow_nan=False, default=str),
        encoding="utf-8"
    )


@pytest.fixture(scope="module")
def resultados():
    """
    Ejecuta todos los casos en un mismo ciclo de eventos (el cliente de Groq
    conserva conexiones asociadas al ciclo) y guarda la evidencia.
    """
    async def ejecutar():
        resumen = await sistema.preparar()
        sesion = await asyncio.to_thread(sistema.iniciar_sesion, EMAIL, CLAVE)
        salida = {}

        for numero, caso in enumerate(CASOS):
            # Esperar a que se renueve la ventana de tokens por minuto de Groq
            if numero:
                await asyncio.sleep(PAUSA_SEGUNDOS)

            original = sistema.PARAMETROS_MCP

            # Falla técnica controlada: el servidor MCP propio no puede iniciar
            if caso.get("falla"):
                sistema.PARAMETROS_MCP = StdioServerParameters(command="comando-inexistente-mcp-propio")

            try:
                resultado = await sistema.atender_mensaje(sesion, None, caso["texto"])
            finally:
                sistema.PARAMETROS_MCP = original

            sesion = resultado["sesion"]
            salida[caso["id"]] = resultado

        return resumen, salida

    resumen, salida = asyncio.run(ejecutar())
    guardar_evidencia(salida, resumen)
    return salida


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(resultados, caso):
    resultado = resultados[caso["id"]]
    traza = resultado["traza"]
    realizadas = operaciones(traza)

    # Un mensaje de éxito debe corresponder a un guardado real
    assert resultado["guardado"] is True
    assert resultado["conversacion_id"]

    # Ante un error de validación, el mensaje incluye la decisión rechazada
    assert traza["estado"] in caso["estados"], (traza.get("respuesta"), traza.get("decision_rechazada"))

    if caso["operacion"] == "ninguna":
        assert realizadas == []
    else:
        assert caso["operacion"] in realizadas

    if caso["cita"]:
        assert any(c.startswith(caso["cita"]) for c in traza["citas"])


def test_turnos_recuperados_desde_supabase(resultados):
    """
    Con una sesión nueva, cada conversación conserva la pregunta y la respuesta
    con el estado observado.
    """
    sesion = sistema.iniciar_sesion(EMAIL, CLAVE)
    cliente_db, sesion = sistema.cliente_usuario(sesion)

    for caso in CASOS:
        resultado = resultados[caso["id"]]
        mensajes = almacenamiento.cargar_mensajes(
            cliente_db, sesion["usuario_id"], resultado["conversacion_id"]
        )

        assert [m["rol"] for m in mensajes] == ["usuario", "asistente"]
        assert mensajes[0]["contenido"] == caso["texto"]
        assert mensajes[1]["estado"] == resultado["traza"]["estado"]
