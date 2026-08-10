"""
Testes que verificam, item por item, o checklist da Etapa 2.8 da
documentação (docs/documentacao.md):

    "Modelagem se verifica de forma indireta -- o que se testa é que a
    estrutura sustenta as operações."

Cada função de teste abaixo tem uma correspondência direta com uma linha
daquele checklist -- o nome da função e o comentário logo depois citam
qual. Os testes passam pela API (TestClient), não pelos modelos
diretamente: o que a Etapa 2.8 quer garantir é o comportamento observável
do sistema inteiro (modelo + schema + rota), não só que o SQLAlchemy sabe
salvar uma linha.

Nenhuma criação de lista/cartão aqui informa `posicao` -- desde a Etapa 3,
isso não é mais um campo aceito do cliente (ver app/schemas/lista.py e
app/schemas/cartao.py: toda criação é anexada ao final, e reordenar é uma
operação própria com vizinhos). Os testes específicos da lógica de
ordenação em si estão em test_ordenacao.py.
"""

from decimal import Decimal

from fastapi.testclient import TestClient


def registrar_e_logar(cliente: TestClient, email: str = "usuaria@example.com", senha: str = "senha-segura-123") -> dict:
    """Fluxo comum a quase todo teste: cadastra uma usuária e já efetua o
    login, deixando o cookie de sessão guardado no cookie jar do cliente
    para as próximas chamadas."""
    cliente.post("/auth/registrar", json={"email": email, "senha": senha})
    resposta_login = cliente.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200
    return resposta_login.json()


def criar_quadro_lista_cartao(cliente: TestClient) -> tuple[dict, dict, dict]:
    """Monta o caminho mais curto Quadro → Lista → Cartão (Etapa 2.2),
    devolvendo os três objetos criados. Ponto de partida repetido por
    vários testes abaixo."""
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        json={"titulo": "Lavar roupa"},
    ).json()
    return quadro, lista, cartao


def test_criar_quadro_lista_cartao_e_recupera_los_ligados_corretamente(cliente: TestClient):
    """Checklist: "Criar quadro, lista e cartão, e recuperá-los ligados
    corretamente"."""
    registrar_e_logar(cliente)
    quadro, lista, cartao = criar_quadro_lista_cartao(cliente)

    # Recupera cada nível por uma rota de LEITURA separada da que criou --
    # não basta o POST ter devolvido os dados certos, a consulta também
    # precisa enxergá-los amarrados uns aos outros.
    quadro_recuperado = cliente.get(f"/quadros/{quadro['id']}").json()
    assert quadro_recuperado["id"] == quadro["id"]

    listas_do_quadro = cliente.get(f"/quadros/{quadro['id']}/listas").json()
    assert [l["id"] for l in listas_do_quadro] == [lista["id"]]
    assert listas_do_quadro[0]["quadro_id"] == quadro["id"]

    cartoes_da_lista = cliente.get(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes"
    ).json()
    assert [c["id"] for c in cartoes_da_lista] == [cartao["id"]]
    assert cartoes_da_lista[0]["lista_id"] == lista["id"]


def test_mover_cartao_entre_listas_altera_apenas_lista_id(cliente: TestClient):
    """Checklist: "Mover um cartão entre listas altera apenas lista_id"
    -- a consequência direta da decisão central da Etapa 2.3 (o estado do
    cartão É a lista onde ele está)."""
    registrar_e_logar(cliente)
    quadro, lista_origem, cartao = criar_quadro_lista_cartao(cliente)
    lista_destino = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "Pronto"}).json()

    # Lista de destino vazia: sem vizinhos, o cartão só cai no único
    # espaço livre dela (Etapa 3.7, caso "lista vazia").
    resposta = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista_origem['id']}/cartoes/{cartao['id']}/mover",
        json={"lista_id": lista_destino["id"]},
    )
    assert resposta.status_code == 200
    cartao_movido = resposta.json()

    # Mudou o que deveria mudar (a lista, e a posição recalculada)...
    assert cartao_movido["lista_id"] == lista_destino["id"]
    # ...e nada mais: título e descrição continuam exatamente os mesmos.
    assert cartao_movido["titulo"] == cartao["titulo"]
    assert cartao_movido["descricao"] == cartao["descricao"]

    # E o cartão de fato saiu de uma lista de cartões e entrou na outra.
    cartoes_origem = cliente.get(
        f"/quadros/{quadro['id']}/listas/{lista_origem['id']}/cartoes"
    ).json()
    assert cartoes_origem == []
    cartoes_destino = cliente.get(
        f"/quadros/{quadro['id']}/listas/{lista_destino['id']}/cartoes"
    ).json()
    assert [c["id"] for c in cartoes_destino] == [cartao["id"]]


def test_usuario_nao_alcanca_quadro_de_outro(fabrica_cliente):
    """Checklist: "Um usuário não alcança quadro de outro (mesmo sendo um
    app pessoal, a fronteira existe)"."""
    cliente_a = fabrica_cliente()
    registrar_e_logar(cliente_a, email="usuaria-a@example.com")
    quadro_da_a = cliente_a.post("/quadros", json={"nome": "Quadro da A"}).json()

    cliente_b = fabrica_cliente()
    registrar_e_logar(cliente_b, email="usuaria-b@example.com")

    # B, logada com a própria sessão, tenta acessar o quadro que pertence
    # à A. A resposta é 404 -- não 403 -- para nem confirmar que aquele
    # quadro existe (ver o comentário em obter_quadro_do_usuario, em
    # app/rotas/quadros.py).
    resposta = cliente_b.get(f"/quadros/{quadro_da_a['id']}")
    assert resposta.status_code == 404

    # E B também não vê o quadro da A na própria listagem.
    quadros_da_b = cliente_b.get("/quadros").json()
    assert quadro_da_a["id"] not in [q["id"] for q in quadros_da_b]


