"""
Rota do calendário (Etapa 4.5).

Não é uma entidade nova -- é uma consulta com outro recorte: os mesmos
cartões que já existem nos quadros, filtrados por `prazo` em vez de
agrupados por lista. Por isso não há um roteador aninhado sob
`/quadros/{quadro_id}/...` aqui: o calendário atravessa quadros de
propósito (Etapa 4.5) -- a pergunta que ele responde, "o que eu tenho
hoje?", não respeita a divisão entre "Casa" e "Faculdade". Um filtro
opcional por `quadro_id` fica disponível para quem quiser recortar.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencias import obter_usuario_atual
from app.database import obter_sessao
from app.modelos.cartao import Cartao
from app.modelos.lista import Lista
from app.modelos.quadro import Quadro
from app.modelos.usuario import Usuario
from app.schemas.cartao import CartaoLeitura

roteador = APIRouter(prefix="/calendario", tags=["calendário"])


@roteador.get("", response_model=list[CartaoLeitura])
def listar_cartoes_no_periodo(
    de: datetime,
    ate: datetime,
    quadro_id: int | None = Query(
        default=None,
        description="Filtra por um único quadro. Por padrão, atravessa todos os quadros do usuário (Etapa 4.5).",
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    sessao: Session = Depends(obter_sessao),
):
    """Os cartões do usuário com `prazo` entre `de` e `ate`, dos quadros
    inteiros dele -- não só de um.

    O cartão não guarda `quadro_id` (Etapa 2.5, normalizado), então
    alcançar "de qual quadro é este cartão" exige o mesmo JOIN duplo que a
    Etapa 4.5 já antecipa: Cartao → Lista → Quadro. É o preço aceito
    daquela decisão de modelagem, cobrado aqui.
    """
    consulta = (
        select(Cartao)
        .join(Lista, Cartao.lista_id == Lista.id)
        .join(Quadro, Lista.quadro_id == Quadro.id)
        .where(
            Quadro.usuario_id == usuario_atual.id,
            # Etapa 2.7: cartão arquivado some das consultas normais: o
            # calendário não é diferente.
            Cartao.arquivado.is_(False),
            # A maioria dos cartões não tem prazo (Etapa 4.6) -- esta
            # cláusula deixa explícito que eles ficam de fora, embora a
            # comparação de intervalo abaixo já os excluísse sozinha (NULL
            # nunca satisfaz BETWEEN).
            Cartao.prazo.is_not(None),
            Cartao.prazo >= de,
            Cartao.prazo <= ate,
        )
        .order_by(Cartao.prazo, Cartao.id)
    )
    if quadro_id is not None:
        consulta = consulta.where(Quadro.id == quadro_id)
    return list(sessao.scalars(consulta))
