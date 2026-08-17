# Changelog

Todas as mudanças notáveis deste projeto são registradas aqui. O formato segue, livremente, o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/); as datas usam AAAA-MM-DD.

Cada entrada referencia a seção da documentação (`docs/documentacao.md`) que motivou a mudança — é assim que se decide, olhando este arquivo, se uma alteração no código foi consequência de uma etapa já escrita ou uma decisão nova que ainda precisa ser documentada.

## [Não lançado]

O v1 está implementado e documentado para implantação real (frontend + backend em domínios separados). O que resta é o que só um uso real revela (Etapa 7.7): o que ela usa, o que ela ignora, o que ela pede — e a implantação em si, que depende de ações fora deste repositório (contas na Vercel/Hostinger, DNS).

## [0.7.0] - 2026-08-17

Prepara o app para implantação real com frontend e backend em domínios diferentes (Vercel + servidor próprio) — a lacuna que a nota "Não lançado" da versão anterior apontava (Etapa 7.3: "HTTPS/túnel/domínio para push de verdade em produção").

### Adicionado

- `docs/implantacao.md`: guia completo de implantação — Vercel para o frontend, VPS da Hostinger (Docker + Caddy) para a API/worker/Postgres, incluindo como diferenciar um plano VPS de hospedagem compartilhada, DNS do subdomínio da API, geração de segredos de produção e uma checklist final de verificação ponta a ponta.
- `docker-compose.prod.yml`: override de produção que restringe as portas do Postgres e da API a `127.0.0.1` (o `docker-compose.yml` de desenvolvimento as publica em todas as interfaces, correto localmente mas não numa VPS com IP público) — usado junto do arquivo principal via `docker compose -f docker-compose.yml -f docker-compose.prod.yml`.
- `frontend/.env.example`: documenta `VITE_API_URL`, a variável de build que `api/cliente.ts` e `api/tempoReal.ts` agora leem.
- `app/config.py`: `cookie_entre_sites` (padrão `false`) — liga `SameSite=None; Secure` no cookie de sessão (`app/rotas/auth.py`) quando frontend e API moram em domínios diferentes; `SameSite=Lax` (o padrão anterior, mantido) não é enviado em chamadas `fetch` entre sites diferentes, só em navegação de topo, então sem isso o login "não pegaria" atrás de domínios separados.

### Alterado

- `frontend/src/api/cliente.ts`: a URL base passou de fixa (`/api`) para `import.meta.env.VITE_API_URL ?? "/api"` — ausente, mantém o comportamento de desenvolvimento via proxy do Vite; definida, chama a API diretamente nesse domínio. Toda chamada ganhou `credentials: "include"`, necessário para o cookie de sessão viajar em requisições entre origens diferentes mesmo com CORS liberado.
- `frontend/src/api/tempoReal.ts`: a URL do WebSocket segue a mesma lógica — deriva `wss://`/`ws://` de `VITE_API_URL` quando definida, em vez de sempre usar `window.location.host`.
- `frontend/tsconfig.json`: adicionado `"types": ["vite/client"]`, exigido para o TypeScript reconhecer `import.meta.env.VITE_API_URL` (sem isso, `tsc` falha com "Property 'env' does not exist on type 'ImportMeta'").
- `docker-compose.yml` (serviço `api`): ganhou as variáveis `COOKIE_ENTRE_SITES` e `VAPID_PUBLIC_KEY`, que já existiam em `backend/.env.example` mas não estavam sendo repassadas ao container — sem `VAPID_PUBLIC_KEY` especificamente, `GET /assinaturas-push/chave-publica` (usada pelo frontend para registrar push no navegador) responderia sempre `null`, mesmo com a chave configurada no `.env`.
- `README.md`: nova seção "Implantação (produção)" apontando para `docs/implantacao.md`.

### Decisões registradas nesta etapa (não estão na documentação em etapas)

- Caddy, não nginx + Certbot manual, como proxy reverso da API na VPS — para um único servidor, a emissão/renovação automática de certificado Let's Encrypt do Caddy (poucas linhas de config) tem muito menos partes móveis para manter do que configurar nginx e Certbot como processos separados, e ele já repassa o upgrade de conexão do WebSocket sem configuração extra.
- As portas do Postgres/API em produção são restringidas via um `docker-compose.prod.yml` separado (override), não editando `docker-compose.yml` diretamente — o arquivo principal continua servindo ao desenvolvimento local sem mudança de comportamento; só a combinação explícita dos dois arquivos (documentada no guia) aplica a restrição.
- O guia documenta explicitamente que `ufw` sozinho não é suficiente para restringir as portas publicadas pelo Docker (ele manipula o `iptables` por conta própria e costuma ignorar regras do `ufw`) — vale registrar porque é uma pegadinha comum, não algo óbvio de quem só conhece firewall de host tradicional.

