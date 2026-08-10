"""
Schemas Pydantic da Lista (coluna do kanban).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ListaCriar(BaseModel):
    """`quadro_id` não aparece aqui: ele vem da URL da rota (ex.:
    POST /quadros/{quadro_id}/listas), não do corpo — o mesmo raciocínio de
    QuadroCriar sobre `usuario_id`.

    Não existe campo `posicao` aqui (diferente da Etapa 2): uma lista nova
    é sempre anexada ao final do quadro. A rota calcula essa posição
    chamando app/servicos/ordenacao.py — o cliente nunca envia um número
    calculado por conta própria (Etapa 3.6: o cálculo fica isolado num
    único lugar)."""

    nome: str = Field(min_length=1, max_length=120)


class ListaAtualizar(BaseModel):
    """Cobre a edição de conteúdo: renomear (`nome`) e arquivar
    (`arquivado` — ver Etapa 2.7). Reordenar as colunas NÃO é um campo
    aqui — é a operação própria `ListaMover` abaixo, porque mover exige
    saber os vizinhos de destino, não só um número."""

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    arquivado: bool | None = None


class ListaMover(BaseModel):
    """O que a rota de mover lista (Etapa 3.3) recebe: não uma posição
    numérica, mas os vizinhos entre os quais a lista deve cair depois do
    arrasto — exatamente como a usuária vê na tela ("essa lista foi solta
    entre a lista X e a lista Y"). A rota busca a `posicao` de cada
    vizinho e delega o cálculo a `calcular_posicao` (Etapa 3.6).

    Ambos são opcionais e cobrem os casos de borda da Etapa 3.7:
    - os dois `None`: não deveria acontecer com um quadro que já tem essa
      lista (ela mesma seria o único item) — mas se o quadro só tiver essa
      lista, o resultado é apenas "a mesma posição de sempre".
    - só `lista_posterior_id`: soltar no topo do quadro.
    - só `lista_anterior_id`: soltar no fim do quadro.
    - os dois: soltar entre duas listas — o caso comum de arrastar.
    """

    lista_anterior_id: int | None = None
    lista_posterior_id: int | None = None


class ListaLeitura(BaseModel):
    id: int
    quadro_id: int
    nome: str
    # Decimal, não float: é o mesmo tipo armazenado no banco (Etapa 3.6),
    # e evita reintroduzir na camada de API a perda de precisão que a
    # Etapa 3.4 tirou do armazenamento. O cliente nunca faz aritmética
    # sobre este valor (toda reordenação passa por ListaMover, com ids de
    # vizinhos) — ele existe na leitura só para inspeção/depuração.
    posicao: Decimal
    arquivado: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
