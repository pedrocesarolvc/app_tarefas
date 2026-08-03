"""
Configuração do Alembic para este projeto.

A única customização real em relação ao template padrão do Alembic é: em
vez de ler a URL do banco do `alembic.ini`, lemos de
`app.config.configuracoes` (a mesma fonte que a própria API usa) e
apontamos `target_metadata` para `app.database.Base.metadata` (que só
conhece os modelos depois que `app.modelos` é importado -- ver o
comentário em app/modelos/__init__.py). Isso é o que permite
`alembic revision --autogenerate` comparar o banco real contra os modelos
Python e gerar a migração sozinho.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import configuracoes
from app.database import Base

# Importa o pacote de modelos só pelo efeito colateral de registrar todas
# as classes mapeadas em Base.metadata -- sem isto, target_metadata
# ficaria "vazio" e o autogenerate não veria nenhuma tabela.
import app.modelos  # noqa: F401

config = context.config

# Sobrescreve o `sqlalchemy.url` (propositalmente vazio no alembic.ini)
# com a URL real, vinda da mesma configuração que app/database.py usa.
config.set_main_option("sqlalchemy.url", configuracoes.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera o SQL das migrações sem se conectar a um banco de verdade
    (usado por `alembic upgrade --sql`, por exemplo, para revisar o SQL
    antes de aplicá-lo manualmente)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """O caminho normal: conecta no banco de verdade e aplica as
    migrações."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
