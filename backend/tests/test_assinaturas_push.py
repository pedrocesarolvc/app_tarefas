"""
Testes das rotas de AssinaturaPush (Etapa 5.6) -- só o contrato da API em
si (o worker, que é quem de fato consome essas assinaturas, é testado à
parte em test_worker.py).
"""

from fastapi.testclient import TestClient

from tests.test_modelo_kanban import registrar_e_logar


def test_criar_assinatura_reatribui_endpoint_existente_ao_usuario_atual(cliente: TestClient):
    """Cobre o caminho normal (criar e listar) e a decisão registrada em
    app/rotas/assinaturas_push.py: o mesmo endpoint assinando de novo é
    reatribuído ao usuário atual, não duplicado nem rejeitado."""
    registrar_e_logar(cliente, email="a@example.com")
    resposta = cliente.post(
        "/assinaturas-push",
        json={"endpoint": "https://push.exemplo/x", "chave_p256dh": "p256dh", "chave_auth": "auth"},
    )
    assert resposta.status_code == 201
    assinatura_id = resposta.json()["id"]
    assert [a["id"] for a in cliente.get("/assinaturas-push").json()] == [assinatura_id]

    # O mesmo navegador (mesmo endpoint) assinando de novo, agora logado
    # como outra usuária -- deve ser a MESMA linha, só com o dono trocado.
    registrar_e_logar(cliente, email="b@example.com")
    resposta_b = cliente.post(
        "/assinaturas-push",
        json={"endpoint": "https://push.exemplo/x", "chave_p256dh": "p256dh-novo", "chave_auth": "auth"},
    )
    assert resposta_b.json()["id"] == assinatura_id
    assert [a["id"] for a in cliente.get("/assinaturas-push").json()] == [assinatura_id]


def test_apagar_assinatura_de_outro_usuario_devolve_404(fabrica_cliente):
    """A mesma fronteira de posse do resto da API (Etapa 2.8) também vale
    aqui."""
    cliente_a = fabrica_cliente()
    registrar_e_logar(cliente_a, email="a@example.com")
    assinatura = cliente_a.post(
        "/assinaturas-push",
        json={"endpoint": "https://push.exemplo/y", "chave_p256dh": "p256dh", "chave_auth": "auth"},
    ).json()

    cliente_b = fabrica_cliente()
    registrar_e_logar(cliente_b, email="b@example.com")
    resposta = cliente_b.delete(f"/assinaturas-push/{assinatura['id']}")
    assert resposta.status_code == 404
