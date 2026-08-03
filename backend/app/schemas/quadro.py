"""
Schemas Pydantic do Quadro (board).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuadroCriar(BaseModel):
    """Só o nome é pedido ao criar — `usuario_id` nunca vem do corpo da
    requisição, e sim do usuário autenticado (ver
    app/auth/dependencias.py). Se `usuario_id` fosse aceito aqui, qualquer
    pessoa logada poderia criar um quadro em nome de outra, só informando
    o id dela."""

    nome: str = Field(min_length=1, max_length=120)


class QuadroAtualizar(BaseModel):
    """Todos os campos são opcionais porque isto é um PATCH, não um PUT:
    o cliente manda só o que quer mudar (por exemplo, só renomear).
    Campos omitidos permanecem como estavam."""

    nome: str | None = Field(default=None, min_length=1, max_length=120)


class QuadroLeitura(BaseModel):
    id: int
    nome: str
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
