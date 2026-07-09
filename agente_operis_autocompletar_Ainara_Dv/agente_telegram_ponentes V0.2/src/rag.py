from config.settings import RAG_ENABLED, RAG_RESULTS
from config.fuentes import RAG_PATH


def consultar_rag(texto: str) -> list[dict]:
    """RAG mínimo local.

    En esta versión devuelve fragmentos de documentos .md/.txt si RAG_ENABLED=True.
    No sustituye a los datos del backend/BD.
    """
    if not RAG_ENABLED:
        return []

    resultados = []
    docs_dir = RAG_PATH / "documentos"
    if not docs_dir.exists():
        return []

    texto_lower = (texto or "").lower()
    for ruta in list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt")):
        contenido = ruta.read_text(encoding="utf-8")
        if not texto_lower or any(p in contenido.lower() for p in texto_lower.split()[:5]):
            resultados.append({"fuente": str(ruta.name), "contenido": contenido[:1000]})
        if len(resultados) >= RAG_RESULTS:
            break
    return resultados
