# Changelog

Todas as mudanças notáveis deste projeto são registradas aqui. O formato segue, livremente, o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/); as datas usam AAAA-MM-DD.

Cada entrada referencia a seção da documentação (`docs/documentacao.md`) que motivou a mudança — é assim que se decide, olhando este arquivo, se uma alteração no código foi consequência de uma etapa já escrita ou uma decisão nova que ainda precisa ser documentada.

## [Não lançado]

Nada pendente no momento. Próximo passo natural: escrever a Etapa 3 (ordenação por indexação fracionária) e substituir o `Float` provisório de `posicao` pelo esquema definitivo.

## [0.1.0] - 2026-08-03

Estrutura inicial do projeto, implementando o que as Etapas 1 e 2 da documentação já haviam decidido.

### Adicionado — backend

- Estrutura de pastas do backend (`backend/app/{modelos,schemas,auth,rotas}`), seguindo o esqueleto da Etapa 1.6.
- Modelos SQLAlchemy `Usuario`, `Quadro`, `Lista`, `Cartao`, implementando o desenho de entidades da Etapa 2.5 — incluindo a decisão central da Etapa 2.3 ("o estado do cartão é a lista onde ele está", sem campo `status`).
- Campo `arquivado` adicionado ao modelo `Lista` (não estava no diagrama da Etapa 2.5, mas é exigido pelo comportamento descrito na Etapa 2.7 — "arquivar a lista arquiva os cartões dentro dela").
- Campo `posicao` (`Lista` e `Cartao`) implementado como `Float`, explicitamente provisório: o tipo definitivo é decisão da Etapa 3, ainda não escrita.
- Campos `prazo` e `aviso_previo_minutos` no modelo `Cartao` (Etapa 2.5), sem nenhuma regra de negócio associada ainda — armazenamento apenas, a lógica é da Etapa 4.
- Soft delete (`arquivado`) em `Lista` e `Cartao`, nunca exclusão real — Etapa 2.7.
- Schemas Pydantic de criação, atualização e leitura para as quatro entidades, incluindo um schema dedicado (`CartaoMover`) para a operação de mover cartão entre listas, separada da edição de conteúdo.
- Autenticação simples por sessão (Etapa 1.4): cadastro, login e logout com cookie assinado (`itsdangerous`) e senha com hash `bcrypt`.
- Rotas REST completas para quadro, lista e cartão, todas respeitando a fronteira "um usuário não alcança quadro de outro" (Etapa 2.8) — devolvendo 404, não 403, para não vazar a existência de recursos de outros usuários.
- Rota dedicada de arquivar lista, que arquiva em cascata os cartões dentro dela (Etapa 2.7).
- Suíte de testes (`pytest`, contra SQLite em memória) cobrindo, um a um, os sete itens do checklist da Etapa 2.8.
- Configuração via variável de ambiente (`pydantic-settings`), conexão com PostgreSQL via SQLAlchemy, migrações com Alembic, `Dockerfile` e `requirements.txt`.

### Adicionado — frontend

- Esqueleto mínimo com Vite + React + TypeScript (Etapa 1.5), sem nenhuma tela de kanban — só o ferramental, mais uma página de verificação que confirma a conexão com o backend via proxy.
- Deliberadamente **sem** `manifest.json` e sem service worker: tornar o app instalável (PWA) é conteúdo da Etapa 7, ainda não escrita.

### Adicionado — projeto

- `docs/documentacao.md`: a documentação recebida do usuário, persistida no repositório (referenciada pela própria estrutura de pastas da Etapa 1.6).
- `docker-compose.yml` orquestrando banco de dados (PostgreSQL) e API.
- `README.md` com instruções de execução (local, testes, Docker, frontend).
- Este `CHANGELOG.md`.

### Decisões registradas nesta etapa (não estão na documentação ainda)

- Hash de senha com a biblioteca `bcrypt` diretamente, em vez de `passlib` (comum em tutoriais) — `passlib` está sem manutenção ativa e quebrou com a versão atual do `bcrypt` durante os testes deste scaffold.
- Exclusão de quadro é destrutiva de verdade (cascade sobre listas e cartões), diferente da regra de arquivar de lista/cartão (Etapa 2.7) — por ser uma ação rara e deliberada, não o "excluir" do dia a dia que precisa ser perdoável.
- Mover um cartão entre listas só é permitido dentro do mesmo quadro — mover entre quadros diferentes não é uma operação descrita na documentação, então não foi inventada aqui.
