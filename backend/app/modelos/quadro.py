"""
Modelo Quadro (board) — o agrupamento maior, ex.: "Casa", "Faculdade"
(Etapa 2.2 e 2.9).
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.modelos.lista import Lista
    from app.modelos.usuario import Usuario


class Quadro(Base):
    __tablename__ = "quadro"

    id: Mapped[int] = mapped_column(primary_key=True)

    # A chave estrangeira que amarra o quadro ao dono dele. index=True
    # porque "listar meus quadros" (WHERE usuario_id = ?) é a consulta mais
    # comum sobre esta tabela.
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False, index=True)

    nome: Mapped[str] = mapped_column(String(120), nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="quadros")

    # As listas de um quadro, sempre na ordem visual definida por
    # `posicao` (Etapa 2.2: "listas também precisam de ordem"). Pedir essa
    # ordenação aqui, no relacionamento, evita que cada rota que lê listas
    # precise lembrar de adicionar `ORDER BY posicao` manualmente.
    #
    # cascade="all, delete-orphan": apagar um quadro apaga suas listas (e,
    # por sua vez, o cascade de Lista.cartoes apaga os cartões). Assim como
    # em Usuario, isso é intencional só para o caso raro de apagar o quadro
    # inteiro — o "excluir" do dia a dia sobre lista/cartão continua sendo
    # arquivar (Etapa 2.7), nunca este cascade.
    # Desempate por `id` além de `posicao` (Etapa 3.8) — ver o comentário
    # equivalente em Lista.cartoes, app/modelos/lista.py.
    listas: Mapped[list["Lista"]] = relationship(
        back_populates="quadro",
        cascade="all, delete-orphan",
        order_by="Lista.posicao, Lista.id",
    )