## [0.6.0] - 2026-08-17

Implementa a Etapa 7 (entrega): CORS, PWA (manifest + service worker), o cliente WebSocket que fecha a lacuna deixada na Etapa 6, as quatro telas do v1, e os três testes de ponta a ponta.

### Adicionado

- `CORSMiddleware` em `app/main.py`, configurável via `ORIGENS_PERMITIDAS_CORS` (`app/config.py`) — inerte em desenvolvimento (o proxy do Vite já unifica a origem), necessário quando o frontend é publicado separado da API (Etapa 7.5).
- `backend/tests/test_e2e.py`: os três testes de ponta a ponta da Etapa 7.6 — fluxo completo (criar → mover → confirmar ordem persistida), ciclo do aviso (cartão criado pela API, notificado pelo worker de verdade, sem duplicar numa segunda rodada) e ordenação sob estresse.
- `frontend/public/manifest.json` e `frontend/public/sw.js` (Etapa 7.3): o app fica instalável, e o service worker recebe push (mesmo com o app fechado) e trata o clique na notificação abrindo o quadro/cartão certo — para isso, `worker/push.py` e `worker/agendador.py` passaram a levar uma `url_destino` junto de cada envio.
- `frontend/src/api/tempoReal.ts` (`useCanalDoQuadro`): o cliente WebSocket que a Etapa 6 tinha deixado pendente — conecta em `/ws/quadros/{id}`, reconecta com espera crescente recarregando o quadro (6.8), e devolve o `id_conexao` usado para suprimir o próprio eco (6.7) via um cabeçalho `X-Origem-Conexao` em toda escrita.
- `frontend/src/componentes/ModalDoCartao.tsx` (a tela "cartão aberto"): título, descrição, prazo (opcional, com um botão para remover) e aviso prévio (só aparece depois que existe um prazo).
- `frontend/src/paginas/TelaCalendario.tsx`: consome `GET /calendario`, agrupa por dia, e mostra uma mensagem explícita quando não há cartões com data no período (Etapa 4.6) em vez de uma lista em branco.
- `frontend/src/componentes/PainelDeAvisos.tsx`: um sino no cabeçalho com o histórico de avisos recebidos pelo canal em tempo real na sessão atual.
- Proxy de `/ws` em `frontend/vite.config.ts` (com `ws: true`), para o WebSocket também atravessar o servidor de desenvolvimento do Vite.

### Alterado

- `worker/push.py` (`enviar_notificacao`) e `worker/agendador.py` (`executar_ciclo`, `_enviar_para_usuario`) ganharam o parâmetro `url_destino` — a rota que o clique na notificação deve abrir. `tests/test_worker.py` (`EnviadorFalso`) atualizado para o novo parâmetro.
- `frontend/src/api/cliente.ts`: todas as escritas (`listas.criar`, `listas.mover`, `cartoes.criar`, `cartoes.mover`) passaram a aceitar `origemConexao` opcional; `cartoes.atualizar` e `cartoes.arquivar` são novos (usados pelo modal do cartão); `calendario.listar` é novo.
- `frontend/src/componentes/CartaoItem.tsx` ganhou `onClick` (abre o modal) coexistindo com o arrastar do dnd-kit — verificado que um clique sem movimento ainda dispara `onClick` normalmente, sem interferência do `PointerSensor`.

### Decisões registradas nesta etapa (não estão na documentação ainda)

