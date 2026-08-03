# Projeto Kanban — App de tarefas com dimensão tempo

> **Documentação em construção, escrita por etapas.**
> Cada etapa corresponde a um pedaço construível do projeto.

| Etapa | Conteúdo | Status |
|---|---|---|
| **1** | Visão, domínio e escopo | ✅ escrita |
| **2** | O modelo kanban — quadro, lista, cartão | ✅ escrita |
| 3 | Ordenação — indexação fracionária | ⬜ pendente |
| 4 | A dimensão tempo — data no cartão e o calendário | ⬜ pendente |
| 5 | Notificações — o worker que roda sozinho | ⬜ pendente |
| 6 | Tempo real — WebSocket e atualização otimista | ⬜ pendente |
| 7 | Entrega — API, PWA, testes e Docker | ⬜ pendente |

---

# Etapa 1 — Visão, domínio e escopo

## 1.1 O que é, e para quem

Um app de tarefas em formato kanban — quadros com colunas, cartões que se arrastam entre elas — **com uma dimensão a mais que o kanban clássico não tem: tempo.**

Diferente dos outros projetos, este não existe para o mercado. Existe por diversão e desafio, e tem **uma usuária real e específica**. Isso muda as regras de decisão de um jeito importante: não há "melhor prática" que vença o gosto dela. Se ela achar algo intuitivo, é intuitivo. Se ela não usar, não importa quão elegante seja.

Ter um usuário real é um luxo que projeto de portfólio não tem. A validação aqui não é teórica — é perguntar.

## 1.2 A regra que protege o projeto

O kanban é amado por ser simples. Quase todo app de produtividade morre por olhar o Trello, pensar "eu faria melhor com só mais uns detalhes", adicionar os detalhes, e produzir algo que ninguém quer usar.

A regra deste projeto, cravada antes da primeira linha de código:

> **Uma dimensão é adicionada ao kanban. Uma só. Todo o resto permanece ortodoxo.**

A dimensão escolhida é **tempo** — e ela não foi escolhida por mim nem por gosto técnico: foi o que a usuária pediu, entre dez opções apresentadas. Ela escolheu calendário e aviso de prazo, que são a mesma dimensão vista de dois ângulos.

Tudo que não for tempo — etiquetas, checklists, subtarefas, dependências, limite de WIP — fica de fora do v1 por princípio, não por falta de tempo de desenvolvimento.

## 1.3 Por que "tempo" é a lacuna certa

O kanban modela **um instante**: onde cada coisa está agora. Ele responde "em que pé está cada tarefa?" com perfeição.

O que ele não responde: **quando**. O prazo, no Trello, é apenas um campo — não estrutura nada, não ordena nada, não dispara nada. É por isso que todo mundo que usa Trello a sério acaba grudando um calendário por cima.

Adicionar tempo significa duas coisas concretas:

**O calendário** — os mesmos cartões, olhados por outro eixo. Não é uma entidade nova; é uma **lente**. Cartão sem data simplesmente não aparece nela.

**O aviso de prazo** — a primeira coisa no app que acontece **porque o tempo passou**, e não porque alguém clicou. É a mudança arquitetural real do projeto, e o desafio técnico mais novo dele.

## 1.4 Escopo do v1

### Entra

| Item | Detalhe |
|---|---|
| Quadros, listas e cartões | A estrutura kanban clássica |
| Arrastar cartão | Entre listas e dentro da lista, com ordenação estável |
| Cartão | Título, descrição, prazo (data e hora) |
| Visão de calendário | Os cartões com prazo, por dia e por semana |
| Aviso de prazo | Antecedência configurável **por cartão** |
| Notificação no celular | Via Web Push, com o app fechado |
| Notificação dentro do app | Em tempo real, sem recarregar |
| Login | Simples — identifica o usuário e suas assinaturas de push |

### Fica no roadmap

| Item | Por que fica de fora |
|---|---|
| Etiquetas, checklists, anexos, comentários | Não são tempo. A regra da 1.2 |
| Cartão em posição intermediária entre colunas | Ideia registrada, mas não escolhida por ela. Fica disponível se ela quiser depois |
| Limite de WIP | Feature de time; com uma usuária, provavelmente inútil |
| Subtarefas e dependências | Adicionam uma segunda dimensão — viola a regra |
| Idade do cartão e cycle time | Baratos e interessantes, mas são análise, não tempo-prazo |
| Sugestões por padrão de uso | Precisa de meses de histórico acumulado. Fase posterior por natureza |
| App Android nativo | Fase 2 opcional, sobre a mesma API |
| Compartilhar quadro / colaboração | O app é de uma pessoa. Multiusuário é outro projeto |

