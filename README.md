# Kanban com tempo

App de tarefas em formato kanban com uma dimensão a mais que o kanban clássico não tem: **tempo** (prazo no cartão e aviso de vencimento). Projeto pessoal, para uma usuária real e específica — não um produto de mercado.

A documentação completa (visão, domínio, decisões de arquitetura, e o plano de etapas) está em [`docs/documentacao.md`](docs/documentacao.md). Leia-a antes de mexer em qualquer coisa aqui: cada decisão de código deste repositório existe porque uma seção específica daquele documento pediu por ela — os comentários no código apontam de volta para a etapa correspondente.

## Estado atual

Implementadas: **Etapa 1** (visão, domínio e escopo), **Etapa 2** (o modelo kanban — quadro, lista, cartão), **Etapa 3** (ordenação por indexação fracionária), **Etapa 4** (a dimensão tempo — prazo, aviso prévio e calendário), **Etapa 5** (notificações via Web Push) e **Etapa 6** (tempo real — só o lado de servidor, ver a ressalva abaixo). Isso significa que hoje existem:

- A API (backend/) com CRUD completo de quadro, lista e cartão, login simples por sessão, e a fronteira de posse entre usuários.
- Ordenação de listas e cartões por indexação fracionária (Etapa 3): o campo `posicao` é `NUMERIC` (Decimal), calculado sempre a partir de vizinhos por `backend/app/servicos/ordenacao.py` — nunca um número escolhido pelo cliente. Criar uma lista/cartão sempre anexa no final; reordenar é feito pelas rotas `POST .../mover`, que recebem os ids dos vizinhos onde o item foi solto, não uma posição pronta.
- A dimensão tempo (Etapa 4): o cartão ganhou `prazo` (quando vence), `aviso_previo` (duração `INTERVAL`, quanto tempo antes avisar), `notificar_em` (o instante do disparo, `prazo - aviso_previo`, já calculado) e `notificado`. Mudar `prazo` ou `aviso_previo` recalcula `notificar_em` e reseta `notificado` — regra isolada em `backend/app/servicos/prazos.py`. A rota `GET /calendario` é a "lente": os mesmos cartões, filtrados por prazo, atravessando todos os quadros do usuário.
- O worker de notificação (Etapa 5, `backend/worker/`): um processo separado da API que acorda a cada minuto, seleciona cartões com `notificar_em` vencido e `notificado = false`, e envia via Web Push (`pywebpush`/VAPID) para todas as assinaturas do usuário (`AssinaturaPush`, gerenciadas pelas rotas `/assinaturas-push`). Marca `notificado` só depois do envio bem-sucedido ("pelo menos uma vez", nunca "no máximo uma vez" — Etapa 5.4), remove assinaturas expiradas (404/410), e ignora avisos atrasados há mais de 24h.
- Tempo real no servidor (Etapa 6, `backend/app/realtime/`): WebSocket por quadro (`GET /ws/quadros/{id}`) com salas em memória — toda escrita de lista/cartão transmite um evento só para quem está conectado àquele quadro, carregando o id de conexão de origem (para uma futura supressão de eco). O worker publica nesse canal via uma ponte HTTP interna (`POST /interno/eventos-tempo-real`, `backend/worker/tempo_real.py`) — necessária porque o worker é um processo à parte da API (Etapa 5.2) e as salas vivem só na memória do processo da API (Etapa 6.5).
- **O quadro kanban de verdade** (`frontend/src/paginas/QuadroKanban.tsx`): colunas e cartões vindos da API, arrastar-e-soltar entre listas com [`@dnd-kit`](https://dndkit.com/), e atualização otimista (Etapa 6.6) — o cartão se move na tela na hora, a escrita na API acontece depois, e uma falha reverte recarregando o quadro. Tema escuro, cores desaturadas por acento de coluna, e uma animação curta ao segurar (leve escala/rotação/brilho) e ao soltar (um pulso rápido no cartão). O cliente ainda **não abre WebSocket nenhum** — não recebe mudanças de outra aba/dispositivo em tempo real; isso, a supressão de eco e a reconexão (Etapa 6.7/6.8) continuam pendentes (ver `docs/documentacao.md`, seção 6.13).
- Login simples (`frontend/src/paginas/TelaLogin.tsx`) e o resto do ferramental (Vite + React + TypeScript). O service worker que recebe push (`frontend/src/sw.ts`) ainda não existe — é conteúdo da Etapa 7, junto com o PWA instalável.

Ainda **não** existem: cliente WebSocket, service worker / PWA instalável, calendário no frontend. `frontend/src/sw.ts` só nasce quando a etapa correspondente da documentação for escrita — ver a regra "pasta nasce quando o código nasce" na seção 1.6 da documentação.

Veja o [`CHANGELOG.md`](CHANGELOG.md) para o histórico detalhado do que foi feito.

## Estrutura

```
backend/
  app/
    realtime/     Salas de WebSocket por quadro (Etapa 6)
    ...           Resto da API em FastAPI
  worker/         O processo de notificação (Etapa 5), separado da API
frontend/
  src/
    api/          Tipos + cliente HTTP fino para a API
    componentes/  Cartão, coluna
    paginas/      Login, o quadro kanban
    estilos/      CSS (tema escuro, animações de arrastar)
docs/             A documentação do projeto, escrita por etapas
```

## Rodando o backend localmente (sem Docker)

Requer Python 3.12+ e um PostgreSQL acessível (ou use o `docker-compose.yml` só para o banco — veja abaixo).

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
copy .env.example .env   # ajuste DATABASE_URL e CHAVE_SECRETA se precisar
```

Aplicar as migrações (com o Postgres já rodando):

```bash
alembic revision --autogenerate -m "schema inicial"
alembic upgrade head
```

Subir a API:

```bash
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. `http://localhost:8000/docs` tem a documentação interativa (Swagger), gerada automaticamente pelo FastAPI a partir das rotas e schemas.

### Rodando o worker (Etapa 5)

Em outro terminal, com o `.venv` já ativado e o Postgres no ar:

```bash
cd backend
python -m worker
```

Ele acorda a cada 60 segundos, procura cartões vencidos e tenta notificar. Sem `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` configuradas no `.env` (ver `backend/.env.example` para como gerar o par), o worker continua rodando normalmente — só o envio de push de verdade fica desativado. Depois de notificar, ele também tenta avisar o canal em tempo real (Etapa 6.5/`worker/tempo_real.py`) via `POST /interno/eventos-tempo-real` na API — best-effort: se a API estiver fora do ar ou `CHAVE_INTERNA` divergir entre os dois processos, o worker segue normalmente, só sem o aviso in-app.

### Testes

```bash
cd backend
pytest -v
```

Os testes rodam contra um SQLite em memória (não precisam do Postgres no ar). `test_modelo_kanban.py` e `test_ordenacao.py` cobrem os checklists completos das Etapas 2.8 e 3.9; `test_dimensao_tempo.py` (Etapa 4), `test_worker.py` (Etapa 5) e `test_realtime.py` (Etapa 6) cobrem os itens de maior valor dos respectivos checklists — em especial o teste que fecha o bug silencioso da 4.3 (adiar um cartão já notificado precisa resetar `notificado`), o teste de assinatura da 5.10 (rodar o worker duas vezes seguidas não notifica de novo), e a prova de isolamento de salas da 6.10 (um quadro nunca recebe evento de outro). `test_worker.py` isola o envio atrás de um dublê (`EnviadorFalso`) — nenhum teste fala com um serviço de push de verdade, nem com a ponte de tempo real. `test_realtime.py` usa `TestClient.websocket_connect` para abrir conexões WebSocket de verdade contra a aplicação, sem precisar de um servidor rodando à parte. O teste de assinatura da Etapa 3 — cinquenta inserções consecutivas no mesmo ponto sem colapso de precisão — roda contra `Decimal` puro, sem banco nenhum envolvido.

## Rodando com Docker Compose

Sobe o Postgres, a API e o worker juntos:

```bash
docker compose up --build
```

Para o envio de push funcionar de verdade dentro do compose, exporte `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`/`VAPID_SUBJECT` no seu shell antes de subir (ver `backend/.env.example` para como gerar o par) — sem elas, os três serviços sobem normalmente, só o envio fica desativado. `CHAVE_INTERNA` (a ponte do worker até o canal em tempo real da API, Etapa 6.5) já vem com o mesmo valor fixo nos dois serviços no `docker-compose.yml`; só precisa ser trocada se você mudar uma cópia sem mudar a outra.

Na primeira vez, aplique as migrações dentro do container da API (em outro terminal, com os serviços já no ar):

```bash
docker compose exec api alembic revision --autogenerate -m "schema inicial"
docker compose exec api alembic upgrade head
```

## Rodando o frontend

```bash
cd frontend
npm install
npm run dev
```

Sobe em `http://localhost:5173`. As chamadas para `/api/*` são redirecionadas para o backend em `http://localhost:8000` pelo proxy configurado em `frontend/vite.config.ts` — suba o backend também (e o Postgres, ver acima) antes de abrir a página. Crie uma conta na própria tela de login (não há usuária de teste pré-cadastrada); o primeiro quadro também se cria pela interface, se você ainda não tiver um.
