"""
Testes do worker (Etapa 5), cobrindo o checklist da 5.10.

O envio de verdade (pywebpush, rede, o serviço de push do Google) nunca
entra aqui — nos termos da própria Etapa 5.10, "você testa a lógica, não
a rede". `EnviadorFalso` substitui `enviar_notificacao`
(worker/push.py) por um dublê que só registra o que teria sido enviado,
e decide por endpoint se aquele envio "funciona" ou "falha", sem tocar
em HTTP nenhum.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.modelos.assinatura_push import AssinaturaPush
from app.modelos.cartao import Cartao
from tests.test_modelo_kanban import registrar_e_logar
from worker.agendador import LIMITE_DE_ATRASO, executar_ciclo
from worker.push import AssinaturaExpiradaError

AGORA = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


class EnviadorFalso:
    """Dublê de `enviar_notificacao`: registra cada tentativa de envio em
    `chamadas` (lista de endpoints) e decide o resultado por endpoint via
    `resultados` -- None (ou ausente) é sucesso; uma instância de exceção
    é levantada como se o envio tivesse falhado daquele jeito."""

    def __init__(self, resultados: dict[str, Exception] | None = None):
        self.resultados = resultados or {}
        self.chamadas: list[str] = []

    def __call__(self, assinatura: AssinaturaPush, titulo: str, corpo: str, url_destino: str) -> None:
        self.chamadas.append(assinatura.endpoint)
        resultado = self.resultados.get(assinatura.endpoint)
        if resultado is not None:
            raise resultado


def _criar_cartao(cliente, notificar_em: datetime, titulo: str = "Tarefa"):
    """Cria quadro/lista/cartão cujo `notificar_em` é exatamente o
    instante pedido -- usa `aviso_previo=0` para que `notificar_em` seja
    igual ao `prazo` (Etapa 4.3: notificar_em = prazo - aviso_previo)."""
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        json={"titulo": titulo, "prazo": notificar_em.isoformat(), "aviso_previo": 0},
    ).json()
    return quadro, lista, cartao


def _criar_assinatura(cliente, endpoint: str = "https://push.exemplo/1"):
    return cliente.post(
        "/assinaturas-push",
        json={"endpoint": endpoint, "chave_p256dh": "chave-p256dh", "chave_auth": "chave-auth"},
    ).json()


def _sem_evento_realtime(*args, **kwargs) -> None:
    """Dublê de `publicar_evento_realtime` (Etapa 6.5) que não faz nada.
    Sem ele, o padrão de `executar_ciclo` tentaria uma chamada HTTP de
    verdade para `configuracoes.url_api_interna` a cada notificação bem-
    sucedida -- lenta e sem propósito aqui, já que este arquivo testa o
    worker isolado; a ponte em si é testada em test_realtime.py."""


def _executar(sessao, **kwargs):
    """`executar_ciclo` com o dublê acima já pré-configurado, para não
    repetir `publicar_evento_realtime=_sem_evento_realtime` em cada
    chamada deste arquivo."""
    kwargs.setdefault("publicar_evento_realtime", _sem_evento_realtime)
    return executar_ciclo(sessao, **kwargs)


def test_worker_seleciona_pendentes_e_ignora_arquivado_sem_prazo_e_ja_notificado(
    cliente, sessao_bruta
):
    """Checklist 5.10, itens 1 e 2: seleciona só quem está vencido, não
    arquivado e ainda não notificado."""
    registrar_e_logar(cliente)
    _, _, pendente = _criar_cartao(cliente, AGORA - timedelta(minutes=5), "Pendente")
    quadro_arq, lista_arq, arquivado = _criar_cartao(cliente, AGORA - timedelta(minutes=5), "Arquivado")
    cliente.post(f"/quadros/{quadro_arq['id']}/listas/{lista_arq['id']}/cartoes/{arquivado['id']}/arquivar")
    _, _, futuro = _criar_cartao(cliente, AGORA + timedelta(hours=1), "No futuro")
    quadro = cliente.post("/quadros", json={"nome": "Sem prazo"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    sem_prazo = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes", json={"titulo": "Sem prazo"}
    ).json()

    _executar(sessao_bruta, enviar_notificacao=EnviadorFalso(), agora=AGORA)

    def notificado(cartao_id: int) -> bool:
        return sessao_bruta.get(Cartao, cartao_id).notificado

    assert notificado(pendente["id"]) is True
    assert notificado(arquivado["id"]) is False
    assert notificado(futuro["id"]) is False
    assert notificado(sem_prazo["id"]) is False


def test_envio_bem_sucedido_marca_notificado_true(cliente, sessao_bruta):
    """Checklist 5.10, item 3."""
    registrar_e_logar(cliente)
    _criar_assinatura(cliente)
    _, _, cartao = _criar_cartao(cliente, AGORA - timedelta(minutes=5))

    enviador = EnviadorFalso()
    quantidade = _executar(sessao_bruta, enviar_notificacao=enviador, agora=AGORA)

    assert quantidade == 1
    assert len(enviador.chamadas) == 1
    assert sessao_bruta.get(Cartao, cartao["id"]).notificado is True


def test_envio_com_falha_mantem_notificado_false(cliente, sessao_bruta):
    """Checklist 5.10, item 4 -- "o teste que prova a decisão da 5.4":
    marcar depois do envio, não antes, para nunca perder um aviso por
    causa de uma falha de envio."""
    registrar_e_logar(cliente)
    assinatura = _criar_assinatura(cliente)
    _, _, cartao = _criar_cartao(cliente, AGORA - timedelta(minutes=5))

    enviador = EnviadorFalso(resultados={assinatura["endpoint"]: ConnectionError("serviço de push fora do ar")})
    quantidade = _executar(sessao_bruta, enviar_notificacao=enviador, agora=AGORA)

    assert quantidade == 0
    assert sessao_bruta.get(Cartao, cartao["id"]).notificado is False


def test_cartao_com_varias_assinaturas_envia_para_todas(cliente, sessao_bruta):
    """Checklist 5.10, item 5."""
    registrar_e_logar(cliente)
    a = _criar_assinatura(cliente, "https://push.exemplo/a")
    b = _criar_assinatura(cliente, "https://push.exemplo/b")
    _, _, cartao = _criar_cartao(cliente, AGORA - timedelta(minutes=5))

    enviador = EnviadorFalso()
    _executar(sessao_bruta, enviar_notificacao=enviador, agora=AGORA)

    assert sorted(enviador.chamadas) == sorted([a["endpoint"], b["endpoint"]])
    assert sessao_bruta.get(Cartao, cartao["id"]).notificado is True


def test_assinatura_expirada_e_removida_do_banco(cliente, sessao_bruta):
    """Checklist 5.10, item 6."""
    registrar_e_logar(cliente)
    assinatura = _criar_assinatura(cliente)
    _criar_cartao(cliente, AGORA - timedelta(minutes=5))

    enviador = EnviadorFalso(resultados={assinatura["endpoint"]: AssinaturaExpiradaError("410")})
    _executar(sessao_bruta, enviar_notificacao=enviador, agora=AGORA)

    assert sessao_bruta.get(AssinaturaPush, assinatura["id"]) is None


def test_avisos_atrasados_alem_do_limite_sao_marcados_sem_enviar(cliente, sessao_bruta):
    """Checklist 5.10, item 7."""
    registrar_e_logar(cliente)
    _criar_assinatura(cliente)
    _, _, cartao_muito_atrasado = _criar_cartao(
        cliente, AGORA - LIMITE_DE_ATRASO - timedelta(hours=1), "Vencido há muito tempo"
    )

    enviador = EnviadorFalso()
    quantidade = _executar(sessao_bruta, enviar_notificacao=enviador, agora=AGORA)

    assert quantidade == 0  # marcado, mas não contado como "notificado de verdade"
    assert enviador.chamadas == []
    assert sessao_bruta.get(Cartao, cartao_muito_atrasado["id"]).notificado is True


def test_rodar_worker_duas_vezes_seguidas_nao_envia_duplicado(cliente, sessao_bruta):
    """Checklist 5.10, item 8 -- o teste de assinatura da etapa."""
    registrar_e_logar(cliente)
    _criar_assinatura(cliente)
    _criar_cartao(cliente, AGORA - timedelta(minutes=5))

    enviador = EnviadorFalso()
    primeira_rodada = _executar(sessao_bruta, enviar_notificacao=enviador, agora=AGORA)
    segunda_rodada = _executar(sessao_bruta, enviar_notificacao=enviador, agora=AGORA)

    assert primeira_rodada == 1
    assert segunda_rodada == 0
    assert len(enviador.chamadas) == 1