def test_listas_de_um_quadro_voltam_na_ordem_definida_por_posicao(cliente: TestClient):
    """Checklist: "Listas de um quadro voltam na ordem definida por
    posicao". Também exercita a rota `mover_lista` da Etapa 3: criadas
    fora da ordem final de propósito, e depois reordenadas por vizinhos --
    se a API devolvesse por ordem de criação (ou de id), este teste
    pegaria isso."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Faculdade"}).json()

    # Criação sempre anexa ao final (Etapa 3): a ordem de criação é
    # "Pronto", "A fazer", "Fazendo" -- de propósito diferente da ordem
    # final desejada.
    pronto = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "Pronto"}).json()
    a_fazer = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    fazendo = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "Fazendo"}).json()

    # Move "A fazer" para o topo do quadro (antes de "Pronto")...
    cliente.post(
        f"/quadros/{quadro['id']}/listas/{a_fazer['id']}/mover",
        json={"lista_posterior_id": pronto["id"]},
    )
    # ...e "Fazendo" para entre "A fazer" e "Pronto".
    cliente.post(
        f"/quadros/{quadro['id']}/listas/{fazendo['id']}/mover",
        json={"lista_anterior_id": a_fazer["id"], "lista_posterior_id": pronto["id"]},
    )

    listas = cliente.get(f"/quadros/{quadro['id']}/listas").json()
    assert [l["nome"] for l in listas] == ["A fazer", "Fazendo", "Pronto"]


def test_arquivar_cartao_o_remove_das_consultas_normais_mas_ele_continua_no_banco(
    cliente: TestClient,
):
    """Checklist: "Arquivar um cartão o remove das consultas normais, mas
    ele continua no banco" -- o soft delete da Etapa 2.7."""
    registrar_e_logar(cliente)
    quadro, lista, cartao = criar_quadro_lista_cartao(cliente)

    resposta_arquivar = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes/{cartao['id']}/arquivar"
    )
    assert resposta_arquivar.status_code == 200
    assert resposta_arquivar.json()["arquivado"] is True

    # "Removido das consultas normais": some da listagem padrão.
    cartoes_normais = cliente.get(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes"
    ).json()
    assert cartoes_normais == []

    # "Continua no banco": ainda aparece quando peço explicitamente por
    # arquivados também -- não foi um DELETE de verdade.
    cartoes_com_arquivados = cliente.get(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        params={"incluir_arquivados": True},
    ).json()
    assert [c["id"] for c in cartoes_com_arquivados] == [cartao["id"]]


def test_arquivar_lista_arquiva_seus_cartoes(cliente: TestClient):
    """Checklist: "Arquivar uma lista arquiva seus cartões" -- o
    comportamento em cascata descrito na Etapa 2.7 ("Para listas: arquivar
    a lista arquiva os cartões dentro dela")."""
    registrar_e_logar(cliente)
    quadro, lista, primeiro_cartao = criar_quadro_lista_cartao(cliente)
    segundo_cartao = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        json={"titulo": "Passar roupa"},
    ).json()

    resposta = cliente.post(f"/quadros/{quadro['id']}/listas/{lista['id']}/arquivar")
    assert resposta.status_code == 200
    assert resposta.json()["arquivado"] is True

    cartoes_com_arquivados = cliente.get(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        params={"incluir_arquivados": True},
    ).json()
    ids_arquivados = {c["id"]: c["arquivado"] for c in cartoes_com_arquivados}
    assert ids_arquivados == {
        primeiro_cartao["id"]: True,
        segundo_cartao["id"]: True,
    }


def test_cartao_sem_prazo_e_valido(cliente: TestClient):
    """Checklist: "Um cartão sem prazo é válido -- a data é opcional".
    A dimensão tempo (Etapa 1.3) é opcional por natureza: a maioria dos
    cartões não vai ter prazo, e isso precisa ser o caso normal, não uma
    exceção que quebra a criação do cartão."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()
    lista = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()

    resposta = cliente.post(
        f"/quadros/{quadro['id']}/listas/{lista['id']}/cartoes",
        json={"titulo": "Cartão sem data nenhuma"},
    )
    assert resposta.status_code == 201
    cartao = resposta.json()
    assert cartao["prazo"] is None
    assert cartao["aviso_previo_minutos"] is None


def test_criar_lista_e_cartao_sempre_anexa_no_final(cliente: TestClient):
    """Checklist da Etapa 3.9: comportamento de criação (Etapa 3.7,
    "soltar no fim"). Cada lista/cartão novo entra depois do último
    existente -- nunca antes, nunca no meio."""
    registrar_e_logar(cliente)
    quadro = cliente.post("/quadros", json={"nome": "Casa"}).json()

    primeira = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "A fazer"}).json()
    segunda = cliente.post(f"/quadros/{quadro['id']}/listas", json={"nome": "Fazendo"}).json()
    assert Decimal(str(primeira["posicao"])) < Decimal(str(segunda["posicao"]))

    listas = cliente.get(f"/quadros/{quadro['id']}/listas").json()
    assert [l["nome"] for l in listas] == ["A fazer", "Fazendo"]