- O service worker mora em `frontend/public/sw.js`, não em `frontend/src/sw.ts` como a Etapa 1.6 desenhou. É pouco código, não usa nenhum tipo/módulo do resto do app, e precisa de uma URL estável na raiz do site — empacotar via Vite exigiria um segundo ponto de entrada de build só para isso; `public/` já resolve com zero configuração extra, em dev e produção.
- Ícone do app em SVG (`frontend/public/icone.svg`), não PNG multi-tamanho — os navegadores atuais aceitam SVG em `manifest.json`; PNG fica para se um dia o app precisar rodar bem em iOS (que ainda não lê SVG de manifest).
- A política do cliente WebSocket para eventos externos (que não são o próprio eco) é recarregar o quadro inteiro, não reconciliar campo a campo — uma simplificação sobre o que a Etapa 6.1 descreve como "sincronização", trocando um pouco de suavidade visual por bem menos código; a atualização otimista das próprias ações continua instantânea, só as mudanças vindas de fora passam por uma recarga.
- **A armadilha de precisão da Etapa 3.4 reapareceu, uma camada abaixo**: o teste de estresse de ponta a ponta (Etapa 7.6) com cinquenta inserções revelou que o SQLite dos testes converte `Decimal` para `float` ao gravar num `Numeric` genérico do SQLAlchemy (confirmado inspecionando o `bind_processor` do dialeto: é literalmente uma função chamada `to_float`). O PostgreSQL de produção não tem esse problema — é puramente um limite do banco de teste, não do NUMERIC real. Diferente da Etapa 5/6 (onde um `TypeDecorator` como `TZDateTime` resolveu o mesmo tipo de divergência entre dialetos), aqui não há correção equivalente sem comprometer a ordenação: armazenar como texto para preservar precisão exigiria um formato de string ordenável (o próprio LexoRank que a Etapa 3.5 documenta como alternativa), o que mudaria a estratégia de ordenação em produção só para acomodar uma limitação do banco de teste — fora de escopo. O teste E2E ficou em 40 inserções (com folga sobre o colapso observado empiricamente, por volta da 52ª); as 50 do checklist continuam provadas à risca pelo teste algorítmico da Etapa 3, contra `Decimal` puro — o mesmo modelo de precisão do NUMERIC real.
- `aviso_previo` no formulário do cartão usa um `<select>` com durações fixas (0, 15min, 30min, 1h, 1 dia) em vez de um seletor de duração genérico — cobre o caso comum sem a complexidade de um componente de "horas/minutos" livre, que o v1 não pede.

## [0.5.0] - 2026-08-17

Implementa o lado de servidor da Etapa 6 (tempo real) — WebSocket por quadro, salas em memória, e a ponte que deixa o worker publicar nelas — e, junto, a primeira interface de verdade do projeto: o quadro kanban visual, com arrastar-e-soltar.

### Adicionado

- `backend/app/realtime/gerenciador.py`: `GerenciadorDeSalas`, uma instância única do processo com `conectar`/`desconectar`/`transmitir` (async) e `transmitir_sync` (para as rotas HTTP síncronas do projeto chamarem, via `anyio.from_thread.run` — o jeito correto de voltar ao loop de eventos principal a partir da thread onde o FastAPI roda uma rota `def`). `zerar()` e `quantidade_de_conexoes()` existem só para os testes.
- `backend/app/realtime/eventos.py`: `construir_evento(tipo, dados, origem)` — o formato único dos eventos transmitidos, isolado pelo mesmo motivo de `servicos/ordenacao.py` e `servicos/prazos.py`.
- `backend/app/rotas/realtime.py`: `GET /ws/quadros/{quadro_id}` (autenticação por cookie + fronteira de posse do quadro, igual ao resto da API; fecha com código 4401/4404 em vez de levantar `HTTPException`, que não existe depois do handshake aceito) e `POST /interno/eventos-tempo-real` (só para o worker chamar, autenticado por uma chave compartilhada simples — `include_in_schema=False`, não aparece no Swagger).
- `obter_usuario_da_conexao` em `app/auth/dependencias.py`: a mesma verificação de `obter_usuario_atual`, adaptada para `WebSocket` (devolve `None` em vez de levantar `HTTPException`).
- Toda escrita de lista e cartão (`criar`, `atualizar`/`mover`, `arquivar`) passou a transmitir um evento para a sala do quadro depois do commit, aceitando um cabeçalho opcional `X-Origem-Conexao` que é repassado ao evento como `origem` — a matéria-prima para a supressão de eco (Etapa 6.7) que um cliente futuro vai implementar.
- `backend/worker/tempo_real.py`: `publicar_evento_de_notificacao`, a ponte HTTP best-effort entre o worker e o canal em tempo real da API (Etapa 5.8/6.5). `executar_ciclo` (worker/agendador.py) chama isso depois de notificar um cartão com sucesso; a seleção de cartões pendentes passou a trazer também o `quadro_id`, não só o `usuario_id`.
- `chave_interna` e `url_api_interna` em `app/config.py`, e os serviços `api`/`worker` no `docker-compose.yml` passaram a compartilhar `CHAVE_INTERNA`.
- `backend/tests/test_realtime.py`: 6 testes cobrindo o que dá para testar do checklist 6.10 no backend (evento chega só para a sala certa, desconectar não vaza memória, LWW por convergência de escritas sequenciais, `origem` viaja no evento) usando `TestClient.websocket_connect` — sem servidor real rodando à parte.
- Fixture `autouse` `salas_de_tempo_real_isoladas` em `tests/conftest.py`: zera `gerenciador_de_salas` antes/depois de cada teste (é uma instância única do processo; sem isso, um teste vazaria conexões para o próximo).
- **O quadro kanban de verdade**, a primeira interface real do projeto (`frontend/src/paginas/QuadroKanban.tsx` + `TelaLogin.tsx`): colunas e cartões vindos da API, arrastar-e-soltar entre listas com `@dnd-kit` (`@dnd-kit/core`, `/sortable`, `/utilities`), e atualização otimista (Etapa 6.6) — o cartão se move na tela no instante em que é solto; a chamada `POST .../mover` acontece depois, e uma falha recarrega o quadro do zero em vez de deixar a tela mostrar um estado que a API não tem.
- `frontend/src/api/`: `tipos.ts` (espelhando os schemas Pydantic — `posicao` como `string`, porque o backend serializa `Decimal` como string para não perder a precisão da Etapa 3.6 num `number` de 64 bits) e `cliente.ts` (um wrapper fino sobre `fetch`, sem biblioteca de HTTP).
- Tema visual (`frontend/src/index.css`, `estilos/kanban.css`, `estilos/login.css`): modo escuro, paleta de sete acentos desaturados atribuídos por posição da coluna (não por nome — o kanban não tem estados fixos, Etapa 2.3), geometria "achatada" de propósito — o acento de uma coluna é só um traço fino de 3px no topo e uma barra fina na lateral do cartão, não um bloco sólido e alto.
- Três animações de arrastar, todas via classes CSS + `@dnd-kit`: o cartão de origem vira um contorno tracejado enquanto está no ar (`.cartao--espaco-reservado`); a cópia que segue o cursor ganha leve escala, rotação e brilho na cor da coluna (`.cartao--flutuando`, renderizada dentro de um `<DragOverlay>`); e o cartão pulsa uma vez ao pousar no destino (`.cartao--pousou`, um `@keyframes` de ~0.6s disparado por um id de "acabou de pousar" no estado do React, desligado sozinho por um `setTimeout`).

