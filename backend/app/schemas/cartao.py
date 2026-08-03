"""
Schemas Pydantic do Cartao — a tarefa.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CartaoCriar(BaseModel):
    """`lista_id` vem da URL (POST /listas/{lista_id}/cartoes), não daqui.

    `prazo` e `aviso_previo_minutos` já existem no schema porque já existem
    no modelo (Etapa 2.5), mas nenhuma regra de negócio em torno deles
    (por exemplo, "não faz sentido ter aviso sem prazo") está implementada
    ainda — isso é conteúdo da Etapa 4. Por ora são só campos opcionais
    guardados como vieram."""

    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = None
    posicao: float
    prazo: datetime | None = None
    aviso_previo_minutos: int | None = Field(default=None, ge=0)


class CartaoAtualizar(BaseModel):
    """Edição de conteúdo do cartão. Note que `lista_id` propositalmente
    NÃO está aqui — mover um cartão de lista é uma operação com identidade
    própria (ver CartaoMover abaixo), não um campo a mais num PATCH
    genérico. Isso reflete a Etapa 2.3: mudar `lista_id` é mudar o estado
    do cartão, e vale a pena a rota deixar essa intenção explícita."""

    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descricao: str | None = None
    prazo: datetime | None = None
    aviso_previo_minutos: int | None = Field(default=None, ge=0)


class CartaoMover(BaseModel):
    """O schema da operação central do kanban (Etapa 2.3): "mover um
    cartão entre listas altera apenas lista_id". `nova_posicao` também é
    aceita porque mover quase sempre implica reordenar — o cartão não só
    troca de coluna, como cai numa posição específica dentro dela."""

    lista_id: int
    nova_posicao: float


class CartaoLeitura(BaseModel):
    id: int
    lista_id: int
    titulo: str
    descricao: str | None
    posicao: float
    prazo: datetime | None
    aviso_previo_minutos: int | None
    arquivado: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
