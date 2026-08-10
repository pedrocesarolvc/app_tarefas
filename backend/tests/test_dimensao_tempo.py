"""
Testes da Etapa 4 (a dimensão tempo).

O checklist completo da Etapa 4.8 tem nove itens; aqui só os de maior
valor — os que, se quebrassem, quebrariam de um jeito que não dá erro
nenhum (a regra do notificar_em/notificado) ou que exercitam a única
decisão de produto nova desta etapa (o calendário atravessar quadros).
Simetrias óbvias do mesmo mecanismo (por exemplo, "alterar só o aviso
prévio também recalcula" — mesmo caminho de código de "alterar o prazo
recalcula") e testes de fidelidade de framework (round-trip de TIMESTAMPTZ)
ficam de fora de propósito.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from tests.test_modelo_kanban import registrar_e_logar


def test_criar_cartao_sem_prazo_e_valido_e_notificar_em_fica_nulo(cliente: TestClient):
    """Etapa 4.8, item 1. A maioria dos cartões não terá prazo (Etapa
    4.6) — isso precisa continuar funcionando exatamente como antes da
    Etapa 4."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()

    cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        json={"titulo": "Lista de compras"},
    ).json()
    assert cartao["prazo"] is None
    assert cartao["notificar_em"] is None
    assert cartao["notificado"] is False


def test_definir_prazo_e_aviso_previo_calcula_notificar_em(cliente: TestClient):
    """Etapa 4.8, item 2: notificar_em = prazo - aviso_previo (Etapa
    4.3)."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()

    prazo = datetime(2026, 3, 10, 18, 0, tzinfo=timezone.utc)
    cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        json={"titulo": "Pagar boleto", "prazo": prazo.isoformat(), "aviso_previo": 3600},
    ).json()

    assert datetime.fromisoformat(cartao["notificar_em"]) == prazo - timedelta(hours=1)


def test_alterar_prazo_recalcula_notificar_em_e_reseta_notificado(cliente: TestClient, sessao_bruta):
    """Etapa 4.8, item 3 — o teste mais valioso da etapa (4.8): "o teste
    que fecha o bug silencioso da 4.3". Se a usuária adia o prazo de um
    cartão que já foi notificado, ela espera ser avisada de novo. Sem
    resetar `notificado`, o aviso nunca mais chegaria — e nada acusaria
    erro."""
    from app.modelos.cartao import Cartao

    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()

    prazo_original = datetime(2026, 3, 10, 18, 0, tzinfo=timezone.utc)
    cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        json={"titulo": "Entregar relatório", "prazo": prazo_original.isoformat(), "aviso_previo": 3600},
    ).json()

    # Simula o worker (Etapa 5, ver backend/worker/) já tendo notificado --
    # nenhuma rota da API grava `notificado=True` diretamente (só o
    # worker faz isso, depois de um envio bem-sucedido), então o teste
    # manipula o banco direto para chegar nesse estado.
    cartao_no_banco = sessao_bruta.get(Cartao, cartao["id"])
    cartao_no_banco.notificado = True
    sessao_bruta.commit()

    novo_prazo = prazo_original + timedelta(days=2)
    resposta = cliente.patch(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes/{cartao['id']}",
        json={"prazo": novo_prazo.isoformat()},
    )
    assert resposta.status_code == 200
    cartao_atualizado = resposta.json()

    assert cartao_atualizado["notificado"] is False
    assert datetime.fromisoformat(cartao_atualizado["notificar_em"]) == novo_prazo - timedelta(hours=1)


def test_calendario_filtra_periodo_atravessa_quadros_e_ignora_arquivados(cliente: TestClient):
    """Etapa 4.8, itens 6, 7 e 8, num único teste: o calendário devolve só
    cartões com prazo dentro do intervalo pedido, atravessa quadros do
    mesmo usuário (Etapa 4.5 — a decisão de produto nova desta etapa), e
    ignora cartões arquivados (Etapa 2.7)."""
    registrar_e_logar(cliente)
    quadro_casa = cliente.post("/quadros", json={"nome": "Casa"}).json()
    quadro_faculdade = cliente.post("/quadros", json={"nome": "Faculdade"}).json()
    lista_casa = cliente.post(f"/quadros/{quadro_casa['id']}/listas", json={"nome": "A fazer"}).json()
    lista_faculdade = cliente.post(
        f"/quadros/{quadro_faculdade['id']}/listas", json={"nome": "A fazer"}
    ).json()

    def criar_cartao(lista, titulo, prazo=None):
        corpo = {"titulo": titulo}
        if prazo is not None:
            corpo["prazo"] = prazo.isoformat()
        return cliente.post(f"/quadros/{lista['quadro_id']}/listas/{lista['id']}/cartoes", json=corpo).json()

    dentro_casa = criar_cartao(lista_casa, "Dentro do período (Casa)", datetime(2026, 3, 5, tzinfo=timezone.utc))
    dentro_faculdade = criar_cartao(
        lista_faculdade, "Dentro do período (Faculdade)", datetime(2026, 3, 6, tzinfo=timezone.utc)
    )
    fora_do_periodo = criar_cartao(lista_casa, "Fora do período", datetime(2026, 4, 1, tzinfo=timezone.utc))
    criar_cartao(lista_casa, "Sem prazo nenhum")
    a_ser_arquivado = criar_cartao(lista_casa, "Arquivado", datetime(2026, 3, 7, tzinfo=timezone.utc))
    cliente.post(
        f"/quadros/{quadro_casa['id']}/listas/{lista_casa['id']}/cartoes/{a_ser_arquivado['id']}/arquivar"
    )

    resposta = cliente.get(
        "/calendario",
        params={"de": "2026-03-01T00:00:00Z", "ate": "2026-03-31T23:59:59Z"},
    )
    assert resposta.status_code == 200
    ids_retornados = [c["id"] for c in resposta.json()]

    assert ids_retornados == [dentro_casa["id"], dentro_faculdade["id"]]
    assert fora_do_periodo["id"] not in ids_retornados
    assert a_ser_arquivado["id"] not in ids_retornados