**Regra anti-crescimento:** nada sai do roadmap antes de todo o v1 estar funcionando. E qualquer item novo precisa passar pelo teste da 1.2 — é tempo, ou é uma segunda dimensão?

## 1.5 Decisões de arquitetura

**Backend em Python com FastAPI e PostgreSQL.**

Não por Python ser superior, mas porque o desafio novo deste projeto está no *worker de notificação* e nos problemas de ordenação e sincronização — nenhum deles depende da linguagem. Trocar de stack ao mesmo tempo faria aprender menos das duas coisas.

**Cliente web em React/TypeScript, instalável como PWA.**

Foi avaliado fazer um app Android nativo em Kotlin. A decisão foi não, por três razões: Web Push funciona bem no Android (as limitações sérias são do iPhone), então a exigência da usuária está atendida; arrastar cartão — a interação central do app — é significativamente mais fácil na web do que em Compose; e o backend é idêntico nas duas rotas, o que mantém o app nativo disponível como fase 2 sobre a mesma API.

**Ordenação por posição fracionária, não por inteiros consecutivos.**

Posições inteiras obrigam a renumerar N cartões a cada arraste e corrompem a ordem sob concorrência. A posição será um valor fracionário, permitindo inserir entre dois cartões com uma única escrita. Detalhado na Etapa 3.

**Um worker separado da API.**

A notificação precisa disparar com o app fechado e ninguém olhando. Isso exige um processo que roda por tempo, não por requisição — a peça de arquitetura que este projeto acrescenta. Detalhado na Etapa 5.

**Resolução de conflito por "quem escreve por último ganha".**

Sem CRDT, sem Operational Transformation. As operações do kanban são absolutas ("cartão X vai para lista B, posição 2.5"), não relativas — o que torna a estratégia simples correta. Detalhado na Etapa 6.

## 1.6 Estrutura de pastas

```
projeto-kanban/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI: app e rotas
│   │   ├── config.py           # configuração via variável de ambiente
│   │   ├── database.py         # conexão e sessão
│   │   ├── modelos/            # quadro, lista, cartão, usuário, assinatura de push
│   │   ├── schemas/            # schemas Pydantic
│   │   ├── auth/                # login e sessão
│   │   ├── rotas/               # endpoints, um arquivo por recurso
│   │   ├── servicos/
│   │   │   └── ordenacao.py    # cálculo de posição fracionária (Etapa 3)
│   │   └── realtime/            # WebSocket e salas por quadro (Etapa 6)
│   ├── worker/                  # Etapa 5 — o processo que roda sozinho
│   │   ├── agendador.py        # verifica prazos periodicamente
│   │   └── push.py             # envio via Web Push
│   ├── tests/
│   ├── alembic/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── componentes/         # quadro, lista, cartão, calendário
│   │   ├── paginas/
│   │   ├── api/
│   │   └── sw.ts               # service worker — recebe o push (Etapa 5)
│   ├── manifest.json           # torna o app instalável (PWA)
│   └── package.json
│
├── docs/
│   └── documentacao.md
├── docker-compose.yml
└── README.md
```

Como nos outros projetos: **pasta nasce quando o código nasce.** O esqueleto acima é o destino, não o ponto de partida — `worker/` e `realtime/` só existem quando as Etapas 5 e 6 chegarem.

Duas merecem destaque. **`worker/`** é a peça que nenhum projeto anterior teve: um processo à parte da API, com ciclo de vida próprio. E **`sw.ts`** — o service worker — é o que permite a notificação chegar com o app fechado; sem ele, Web Push não existe.

