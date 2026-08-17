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
from app.schemas.cartao import CartaoLeitura
from worker.push import AssinaturaExpiradaError
from worker.push import enviar_notificacao as enviar_notificacao_padrao
from worker.tempo_real import publicar_evento_de_notificacao as publicar_evento_de_notificacao_padrao

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

    Devolve triplas (Cartao, quadro_id, usuario_id) — as duas vêm do JOIN
    Cartao → Lista → Quadro (o cartão não guarda quadro_id, Etapa 2.5):
    `usuario_id` diz para quem mandar o Web Push (Etapa 5.6);
    `quadro_id` diz em qual sala publicar o aviso in-app (Etapa 6.5).
    """
    consulta = (
        select(Cartao, Quadro.id, Quadro.usuario_id)
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
    url_destino: str,
    enviar_notificacao: Callable[[AssinaturaPush, str, str, str], None],
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
            enviar_notificacao(assinatura, titulo, corpo, url_destino)
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


def _url_do_cartao(quadro_id: int, cartao_id: int) -> str:
    """A URL que o clique na notificação deve abrir (Etapa 5.7: "abrir o
    app já no cartão certo, não na tela inicial"). O frontend ainda não
    tem rotas de verdade (é uma página só, ver frontend/src/App.tsx) --
    por isso um caminho com query string simples, que `QuadroKanban.tsx`
    lê ao carregar para selecionar o quadro certo, em vez de um esquema de
    rotas completo que este projeto não precisa ainda."""
    return f"/?quadro={quadro_id}&cartao={cartao_id}"


def executar_ciclo(
    sessao: Session,
    enviar_notificacao: Callable[[AssinaturaPush, str, str, str], None] = enviar_notificacao_padrao,
    publicar_evento_realtime: Callable[[int, dict], None] = publicar_evento_de_notificacao_padrao,
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
    `enviar_notificacao` e `publicar_evento_realtime` são injetáveis pelo
    mesmo motivo do lado do envio — os dublês da Etapa 5.10, agora dois
    canais em vez de um.
    """
    agora = agora or datetime.now(timezone.utc)
    notificados_neste_ciclo = 0

    for cartao, quadro_id, usuario_id in _selecionar_cartoes_pendentes(sessao, agora):
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
            url_destino=_url_do_cartao(quadro_id, cartao.id),
            enviar_notificacao=enviar_notificacao,
        )
        if sucesso:
            # Etapa 5.4: marca DEPOIS do envio bem-sucedido — "pelo menos
            # uma vez", nunca "no máximo uma vez". Marcar antes e o envio
            # falhar perderia o aviso para sempre; isto aqui, na pior das
            # hipóteses, manda de novo no próximo ciclo.
            cartao.notificado = True
            notificados_neste_ciclo += 1
            # Etapa 5.8/6.5: "o worker também emite nesse canal" -- só
            # quando o cartão foi de fato notificado (nunca no ramo do
            # atraso excessivo acima, que nem tenta enviar nada).
            publicar_evento_realtime(quadro_id, CartaoLeitura.model_validate(cartao).model_dump(mode="json"))
        # Se `sucesso` for False, `notificado` permanece False de
        # propósito — nenhuma linha a escrever aqui é a regra em si.

    sessao.commit()
    return notificados_neste_ciclo
