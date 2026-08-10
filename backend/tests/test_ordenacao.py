"""
Testes que verificam, item por item, o checklist da Etapa 3.9 da
documentação (docs/documentacao.md).

Os quatro primeiros itens e o teste de assinatura (o sétimo, "cinquenta
inserções consecutivas") testam `calcular_posicao` diretamente --
`Decimal` puro, sem nenhum banco envolvido. É a forma mais direta de
provar que o algoritmo em si está correto (Etapa 3.6: "o cálculo fica
isolado num único lugar"), e evita qualquer dúvida sobre como o SQLite dos
testes de API guarda um NUMERIC (o PostgreSQL de produção guarda com
precisão de fato ilimitada; não é o que este arquivo está testando).

Os itens sobre efeito colateral de escrita (mover altera só um registro,
mover entre listas recalcula no destino, desempate por id) precisam da
API/banco de verdade, porque são sobre o que é ou não gravado -- não dá
para provar isso com uma função pura.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.servicos.ordenacao import POSICAO_INICIAL, PosicaoInvalidaError, calcular_posicao
from tests.test_modelo_kanban import registrar_e_logar


# --- calcular_posicao, isolado (Etapa 3.9, itens 1 a 4 e 7) --------------


def test_inserir_em_lista_vazia_funciona():
    """Checklist: "Inserir em lista vazia funciona"."""
    assert calcular_posicao(anterior=None, posterior=None) == POSICAO_INICIAL


def test_inserir_no_topo_produz_posicao_menor_que_a_do_primeiro():
    """Checklist: "Inserir no topo produz posição menor que a do
    primeiro"."""
    posicao_do_primeiro = Decimal("500")
    nova_posicao = calcular_posicao(anterior=None, posterior=posicao_do_primeiro)
    assert nova_posicao < posicao_do_primeiro


def test_inserir_no_fim_produz_posicao_maior_que_a_do_ultimo():
    """Checklist: "Inserir no fim produz posição maior que a do
    último"."""
    posicao_do_ultimo = Decimal("500")
    nova_posicao = calcular_posicao(anterior=posicao_do_ultimo, posterior=None)
    assert nova_posicao > posicao_do_ultimo


def test_inserir_entre_dois_produz_posicao_estritamente_entre_as_duas():
    """Checklist: "Inserir entre dois cartões produz posição estritamente
    entre as duas" -- o ponto médio da Etapa 3.3."""
    anterior = Decimal("1.0")
    posterior = Decimal("2.0")
    nova_posicao = calcular_posicao(anterior=anterior, posterior=posterior)
    assert anterior < nova_posicao < posterior
    assert nova_posicao == Decimal("1.5")


def test_anterior_maior_ou_igual_a_posterior_e_invalido():
    """Guarda de sanidade que não está no checklist da Etapa 3.9 mas é a
    contraparte natural do teste acima: se os vizinhos vierem trocados
    (anterior >= posterior), calcular uma posição "entre" os dois não faz
    sentido matemático nenhum, e a função recusa a calcular em vez de
    devolver um valor sem significado."""
    with pytest.raises(PosicaoInvalidaError):
        calcular_posicao(anterior=Decimal("2.0"), posterior=Decimal("1.0"))
    with pytest.raises(PosicaoInvalidaError):
        calcular_posicao(anterior=Decimal("1.0"), posterior=Decimal("1.0"))


def test_cinquenta_insercoes_consecutivas_no_mesmo_ponto_mantem_ordem_correta():
    """Checklist, item de assinatura da etapa: "Cinquenta inserções
    consecutivas no mesmo ponto mantêm a ordem correta".

    Reproduz o cenário da Etapa 3.4: a usuária arrasta um cartão para
    ficar logo depois de um cartão de referência fixo, repetidamente --
    cada nova inserção pega o ponto médio do intervalo que sobrou entre a
    referência e a última posição inserida. Com float64 (52 bits de
    mantissa) isso colapsa por volta da 52ª inserção: o ponto médio vira
    igual a um dos dois operandos, e a ordem entre os dois deixa de ser
    determinística. Com `Decimal` (Etapa 3.6), cada inserção só acrescenta
    mais um dígito decimal -- sem limite prático nas dezenas de inserções
    que este teste faz.
    """
    referencia = Decimal("1.0")
    posicao_anterior_mais_proxima = Decimal("2.0")
    posicoes_geradas: list[Decimal] = []

    for _ in range(50):
        nova_posicao = calcular_posicao(anterior=referencia, posterior=posicao_anterior_mais_proxima)

        # A prova de que a armadilha da Etapa 3.4 está fechada: mesmo na
        # 50ª volta, o ponto médio ainda é estritamente maior que a
        # referência -- nunca colapsa para ser igual a ela.
        assert nova_posicao > referencia
        assert nova_posicao < posicao_anterior_mais_proxima

        posicoes_geradas.append(nova_posicao)
        posicao_anterior_mais_proxima = nova_posicao

    # E a sequência inteira, na ordem em que foi inserida, é estritamente
    # decrescente -- ou seja, se cada uma virasse um cartão de verdade,
    # `ORDER BY posicao` reproduziria exatamente a ordem de inserção,
    # sem dois cartões jamais empatando.
    assert posicoes_geradas == sorted(posicoes_geradas, reverse=True)
    assert len(set(posicoes_geradas)) == len(posicoes_geradas)


