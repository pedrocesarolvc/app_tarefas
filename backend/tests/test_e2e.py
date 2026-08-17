"""
Os três testes de ponta a ponta da Etapa 7.6 — "atravessam o sistema
inteiro". Diferente do resto da suíte (que isola cada peça: modelo,
ordenação, worker, tempo real), estes três propositalmente NÃO isolam
nada — cada um caminha pela API como uma usuária caminharia, e o valor
deles está exatamente em juntar peças que os outros testes provam
separadas.
"""

from datetime import datetime, timedelta, timezone

from app.modelos.cartao import Cartao
from tests.test_modelo_kanban import registrar_e_logar
from worker.agendador import executar_ciclo


def test_fluxo_completo_criar_mover_e_confirmar_ordem_persistida(cliente):
    """Etapa 7.6, item 1: "criar quadro → criar listas → criar cartão →
    arrastar entre listas → confirmar a ordem persistida. Se passa, o
    núcleo funciona"."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Projeto"}).json()
    a_fazer = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    pronto = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "Pronto"}).json()

    caminho_a_fazer = f"/quadros/{quadro['id']}/listas/{a_fazer['id']}/cartoes"
    um = cliente.post(caminho_a_fazer, json={"titulo": "Um"}).json()
    dois = cliente.post(caminho_a_fazer, json={"titulo": "Dois"}).json()
    tres = cliente.post(caminho_a_fazer, json={"titulo": "Três"}).json()

    resposta_mover = cliente.post(
        f"{caminho_a_fazer}/{dois['id']}/mover", json={"lista_id": pronto["id"]}
    )
    assert resposta_mover.status_code == 200
    assert resposta_mover.json()["lista_id"] == pronto["id"]

    restantes = cliente.get(caminho_a_fazer).json()
    assert [c["id"] for c in restantes] == [um["id"], tres["id"]]

    destino = cliente.get(f"/quadros/{quadro['id']}/listas/{pronto['id']}/cartoes").json()
    assert [c["id"] for c in destino] == [dois["id"]]


def test_ciclo_do_aviso_worker_notifica_sem_duplicar(cliente, sessao_bruta):
    """Etapa 7.6, item 2 — "o teste de assinatura do projeto": criar
    cartão com prazo próximo → rodar o worker → confirmar notificado →
    rodar de novo → confirmar que não duplicou.

    Diferente de tests/test_worker.py (que isola o worker com dublês de
    envio), aqui o cartão nasce pela API de verdade, e `executar_ciclo`
    roda contra o mesmo banco que a API acabou de escrever -- é a ligação
    entre as Etapas 4 (o campo `notificar_em`), 2/3 (a API que grava o
    cartão) e 5 (o worker que o consome) sendo exercitada junta."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()

    prazo_ja_vencido = datetime.now(timezone.utc) - timedelta(minutes=1)
    cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        json={"titulo": "Tarefa urgente", "prazo": prazo_ja_vencido.isoformat(), "aviso_previo": 0},
    ).json()
    assert cartao["notificado"] is False

    def sem_evento_realtime(*_args, **_kwargs) -> None:
        pass  # a ponte de tempo real (Etapa 6.5) é testada à parte, em test_realtime.py

    primeira_rodada = executar_ciclo(sessao_bruta, publicar_evento_realtime=sem_evento_realtime)
    assert primeira_rodada == 1
    assert sessao_bruta.get(Cartao, cartao["id"]).notificado is True

    segunda_rodada = executar_ciclo(sessao_bruta, publicar_evento_realtime=sem_evento_realtime)
    assert segunda_rodada == 0


def test_ordenacao_sob_estresse_muitas_insercoes_no_mesmo_ponto(cliente):
    """Etapa 7.6, item 3: inserções consecutivas no mesmo ponto,
    verificando que a ordem permanece correta -- a versão de ponta a
    ponta do teste de assinatura da Etapa 3, que já existe e já prova
    exatamente as cinquenta inserções do checklist
    (test_ordenacao.py::test_cinquenta_insercoes_consecutivas...,
    contra `Decimal` puro, com precisão de fato ilimitada -- o mesmo
    modelo do NUMERIC do PostgreSQL de produção).

    Este teste aqui prova o complemento: que a API e o banco de verdade
    (não só o algoritmo) sustentam o mesmo padrão de inserção através de
    requisições HTTP reais. O número de rodadas é menor que 50 por um
    motivo que vale registrar: o SQLite usado nos testes (ver
    tests/conftest.py) não tem um tipo decimal nativo, e o driver do
    SQLAlchemy para esse dialeto converte o `Decimal` para `float`
    (binário, 52 bits de mantissa) ao gravar -- a própria armadilha da
    Etapa 3.4, reaparecendo na camada de binding em vez do cálculo. O
    PostgreSQL real não tem esse problema (o NUMERIC é nativamente
    ilimitado, sem passar por float em nenhum momento); é só uma
    limitação do banco de teste, e por isso o teste algorítmico acima é
    quem carrega a prova rigorosa das 50 inserções -- este aqui usa 40,
    com folga confortável sobre o ponto de colapso do SQLite observado
    empiricamente (~52 rodadas neste cenário), só para confirmar que a
    ordem sobrevive ponta a ponta.
    """
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    caminho_cartoes = f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes"

    referencia = cliente.post(caminho_cartoes, json={"titulo": "Referência"}).json()
    fronteira_distante = cliente.post(caminho_cartoes, json={"titulo": "Fronteira"}).json()

    fronteira_mais_proxima_id = fronteira_distante["id"]
    ids_inseridos_em_ordem = []
    for indice in range(40):
        novo = cliente.post(caminho_cartoes, json={"titulo": f"Inserção {indice}"}).json()
        resposta = cliente.post(
            f"{caminho_cartoes}/{novo['id']}/mover",
            json={
                "lista_id": lista["id"],
                "cartao_anterior_id": referencia["id"],
                "cartao_posterior_id": fronteira_mais_proxima_id,
            },
        )
        assert resposta.status_code == 200
        fronteira_mais_proxima_id = novo["id"]
        ids_inseridos_em_ordem.append(novo["id"])

    cartoes_na_ordem_final = cliente.get(caminho_cartoes).json()
    # Cada inserção ficou mais perto da referência que a anterior -- a
    # ordem final é a referência, depois as inserções de trás para
    # frente (a mais recente é a mais próxima), depois a fronteira.
    ids_esperados = [referencia["id"], *reversed(ids_inseridos_em_ordem), fronteira_distante["id"]]
    assert [c["id"] for c in cartoes_na_ordem_final] == ids_esperados
