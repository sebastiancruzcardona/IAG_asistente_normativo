"""
Construcción del corpus (corpus.py).

No consumen Groq ni escriben en Supabase. Las pruebas que leen el corpus
guardado requieren CORPUS_EMAIL/PASSWORD en app/.env; si faltan, se omiten.
La reproducción carga el modelo de embeddings con EMBEDDINGS_REVISION.
"""

import json
import os

import numpy as np
import pytest

import corpus
import sistema

EMAIL = os.environ.get("CORPUS_EMAIL", "").strip()
CLAVE = os.environ.get("CORPUS_PASSWORD", "")

requiere_cuenta = pytest.mark.skipif(
    not (EMAIL and CLAVE),
    reason="Faltan CORPUS_EMAIL o CORPUS_PASSWORD en app/.env."
)


@pytest.fixture(scope="module")
def cliente_db():
    sesion = sistema.iniciar_sesion(EMAIL, CLAVE)
    cliente, _ = sistema.cliente_usuario(sesion)
    return cliente


@pytest.fixture(scope="module")
def guardados(cliente_db):
    """
    Fragmentos del corpus configurado en app/.env, ordenados por chunk_id.
    """
    return (
        cliente_db.table("clase08_fragmentos")
        .select("chunk_id,content,metadata,configuracion,embedding")
        .eq("corpus_id", os.environ["CORPUS_ID"])
        .order("chunk_id").limit(501).execute().data
    )


@requiere_cuenta
def test_fragmentar_reproduce_el_corpus_guardado(cliente_db, guardados):
    if corpus.hay_cambios(cliente_db, os.environ["CORPUS_ID"]):
        pytest.skip("FUENTES cambió y aún no se sincroniza: arranca la app para generar la versión nueva.")

    corpus.cargar_modelo(os.environ["EMBEDDINGS_REVISION"])
    registros = corpus.fragmentar(corpus.ESTRATEGIA, corpus.leer_documentos())
    locales = {r["chunk_id"]: r for r in registros}

    assert len(registros) == len(guardados)
    assert set(locales) == {g["chunk_id"] for g in guardados}

    for g in guardados:
        local = locales[g["chunk_id"]]
        assert local["texto"] == g["content"]
        assert {k: v for k, v in local.items() if k not in ("texto", "chunk_id")} == g["metadata"]

    # Muestra de embeddings: el primero y el último fragmento
    for g in (guardados[0], guardados[-1]):
        vector = corpus.modelo.encode(g["content"], normalize_embeddings=True)
        assert float(vector @ np.array(json.loads(g["embedding"]))) >= 0.999


@requiere_cuenta
def test_corpus_actual_sin_cambios(cliente_db):
    if corpus.hay_cambios(cliente_db, os.environ["CORPUS_ID"]):
        pytest.skip("FUENTES cambió y aún no se sincroniza: arranca la app para generar la versión nueva.")


@requiere_cuenta
def test_texto_modificado_genera_cambios(cliente_db, monkeypatch):
    fuentes = dict(corpus.FUENTES)
    primero = next(iter(fuentes))
    fuentes[primero] += "\nTexto agregado.\n"
    monkeypatch.setattr(corpus, "FUENTES", fuentes)

    assert corpus.hay_cambios(cliente_db, os.environ["CORPUS_ID"]) is True


def test_sin_corpus_id_hay_cambios():
    assert corpus.hay_cambios(None, "") is True


def test_actualizar_env_conserva_las_demas_lineas(tmp_path, monkeypatch):
    ruta = tmp_path / ".env"
    ruta.write_text(
        "# Comentario\nGROQ_MODEL=modelo\nCORPUS_ID=anterior\n"
        "EMBEDDINGS_REVISION=" + "a" * 40 + "\nPORT=7860\n",
        encoding="utf-8"
    )
    monkeypatch.setenv("CORPUS_ID", "anterior")
    monkeypatch.setenv("EMBEDDINGS_REVISION", "a" * 40)

    corpus.actualizar_env(ruta, "asistente_normativo-0123456789ab", "b" * 40)

    assert ruta.read_text(encoding="utf-8") == (
        "# Comentario\nGROQ_MODEL=modelo\nCORPUS_ID=asistente_normativo-0123456789ab\n"
        "EMBEDDINGS_REVISION=" + "b" * 40 + "\nPORT=7860\n"
    )
    assert os.environ["CORPUS_ID"] == "asistente_normativo-0123456789ab"
