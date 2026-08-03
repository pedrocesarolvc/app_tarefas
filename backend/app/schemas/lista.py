"""
Schemas Pydantic da Lista (coluna do kanban).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ListaCriar(BaseModel):
    """`quadro_id` não aparece aqui: ele vem da URL da rota (ex.:
    POST /quadros/{quadro_id}/listas), não do corpo — o mesmo raciocínio de
    QuadroCriar sobre `usuario_id`.

    `posicao` é aceito do cliente por enquanto (o cálculo automático de
    "entre qual e qual cartão/lista este vai" é o assunto da Etapa 3,
    ainda não implementado). Até lá, quem decide o valor numérico é quem
    chama a API."""

    nome: str = Field(min_length=1, max_length=120)
    posicao: float


class ListaAtualizar(BaseModel):
    """Cobre três operações que, na interface, parecem distintas mas no
    banco são todas um UPDATE em Lista: renomear (`nome`), reordenar as
    colunas (`posicao`) e arquivar (`arquivado` — ver Etapa 2.7)."""

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    posicao: float | None = None
    arquivado: bool | None = None


class ListaLeitura(BaseModel):
    id: int
    quadro_id: int
    nome: str
    posicao: float
    arquivado: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
