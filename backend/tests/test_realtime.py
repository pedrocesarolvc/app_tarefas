"""
Testes do canal em tempo real (Etapa 6) -- o que dá para testar com
confiança no backend, seguindo o checklist da Etapa 6.10.

A parte de cliente do checklist (o cliente ignora o próprio eco; falha na
requisição reverte a atualização otimista; reconectar recarrega o
quadro) não tem o que testar aqui: são comportamentos de interface, e não
existe nenhuma interface construída ainda (ver o comentário no topo de
docs/documentacao.md sobre o estado desta etapa). O que o backend garante
-- e é o que estes testes provam -- é a matéria-prima que esse
comportamento de cliente vai precisar: eventos chegam só para quem está
na sala certa, desconectar não vaza memória, e o evento carrega o `origem`
que a supressão de eco (Etapa 6.7) vai comparar.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.realtime.gerenciador import gerenciador_de_salas
from tests.test_modelo_kanban import registrar_e_logar


def test_cliente_conectado_recebe_evento_do_proprio_quadro(cliente: TestClient):
    """Checklist 6.10, item 1."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()

    with cliente.websocket_connect(f"/ws/quadros/{quadro['id']}") as ws:
        primeira_mensagem = ws.receive_json()
        assert primeira_mensagem["tipo"] == "conectado"

        lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()

        evento = ws.receive_json()
        assert evento["tipo"] == "lista_criada"
        assert evento["dados"]["id"] == lista["id"]


def test_cliente_nao_recebe_evento_de_outro_quadro(cliente: TestClient):
    """Checklist 6.10, item 2. Conecta na sala do quadro A, dispara uma
    mudança no quadro B (nenhuma sala) e depois uma no A -- se o evento de
    B tivesse vazado para a conexão de A, seria essa a primeira mensagem
    recebida, não a de A."""
    registrar_e_logar(cliente)
    quadro_a = cliente.post("/quadros", json={"nome": "A"}).json()
    quadro_b = cliente.post("/quadros", json={"nome": "B"}).json()

    with cliente.websocket_connect(f"/ws/quadros/{quadro_a['id']}") as ws:
        ws.receive_json()  # "conectado"

        cliente.post(f"/quadros/{quadro_b['id']}/listas", json={"nome": "Não deveria chegar"})
        lista_do_a = cliente.post(f"/quadros/{quadro_a['id']}/listas", json={"nome": "Do quadro A"}).json()

        evento = ws.receive_json()
        assert evento["dados"]["id"] == lista_do_a["id"]
        assert evento["dados"]["nome"] == "Do quadro A"


def test_desconectar_remove_da_sala_sem_vazamento(cliente: TestClient):
    """Checklist 6.10, item 3."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()

    assert gerenciador_de_salas.quantidade_de_conexoes(quadro["id"]) == 0
    with cliente.websocket_connect(f"/ws/quadros/{quadro['id']}") as ws:
        ws.receive_json()  # "conectado"
        assert gerenciador_de_salas.quantidade_de_conexoes(quadro["id"]) == 1

    assert gerenciador_de_salas.quantidade_de_conexoes(quadro["id"]) == 0


def test_conectar_a_quadro_de_outro_usuario_fecha_a_conexao(fabrica_cliente):
    """A mesma fronteira de posse do resto da API (Etapa 2.8) também vale
    para o WebSocket -- não é um item literal do checklist 6.10, mas seria
    um jeito e tanto de vazar dados de uma usuária para outra se não
    valesse."""
    cliente_a = fabrica_cliente()
    registrar_e_logar(cliente_a, email="a@example.com")
    quadro_da_a = cliente_a.post("/quadros", json={"nome": "Da A"}).json()

    cliente_b = fabrica_cliente()
    registrar_e_logar(cliente_b, email="b@example.com")

    # O servidor aceita o handshake HTTP (é assim que WebSocket funciona)
    # e fecha em seguida -- perto o bastante do próprio `__enter__` que o
    # TestClient já levanta `WebSocketDisconnect` ali, antes de qualquer
    # mensagem ser trocada.
    with pytest.raises(WebSocketDisconnect) as excecao:
        with cliente_b.websocket_connect(f"/ws/quadros/{quadro_da_a['id']}"):
            pass
    assert excecao.value.code == 4404


def test_duas_atualizacoes_no_mesmo_cartao_convergem_para_a_ultima(cliente: TestClient):
    """Checklist 6.10, item 4 (LWW). As operações do kanban são absolutas
    (Etapa 6.2/6.3) -- a rota PATCH já aplica "quem escreve por último
    ganha" sem nenhum código extra desta etapa; o teste prova que o
    resultado final é sempre o da escrita mais recente, nunca um estado
    misturado."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes", json={"titulo": "Original"}
    ).json()

    caminho = f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes/{cartao['id']}"
    cliente.patch(caminho, json={"titulo": "Escrita 1"})
    resposta_final = cliente.patch(caminho, json={"titulo": "Escrita 2"})

    assert resposta_final.json()["titulo"] == "Escrita 2"
    assert cliente.get(f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes").json()[0]["titulo"] == "Escrita 2"


def test_evento_transmitido_carrega_a_origem_para_supressao_de_eco(cliente: TestClient):
    """Checklist 6.10, item 5 -- a metade que o backend pode garantir: o
    evento carrega o `origem` que o cliente vai comparar contra o próprio
    id de conexão para reconhecer e ignorar o eco (Etapa 6.7). A
    supressão em si é responsabilidade do cliente, que ainda não existe."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()

    with cliente.websocket_connect(f"/ws/quadros/{quadro['id']}") as ws:
        ws.receive_json()  # "conectado"

        cliente.post(
            f"/quadros/{quadro['id']}/listas",
            json={"nome": "A fazer"},
            headers={"X-Origem-Conexao": "conexao-de-teste-123"},
        )

        evento = ws.receive_json()
        assert evento["origem"] == "conexao-de-teste-123"
