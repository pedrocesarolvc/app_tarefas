"""
Fixtures compartilhadas pelos testes: um banco SQLite em memória (no lugar
do PostgreSQL real) e clientes HTTP de teste contra a aplicação FastAPI.

Por que SQLite em memória, se o projeto usa PostgreSQL (Etapa 1.5)?
Porque o que os testes de API pedem é a estrutura do modelo e o
comportamento das rotas -- nenhum deles depende de um recurso específico
do PostgreSQL. Testar contra SQLite deixa a suíte rápida e sem exigir um
banco de verdade no ar só para rodar `pytest`. O teste que de fato prova
a armadilha de precisão da Etapa 3.4 (50 inserções consecutivas) roda
contra `Decimal` puro, sem nenhum banco envolvido -- ver
tests/test_ordenacao.py -- então nem essa ressalva do SQLite chega a
importar ali.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, obter_sessao
from app.main import app


@pytest.fixture()
def motor_de_teste():
    """O engine SQLAlchemy do banco de teste, isolado por teste.

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
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def app_com_banco_de_teste(motor_de_teste):
    """Substitui a dependência `obter_sessao` da aplicação para que toda
    rota, durante o teste, converse com `motor_de_teste` -- em vez do
    PostgreSQL de `app/config.py`."""
    FabricaSessaoDeTeste = sessionmaker(autocommit=False, autoflush=False, bind=motor_de_teste)

    def sobrescrever_obter_sessao():
        sessao = FabricaSessaoDeTeste()
        try:
            yield sessao
        finally:
            sessao.close()

    app.dependency_overrides[obter_sessao] = sobrescrever_obter_sessao
    yield app
    app.dependency_overrides.clear()


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


@pytest.fixture()
def sessao_bruta(motor_de_teste):
    """Uma sessão SQLAlchemy direta contra o mesmo banco que a API de
    teste está usando (`motor_de_teste`), para os poucos testes que
    precisam manipular o banco por baixo da API -- por exemplo, forçar
    duas posições idênticas para testar o desempate por `id` da Etapa 3.8,
    algo que a própria API nunca produz sozinha (ela sempre calcula
    posições distintas via app/servicos/ordenacao.py)."""
    FabricaSessao = sessionmaker(autocommit=False, autoflush=False, bind=motor_de_teste)
    sessao: Session = FabricaSessao()
    try:
        yield sessao
    finally:
        sessao.close()
