"""
Modelo Usuario.

É a raiz de toda a árvore de propriedade do sistema (Usuário → Quadro →
Lista → Cartão, ver Etapa 2.2 da documentação). É através do `usuario_id`
em Quadro que a regra "um usuário não alcança quadro de outro" (Etapa 2.8)
é garantida — toda consulta de quadro no resto da aplicação passa por
esse campo.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TZDateTime

# Import só para o verificador de tipos (mypy/pyright) enxergar "Quadro" na
# anotação `Mapped[list["Quadro"]]" abaixo, sem criar um import circular em
# tempo de execução (quadro.py também importa coisas de volta, indiretamente,
# através de app/modelos/__init__.py).
if TYPE_CHECKING:
    from app.modelos.assinatura_push import AssinaturaPush
    from app.modelos.quadro import Quadro


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)

    # unique=True garante no próprio banco que dois usuários não podem
    # cadastrar o mesmo e-mail — a validação não fica só no lado da
    # aplicação, que poderia ser burlada por uma escrita concorrente.
    # index=True porque todo login busca o usuário por e-mail.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Nunca guardamos a senha em texto puro — só o hash (ver
    # app/auth/seguranca.py, que usa bcrypt). Mesmo sendo um app de uma
    # única usuária, não há razão para tratar uma senha com menos cuidado.
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        TZDateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Um usuário pode ter vários quadros ("Casa", "Faculdade", ver 2.2).
    # cascade="all, delete-orphan" significa: se o usuário for apagado, seus
    # quadros vão junto. Isso é diferente da regra de arquivar definida para
    # lista/cartão (Etapa 2.7) — apagar a conta de um usuário é uma operação
    # rara e deliberadamente destrutiva, não um "excluir" acidental do dia a
    # dia, então não precisa do mesmo cuidado de reversibilidade.
    quadros: Mapped[list["Quadro"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )

    # As assinaturas de Web Push do usuário (Etapa 5.6) — uma por
    # navegador/dispositivo. cascade igual ao de `quadros`: apagar o
    # usuário apaga as assinaturas dele, mesmo raciocínio de "operação
    # rara e deliberada" citado acima.
    assinaturas_push: Mapped[list["AssinaturaPush"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
