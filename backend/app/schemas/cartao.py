"""
Schemas Pydantic do Cartao — a tarefa.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CartaoCriar(BaseModel):
    """`lista_id` vem da URL (POST /listas/{lista_id}/cartoes), não daqui.

    Sem campo `posicao` (Etapa 3, igual a ListaCriar): um cartão novo é
    sempre anexado ao final da lista; a rota calcula a posição via
    app/servicos/ordenacao.py.

    `prazo` e `aviso_previo` são a dimensão tempo (Etapa 4.2) -- os dois
    opcionais, e de propósito: a maioria dos cartões não terá nenhum dos
    dois (Etapa 4.6), e criar cartão não deveria exigir preencher data.
    `notificar_em`/`notificado` não aparecem aqui -- são calculados pela
    rota via app/servicos/prazos.py, nunca recebidos do cliente."""

    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = None
    prazo: datetime | None = None
    aviso_previo: timedelta | None = None


class CartaoAtualizar(BaseModel):
    """Edição de conteúdo do cartão. Note que nem `lista_id` nem posição
    aparecem aqui — mover um cartão de lista (e para onde, dentro dela) é
    uma operação com identidade própria (ver CartaoMover abaixo), não um
    campo a mais num PATCH genérico. Isso reflete a Etapa 2.3: mudar
    `lista_id` é mudar o estado do cartão, e vale a pena a rota deixar
    essa intenção explícita.

    Mudar `prazo` ou `aviso_previo` por aqui recalcula `notificar_em` e
    reseta `notificado` (Etapa 4.3) -- ver app/servicos/prazos.py e a
    rota `atualizar_cartao` em app/rotas/cartoes.py, que é quem de fato
    aplica essa regra."""

    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    descricao: str | None = None
    prazo: datetime | None = None
    aviso_previo: timedelta | None = None


class CartaoMover(BaseModel):
    """O schema da operação central do kanban (Etapa 2.3 + Etapa 3.3):
    "mover um cartão entre listas altera apenas lista_id" — e a posição
    dentro da lista de destino é calculada a partir de vizinhos, nunca
    recebida como número pronto do cliente.

    `cartao_anterior_id` e `cartao_posterior_id` identificam os cartões
    que, na lista de DESTINO (`lista_id`), devem ficar imediatamente antes
    e depois do cartão movido — a rota busca a `posicao` de cada um e
    delega a `calcular_posicao` (Etapa 3.6). Os dois são opcionais, e
    cobrem os casos de borda da Etapa 3.7:

    - os dois `None`: a lista de destino está vazia, ou o cartão vai para
      o único espaço livre nela.
    - só `cartao_posterior_id`: soltar no topo da lista de destino.
    - só `cartao_anterior_id`: soltar no fim da lista de destino
      (o caso mais comum: mover um cartão "para a próxima coluna").
    - os dois: soltar entre dois cartões já existentes na lista de
      destino.
    """

    lista_id: int
    cartao_anterior_id: int | None = None
    cartao_posterior_id: int | None = None


class CartaoLeitura(BaseModel):
    id: int
    lista_id: int
    titulo: str
    descricao: str | None
    # Decimal, não float — mesmo raciocínio do ListaLeitura.posicao
    # (app/schemas/lista.py): é o tipo real armazenado (Etapa 3.6), e o
    # cliente nunca deveria fazer conta em cima dele.
    posicao: Decimal
    prazo: datetime | None
    aviso_previo: timedelta | None
    # `notificar_em` e `notificado` (Etapa 4.3) são só leitura -- ninguém
    # os envia, a API sempre os calcula (ver app/servicos/prazos.py).
    notificar_em: datetime | None
    notificado: bool
    arquivado: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
