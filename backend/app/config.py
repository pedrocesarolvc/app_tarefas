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

    # --- VAPID (Etapa 5.5) ---
    # O par de chaves que identifica ESTE servidor perante o serviço de
    # push (Google, no Chrome) — é o que impede qualquer um de mandar
    # notificação em nome do app. A pública vai para o frontend (usada ao
    # criar uma assinatura); a privada assina os envios do worker
    # (backend/worker/push.py) e nunca deve sair do backend.
    #
    # Sem valor padrão de propósito — diferente de `chave_secreta` acima,
    # não existe uma chave VAPID "de desenvolvimento" plausível: ou o par
    # é gerado de verdade (ver backend/.env.example), ou o envio de push
    # simplesmente não funciona. O resto da aplicação continua de pé sem
    # elas — só o worker fica sem conseguir enviar (mas ainda marca
    # avisos atrasados corretamente e não quebra).
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    # O "claim" `sub` exigido pelo protocolo VAPID — um contato (e-mail ou
    # URL) que o serviço de push pode usar para falar com o dono do
    # servidor em caso de abuso. Tem um valor padrão inofensivo porque,
    # ao contrário das chaves, não é secreto nem impede nada de subir.
    vapid_subject: str = "mailto:contato@example.com"

    # --- Ponte worker → tempo real (Etapa 6.5) ---
    # As salas de WebSocket vivem na memória do processo da API (Etapa
    # 6.5) -- e o worker (Etapa 5.2) é, por desenho, um processo à parte.
    # Ele não enxerga esse dicionário em memória de jeito nenhum; a única
    # forma de "o worker notificou um cartão" virar um evento na sala do
    # quadro é o worker chamar de volta a própria API por HTTP (ver
    # backend/worker/tempo_real.py e a rota interna em
    # app/rotas/realtime.py). `chave_interna` é um segredo simples
    # compartilhado entre os dois processos só para essa chamada não
    # aceitar qualquer requisição de qualquer origem -- reaproveita
    # `chave_secreta` como valor padrão de desenvolvimento para não exigir
    # mais uma variável de ambiente só para isso.
    url_api_interna: str = "http://localhost:8000"
    chave_interna: str = "chave-de-desenvolvimento-troque-em-producao"

    # --- CORS (Etapa 7.5) ---
    # Em desenvolvimento, o frontend nunca precisa disso: o proxy do Vite
    # (frontend/vite.config.ts) faz o navegador enxergar tudo como uma
    # origem só. Mas a Etapa 7.5 já antecipa a entrega de verdade: "o mais
    # simples é publicar [o frontend] num serviço de hospedagem estática
    # apontando para a API" -- nesse cenário, frontend e API moram em
    # origens diferentes de verdade, e o navegador bloqueia a chamada sem
    # essa autorização explícita.
    #
    # Uma string separada por vírgulas, não uma lista -- variável de
    # ambiente é sempre texto, e uma lista exigiria um formato (JSON?
    # vírgula?) que só complicaria o .env sem necessidade; a conversão
    # para lista acontece em app/main.py, no único lugar que precisa dela.
    #
    # allow_credentials=True (main.py) é obrigatório porque o login desta
    # aplicação é cookie de sessão (Etapa 1.4) -- e o CORS do navegador
    # proíbe combinar allow_credentials com "qualquer origem" (*); por
    # isso a lista precisa ser explícita, nunca um curinga.
    origens_permitidas_cors: str = "http://localhost:5173"

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
