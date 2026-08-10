"""
O laço do worker (Etapa 5.3): acorda, consulta, envia, dorme.

Roda como um processo separado da API (Etapa 5.2 — ver worker/__main__.py
e o serviço `worker` no docker-compose.yml). Compartilha os modelos e a
conexão com o banco (app/database.py, app/modelos/), mas nada mais:
nenhuma rota da API importa nada deste pacote, e este módulo não expõe
nada por HTTP.

Toda a lógica de negócio do envio mora aqui, não em worker/__main__.py —
`executar_ciclo` é a função que os testes chamam diretamente, sem precisar
de um laço `while True` rodando de verdade.
"""

from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.assinatura_push import AssinaturaPush
from app.modelos.cartao import Cartao
from app.modelos.lista import Lista
from app.modelos.quadro import Quadro
from worker.push import AssinaturaExpiradaError
from worker.push import enviar_notificacao as enviar_notificacao_padrao

# Etapa 5.3: "ignorar avisos atrasados além de um limite (digamos, 24
# horas), marcando-os como notificados sem enviar". Sem isso, um worker
# que ficou dias fora do ar dispararia, ao voltar, uma enxurrada de
# avisos vencidos de uma vez só — um lembrete de três dias atrás não
# ajuda ninguém.
LIMITE_DE_ATRASO = timedelta(hours=24)

# Etapa 5.3: a cada minuto é suficiente. Até 60s de atraso no aviso é
# irrelevante para prazos medidos em horas ou dias; rodar mais rápido só
# gastaria recurso. Usado por worker/__main__.py — vive aqui porque é uma
# constante do domínio (a frequência do laço), não um detalhe do processo.
INTERVALO_PADRAO_SEGUNDOS = 60


def _selecionar_cartoes_pendentes(sessao: Session, agora: datetime):
    """A consulta do worker (Etapa 5.3) — simples porque `notificar_em`
    já vem calculado desde a Etapa 4.3, em vez de uma conta entre colunas.

    `<= agora`, não uma janela de tempo: pega TUDO que já venceu, não só
    o que venceu neste ciclo. É essa escolha que torna o worker resistente
    a ficar fora do ar — uma janela ("entre agora-1min e agora") perderia
    esses avisos em silêncio se o worker não estivesse rodando bem nessa
    janela específica.

    Devolve pares (Cartao, usuario_id) — o `usuario_id` vem do JOIN
    Cartao → Lista → Quadro (o cartão não guarda quadro_id, Etapa 2.5), e
    é ele que diz para quem mandar a notificação.
    """
    consulta = (
        select(Cartao, Quadro.usuario_id)
        .join(Lista, Cartao.lista_id == Lista.id)
        .join(Quadro, Lista.quadro_id == Quadro.id)
        .where(
            Cartao.notificar_em.is_not(None),
            Cartao.notificar_em <= agora,
            Cartao.notificado.is_(False),
            Cartao.arquivado.is_(False),
        )
        .order_by(Cartao.notificar_em, Cartao.id)
    )
    return sessao.execute(consulta).all()


def _enviar_para_usuario(
    sessao: Session,
    usuario_id: int,
    titulo: str,
    corpo: str,
    enviar_notificacao: Callable[[AssinaturaPush, str, str], None],
) -> bool:
    """Envia para TODAS as assinaturas do usuário (Etapa 5.6: "notificar
    significa enviar para todas").

    Devolve True se pelo menos um envio teve sucesso, OU se o usuário não
    tem nenhuma assinatura — a ausência de assinatura não é uma falha a
    ser tentada de novo para sempre (Etapa 5.9: "não há assinatura → o
    app degrada para aviso in-app apenas"); é um estado aceito, sem nada
    pendente de reenvio.

    Assinaturas que respondem 404/410 são apagadas do banco na hora,
    independentemente do resultado das outras (Etapa 5.6/5.9) — isso não
    está no checklist 5.10 nomeando "sucesso" ou "falha", é limpeza que
    acontece nos dois casos.
    """
    assinaturas = list(
        sessao.scalars(select(AssinaturaPush).where(AssinaturaPush.usuario_id == usuario_id))
    )
    if not assinaturas:
        return True

    algum_envio_teve_sucesso = False
    for assinatura in assinaturas:
        try:
            enviar_notificacao(assinatura, titulo, corpo)
            algum_envio_teve_sucesso = True
        except AssinaturaExpiradaError:
            sessao.delete(assinatura)
        except Exception:
            # Falha temporária desta assinatura específica (rede, serviço
            # de push fora do ar — Etapa 5.9). Não interrompe o envio para
            # as outras assinaturas do mesmo usuário.
            pass

    return algum_envio_teve_sucesso


def _corpo_da_notificacao(cartao: Cartao) -> str:
    if cartao.prazo is None:
        return f"“{cartao.titulo}” está no prazo."
    return f"“{cartao.titulo}” vence em {cartao.prazo:%d/%m às %H:%M}."


def executar_ciclo(
    sessao: Session,
    enviar_notificacao: Callable[[AssinaturaPush, str, str], None] = enviar_notificacao_padrao,
    agora: datetime | None = None,
) -> int:
    """Um ciclo do laço: seleciona os cartões pendentes, tenta enviar,
    marca `notificado`. Devolve quantos cartões foram efetivamente
    notificados neste ciclo (não conta os marcados por atraso excessivo
    sem envio) — é o número que os testes usam para provar a idempotência
    (Etapa 5.10, o teste de assinatura da etapa: chamar duas vezes
    seguidas com o mesmo `agora` não deve notificar de novo).

    `agora` é injetável de propósito: os testes fixam um instante em vez
    de depender do relógio de verdade, o que tornaria os testes lentos
    (esperar minutos de verdade) ou frágeis (correr contra o tempo real).
    `enviar_notificacao` é injetável pelo mesmo motivo do lado do envio —
    o dublê da Etapa 5.10.
    """
    agora = agora or datetime.now(timezone.utc)
    notificados_neste_ciclo = 0

    for cartao, usuario_id in _selecionar_cartoes_pendentes(sessao, agora):
        if agora - cartao.notificar_em > LIMITE_DE_ATRASO:
            # Etapa 5.3: atrasado demais — marca como notificado SEM
            # enviar, para não disparar um aviso que já perdeu o sentido.
            cartao.notificado = True
            continue

        sucesso = _enviar_para_usuario(
            sessao,
            usuario_id,
            titulo=cartao.titulo,
            corpo=_corpo_da_notificacao(cartao),
            enviar_notificacao=enviar_notificacao,
        )
        if sucesso:
            # Etapa 5.4: marca DEPOIS do envio bem-sucedido — "pelo menos
            # uma vez", nunca "no máximo uma vez". Marcar antes e o envio
            # falhar perderia o aviso para sempre; isto aqui, na pior das
            # hipóteses, manda de novo no próximo ciclo.
            cartao.notificado = True
            notificados_neste_ciclo += 1
        # Se `sucesso` for False, `notificado` permanece False de
        # propósito — nenhuma linha a escrever aqui é a regra em si.

    sessao.commit()
    return notificados_neste_ciclo
