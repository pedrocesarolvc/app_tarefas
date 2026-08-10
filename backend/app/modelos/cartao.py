"""
Modelo Cartao (card) — a tarefa em si, o nível mais baixo da hierarquia
(Etapa 2.2: "nada abaixo do cartão").

Carrega os dois únicos campos que fazem deste um kanban "com tempo", em vez
de um kanban comum: `prazo` e `aviso_previo_minutos` (Etapa 1.3 e 2.5). A
lógica em torno deles — calendário, disparo de notificação — só chega na
Etapa 4 e 5; por enquanto eles são apenas colunas guardadas, sem
comportamento.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.modelos.lista import Lista


class Cartao(Base):
    __tablename__ = "cartao"

    id: Mapped[int] = mapped_column(primary_key=True)

    # A chave estrangeira para Lista é o que define o "estado" do cartão
    # (Etapa 2.3) — mover um cartão entre colunas é, no banco, só um
    # UPDATE neste campo. Note que, seguindo a decisão normalizada da
    # Etapa 2.5, o cartão NÃO guarda `quadro_id` diretamente: o quadro se
    # alcança indiretamente, via `cartao.lista.quadro_id`. Isso significa
    # que "todos os cartões deste quadro" exige um JOIN — aceito
    # deliberadamente por ora (ver 2.5, "o JOIN é irrelevante").
    lista_id: Mapped[int] = mapped_column(ForeignKey("lista.id"), nullable=False, index=True)

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)

    # Opcional: um cartão pode não ter descrição nenhuma, só um título.
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # POSIÇÃO — indexação fracionária (Etapa 3.6). Mesmo raciocínio de
    # app/modelos/lista.py: `Numeric` sem precisão/escala é um NUMERIC de
    # precisão arbitrária no PostgreSQL, que não colapsa como `Float`
    # colapsaria depois de muitas inserções no mesmo ponto (Etapa 3.4). O
    # valor sempre vem de app/servicos/ordenacao.py, nunca calculado à mão
    # numa rota.
    posicao: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

    # --- A dimensão tempo (Etapa 1.3 / 2.5) ---
    #
    # `prazo`: quando o cartão vence. TIMESTAMPTZ (DateTime com timezone),
    # não um DateTime "ingênuo" — um prazo sem fuso horário é ambíguo assim
    # que o app tiver mais de um fuso envolvido, e mesmo num app de uma
    # única usuária isso evita bugs de horário de verão. É opcional: a
    # Etapa 2.8 exige explicitamente que "um cartão sem prazo é válido", já
    # que a maioria dos cartões não vai ter data nenhuma.
    prazo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # `aviso_previo_minutos`: quanto tempo antes do prazo a notificação
    # deve disparar (Etapa 1.3, "aviso de prazo"; Etapa 2.5,
    # `aviso_previo`). A documentação ainda não fixou a unidade — o nome do
    # campo aqui já a declara (minutos) para não deixar ambíguo. Só faz
    # sentido em conjunto com `prazo`; um cartão sem prazo não tem o que
    # avisar. Essa regra (não pode ter aviso sem prazo) ainda não é
    # validada em código — a Etapa 4 é quem vai desenhar as regras em
    # volta desses dois campos; aqui eles são só armazenamento.
    aviso_previo_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Soft delete (Etapa 2.7): "excluir" um cartão na interface só marca
    # esta flag como True. Toda consulta "normal" (listar cartões de uma
    # lista, por exemplo) deve filtrar `arquivado == False` explicitamente
    # — ver app/rotas/cartoes.py.
    arquivado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    lista: Mapped["Lista"] = relationship(back_populates="cartoes")
