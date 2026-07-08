"""Modelos Pydantic v2 usados a lo largo del pipeline."""

# importo las anotaciones de tipo modernas para poder escribir "str | None"
from __future__ import annotations

# traigo Literal (lista cerrada de valores) y Optional (algo que puede ser None)
from typing import Literal, Optional

# traigo la clase base de Pydantic y Field para describir cada campo
from pydantic import BaseModel, Field

# defino que una diputación solo puede ser una de estas tres palabras exactas
Diputacion = Literal["Araba", "Gipuzkoa", "Bizkaia"]


# creo el molde de una convocatoria ya limpia y estructurada
class Convocatoria(BaseModel):
    """Una convocatoria/licitación tal como se estructura tras pasar por extractor.py."""

    # guardo el código de expediente (el identificador único de la convocatoria)
    id_expediente: str
    # guardo a qué diputación pertenece (solo Araba, Gipuzkoa o Bizkaia)
    diputacion: Diputacion
    # guardo el objeto del contrato (qué se pide en el concurso)
    objeto: str
    # guardo quién convoca el concurso
    organo_convocante: str
    # guardo el importe; lo dejo en None si no consigo sacarlo del pliego
    importe: Optional[str] = Field(
        default=None, description="Null si el pliego no permite extraer un importe claro."
    )
    # guardo la fecha límite para presentarse; None si no la puedo sacar
    plazo_presentacion: Optional[str] = Field(
        default=None, description="Null si no se pudo extraer una fecha límite clara."
    )
    # guardo el enlace al pliego para poder abrirlo desde el email
    enlace_pliego: str
    # guardo la fecha de publicación si está disponible
    fecha_publicacion: Optional[str] = None


# creo el molde del veredicto que devuelve el filtro de relevancia
class VeredictoRelevancia(BaseModel):
    """Salida del filtro semántico de relevance.py."""

    # apunto si la convocatoria es relevante (True) o no (False)
    relevante: bool
    # explico con palabras por qué encaja o no encaja con Mitumi
    motivo: str = Field(
        description="Explicación concreta del encaje (o no encaje) con el perfil de Mitumi, "
        "no basta con 'es relevante'."
    )
    # guardo una lista de requisitos que no puedo confirmar contra el perfil de Mitumi
    campos_no_verificables: list[str] = Field(
        # si no hay ninguno, empiezo con una lista vacía
        default_factory=list,
        description="Requisitos del pliego que no se pueden confirmar ni descartar contra el "
        "perfil de Mitumi (p. ej. certificaciones, facturación mínima).",
    )
