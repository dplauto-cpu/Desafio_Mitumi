from src.funciones import guardar_log


def registrar_memoria(nombre: str, datos: dict) -> None:
    """Memoria simple basada en JSONL para trazabilidad local."""
    guardar_log(nombre, datos)
