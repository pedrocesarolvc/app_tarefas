# Kanban com tempo

App de tarefas em formato kanban com uma dimensão a mais que o kanban clássico não tem: **tempo** (prazo no cartão e aviso de vencimento). Projeto pessoal, para uma usuária real e específica — não um produto de mercado.

A documentação completa (visão, domínio, decisões de arquitetura, e o plano de etapas) está em [`docs/documentacao.md`](docs/documentacao.md). Leia-a antes de mexer em qualquer coisa aqui: cada decisão de código deste repositório existe porque uma seção específica daquele documento pediu por ela — os comentários no código apontam de volta para a etapa correspondente.

## Como usar — passo a passo

### 1. Subir tudo

O caminho mais curto é o Docker Compose (sobe banco, API e worker juntos):

```bash
docker compose up --build
```

Na primeira vez, aplique as migrações (em outro terminal, com os serviços já no ar):

```bash
docker compose exec api alembic revision --autogenerate -m "schema inicial"
docker compose exec api alembic upgrade head
```

Depois, o frontend (fora do Docker — ver "Rodando o frontend" mais abaixo):

```bash
cd frontend
npm install
npm run dev
```

Sem Docker instalado, dá para rodar tudo local (Python + PostgreSQL + Node) — o passo a passo completo está nas seções "Rodando o backend localmente", "Rodando o worker" e "Rodando o frontend" logo abaixo.

### 2. Abrir o app e criar sua conta

Acesse `http://localhost:5173`. Não existe usuária de teste pré-cadastrada — na própria tela de login, clique em **"Ainda não tenho conta"**, preencha e-mail e senha (mínimo 8 caracteres) e clique em **"Criar conta e entrar"**. Da próxima vez, é só entrar normalmente com esse e-mail e senha.

### 3. Criar seu primeiro quadro

Sem nenhum quadro ainda, o app pede um nome (ex.: "Casa", "Faculdade") e um clique em **"Criar"**. Um quadro é um contexto de organização — pode criar quantos quiser depois, trocando entre eles pelo seletor no cabeçalho.

### 4. Criar listas (as colunas)

No fim da fileira de colunas, clique em **"+ Nova lista"**, digite um nome (ex.: "A fazer", "Fazendo", "Pronto" — mas o nome é livre, o app não tem estados fixos) e aperte Enter.

### 5. Criar cartões (as tarefas)

Dentro de uma coluna, clique em **"+ Adicionar cartão"**, digite o título e aperte Enter. Não pede prazo — a maioria dos cartões não vai ter um, e está tudo bem.

### 6. Arrastar cartões entre colunas

Clique e segure um cartão, arraste para outra coluna (ou para outra posição na mesma coluna) e solte. A mudança já aparece na tela na hora; um pulso rápido marca onde o cartão pousou.

### 7. Definir prazo e aviso prévio (opcional)

Clique no cartão (sem arrastar) para abrir o detalhe. Título e descrição são editáveis; o campo **Prazo** é opcional e tem um botão **"Remover"** quando preenchido. Só depois de definir um prazo aparece o campo **Avisar**, com opções como "15 minutos antes", "1 hora antes", "1 dia antes". Clique em **Salvar**.

### 8. Ver o calendário

O botão **"Calendário"** no cabeçalho troca a visão do quadro por uma agenda dos próximos 30 dias, com todos os cartões que têm prazo — de todos os seus quadros, não só o que está aberto. Sem nenhum cartão com data no período, a tela diz isso explicitamente (não é bug).

### 9. Receber avisos

O sino 🔔 no cabeçalho guarda os avisos que chegaram durante a sessão atual, entregues em tempo real assim que o worker notifica um cartão (não precisa recarregar a página). Para notificação push de verdade — com o app fechado, no celular — veja a ressalva sobre HTTPS mais abaixo, em "Rodando o frontend".

### 10. Sair

Botão **"Sair"** no cabeçalho, a qualquer momento.

## Estado atual

**Todas as sete etapas da documentação estão implementadas** (`docs/documentacao.md`) — este é o v1 completo. Isso significa que hoje existem:

- A API (backend/) com CRUD completo de quadro, lista e cartão, login simples por sessão, e a fronteira de posse entre usuários.
- Ordenação de listas e cartões por indexação fracionária (Etapa 3): o campo `posicao` é `NUMERIC` (Decimal), calculado sempre a partir de vizinhos por `backend/app/servicos/ordenacao.py` — nunca um número escolhido pelo cliente.
- A dimensão tempo (Etapa 4): `prazo`, `aviso_previo` (`INTERVAL`), `notificar_em` (materializado) e `notificado` no cartão, com a regra de recálculo isolada em `backend/app/servicos/prazos.py`. `GET /calendario` é a "lente" que atravessa quadros.
- O worker de notificação (Etapa 5, `backend/worker/`): processo separado da API, Web Push via `pywebpush`/VAPID, idempotente ("pelo menos uma vez", nunca duplicado — Etapa 5.4).
- Tempo real (Etapa 6, `backend/app/realtime/` + `frontend/src/api/tempoReal.ts`): WebSocket por quadro com salas em memória, ponte HTTP do worker até a API (`POST /interno/eventos-tempo-real`), e agora **também o cliente**: reconexão com espera crescente recarregando o quadro (6.8), e supressão do próprio eco pelo id de conexão (6.7).
- **CORS** (Etapa 7.5, `app/main.py`) — configurável via `ORIGENS_PERMITIDAS_CORS`, para quando o frontend for publicado numa origem diferente da API.
- **PWA** (Etapa 7.3): `frontend/public/manifest.json` e `frontend/public/sw.js` — o app instala na tela inicial, e o service worker recebe push com o app fechado e abre no cartão certo ao clicar.
- **As quatro telas do v1** (Etapa 7.4): o quadro (`QuadroKanban.tsx`, arrastar-e-soltar com [`@dnd-kit`](https://dndkit.com/) e atualização otimista — Etapa 6.6), o cartão aberto (`ModalDoCartao.tsx` — prazo opcional e explicitamente não obrigatório, Etapa 4.6), o calendário (`TelaCalendario.tsx`, agenda por dia) e a lista de avisos (`PainelDeAvisos.tsx`, avisos in-app chegando pelo WebSocket).
- Três testes de ponta a ponta (Etapa 7.6, `backend/tests/test_e2e.py`).

O que fica de fora, e por quê, está em `docs/documentacao.md` seção 7.11: HTTPS/túnel/hospedagem são infraestrutura, não código (a fricção mais chata do projeto, nas palavras da própria documentação); o service worker mora em `public/sw.js`, não em `src/sw.ts` como o desenho original previa (ver a seção para o porquê).

Veja o [`CHANGELOG.md`](CHANGELOG.md) para o histórico detalhado do que foi feito.

## Estrutura

```
backend/
  app/
    realtime/     Salas de WebSocket por quadro (Etapa 6)
    ...           Resto da API em FastAPI
  worker/         O processo de notificação (Etapa 5), separado da API
frontend/
  public/         manifest.json, sw.js, ícone -- servidos como estão (Etapa 7.3)
  src/
    api/          Tipos, cliente HTTP e o cliente WebSocket (tempoReal.ts)
    componentes/  Cartão, coluna, modal do cartão, painel de avisos
    paginas/      Login, o quadro kanban, o calendário
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

Os testes rodam contra um SQLite em memória (não precisam do Postgres no ar). `test_modelo_kanban.py` e `test_ordenacao.py` cobrem os checklists completos das Etapas 2.8 e 3.9; `test_dimensao_tempo.py` (Etapa 4), `test_worker.py` (Etapa 5) e `test_realtime.py` (Etapa 6) cobrem os itens de maior valor dos respectivos checklists; `test_e2e.py` (Etapa 7.6) tem os três testes de ponta a ponta — o fluxo completo (criar → mover → confirmar ordem persistida), o ciclo do aviso (API cria o cartão, o worker de verdade notifica, roda de novo e não duplica) e a ordenação sob estresse.

O terceiro merece uma nota: a documentação pede cinquenta inserções consecutivas no mesmo ponto — o teste algorítmico da Etapa 3 (`test_ordenacao.py`) já prova exatamente isso, contra `Decimal` puro. A versão de ponta a ponta em `test_e2e.py` usa 40, porque o SQLite dos testes converte `Decimal` para `float` ao gravar (o `Numeric` genérico do SQLAlchemy nesse dialeto), reintroduzindo a própria armadilha da Etapa 3.4 um nível abaixo, na camada de binding — algo que o PostgreSQL de produção não faz. O comentário no teste detalha a investigação.

`test_worker.py` isola o envio atrás de um dublê (`EnviadorFalso`) — nenhum teste fala com um serviço de push de verdade, nem com a ponte de tempo real. `test_realtime.py` usa `TestClient.websocket_connect` para abrir conexões WebSocket de verdade contra a aplicação, sem precisar de um servidor rodando à parte.

## Rodando com Docker Compose

Sobe o Postgres, a API e o worker juntos:

```bash
docker compose up --build
```

Para o envio de push funcionar de verdade dentro do compose, exporte `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`/`VAPID_SUBJECT` no seu shell antes de subir (ver `backend/.env.example` para como gerar o par) — sem elas, os três serviços sobem normalmente, só o envio fica desativado. `CHAVE_INTERNA` (a ponte do worker até o canal em tempo real da API, Etapa 6.5) já vem com o mesmo valor fixo nos dois serviços no `docker-compose.yml`; só precisa ser trocada se você mudar uma cópia sem mudar a outra. Se o frontend for publicado numa origem diferente da API, exporte `ORIGENS_PERMITIDAS_CORS` com essa URL (Etapa 7.5) — o padrão só cobre `http://localhost:5173`.

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

Sobe em `http://localhost:5173`. As chamadas para `/api/*` (e o WebSocket em `/ws/*`) são redirecionadas para o backend em `http://localhost:8000` pelo proxy configurado em `frontend/vite.config.ts` — suba o backend também (e o Postgres, ver acima) antes de abrir a página. Crie uma conta na própria tela de login (não há usuária de teste pré-cadastrada); o primeiro quadro também se cria pela interface, se você ainda não tiver um.

Notificação push de verdade **não** funciona em `http://localhost` fora do Chrome/Edge de desenvolvimento — Web Push e service worker exigem HTTPS (Etapa 7.3). Testar no celular dela exige um túnel (ngrok, Cloudflare Tunnel) apontando para o frontend, com `ORIGENS_PERMITIDAS_CORS` no backend incluindo a URL do túnel. O resto do app (quadro, arrastar, calendário, avisos in-app pelo WebSocket) funciona normalmente em `localhost`, sem HTTPS nenhum.

## Implantação (produção)

Publicar de verdade — frontend na Vercel, backend (API + worker + Postgres) num servidor próprio — é um cenário diferente do desenvolvimento local acima: exige `VITE_API_URL`, CORS e cookie entre domínios configurados. Passo a passo completo em [`docs/implantacao.md`](docs/implantacao.md).
