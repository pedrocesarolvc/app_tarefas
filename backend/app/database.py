"""
Conexão com o banco de dados e fábrica de sessões do SQLAlchemy.

Este arquivo não conhece nenhuma regra de negócio — ele só monta o "cano"
por onde os modelos (em app/modelos/) conversam com o PostgreSQL. Toda
rota da API pede uma sessão daqui através da função `obter_sessao`.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import configuracoes

# O "engine" é o objeto que sabe como abrir conexões com o banco descrito
# em `database_url`. Ele mantém um pool de conexões por baixo dos panos,
# então não abrimos uma conexão TCP nova a cada requisição — isso seria
# lento e desperdiçaria recursos do Postgres.
engine = create_engine(configuracoes.database_url)

# SessionLocal é uma "fábrica" de sessões: cada vez que chamamos
# SessionLocal(), ganhamos uma sessão nova e independente. Uma sessão é o
# espaço de trabalho onde o SQLAlchemy rastreia os objetos Python que
# representam linhas do banco, e onde ficam pendentes as mudanças até um
# `commit()`.
#
# autocommit=False e autoflush=False são os valores recomendados pelo
# próprio SQLAlchemy: sem eles, o SQLAlchemy tentaria enviar mudanças pro
# banco em momentos imprevisíveis (a cada consulta), o que dificulta
# raciocinar sobre quando exatamente uma escrita acontece.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    Classe-base de que todo modelo (Usuario, Quadro, Lista, Cartao) herda.

    É só isso — não tem comportamento próprio. Ela existe porque o
    SQLAlchemy usa herança para descobrir, em tempo de execução, quais
    classes Python representam tabelas do banco. `Base.metadata` (usado
    pelo Alembic para gerar migrações) só conhece os modelos que herdam
    dela.
    """

    pass


def obter_sessao():
    """
    Dependência do FastAPI que entrega uma sessão de banco de dados por
    requisição, e garante que ela é fechada no final — mesmo se a rota
    lançar uma exceção no meio do caminho.

    O padrão `yield` aqui é o que permite isso: tudo antes do `yield` roda
    antes da rota; tudo depois roda depois, sempre (é equivalente a um
    `try/finally`). Cada requisição HTTP ganha sua própria sessão, isolada
    das demais — duas requisições simultâneas nunca compartilham a mesma
    sessão por acidente.
    """
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()
