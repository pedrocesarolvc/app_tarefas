"""
Regras da dimensão tempo do cartão (Etapa 4): o cálculo de `notificar_em`,
e a regra que o acompanha.

Por que isso é um serviço, e não lógica espalhada pelas rotas (Etapa 4.3):
"Isso mora na camada de serviço, junto com o resto das regras — não
espalhado por cada rota que edita cartão." Toda rota que grava `prazo` ou
`aviso_previo` (criar_cartao, atualizar_cartao, em app/rotas/cartoes.py)
passa por aqui — nenhuma delas recalcula `notificar_em` com as próprias
mãos.
"""

from datetime import datetime, timedelta

from app.modelos.cartao import Cartao

# Os únicos dois campos cuja mudança afeta quando notificar (Etapa 4.3).
# Editar título ou descrição, por exemplo, não deveria resetar
# `notificado` — só estes dois.
_CAMPOS_QUE_AFETAM_NOTIFICACAO = {"prazo", "aviso_previo"}


def calcular_notificar_em(prazo: datetime | None, aviso_previo: timedelta | None) -> datetime | None:
    """O instante em que a notificação deveria disparar: `prazo -
    aviso_previo` (Etapa 4.2/4.3). Sem os dois -- a maioria dos cartões
    não tem prazo (Etapa 4.6), e um cartão pode ter prazo sem ter pedido
    aviso algum -- não há o que calcular, e o resultado é `None`, um
    estado válido, não um erro."""
    if prazo is None or aviso_previo is None:
        return None
    return prazo - aviso_previo


def aplicar_edicao_de_cartao(cartao: Cartao, campos_alterados: dict) -> None:
    """Aplica `campos_alterados` (só os campos que o cliente de fato
    mandou -- tipicamente `CartaoAtualizar(...).model_dump(exclude_unset=True)`)
    num `Cartao` já carregado, e garante a regra da Etapa 4.3: se `prazo`
    ou `aviso_previo` estiverem entre os campos alterados, `notificar_em`
    é recalculado E `notificado` volta para `False` — mesmo que o cartão
    já tivesse sido notificado antes.

    É a metade da regra que costuma escapar: sem resetar a flag, adiar um
    cartão já notificado faz o aviso nunca mais chegar, e nada acusa
    erro — o bug fica silencioso até a usuária reclamar que não foi
    avisada.
    """
    for campo, valor in campos_alterados.items():
        setattr(cartao, campo, valor)

    if _CAMPOS_QUE_AFETAM_NOTIFICACAO & campos_alterados.keys():
        cartao.notificar_em = calcular_notificar_em(cartao.prazo, cartao.aviso_previo)
        cartao.notificado = False