# --- efeitos de escrita na API (Etapa 3.9, itens 5, 6 e 8) ---------------


def test_mover_cartao_altera_apenas_aquele_registro(cliente: TestClient):
    """Checklist: "Mover um cartão altera apenas aquele cartão -- nenhum
    outro registro é escrito"."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()

    a = cliente.post(f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes", json={"titulo": "A"}).json()
    b = cliente.post(f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes", json={"titulo": "B"}).json()
    c = cliente.post(f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes", json={"titulo": "C"}).json()

    # Move C para o topo (antes de A) -- A e B não deveriam ser tocados.
    resposta = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes/{c['id']}/mover",
        json={"lista_id": lista["id"], "cartao_posterior_id": a["id"]},
    )
    assert resposta.status_code == 200
    c_movido = resposta.json()
    assert Decimal(str(c_movido["posicao"])) < Decimal(str(a["posicao"]))

    cartoes_depois = {
        cartao["id"]: cartao
        for cartao in cliente.get(f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes").json()
    }
    # A e B continuam exatamente como estavam criados -- nenhuma
    # renumeração em cascata, diferente da abordagem ingênua da Etapa 3.2.
    assert cartoes_depois[a["id"]] == a
    assert cartoes_depois[b["id"]] == b
    # E a ordem visível reflete o arrasto: C passou para antes de A.
    assert [cartoes_depois[id_]["titulo"] for id_ in (c["id"], a["id"], b["id"])] == ["C", "A", "B"]


def test_mover_entre_listas_atualiza_lista_id_e_recalcula_posicao_no_destino(cliente: TestClient):
    """Checklist: "Mover entre listas atualiza lista_id e recalcula a
    posição no destino"."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    origem = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    destino = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "Pronto"}).json()

    cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{origem['id']}/cartoes", json={"titulo": "Tarefa"}
    ).json()
    x = cliente.post(f"/quadros/{quadro['id']}/listas/{destino['id']}/cartoes", json={"titulo": "X"}).json()
    y = cliente.post(f"/quadros/{quadro['id']}/listas/{destino['id']}/cartoes", json={"titulo": "Y"}).json()

    resposta = cliente.post(
        f"/quadros/{quadro['id']}/listas/{origem['id']}/cartoes/{cartao['id']}/mover",
        json={
            "lista_id": destino["id"],
            "cartao_anterior_id": x["id"],
            "cartao_posterior_id": y["id"],
        },
    )
    assert resposta.status_code == 200
    cartao_movido = resposta.json()

    assert cartao_movido["lista_id"] == destino["id"]
    # A posição não é "a mesma de origem carregada para o destino" -- foi
    # recalculada em função dos vizinhos NO DESTINO (Etapa 3.3).
    assert Decimal(str(x["posicao"])) < Decimal(str(cartao_movido["posicao"])) < Decimal(str(y["posicao"]))


def test_duas_posicoes_iguais_sao_desempatadas_de_forma_estavel_pelo_id(
    cliente: TestClient, sessao_bruta
):
    """Checklist: "Duas posições iguais são desempatadas de forma estável
    pelo id" -- a defesa da Etapa 3.8 contra duas inserções concorrentes
    que calculam o mesmo ponto médio.

    A API sozinha nunca produz esse empate (cada cálculo de posição é
    determinístico e sequencial dentro de um teste) -- por isso este teste
    força o empate manipulando o banco diretamente com `sessao_bruta`,
    simulando o que duas escritas concorrentes fariam.
    """
    from app.modelos.cartao import Cartao

    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()

    primeiro = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes", json={"titulo": "Criado primeiro"}
    ).json()
    segundo = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes", json={"titulo": "Criado depois"}
    ).json()
    assert primeiro["id"] < segundo["id"]

    # Força as duas posições a serem idênticas -- o cenário de duas
    # inserções concorrentes calculando o mesmo ponto médio.
    cartao_segundo_no_banco = sessao_bruta.get(Cartao, segundo["id"])
    cartao_segundo_no_banco.posicao = Decimal(str(primeiro["posicao"]))
    sessao_bruta.commit()

    cartoes = cliente.get(f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes").json()
    # Mesmo com posicao empatada, a ordem devolvida é determinística: o id
    # menor (criado primeiro) vem antes -- `ORDER BY posicao, id` (Etapa
    # 3.8), não a ordem "por acaso" que o banco escolheria sem o segundo
    # critério.
    assert [c["id"] for c in cartoes] == [primeiro["id"], segundo["id"]]
