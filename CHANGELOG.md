# Changelog

Todas as mudanças notáveis deste projeto são registradas aqui. O formato segue, livremente, o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/); as datas usam AAAA-MM-DD.

Cada entrada referencia a seção da documentação (`docs/documentacao.md`) que motivou a mudança — é assim que se decide, olhando este arquivo, se uma alteração no código foi consequência de uma etapa já escrita ou uma decisão nova que ainda precisa ser documentada.

## [Não lançado]

Nada pendente no momento. Próximo passo natural: escrever a Etapa 6 (tempo real — WebSocket e atualização otimista).

## [0.4.0] - 2026-08-10

Implementa a Etapa 5 (notificações): o worker separado da API, a entidade de assinatura de Web Push, e o laço idempotente que dispara os avisos.

### Adicionado

- `AssinaturaPush` (`backend/app/modelos/assinatura_push.py`): `usuario_id`, `endpoint` (único), `chave_p256dh`, `chave_auth` — Etapa 5.6. `Usuario.assinaturas_push` com o mesmo cascade de `Usuario.quadros`.
- Rotas `backend/app/rotas/assinaturas_push.py`: `GET /assinaturas-push/chave-publica` (a chave pública VAPID, sem exigir login — não é secreta), `POST /assinaturas-push` (registra; reatribui o endpoint ao usuário atual se ele já existir), `GET /assinaturas-push` e `DELETE /assinaturas-push/{id}` (com a mesma fronteira de posse 404 do resto da API).
- `backend/worker/` (processo novo, separado da API — Etapa 5.2): `push.py` isola `pywebpush`/VAPID atrás de `enviar_notificacao` e `AssinaturaExpiradaError`; `agendador.py` tem `executar_ciclo`, a função testável que seleciona cartões pendentes, envia para todas as assinaturas do usuário, marca `notificado` só depois do envio bem-sucedido (Etapa 5.4: "pelo menos uma vez"), ignora avisos atrasados há mais de 24h (Etapa 5.3), e apaga assinaturas que respondem 404/410; `__main__.py` é o laço "acorda, consulta, envia, dorme" (`python -m worker`, 60s de intervalo).
- Chaves `vapid_public_key`/`vapid_private_key`/`vapid_subject` em `app/config.py`, sem valor padrão para as duas primeiras — sem elas o worker roda normalmente, só o envio de verdade fica desativado.
- Serviço `worker` no `docker-compose.yml`: mesma imagem da API, `command` diferente, sem `ports` (não responde requisição nenhuma — Etapa 5.2).
- `backend/tests/test_worker.py` (7 testes, cobrindo o checklist 5.10 completo, com um dublê `EnviadorFalso` no lugar de `pywebpush`) e `backend/tests/test_assinaturas_push.py` (2 testes do contrato da API).
- `TZDateTime` (`app/database.py`): um `TypeDecorator` sobre `DateTime(timezone=True)` que reattacha `tzinfo=UTC` quando ausente, na gravação e na leitura. Motivo: o SQLite dos testes devolve datetimes sem fuso mesmo para colunas gravadas como aware, e a subtração `agora - cartao.notificar_em` do worker (Etapa 5.3) estourava `TypeError` contra o banco de teste — o PostgreSQL de produção não tem esse problema (é aware nos dois lados), mas o tipo precisava existir para os testes exercitarem o código de verdade. Todos os `DateTime(timezone=True)` dos cinco modelos foram trocados por ele; como efeito colateral, o workaround manual que os testes da Etapa 4 tinham para essa mesma inconsistência (`_sem_fuso`) foi removido — não é mais necessário.

### Decisões registradas nesta etapa (não estão na documentação ainda)

- Usuário sem nenhuma assinatura: `executar_ciclo` marca o cartão como `notificado` mesmo sem enviar nada (Etapa 5.9: "degrada para aviso in-app apenas"). Não há por que tentar de novo indefinidamente por uma assinatura que pode nunca chegar a existir.
- Cartão com várias assinaturas: `notificado` vira `true` se PELO MENOS UMA tiver sucesso — não é preciso que todos os dispositivos recebam para o cartão ser considerado notificado. A documentação da Etapa 5 não cobre esse caso de parcial sucesso explicitamente; essa foi a leitura mais consistente com "pelo menos uma vez" (5.4) aplicada por usuário, não por dispositivo.
- `POST /assinaturas-push` reatribui (upsert) em vez de rejeitar um `endpoint` já existente — cobre o caso real de duas contas no mesmo navegador sem cancelar a assinatura anterior.

## [0.3.0] - 2026-08-10

Implementa a Etapa 4 (a dimensão tempo): os campos que fazem deste um kanban "com tempo", e a lente do calendário.

### Adicionado

- `Cartao.notificar_em` (`DateTime(timezone=True)`, nullable) e `Cartao.notificado` (`Boolean`, default `False`) — os dois campos novos da Etapa 4.2/4.3.
- `backend/app/servicos/prazos.py`: `calcular_notificar_em(prazo, aviso_previo)` e `aplicar_edicao_de_cartao(cartao, campos_alterados)`, isolando a regra da Etapa 4.3 — mudar `prazo` ou `aviso_previo` recalcula `notificar_em` e reseta `notificado` para `False`, mesmo que o cartão já tivesse sido notificado.
- Rota `GET /calendario` (`backend/app/rotas/calendario.py`): os cartões do usuário com `prazo` num intervalo `de`/`ate`, atravessando todos os quadros dele (filtro opcional por `quadro_id`) — a "lente" da Etapa 4.5, sem tabela nova.
- `backend/tests/test_dimensao_tempo.py`: quatro testes, não os nove do checklist 4.8 completo — a pedido explícito, cobrindo só os de maior valor (cartão sem prazo, cálculo de `notificar_em` na criação, o reset de `notificado` ao adiar um prazo já notificado, e o contrato do calendário — período, cross-quadro, arquivados — num único teste).

