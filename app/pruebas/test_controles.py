"""
Comprobaciones locales (punto 8 del notebook, comprobar_controles()).

No consumen Groq. El MCP propio se ejecuta de verdad; del MCP externo se
verifica el catálogo y que las llamadas inválidas se rechacen antes de
contactar al servidor. La parte de MEMORIA se reemplaza por
historial_para_modelo(), que arma la memoria desde los mensajes guardados.
"""

import asyncio

import pytest

import almacenamiento
import sistema
from sistema import (
    Decision, Detencion, codigos_permitidos, controlar_operacion, fusionar_rrf,
    sentencias_en, sentencias_permitidas, validar_decision
)


@pytest.fixture(scope="session", autouse=True)
def mcp_preparado():
    """
    Prepara y descubre los dos servidores MCP una vez por sesión de pruebas.
    """
    asyncio.run(sistema.preparar_mcp())


# ---------- MCP propio: procesos ficticios ----------

def test_mcp_propio_catalogo():
    assert sistema.CATALOGO_MCP["nombre"] == "consultar_estado_proceso"


def test_mcp_propio_proceso_existente():
    existente = asyncio.run(sistema.consultar_por_mcp("P-20210010001"))
    assert existente["encontrado"] is True
    assert existente["registro"]["estado"] == "activo"


def test_mcp_propio_proceso_desconocido():
    # Formato válido pero no existe: no es un error técnico
    desconocido = asyncio.run(sistema.consultar_por_mcp("P-20240070977"))
    assert desconocido["encontrado"] is False and desconocido["registro"] is None


def test_mcp_propio_rechaza_codigo_invalido():
    async def llamar():
        async with sistema.conexion_mcp() as conexion:
            return await conexion.call_tool("consultar_estado_proceso", {"codigo_proceso": "1001"})

    assert asyncio.run(llamar()).is_error


# ---------- Códigos de proceso y sentencias permitidos ----------

def test_codigos_permitidos():
    assert codigos_permitidos("¿Y ese proceso?", []) == set()
    assert codigos_permitidos(
        "Ahora P-20220010202",
        [{"usuario": "Antes P-20210010001"}]
    ) == {"P-20220010202", "P-20210010001"}


def test_sentencias():
    assert sentencias_en("C-337 de 2011") == sentencias_en("c-337/11") == {("C", 337, 11)}
    assert sentencias_en("T-099/24") == sentencias_en("T-99/24")
    assert sentencias_permitidas(
        "¿Y esa sentencia?",
        [{"usuario": "Busca sobre vida", "respuesta": "Encontré la T-1059/06."}]
    ) == {("T", 1059, 6)}


# ---------- Memoria desde el historial guardado ----------

def _mensajes(turnos, estado="RESPONDER"):
    filas = []
    for numero in range(turnos):
        filas.append({"rol": "usuario", "contenido": f"Turno {numero}: P-20210010001"})
        filas.append({"rol": "asistente", "contenido": "Respuesta de prueba.", "estado": estado})
    return filas


def test_historial_conserva_ultimos_turnos():
    historial = almacenamiento.historial_para_modelo(_mensajes(6), sistema.MAX_TURNOS)
    assert len(historial) == sistema.MAX_TURNOS
    assert historial[0]["usuario"].startswith("Turno 2")


def test_historial_excluye_turnos_incompletos():
    mensajes = _mensajes(1) + _mensajes(1, estado="ERROR_TECNICO")
    historial = almacenamiento.historial_para_modelo(mensajes, sistema.MAX_TURNOS)
    assert len(historial) == 1


def test_conversacion_nueva_no_hereda_codigos():
    # Otra conversación (sin mensajes) no hereda los códigos de la primera
    vacio = almacenamiento.historial_para_modelo([], sistema.MAX_TURNOS)
    assert "P-20210010001" not in codigos_permitidos("¿Y ese proceso?", vacio)