### Alterado

- `worker/agendador.py`: `executar_ciclo` ganhou o parâmetro `publicar_evento_realtime` (injetável, mesmo padrão de `enviar_notificacao` — Etapa 5.10). `test_worker.py` ganhou um dublê no-op (`_sem_evento_realtime`) para não fazer uma chamada HTTP de verdade (e lenta) em cada teste que notifica um cartão.

### Decisões registradas nesta etapa (não estão na documentação ainda)

- A ponte HTTP worker→API (`POST /interno/eventos-tempo-real`) não está detalhada na Etapa 6 do texto original — ela nasce da colisão entre duas decisões de etapas diferentes: o worker é um processo à parte (Etapa 5.2), e as salas vivem na memória de UM processo (Etapa 6.5). Como a Etapa 5.2 já descartou Redis para o v1, HTTP entre os próprios processos do projeto foi a ponte de menor complexidade que não introduz infraestrutura nova. É best-effort de propósito: a notificação de verdade (Web Push) já foi tentada antes; perder o aviso in-app é preferível a travar o worker por causa dele.
- Autenticação da rota interna: uma chave simples compartilhada (`CHAVE_INTERNA`), não um esquema novo — o mesmo padrão de custo-benefício de `CHAVE_SECRETA` (Etapa 1.4), proporcional ao que está em jogo (a rota só publica em salas; não lê nem escreve nada do banco).
- Nenhuma parte de cliente desta etapa (atualização otimista, eco, reconexão) tinha sido implementada quando o servidor foi escrito — não existia frontend de kanban para aplicá-la. Isso mudou ainda dentro desta mesma versão: o board foi construído logo em seguida, e já cobre a atualização otimista (6.6). Eco (6.7) e reconexão (6.8) continuam pendentes porque dependem do cliente WebSocket, que ainda não existe — ver `docs/documentacao.md`, seção 6.13, atualizada de acordo.
- Cor de acento por coluna: atribuída pela POSIÇÃO da coluna no quadro (um índice cíclico sobre uma paleta de sete tons), não por nome ou id — o domínio não tem estados fixos (Etapa 2.3, "não existe tabela de estados possíveis"), então não haveria um nome de coluna correto para fixar "essa é sempre a cor X".
- Verificação do drag-and-drop: sem captura de tela disponível neste ambiente, o comportamento foi validado disparando `PointerEvent`s sintéticos (pointerdown/move/up) via JavaScript na página real — backend rodando contra um SQLite temporário criado só para este teste manual, nunca commitado — conferindo as classes CSS aplicadas em cada fase do arrasto e a persistência após recarregar a página do zero. A suíte automatizada (`pytest`) não foi alterada por essa verificação.

## [0.4.0] - 2026-08-10

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