### Alterado

- `Cartao.aviso_previo_minutos` (`Integer`) virou `Cartao.aviso_previo` (`Interval`/`timedelta`, Etapa 4.2) — `INTERVAL` nativo do PostgreSQL, não mais um inteiro de minutos escolhido por falta de tipo melhor. Refletido em `CartaoCriar`, `CartaoAtualizar` e `CartaoLeitura`.
- `criar_cartao` e `atualizar_cartao` (`backend/app/rotas/cartoes.py`) passaram a calcular `notificar_em` via o serviço em vez de só guardar `prazo`/`aviso_previo` como campos soltos; `atualizar_cartao` trocou o `setattr` genérico por `aplicar_edicao_de_cartao`.
- `main.py`: registra o roteador do calendário; descrição da API atualizada para refletir as Etapas 1-4.

### Decisões registradas nesta etapa (não estão na documentação ainda)

- O teste de `notificar_em`/`notificado` simula "cartão já notificado" escrevendo direto no banco de teste (`sessao_bruta`), já que nenhuma rota grava `notificado=True` ainda — isso só existe quando o worker da Etapa 5 for escrito.
- Nos testes (SQLite em memória), um `DateTime(timezone=True)` volta do banco sem `tzinfo`, embora represente o mesmo instante — particularidade do SQLite, não do comportamento da API contra PostgreSQL de verdade. As comparações de data nos testes normalizam isso; não é um ajuste no código de produção.

## [0.2.0] - 2026-08-10

Implementa a Etapa 3 (ordenação por indexação fracionária), substituindo o `Float` provisório da Etapa 2 pelo esquema definitivo.

### Adicionado

- `backend/app/servicos/ordenacao.py`: o único lugar do sistema que calcula uma posição (`calcular_posicao`), cobrindo os quatro casos da Etapa 3 (lista vazia, topo, fim, entre dois vizinhos). O cálculo do ponto médio roda num `decimal.localcontext` com 200 dígitos de precisão — o padrão do Python (28 dígitos) não é de fato "arbitrário" como o `NUMERIC` do PostgreSQL, e bisecções sucessivas no mesmo ponto reintroduziriam a própria armadilha da Etapa 3.4 um nível abaixo, dentro do cálculo em Python, se a precisão não fosse elevada explicitamente.
- `PosicaoInvalidaError`: erro dedicado para quando `anterior`/`posterior` chegam fora de ordem a `calcular_posicao` — as rotas convertem para 400.
- `ListaMover` e a rota `POST /quadros/{quadro_id}/listas/{lista_id}/mover`: reordena colunas por vizinhos (`lista_anterior_id`/`lista_posterior_id`), não por número.
- `CartaoMover` redesenhado: `nova_posicao` (Etapa 2) deu lugar a `cartao_anterior_id`/`cartao_posterior_id` — a posição no destino é sempre recalculada a partir dos vizinhos de lá, nunca recebida pronta do cliente.
- Testes da Etapa 3 (`backend/tests/test_ordenacao.py`), cobrindo os oito itens do checklist 3.9 — incluindo o teste de assinatura da etapa (cinquenta inserções consecutivas no mesmo ponto sem colapso de precisão), que roda contra `Decimal` puro, sem banco.
- Fixture `sessao_bruta` em `backend/tests/conftest.py`: acesso direto ao banco de teste, usado só para forçar duas posições idênticas e testar o desempate por `id` (Etapa 3.8) — algo que a API sozinha nunca produz.

### Alterado

- `Lista.posicao` e `Cartao.posicao`: de `Float` para `Numeric` (sem precisão/escala definidas — `NUMERIC` de precisão arbitrária no PostgreSQL). Os schemas de leitura (`ListaLeitura`, `CartaoLeitura`) agora expõem `Decimal`, não `float`.
- `ListaCriar` e `CartaoCriar` perderam o campo `posicao`: criar uma lista ou cartão agora sempre anexa ao final (o caso de borda "soltar no fim" da Etapa 3.7) — a rota calcula a posição chamando o serviço, o cliente não envia mais um número escolhido por conta própria.
- Toda consulta que ordena por `posicao` (relacionamentos `Quadro.listas`, `Lista.cartoes`, e as rotas `listar_listas`/`listar_cartoes`) passou a desempatar por `id` (Etapa 3.8: "nunca ordene só por posição").
- Testes da Etapa 2 (`backend/tests/test_modelo_kanban.py`) ajustados ao novo contrato: nenhuma criação informa `posicao` mais; o teste "listas voltam na ordem definida por posicao" agora cria fora de ordem e usa a rota `mover_lista` para corrigir, em vez de informar posições arbitrárias.

### Decisões registradas nesta etapa (não estão na documentação ainda)

- Mover um cartão dentro da MESMA lista (reordenar sem trocar de coluna) usa a mesma rota `POST .../mover`, passando o próprio `lista_id` atual como destino — a documentação da Etapa 3 não distingue os dois casos, e tratá-los com o mesmo endpoint evitou duplicar a lógica de cálculo de vizinhos.
- A posição do "último item visível" (usada para decidir onde anexar uma criação) ignora itens arquivados — um cartão/lista arquivado não deveria empurrar a posição de itens novos, mesmo continuando no banco (Etapa 2.7).

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