# ---------- Control de operaciones ----------

def test_control_de_operaciones():
    visitadas = set()
    controlar_operacion("buscar_jurisprudencia", {"termino": "derecho a la vida", "limite": 3}, visitadas, 0)

    for nombre, argumentos, realizadas, motivo in [
        ("buscar_jurisprudencia", {"limite": 3, "termino": "derecho a la vida"}, 1, "REPETICION_SIN_AVANCE"),
        ("buscar_documentos", {"consulta": "requisitos"}, sistema.MAX_OPERACIONES, "LIMITE_OPERACIONES")
    ]:
        with pytest.raises(Detencion) as error:
            controlar_operacion(nombre, argumentos, visitadas, realizadas)
        assert str(error.value) == motivo


# ---------- RAG: fusión de rankings ----------

def test_fusion_rrf():
    fusion = fusionar_rrf(
        [{"chunk_id": x} for x in ["A", "B", "C"]],
        [{"chunk_id": x} for x in ["C", "A", "D"]]
    )
    assert [r["chunk_id"] for r in fusion] == ["A", "C", "B", "D"]


# ---------- Validación de decisiones ----------

def decision(**campos):
    base = {
        "accion": "responder", "consulta": "", "codigo_proceso": "",
        "termino": "", "sentencia": "", "limite": 0,
        "respuesta": "", "citas": []
    }
    return Decision(**{**base, **campos})


@pytest.mark.parametrize("propuesta, texto, historial, catalogo", [
    # Límite negativo
    (dict(accion="buscar_jurisprudencia", termino="vida", limite=-1), "Busca vida", [], {}),
    # Código no aportado y formato inválido
    (dict(accion="consultar_estado_proceso", codigo_proceso="P-20210010001"), "¿Cómo va mi proceso?", [], {}),
    (dict(accion="consultar_estado_proceso", codigo_proceso="P-123"), "Revisa P-123", [], {}),
    # Término de jurisprudencia de siete palabras o vacío
    (dict(accion="buscar_jurisprudencia", termino="uno dos tres cuatro cinco seis siete"), "Busca algo", [], {}),
    (dict(accion="buscar_jurisprudencia", termino="   "), "Busca algo", [], {}),
    # Sentencia sin formato o no aportada
    (dict(accion="linea_jurisprudencial", sentencia="337 de 2011"), "Línea de la 337 de 2011", [], {}),
    (dict(accion="linea_jurisprudencial", sentencia="C-337/11"), "Dame una línea jurisprudencial", [], {}),
    # Respuestas finales
    (dict(accion="rechazar", respuesta=""), "Hola", [], {}),
    (dict(accion="responder", respuesta="x" * 2501), "Hola", [], {}),
    # Citas con fuentes en el catálogo
    (dict(accion="responder", respuesta="Resultado."), "Consulta", [], {"F1": {}}),
    (dict(accion="responder", respuesta="Resultado [F1].", citas=[]), "Consulta", [], {"F1": {}}),
    (dict(accion="responder", respuesta="Resultado [F2].", citas=["F2"]), "Consulta", [], {"F1": {}}),
])
def test_decisiones_rechazadas(propuesta, texto, historial, catalogo):
    with pytest.raises(ValueError):
        validar_decision(decision(**propuesta), texto, historial, catalogo)


