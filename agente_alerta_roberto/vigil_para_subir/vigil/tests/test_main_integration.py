"""Prueba de integración de main.run() con extractor/relevance/notifier simulados.

No llama a Groq ni a un servidor SMTP real — comprueba que la orquestación
(dedupe, manejo de errores por convocatoria, envío condicionado a que haya
relevantes) sigue lo descrito en las secciones 8 y 9 del build brief.
"""

import vigil.main as main
from vigil.schemas import Convocatoria, VeredictoRelevancia


def _convocatoria(id_expediente: str) -> dict:
    return {
        "diputacion": "Araba",
        "objeto": f"Objeto de {id_expediente}",
        "enlace_pliego": f"https://example.org/{id_expediente}",
        "id_expediente": id_expediente,
        "fecha_publicacion": "05/07/2026",
        "organo_convocante": "Diputación Foral de Álava",
        "importe": "10.000,00",
        "plazo_presentacion": "30/07/2026",
    }


def _fake_extraer(cruda: dict) -> Convocatoria:
    return Convocatoria(
        id_expediente=cruda["id_expediente"],
        diputacion=cruda["diputacion"],
        objeto=cruda["objeto"],
        organo_convocante=cruda["organo_convocante"],
        importe=cruda["importe"],
        plazo_presentacion=cruda["plazo_presentacion"],
        enlace_pliego=cruda["enlace_pliego"],
    )


def test_convocatoria_relevante_dispara_email_y_queda_marcada(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SQLITE_PATH", str(tmp_path / "vigil.db"))
    monkeypatch.setattr(
        main, "obtener_convocatorias", lambda: [_convocatoria("EXP-REL")]
    )
    monkeypatch.setattr(main, "extraer_convocatoria", _fake_extraer)
    monkeypatch.setattr(
        main,
        "evaluar_relevancia",
        lambda c: VeredictoRelevancia(relevante=True, motivo="Es un congreso institucional."),
    )
    enviados = []
    monkeypatch.setattr(
        main.notifier, "enviar_email", lambda relevantes: enviados.append(relevantes) or True
    )

    main.run()

    assert len(enviados) == 1
    assert len(enviados[0]) == 1
    assert enviados[0][0][0].id_expediente == "EXP-REL"


def test_convocatoria_no_relevante_no_dispara_email(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "SQLITE_PATH", str(tmp_path / "vigil.db"))
    monkeypatch.setattr(
        main, "obtener_convocatorias", lambda: [_convocatoria("EXP-NOREL")]
    )
    monkeypatch.setattr(main, "extraer_convocatoria", _fake_extraer)
    monkeypatch.setattr(
        main,
        "evaluar_relevancia",
        lambda c: VeredictoRelevancia(relevante=False, motivo="Es una obra pública."),
    )
    enviados = []
    monkeypatch.setattr(
        main.notifier, "enviar_email", lambda relevantes: enviados.append(relevantes) or True
    )

    main.run()

    assert enviados == []


def test_segunda_ejecucion_no_reprocesa_lo_ya_visto(tmp_path, monkeypatch):
    db_path = str(tmp_path / "vigil.db")
    monkeypatch.setattr(main, "SQLITE_PATH", db_path)
    monkeypatch.setattr(
        main, "obtener_convocatorias", lambda: [_convocatoria("EXP-DUP")]
    )
    monkeypatch.setattr(main, "extraer_convocatoria", _fake_extraer)
    llamadas_relevancia = []

    def evaluar(c):
        llamadas_relevancia.append(c.id_expediente)
        return VeredictoRelevancia(relevante=True, motivo="Encaja.")

    monkeypatch.setattr(main, "evaluar_relevancia", evaluar)
    monkeypatch.setattr(main.notifier, "enviar_email", lambda relevantes: True)

    main.run()
    main.run()

    assert llamadas_relevancia == ["EXP-DUP"]  # solo se evaluó una vez


def test_fallo_del_llm_no_marca_como_procesada(tmp_path, monkeypatch):
    db_path = str(tmp_path / "vigil.db")
    monkeypatch.setattr(main, "SQLITE_PATH", db_path)
    monkeypatch.setattr(
        main, "obtener_convocatorias", lambda: [_convocatoria("EXP-FALLO")]
    )

    intentos = []

    def extraer_que_falla(cruda):
        intentos.append(cruda["id_expediente"])
        raise RuntimeError("Groq no responde")

    monkeypatch.setattr(main, "extraer_convocatoria", extraer_que_falla)
    monkeypatch.setattr(main.notifier, "enviar_email", lambda relevantes: True)

    main.run()
    main.run()

    # Como falló extractor.py, dedupe.py no debe haberla marcado — se reintenta cada día.
    assert intentos == ["EXP-FALLO", "EXP-FALLO"]
