"""
Conexão com o banco de dados e fábrica de sessões do SQLAlchemy.

Este arquivo não conhece nenhuma regra de negócio — ele só monta o "cano"
por onde os modelos (em app/modelos/) conversam com o PostgreSQL. Toda
rota da API pede uma sessão daqui através da função `obter_sessao`.
"""

from datetime import timezone

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator

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


class TZDateTime(TypeDecorator):
    """Um `DateTime(timezone=True)` que garante ida e volta consistente
    entre dialetos -- usado por todo modelo em vez do tipo genérico do
    SQLAlchemy direto.

    O motivo de existir: o PostgreSQL (produção, ver app/config.py)
    preserva datetimes com fuso horário nativamente (é o TIMESTAMPTZ das
    Etapas 2 e 4). O SQLite (usado pelos testes -- ver tests/conftest.py)
    não tem tipo de data nativo; por baixo dos panos ele guarda texto, e a
    implementação padrão do SQLAlchemy para esse dialeto devolve o valor
    de volta SEM `tzinfo`, mesmo tendo sido gravado como aware. Um
    datetime "agora" (aware, ex.: `datetime.now(timezone.utc)`) subtraído
    de um valor lido do banco (naive) estoura `TypeError` -- foi
    exatamente isso que o worker (Etapa 5.3, `agora - cartao.notificar_em`)
    encontrou contra o banco de teste.

    Este tipo reattacha `tzinfo=UTC` num valor que chegar sem ele, tanto
    ao gravar quanto ao ler -- inofensivo contra o PostgreSQL (que já
    devolve aware; a condição nunca dispara) e é o que faz o mesmo código
    funcionar sem ramificação por dialeto contra os dois bancos.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


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
