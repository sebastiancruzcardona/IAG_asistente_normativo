"""
Servidor MCP propio: consulta del estado de procesos judiciales ficticios.

Código tomado del punto 4 del notebook asistente_normativo_RAG_agente_MCP.ipynb
(variable SERVIDOR_MCP). sistema.py lo ejecuta como subproceso mediante stdio.
"""

# Importar Literal para restringir campos a Enums
from typing import Literal

# Importar la clase que permite crear el servidor MCP
from mcp.server import MCPServer

# Pydantic para validar argumentos y resultados de la herramienta
from pydantic import BaseModel, ConfigDict, Field

# Instanciar el servidor
mcp = MCPServer("Consulta de procesos judiciales")

# Valores permitidos para los campos del registro.
EstadoProceso = Literal[
    "activo",
    "suspendido",
    "terminado"
]

DecisionProceso = Literal[
    "sin_sentencia",
    "sentencia_proferida",
    "sentencia_ejecutoriada"
]

TerminacionProceso = Literal[
    "sentencia",
    "transaccion",
    "desistimiento",
    "desistimiento_tacito",
    "otra",
    "no_terminado"
]

# Registros ficticios basados en los definidos en el prototipo de la Clase 04.
# Sigue siendo base de datos ficticia en memoria
PROCESOS = {
    "P-20210010001": {
        "categoria": "laboral",
        "estado": "activo",
        "decision": "sin_sentencia",
        "terminacion": "no_terminado",
        "detalle": "El proceso se encuentra en trámite y está pendiente de la práctica de pruebas solicitadas por las partes."
    },
    "P-20220010202": {
        "categoria": "civil",
        "estado": "suspendido",
        "decision": "sin_sentencia",
        "terminacion": "no_terminado",
        "detalle": "El proceso se encuentra suspendido temporalmente por disposición judicial y no se han adelantado nuevas actuaciones mientras permanezca vigente la suspensión."
    },
    "P-20190001210": {
        "categoria": "seguridad_social",
        "estado": "terminado",
        "decision": "sentencia_ejecutoriada",
        "terminacion": "sentencia",
        "detalle": "El proceso terminó mediante sentencia que resolvió las pretensiones de las partes. La decisión se encuentra ejecutoriada."
    },
    "P-20230010405": {
        "categoria": "penal",
        "estado": "activo",
        "decision": "sin_sentencia",
        "terminacion": "no_terminado",
        "detalle": "El proceso se encuentra en etapa de investigación y está pendiente de la práctica de diligencias para esclarecer los hechos."
    },
    "P-20200020306": {
        "categoria": "familia",
        "estado": "terminado",
        "decision": "sentencia_ejecutoriada",
        "terminacion": "sentencia",
        "detalle": "El proceso finalizó mediante sentencia ejecutoriada que resolvió el conflicto relacionado con las obligaciones familiares de las partes."
    },
    "P-20240030507": {
        "categoria": "administrativo",
        "estado": "activo",
        "decision": "sin_sentencia",
        "terminacion": "no_terminado",
        "detalle": "El proceso se encuentra en curso y está pendiente de la respuesta de la entidad demandada frente a las pretensiones presentadas."
    },
    "P-20210040608": {
        "categoria": "civil",
        "estado": "terminado",
        "decision": "sin_sentencia",
        "terminacion": "transaccion",
        "detalle": "El proceso terminó mediante una transacción entre las partes, quienes alcanzaron un acuerdo para resolver el conflicto sin necesidad de una sentencia."
    },
    "P-20220050709": {
        "categoria": "laboral",
        "estado": "suspendido",
        "decision": "sin_sentencia",
        "terminacion": "no_terminado",
        "detalle": "El proceso permanece suspendido mientras se resuelve una cuestión previa necesaria para continuar con el trámite judicial."
    },
    "P-20230060810": {
        "categoria": "seguridad_social",
        "estado": "activo",
        "decision": "sentencia_proferida",
        "terminacion": "no_terminado",
        "detalle": "El proceso cuenta con una sentencia proferida por la autoridad judicial, pero la decisión aún no se encuentra ejecutoriada."
    },
    "P-20240070911": {
        "categoria": "penal",
        "estado": "terminado",
        "decision": "sin_sentencia",
        "terminacion": "otra",
        "detalle": "El proceso terminó por una causal legal distinta de la sentencia, la transacción o el desistimiento."
    }
}

class ArgumentosProceso(BaseModel):
    """
    Define esquema estricto de los argumentos de entrada a la herramienta.
    No puede haber campos extra, solo codigo_proceso, que es un string con el
    formato P- seguido de 11 dígitos.
    """
    model_config = ConfigDict(extra="forbid", strict=True)
    codigo_proceso: str = Field(pattern=r"^P-[0-9]{11}$")

class RegistroProceso(BaseModel):
    """
    Define la estructura de datos de un proceso.
    """
    categoria: str
    estado: EstadoProceso
    decision: DecisionProceso
    terminacion: TerminacionProceso
    detalle: str

class ResultadoEstadoProceso(BaseModel):
    """
    Define cómo debe ser la respuesta. El proceso puede o no existir.
    """
    codigo_proceso: str
    encontrado: bool
    registro: RegistroProceso | None
    fuente: str

# Definición de la herramienta
@mcp.tool()
def consultar_estado_proceso(codigo_proceso: str) -> ResultadoEstadoProceso:
    """
    Consulta el estado de un proceso ficticio mediante
    un código P- seguido de 11 dígitos.
    """
    # Validar el argumento recibido con Pydantic y la clase ArgumentosProceso
    codigo = ArgumentosProceso(codigo_proceso=codigo_proceso).codigo_proceso

    # Buscar el código en el diccionario de procesos ficticios. Si no existe
    # el valor es None
    registro = PROCESOS.get(codigo)

    # Retornar con la estructura definida con la clase ResultadoEstadoProceso
    return ResultadoEstadoProceso(
        codigo_proceso=codigo,
        encontrado=registro is not None,
        registro=registro,
        fuente="procesos_ficticios_clase11"
    )

# Iniciar el servidor MCP
if __name__ == "__main__":
    mcp.run(transport="stdio")