## 1.7 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Kanban** | Método de organização visual por colunas que representam etapas |
| **Quadro / lista / cartão** | Os três níveis da estrutura (*board*, *list*, *card*) |
| **Dimensão** | Um eixo de informação além do estado. Aqui: tempo |
| **Prazo** | Data e hora em que o cartão vence |
| **Aviso prévio** | Quanto tempo antes do prazo a notificação dispara. Configurável por cartão |
| **PWA** | *Progressive Web App* — app web instalável na tela inicial, com ícone e tela cheia |
| **Web Push** | Notificação enviada pelo servidor ao navegador, mesmo com o app fechado |
| **Service worker** | Script que roda em segundo plano no navegador e recebe o push |
| **Worker** | Processo separado da API, que executa trabalho por tempo, não por requisição |
| **Posição fracionária** | Ordenação por valores que aceitam sempre um ponto médio entre dois vizinhos |

---

# Etapa 2 — O modelo kanban

## 2.1 O que esta etapa faz

Desenhar as entidades: o que existe no sistema, o que cada coisa guarda, e como se ligam.

Parece a etapa mais burocrática do projeto. Não é — ela contém **uma decisão de modelagem que determina o comportamento de todo o resto**, e que é o oposto do que você fez no projeto anterior. Essa decisão é a seção 2.3, e o resto da etapa é consequência dela.

## 2.2 Os três níveis

```
Usuário
  └── Quadro        (ex.: "Casa", "Faculdade")
        └── Lista   (ex.: "A fazer", "Fazendo", "Pronto")
              └── Cartão   (a tarefa)
```

Três níveis, e **nada abaixo do cartão**. Essa rasidão é característica do kanban, não uma limitação do v1: subtarefas seriam uma segunda dimensão, e a regra da Etapa 1 as manda para o roadmap.

Um detalhe que costuma escapar: **listas também precisam de ordem.** Não é só o cartão que se arrasta — as colunas também se reorganizam. Então `lista` carrega uma posição, exatamente como `cartao`. Quem esquece isso descobre tarde, quando a ordem das colunas começa a variar a cada consulta.

## 2.3 A decisão central: não existe campo `status`

No projeto de agendamento, o estado era um campo — `status = 'marcado'` — governado por uma máquina de estados que definia quais transições eram válidas.

Aqui é o contrário. **O cartão não tem campo de estado. O estado do cartão é em qual lista ele está.**

Mover um cartão de "Fazendo" para "Pronto" não é atualizar um campo `status`; é mudar o `lista_id`. A coluna *é* o estado.

| | Status como campo (projeto Agenda) | Status como posição (kanban) |
|---|---|---|
| Estados possíveis | Fixos, definidos em código | Arbitrários, criados pela usuária |
| Mudar o fluxo | Exige alterar o código e reimplantar | Arrastar uma coluna nova |
| Transições válidas | Máquina de estados explícita | Nenhuma — tudo é permitido |
| Visualização | Precisa ser construída à parte | É o próprio modelo |

## 2.4 O preço dessa decisão

Toda escolha de modelagem cobra alguma coisa. Esta troca **rigor por flexibilidade**, e vale saber exatamente o que se ganha e o que se perde.

**O que se ganha:** a usuária define o próprio fluxo sem programar nada. Ela quer uma coluna "Esperando resposta"? Cria. Quer separar "Comprar" de "Fazer"? Cria. O sistema não tem opinião sobre quais estados existem — e é isso que faz um kanban servir para organizar mudança de casa, trabalho e faculdade com a mesma ferramenta.

**O que se perde:** não existem transições inválidas. Arrastar um cartão de "Pronto" de volta para "A fazer" é permitido, sempre. Não há regra de negócio impedindo, porque não há regra de negócio nenhuma sobre estado.

**E a consequência estrutural:** o cartão está em **exatamente uma** lista. Um estado, nunca dois. Se uma tarefa estiver simultaneamente "em revisão" e "bloqueada", o modelo não representa isso. É a origem da gambiarra das etiquetas coloridas no Trello — uma segunda dimensão de estado colada por fora, justamente porque o modelo só comporta uma.

No v1, isso não é um problema a resolver. É uma característica aceita.

## 2.5 As entidades

```sql
usuario
├── id
├── email
└── senha_hash

quadro
├── id
├── usuario_id      → usuario
├── nome
└── criado_em

lista
├── id
├── quadro_id       → quadro
├── nome
└── posicao         ← as colunas também se reordenam

cartao
├── id
├── lista_id        → lista        ← o "estado" do cartão
├── titulo
├── descricao
├── posicao         ← ordem dentro da lista
├── prazo           ← TIMESTAMPTZ, opcional (Etapa 4)
├── aviso_previo    ← quanto tempo antes notificar (Etapa 4)
├── arquivado
└── criado_em
```

