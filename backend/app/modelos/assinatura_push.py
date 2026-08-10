"""
Modelo AssinaturaPush (Etapa 5.6) — o que o backend guarda para poder
mandar uma notificação a um navegador específico, mesmo com o app
fechado.

Não é a notificação em si, nem o texto dela: é só o "endereço" de um
navegador/dispositivo dentro do Web Push — a URL única gerada pelo
serviço de push (Google, no Chrome) mais as duas chaves de criptografia
que o navegador também gerou. O worker (backend/worker/push.py) é quem
usa isso para de fato enviar.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TZDateTime

if TYPE_CHECKING:
    from app.modelos.usuario import Usuario


class AssinaturaPush(Base):
    __tablename__ = "assinatura_push"

    id: Mapped[int] = mapped_column(primary_key=True)

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False, index=True)

    # A URL do serviço de push (Etapa 5.5) — pertence ao Google (ou outro
    # fornecedor), nunca ao nosso servidor. `Text`, não `String`, porque
    # essas URLs costumam passar de 200 caracteres. `unique=True`: a
    # mesma assinatura (o mesmo navegador) não deveria ter duas linhas —
    # ver o comentário sobre "transferência de dono" na rota de criação,
    # em app/rotas/assinaturas_push.py.
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    # As duas chaves que o navegador gerou junto com o endpoint, usadas
    # para criptografar a mensagem antes de enviar (Etapa 5.5). O worker
    # só as repassa para pywebpush — nada aqui as interpreta.
    chave_p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    chave_auth: Mapped[str] = mapped_column(String(255), nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(timezone.utc)
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="assinaturas_push")
