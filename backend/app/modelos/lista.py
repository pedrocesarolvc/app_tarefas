"""
Modelo Lista (coluna do kanban) — ex.: "A fazer", "Fazendo", "Pronto".

É o modelo mais carregado de decisão de todos: em um kanban ortodoxo a
lista pareceria um detalhe, mas a Etapa 2.3 da documentação explica por que
ela é, na verdade, o coração do desenho — **o cartão não tem campo de
estado; o estado do cartão é em qual lista ele está.** Não existe aqui
nenhuma tabela ou enum de "estados possíveis": a usuária cria e nomeia as
listas que quiser, e isso sozinho define o fluxo de trabalho dela.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.modelos.cartao import Cartao
    from app.modelos.quadro import Quadro


class Lista(Base):
    __tablename__ = "lista"

    id: Mapped[int] = mapped_column(primary_key=True)

    quadro_id: Mapped[int] = mapped_column(ForeignKey("quadro.id"), nullable=False, index=True)

    nome: Mapped[str] = mapped_column(String(120), nullable=False)

    # POSIÇÃO — DECISÃO PROVISÓRIA.
    # A Etapa 2.5 da documentação é explícita: "o tipo de posicao fica em
    # aberto de propósito" — a definição final (número fracionário vs.
    # texto ordenável, e como lidar com a armadilha de precisão que a
    # indexação fracionária esconde) é o assunto inteiro da Etapa 3, que
    # ainda não foi escrita. `Float` aqui é só o suficiente para já não ser
    # inteiro consecutivo (o que a Etapa 1.5 já descartou) e permitir o
    # resto do CRUD ser construído e testado agora. Espere isto mudar de
    # tipo quando a Etapa 3 chegar — é uma decisão pendente, não uma final.
    posicao: Mapped[float] = mapped_column(Float, nullable=False)

    # A Etapa 2.5 (o diagrama de entidades) não lista `arquivado` para
    # Lista — só para Cartão. Mas a Etapa 2.7 ("Apagar, ou arquivar?") é
    # explícita: "Para listas: arquivar a lista arquiva os cartões dentro
    # dela". Não é possível arquivar uma lista sem ter, na própria lista,
    # alguma marca de que ela está arquivada — senão ela continuaria
    # aparecendo no quadro. Este campo preenche essa lacuna do diagrama
    # para tornar o comportamento descrito em 2.7 implementável.
    arquivado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    quadro: Mapped["Quadro"] = relationship(back_populates="listas")

    # Os cartões desta lista, sempre ordenados por `posicao` — mesma lógica
    # do relacionamento `Quadro.listas`.
    cartoes: Mapped[list["Cartao"]] = relationship(
        back_populates="lista",
        cascade="all, delete-orphan",
        order_by="Cartao.posicao",
    )
