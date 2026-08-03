"""
Configuração da aplicação, lida a partir de variáveis de ambiente.

Por quê variável de ambiente, e não valores fixos no código?
Porque o mesmo código roda em três lugares diferentes (sua máquina, o
container Docker, e um servidor de produção no futuro) e cada um tem um
banco de dados e segredos diferentes. Fixar os valores no código obrigaria
a editar código para trocar de ambiente — e criaria a tentação de commitar
uma senha de banco de dados sem querer.

Usamos pydantic-settings: ele lê as variáveis do ambiente do processo (ou
de um arquivo `.env`, se existir) e valida os tipos automaticamente. Se uma
variável obrigatória não existir, a aplicação falha ao subir — o que é bom,
porque um erro imediato e claro é sempre melhor que um `None` silencioso
estourando em algum lugar aleatório do código, três camadas depois.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    # String de conexão do SQLAlchemy com o PostgreSQL.
    # Formato: postgresql+psycopg2://usuario:senha@host:porta/nome_do_banco
    # Tem um valor padrão só para facilitar rodar localmente sem Docker;
    # em produção isso é sempre sobrescrito pela variável de ambiente real.
    database_url: str = "postgresql+psycopg2://kanban:kanban@localhost:5432/kanban"

    # Chave usada para assinar o cookie de sessão do login (ver app/auth/seguranca.py).
    # É "simples" no sentido da Etapa 1.4 (login simples), mas a assinatura
    # ainda precisa de uma chave secreta — sem ela, qualquer um poderia
    # forjar um cookie de sessão e se passar por outro usuário.
    # NUNCA use o valor padrão abaixo em produção — ele existe só para o
    # ambiente de desenvolvimento funcionar sem configuração extra.
    chave_secreta: str = "chave-de-desenvolvimento-troque-em-producao"

    # Quantos segundos um cookie de sessão de login continua válido.
    # 30 dias — um app pessoal não precisa reautenticar toda hora.
    duracao_sessao_segundos: int = 60 * 60 * 24 * 30

    # model_config diz ao pydantic-settings para também procurar um arquivo
    # `.env` na raiz do backend, além das variáveis de ambiente reais do
    # sistema operacional. Isso facilita o desenvolvimento local: em vez de
    # exportar variáveis no terminal toda vez, você cria um `.env` (a partir
    # do `.env.example`) e ele é lido automaticamente.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instância única, importada pelo resto da aplicação.
# Criar isso uma vez só (em vez de instanciar Configuracoes() em cada
# arquivo que precisa dela) evita reler e revalidar as variáveis de
# ambiente repetidamente, e garante que todo mundo enxerga os mesmos valores.
configuracoes = Configuracoes()
