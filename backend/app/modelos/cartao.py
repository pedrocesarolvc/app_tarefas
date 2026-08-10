"""
Modelo Cartao (card) — a tarefa em si, o nível mais baixo da hierarquia
(Etapa 2.2: "nada abaixo do cartão").

Carrega os quatro campos que fazem deste um kanban "com tempo", em vez de
um kanban comum (Etapa 4.2): `prazo` (quando vence), `aviso_previo`
(quanto tempo antes avisar), e mais dois que a Etapa 4.3 acrescenta --
`notificar_em` (o instante do disparo, já calculado) e `notificado` (a
flag de controle). A lógica de disparo em si -- o worker que lê
`notificar_em` -- só chega na Etapa 5; aqui os quatro campos já existem
com o significado e a regra de recálculo corretos (Etapa 4.3, ver
app/servicos/prazos.py), só falta alguém consumi-los periodicamente.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Interval, Numeric, String, Text
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

    # `aviso_previo`: quanto tempo antes do prazo a notificação deve
    # disparar (Etapa 4.2). `Interval` -- não um inteiro de minutos -- vira
    # INTERVAL nativo no PostgreSQL: representa duração de forma direta
    # ('1 day', '2 hours') e soma/subtrai de TIMESTAMPTZ sem conversão
    # manual. Continua opcional: um cartão pode ter prazo sem ter pedido
    # aviso nenhum -- nesse caso `notificar_em` simplesmente fica nulo (ver
    # calcular_notificar_em em app/servicos/prazos.py), não é um erro.
    aviso_previo: Mapped[timedelta | None] = mapped_column(Interval, nullable=True)

    # `notificar_em`: o instante em que o worker (Etapa 5) deveria disparar
    # a notificação -- `prazo - aviso_previo`, MATERIALIZADO nesta coluna
    # em vez de calculado a cada consulta (Etapa 4.3). A consulta do
    # worker vira uma comparação trivial e indexável
    # (`WHERE notificar_em <= now() AND notificado = false`) em vez de uma
    # expressão sobre duas colunas. O preço dessa decisão é a regra que seu
    # nome não deixa óbvia: toda vez que `prazo` ou `aviso_previo` mudam,
    # este campo precisa ser recalculado -- nunca escrito à mão numa rota,
    # sempre via app/servicos/prazos.py.
    notificar_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # `notificado`: já foi disparada a notificação deste cartão? Por que
    # ela mora aqui, e não só na cabeça do worker, é a outra metade da
    # regra da Etapa 4.3 -- a que costuma escapar: se a usuária adia o
    # prazo de um cartão JÁ notificado, ela espera ser avisada de novo na
    # nova data. Sem resetar esta flag para False sempre que `prazo` ou
    # `aviso_previo` mudam, o cartão nunca mais notificaria -- um bug
    # silencioso, porque nada quebra, o aviso só não chega.
    notificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Soft delete (Etapa 2.7): "excluir" um cartão na interface só marca
    # esta flag como True. Toda consulta "normal" (listar cartões de uma
    # lista, por exemplo) deve filtrar `arquivado == False` explicitamente
    # — ver app/rotas/cartoes.py.
    arquivado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    lista: Mapped["Lista"] = relationship(back_populates="cartoes")
