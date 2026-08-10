# Kanban com tempo

App de tarefas em formato kanban com uma dimensão a mais que o kanban clássico não tem: **tempo** (prazo no cartão e aviso de vencimento). Projeto pessoal, para uma usuária real e específica — não um produto de mercado.

A documentação completa (visão, domínio, decisões de arquitetura, e o plano de etapas) está em [`docs/documentacao.md`](docs/documentacao.md). Leia-a antes de mexer em qualquer coisa aqui: cada decisão de código deste repositório existe porque uma seção específica daquele documento pediu por ela — os comentários no código apontam de volta para a etapa correspondente.

## Estado atual

Implementadas: **Etapa 1** (visão, domínio e escopo), **Etapa 2** (o modelo kanban — quadro, lista, cartão), **Etapa 3** (ordenação por indexação fracionária), **Etapa 4** (a dimensão tempo — prazo, aviso prévio e calendário) e **Etapa 5** (notificações via Web Push). Isso significa que hoje existem:

- A API (backend/) com CRUD completo de quadro, lista e cartão, login simples por sessão, e a fronteira de posse entre usuários.
- Ordenação de listas e cartões por indexação fracionária (Etapa 3): o campo `posicao` é `NUMERIC` (Decimal), calculado sempre a partir de vizinhos por `backend/app/servicos/ordenacao.py` — nunca um número escolhido pelo cliente. Criar uma lista/cartão sempre anexa no final; reordenar é feito pelas rotas `POST .../mover`, que recebem os ids dos vizinhos onde o item foi solto, não uma posição pronta.
- A dimensão tempo (Etapa 4): o cartão ganhou `prazo` (quando vence), `aviso_previo` (duração `INTERVAL`, quanto tempo antes avisar), `notificar_em` (o instante do disparo, `prazo - aviso_previo`, já calculado) e `notificado`. Mudar `prazo` ou `aviso_previo` recalcula `notificar_em` e reseta `notificado` — regra isolada em `backend/app/servicos/prazos.py`. A rota `GET /calendario` é a "lente": os mesmos cartões, filtrados por prazo, atravessando todos os quadros do usuário.
- O worker de notificação (Etapa 5, `backend/worker/`): um processo separado da API que acorda a cada minuto, seleciona cartões com `notificar_em` vencido e `notificado = false`, e envia via Web Push (`pywebpush`/VAPID) para todas as assinaturas do usuário (`AssinaturaPush`, gerenciadas pelas rotas `/assinaturas-push`). Marca `notificado` só depois do envio bem-sucedido ("pelo menos uma vez", nunca "no máximo uma vez" — Etapa 5.4), remove assinaturas expiradas (404/410), e ignora avisos atrasados há mais de 24h.
- Um esqueleto mínimo de frontend (Vite + React + TypeScript), só com o ferramental — nenhuma tela de kanban foi desenhada ainda. O service worker que de fato recebe o push (`frontend/src/sw.ts`) ainda não existe — é conteúdo da Etapa 7.

Ainda **não** existem: WebSocket/tempo real, service worker / PWA instalável. Essas pastas (`backend/app/realtime/`, `frontend/src/sw.ts`) só nascem quando as etapas correspondentes da documentação forem escritas — ver a regra "pasta nasce quando o código nasce" na seção 1.6 da documentação.

Veja o [`CHANGELOG.md`](CHANGELOG.md) para o histórico detalhado do que foi feito.

## Estrutura

```
backend/
  app/      A API em FastAPI
  worker/   O processo de notificação (Etapa 5), separado da API
frontend/   Cliente web em React + TypeScript (Vite), instalável como PWA no futuro
docs/       A documentação do projeto, escrita por etapas
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

Ele acorda a cada 60 segundos, procura cartões vencidos e tenta notificar. Sem `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` configuradas no `.env` (ver `backend/.env.example` para como gerar o par), o worker continua rodando normalmente — só o envio de push de verdade fica desativado.

### Testes

```bash
cd backend
pytest -v
```

Os testes rodam contra um SQLite em memória (não precisam do Postgres no ar). `test_modelo_kanban.py` e `test_ordenacao.py` cobrem os checklists completos das Etapas 2.8 e 3.9; `test_dimensao_tempo.py` (Etapa 4) e `test_worker.py` (Etapa 5) cobrem os itens de maior valor dos respectivos checklists — em especial o teste que fecha o bug silencioso da 4.3 (adiar um cartão já notificado precisa resetar `notificado`) e o teste de assinatura da 5.10 (rodar o worker duas vezes seguidas não notifica de novo). `test_worker.py` isola o envio atrás de um dublê (`EnviadorFalso`) — nenhum teste fala com um serviço de push de verdade. O teste de assinatura da Etapa 3 — cinquenta inserções consecutivas no mesmo ponto sem colapso de precisão — roda contra `Decimal` puro, sem banco nenhum envolvido.

## Rodando com Docker Compose

Sobe o Postgres, a API e o worker juntos:

```bash
docker compose up --build
```

Para o envio de push funcionar de verdade dentro do compose, exporte `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`/`VAPID_SUBJECT` no seu shell antes de subir (ver `backend/.env.example` para como gerar o par) — sem elas, os três serviços sobem normalmente, só o envio fica desativado.

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

Sobe em `http://localhost:5173`. As chamadas para `/api/*` são redirecionadas para o backend em `http://localhost:8000` pelo proxy configurado em `frontend/vite.config.ts` — suba o backend também para a página parar de mostrar "Backend: inacessível".
