"""
Fixtures compartilhadas pelos testes: um banco SQLite em memória (no lugar
do PostgreSQL real) e clientes HTTP de teste contra a aplicação FastAPI.

Por que SQLite em memória, se o projeto usa PostgreSQL (Etapa 1.5)?
Porque o que a Etapa 2.8 pede para testar é a estrutura do modelo e o
comportamento das rotas -- nenhum dos testes aqui depende de um recurso
específico do PostgreSQL. Testar contra SQLite deixa a suíte rápida e sem
exigir um banco de verdade no ar só para rodar `pytest`. Se um teste
futuro precisar de algo específico do Postgres (por exemplo, um tipo de
coluna que o SQLite não têm equivalente), aí ele passa a exigir o banco
real -- não é o caso de nenhum teste desta etapa.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, obter_sessao
from app.main import app


@pytest.fixture()
def app_com_banco_de_teste():
    """Cria um banco SQLite isolado para um único teste, e substitui a
    dependência `obter_sessao` da aplicação para que toda rota, durante o
    teste, converse com esse banco -- em vez do PostgreSQL de
    `app/config.py`.

    `poolclass=StaticPool` é necessário porque, por padrão, cada conexão
    SQLite em memória enxerga um banco *diferente e vazio*; StaticPool
    força todas as conexões abertas a partir deste engine a reusarem a
    mesma conexão de fato, então as tabelas criadas por
    `Base.metadata.create_all` continuam visíveis nas requisições
    seguintes dentro do mesmo teste.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    FabricaSessaoDeTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def sobrescrever_obter_sessao():
        sessao = FabricaSessaoDeTeste()
        try:
            yield sessao
        finally:
            sessao.close()

    app.dependency_overrides[obter_sessao] = sobrescrever_obter_sessao
    yield app
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def cliente(app_com_banco_de_teste):
    """Um cliente HTTP de teste com seu próprio cookie jar -- suficiente
    para os testes que giram em torno de uma única usuária logada."""
    with TestClient(app_com_banco_de_teste) as cliente_de_teste:
        yield cliente_de_teste


@pytest.fixture()
def fabrica_cliente(app_com_banco_de_teste):
    """Para o teste que precisa de DUAS usuárias ao mesmo tempo (a
    fronteira de posse da Etapa 2.8): cada chamada devolve um TestClient
    novo, com cookie jar independente, todos contra o mesmo app e o mesmo
    banco de teste -- simulando duas pessoas em dois navegadores
    diferentes, sem misturar a sessão de login de uma com a da outra."""

    def criar_cliente() -> TestClient:
        return TestClient(app_com_banco_de_teste)

    return criar_cliente
