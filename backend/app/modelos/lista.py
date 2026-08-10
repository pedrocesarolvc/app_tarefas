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
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
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

    # POSIÇÃO — indexação fracionária (Etapa 3.6).
    # `Numeric` sem precisão/escala definidas vira um NUMERIC de precisão
    # arbitrária no PostgreSQL: o ponto médio entre dois vizinhos nunca
    # colapsa, por mais vezes que a usuária arraste um cartão para o mesmo
    # lugar (a armadilha de precisão da Etapa 3.4, que aconteceria com
    # `Float`/float64 depois de ~52 inserções no mesmo ponto). Ninguém
    # escreve neste campo diretamente com um número calculado à mão — todo
    # cálculo de posição passa por app/servicos/ordenacao.py.
    posicao: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

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

    # Os cartões desta lista, ordenados por `posicao` e, em caso de empate,
    # por `id` (Etapa 3.8: "nunca ordene só por posição"). Duas inserções
    # concorrentes no mesmo intervalo podem calcular o mesmo ponto médio —
    # não é corrupção, é ambiguidade, e o `id` a desfaz de forma
    # determinística e igual para todo mundo que consultar.
    cartoes: Mapped[list["Cartao"]] = relationship(
        back_populates="lista",
        cascade="all, delete-orphan",
        order_by="Cartao.posicao, Cartao.id",
    )
