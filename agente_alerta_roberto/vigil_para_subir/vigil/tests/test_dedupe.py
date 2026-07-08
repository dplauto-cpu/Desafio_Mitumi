from vigil import dedupe


def test_marcar_y_detectar_procesado(tmp_path):
    db_path = str(tmp_path / "vigil_test.db")

    with dedupe.get_connection(db_path) as conn:
        assert dedupe.ya_procesado(conn, "EXP-1") is False
        dedupe.marcar_procesado(conn, "EXP-1", "https://example.org/exp-1")
        assert dedupe.ya_procesado(conn, "EXP-1") is True

    # Persiste entre conexiones (simula ejecuciones distintas del cron).
    with dedupe.get_connection(db_path) as conn:
        assert dedupe.ya_procesado(conn, "EXP-1") is True
        assert dedupe.ya_procesado(conn, "EXP-2") is False


def test_marcar_procesado_es_idempotente(tmp_path):
    db_path = str(tmp_path / "vigil_test.db")

    with dedupe.get_connection(db_path) as conn:
        dedupe.marcar_procesado(conn, "EXP-1", "https://example.org/exp-1")
        dedupe.marcar_procesado(conn, "EXP-1", "https://example.org/exp-1")  # no debe fallar
        cur = conn.execute("SELECT COUNT(*) FROM procesados WHERE id_expediente = ?", ("EXP-1",))
        assert cur.fetchone()[0] == 1