Três observações sobre esse desenho:

**O tipo de `posicao` fica em aberto de propósito.** Se é número fracionário ou texto ordenável é a decisão da Etapa 3, e ela tem consequências que merecem discussão própria. Por ora, basta saber que **não é inteiro consecutivo**.

**`prazo` e `aviso_previo` são a dimensão adicionada** — os únicos campos que não existiriam num kanban ortodoxo. Toda a Etapa 4 gira em torno deles. Note que são **dois** campos, não um: o prazo é quando vence; o aviso prévio é quanto tempo antes notificar, configurável por cartão.

**O cartão não guarda `quadro_id`.** Ele chega ao quadro pela lista. É o desenho normalizado e correto — mas gera um `JOIN` em consultas como "todos os cartões deste quadro", que a visão de calendário vai precisar. Para um app de uma usuária, o `JOIN` é irrelevante; se um dia doer, aí se pensa em desnormalizar. Otimizar antes disso seria resolver um problema que não existe.

## 2.6 O que deliberadamente não entra no cartão

A regra da Etapa 1 aplicada, e vale listar para não haver dúvida depois:

| Campo ausente | Por quê |
|---|---|
| Etiquetas | Segunda dimensão de estado |
| Checklist | Hierarquia disfarçada |
| Anexos, comentários | Não são tempo |
| Responsável | O app é de uma pessoa |
| Estimativa, prioridade | Cada um é uma dimensão nova |

Nenhum desses é difícil de adicionar. É exatamente por isso que a lista existe: a facilidade de adicionar é o que mata apps de produtividade. Cada campo aqui seria "só um campinho", e dez campinhos viram um formulário que ninguém quer preencher.

## 2.7 Apagar, ou arquivar?

Uma pergunta que o modelo obriga a responder: o que acontece quando se apaga uma lista que tem cartões dentro?

Três respostas possíveis: apagar os cartões junto (destrutivo), impedir enquanto houver cartões (irritante), ou arquivar.

**Decisão do v1: arquivar, não apagar.** O cartão tem `arquivado`, e "excluir" na interface só marca essa flag. Três motivos:

1. **É perdoável.** Arrastar errado e perder uma tarefa é frustrante; num app pessoal, isso queima a confiança rápido.
2. **Preserva histórico** — que é matéria-prima dos itens de roadmap como cycle time e sugestões por padrão de uso. Dado apagado não volta.
3. É a mesma lição do *soft delete* do projeto de agendamento: em sistema com histórico, raramente se apaga de verdade.

Para listas: arquivar a lista arquiva os cartões dentro dela, com aviso claro na interface.

## 2.8 Como testar

Modelagem se verifica de forma indireta — o que se testa é que a estrutura sustenta as operações:

- Criar quadro, lista e cartão, e recuperá-los ligados corretamente
- Mover um cartão entre listas altera apenas `lista_id`
- Um usuário não alcança quadro de outro (mesmo sendo um app pessoal, a fronteira existe)
- Listas de um quadro voltam na ordem definida por `posicao`
- Arquivar um cartão o remove das consultas normais, mas ele continua no banco
- Arquivar uma lista arquiva seus cartões
- Um cartão sem `prazo` é válido — a data é opcional

O último importa mais do que parece: **a maioria dos cartões não vai ter prazo.** A dimensão tempo é opcional por natureza, e o modelo precisa tratar isso como caso normal, não como exceção.

## 2.9 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Quadro** (*board*) | O agrupamento maior — um contexto de organização |
| **Lista** (*list*, coluna) | Uma etapa do fluxo. **É** o estado do cartão |
| **Cartão** (*card*) | A tarefa |
| **Estado como posição** | A decisão de que o estado é a lista onde o cartão está, não um campo |
| **Arquivar** (*soft delete*) | Marcar como oculto preservando o registro, em vez de apagar |
| **Normalizado** | Cada informação guardada num só lugar; relações por chave estrangeira |

---

## Próxima etapa

**Etapa 3 — Ordenação:** por que posições inteiras quebram, o que é indexação fracionária, e a armadilha de precisão que ela esconde — o primeiro dos três problemas técnicos de verdade do projeto.
