# Cómo ejecutar las pruebas

Desde la raíz del proyecto, activa el entorno virtual y entra a `app/`, donde está `pytest.ini`:

```powershell
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
cd app
```

```bash
# Linux o macOS
source .venv/bin/activate
cd app
```

Los comandos de `pytest` son iguales en todos los sistemas.

| Qué | Comando |
|---|---|
| Todas, sin la de recorrido (no consumen Groq) | `pytest -m "not recorrido"` |
| Todas, incluida la de recorrido | `pytest` |
| Solo controles (MCP, RRF y validaciones) | `pytest pruebas/test_controles.py` |
| Solo historial y RLS (cuentas A y B) | `pytest pruebas/test_almacenamiento_rls.py` |
| Solo construcción del corpus (cuenta del corpus) | `pytest pruebas/test_corpus.py` |
| Solo recorrido (Groq real, cerca de 6 min 30 s) | `pytest -m recorrido -v -s` |
| Una prueba por nombre | `pytest -k test_traza_conserva_decision_rechazada` |
| Un caso de recorrido | `pytest -m recorrido -k herramienta_mcp_propio -v -s` |

Opciones útiles:

- **`-v`:** muestra cada prueba con su resultado.
- **`-s`:** muestra la salida mientras corre.
- **`-x`:** se detiene en el primer fallo.

## Notas

- **Requisitos en `app/.env`:**
  - Recorrido: `GROQ_API_KEY` y la cuenta `PRUEBA_USUARIO_A_*`.
  - RLS: las cuentas `PRUEBA_USUARIO_A_*` y `PRUEBA_USUARIO_B_*`.
  - Corpus: `CORPUS_EMAIL` y `CORPUS_PASSWORD`.
  - Si faltan, esas pruebas se omiten.
- **Un caso de recorrido no se ejecuta solo:** las 7 preguntas se ejecutan juntas al inicio, en una misma preparación, y `-k` solo filtra qué resultado se comprueba. Por eso un caso consume lo mismo que todos.
- **Pausa entre preguntas:** es de 50 s, por el límite de tokens por minuto de Groq. Se puede cambiar al ejecutar:
  - Windows (PowerShell): `$env:PRUEBA_PAUSA_SEGUNDOS = "65"` y luego `pytest -m recorrido -v -s`.
  - Linux o macOS: `PRUEBA_PAUSA_SEGUNDOS=65 pytest -m recorrido -v -s`.
- **Evidencia:** la prueba de recorrido la guarda en `evidencias/Entrega_Final_Recorrido.json`, aunque algún caso falle.