@pytest.mark.parametrize("propuesta, texto, historial, catalogo", [
    (dict(accion="consultar_estado_proceso", codigo_proceso="P-20210010001"), "Estado de P-20210010001", [], {}),
    (dict(accion="consultar_estado_proceso", codigo_proceso="P-20210010001"), "¿Y cómo va ahora?",
     [{"usuario": "Revisa P-20210010001", "respuesta": "Está activo."}], {}),
    (dict(accion="buscar_jurisprudencia", termino="derecho a la vida", limite=3),
     "Necesito 3 sentencias sobre el derecho a la vida", [], {}),
    (dict(accion="linea_jurisprudencial", sentencia="C-337/11", limite=3), "Línea de la C-337 de 2011", [], {}),
    (dict(accion="linea_jurisprudencial", sentencia="c-337/11"), "Línea de la C-337 de 2011", [], {}),
    (dict(accion="linea_jurisprudencial", sentencia="T-1059/06"), "Dame la línea de esa sentencia",
     [{"usuario": "Busca sobre vida", "respuesta": "Encontré la T-1059/06."}], {}),
    (dict(accion="responder", respuesta="Encontré la sentencia T-1059/06: https://example.org/t-1059-06"),
     "Busca sobre vida", [], {}),
    (dict(accion="responder", respuesta="Resultado [F1].", citas=["F1"]), "Consulta", [], {"F1": {}}),
])
def test_decisiones_aceptadas(propuesta, texto, historial, catalogo):
    validar_decision(decision(**propuesta), texto, historial, catalogo)


def test_sin_catalogo_se_limpian_etiquetas_inventadas():
    inventada = decision(accion="responder", respuesta="Resultado [F1].", citas=["F1"])
    validar_decision(inventada, "Hola", [], {})
    assert inventada.citas == [] and "[F1]" not in inventada.respuesta


def test_traza_conserva_decision_rechazada(monkeypatch):
    """
    Sin Groq: el modelo consulta el MCP propio y luego declara T1 sin escribir
    [T1]. La traza termina en ERROR_VALIDACION y conserva la decisión rechazada.
    """
    decisiones = iter([
        decision(accion="consultar_estado_proceso", codigo_proceso="P-20210010001"),
        decision(accion="responder", respuesta="El proceso está activo.", citas=["T1"])
    ])

    async def decidir_simulado(texto, historial, observaciones):
        return next(decisiones), None

    monkeypatch.setattr(sistema, "cliente", object())
    monkeypatch.setattr(sistema, "decidir", decidir_simulado)

    traza = asyncio.run(sistema.atender(
        "¿Cuál es el estado del proceso P-20210010001?",
        "00000000-0000-0000-0000-000000000000", [], None
    ))

    assert traza["estado"] == "ERROR_VALIDACION"
    assert traza["respuesta"].startswith("Las citas no coinciden")
    assert traza["decision_rechazada"]["citas"] == ["T1"]
    assert traza["decision_rechazada"]["respuesta"] == "El proceso está activo."


# ---------- MCP externo: jurisprudencia ----------

def test_mcp_externo_catalogo():
    catalogo = sistema.CATALOGO_MCP_EXTERNO
    assert set(catalogo) == sistema.HERRAMIENTAS_NORMATIVA

    esquema_busqueda = catalogo["buscar_jurisprudencia"]["entrada"]
    esquema_linea = catalogo["linea_jurisprudencial"]["entrada"]

    assert {"termino", "limite"} <= set(esquema_busqueda["properties"])
    assert {"sentencia", "limite"} <= set(esquema_linea["properties"])
    assert "termino" in esquema_busqueda.get("required", [])
    assert "sentencia" in esquema_linea.get("required", [])


@pytest.mark.parametrize("herramienta, argumentos", [
    ("buscar_jurisprudencia_suprema", {"termino": "vida"}),
    ("buscar_jurisprudencia", {"termino": "vida", "inventado": 1}),
    ("buscar_jurisprudencia", {"limite": 3}),
    ("linea_jurisprudencial", {"limite": 3}),
])
def test_mcp_externo_rechaza_llamadas_invalidas(herramienta, argumentos):
    with pytest.raises(ValueError):
        asyncio.run(sistema.consultar_por_mcp_externo(herramienta, argumentos))


def test_limites_mcp_externo():
    assert 0 < sistema.LIMITE_POR_DEFECTO_MCP_EXTERNO <= sistema.LIMITE_MAXIMO_MCP_EXTERNO
