# Projeto Kanban — App de tarefas com dimensão tempo

> **Documentação em construção, escrita por etapas.**
> Cada etapa corresponde a um pedaço construível do projeto.

| Etapa | Conteúdo | Status |
|---|---|---|
| **1** | Visão, domínio e escopo | ✅ escrita |
| **2** | O modelo kanban — quadro, lista, cartão | ✅ escrita |
| **3** | Ordenação — indexação fracionária | ✅ escrita |
| **4** | A dimensão tempo — data no cartão e o calendário | ✅ escrita |
| **5** | Notificações — o worker que roda sozinho | ✅ escrita |
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

# Etapa 3 — Ordenação

## 3.1 O que esta etapa resolve

Uma pergunta que parece trivial: como guardar a ordem dos cartões dentro de uma lista, sabendo que a usuária vai arrastá-los para qualquer posição?

É o problema mais bonito do domínio. A solução ingênua funciona nos primeiros testes e quebra de duas formas diferentes depois — uma por desempenho, outra por corrupção de dados. E a solução correta é curta, elegante, e esconde uma armadilha numérica que quase todo mundo descobre em produção.

Vale dizer de saída: a decisão desta etapa é a mesma que torna a Etapa 6 (tempo real) fácil. Elas parecem independentes e não são.

## 3.2 A abordagem óbvia, e por que ela quebra

Cada cartão tem uma coluna `posicao` com um inteiro: 1, 2, 3, 4, 5. Ordena por ela.

Agora a usuária arrasta o cartão da posição 5 para a posição 2:

```
antes:  [A:1] [B:2] [C:3] [D:4] [E:5]
depois: [A:1] [E:2] [B:3] [C:4] [D:5]
                     ↑     ↑     ↑
              três cartões renumerados sem ninguém pedir
```

Mover um cartão exigiu escrever em quatro. Numa lista de 300 cartões, arrastar um item para o topo dispara 300 UPDATEs.

E esse é o problema pequeno. O grande aparece com dois clientes: se duas escritas de renumeração se cruzam no meio do caminho, a ordem final não fica "estranha" — fica corrompida, com posições duplicadas e cartões fora de lugar. Como o app terá tempo real (Etapa 6), isso deixa de ser hipotético.

## 3.3 A virada: os números não precisam ser consecutivos

A pergunta que destrava tudo: por que 1, 2, 3?

A ordenação exige uma única propriedade: dados dois cartões, saber qual vem antes. Inteiros consecutivos são uma restrição autoimposta — e é exatamente ela que obriga a renumerar.

Solte a restrição. Se os cartões estão em 1.0, 2.0 e 3.0, e você quer inserir entre o primeiro e o segundo:

```
posicao = (1.0 + 2.0) / 2 = 1.5
```

Um único UPDATE. Nenhum outro cartão é tocado. Nenhuma coordenação, nenhuma corrida.

Isso se chama **indexação fracionária** (*fractional indexing*), e é o que Trello, Figma, Notion e praticamente todo app com arrastar-e-soltar usam.

Uma precisão importante: a posição é relativa à lista, não global. Dois cartões em listas diferentes podem ter posição 1.5 sem qualquer conflito — o `ORDER BY` sempre acontece dentro de uma lista. Mover um cartão entre listas é mudar `lista_id` e calcular uma posição nova no destino.

## 3.4 A armadilha: a precisão acaba

Aqui está o detalhe que separa quem leu um tutorial de quem já levou o bug em produção.

A usuária arrasta um cartão para o topo. Depois outro. Depois outro. Cada inserção pega o ponto médio do intervalo que sobrou:

```
1.0                      ← cartão de referência
1.5      → intervalo 0.5
1.25     → intervalo 0.25
1.125    → intervalo 0.125
1.0625   → intervalo 0.0625
...
1.0000000000000002       → intervalo ≈ 2⁻⁵²
1.0                      ← COLAPSO: (1.0 + 1.0000000000000002)/2 == 1.0
```

Cada inserção corta o intervalo pela metade. Um float64 tem 52 bits de mantissa — depois de aproximadamente 52 inserções no mesmo ponto, o ponto médio entre dois números é igual a um deles. Dois cartões passam a ter a mesma posição, e a ordem entre eles vira indefinida: muda a cada consulta.

Cinquenta arrastes não é cenário teórico. É uma pessoa organizando o quadro numa tarde.

## 3.5 As quatro saídas

| Estratégia | Como funciona | Custo |
|---|---|---|
| Rebalanceamento periódico | Espaça muito no início (65536, 131072...) e renumera a lista em segundo plano quando o intervalo aperta | O O(n) volta, amortizado; renumerar durante movimentos concorrentes é chato |
| Rank lexicográfico (LexoRank) | A posição vira texto. Entre "aaa" e "aab" cabe "aaaa" — sempre dá para acrescentar um caractere | As strings crescem com o tempo; ainda vale rebalancear, mas raramente |
| Precisão arbitrária (NUMERIC) | Decimal sem limite de precisão no PostgreSQL. O ponto médio nunca colapsa | Valores acumulam dígitos; comparação um pouco mais lenta |
| Lista ligada | Cada cartão aponta para o próximo | Perde o `ORDER BY`; um ponteiro quebrado parte a lista em duas |

Sobre o LexoRank: ele funciona porque, em ordenação lexicográfica, uma string que é prefixo de outra vem antes. Como sempre se pode acrescentar um caractere, nunca acaba — diferente do float, não existe mantissa para estourar.

Sobre a lista ligada: parece elegante e é a pior das quatro na prática. Ler a lista em ordem exige percorrer os ponteiros um a um — em SQL, uma CTE recursiva — e a fragilidade estrutural troca um problema raro por um pior.

## 3.6 A decisão do v1

**NUMERIC no PostgreSQL, com ponto médio.**

O motivo: elimina a armadilha por construção, o código tem poucas linhas, e a desvantagem (valores longos) só importaria numa escala que este app não terá. Quando o volume é pequeno, corretude simples vence microdesempenho.

E o cálculo fica isolado num único lugar — `backend/app/servicos/ordenacao.py`, da estrutura da Etapa 1. Nada no resto do código sabe como a posição é calculada; só chama uma função que devolve "a posição entre A e B".

Isso não é organização estética: é o que torna a estratégia trocável. Se você quiser depois encarar o LexoRank — e ele é, de longe, o quebra-cabeça de algoritmo mais divertido deste projeto —, a troca mexe num arquivo, não em dez. Vale considerar como desafio opcional, com a segurança de que o v1 já funciona sem ele.

## 3.7 Os casos de borda

O ponto médio resolve o caso "entre dois cartões". Faltam três situações, e cada uma precisa de uma convenção:

| Situação | O que fazer |
|---|---|
| Lista vazia | Posição inicial arbitrária (ex.: 1000) |
| Soltar no topo | Não há vizinho antes. Pega a posição do primeiro e subtrai um intervalo fixo — ou divide por dois, caminhando em direção a zero |
| Soltar no fim | Não há vizinho depois. Pega a posição do último e soma um intervalo fixo |

A convenção do topo merece atenção: se você sempre dividir por dois rumo a zero, os valores encolhem indefinidamente e você reencontra o problema de precisão pelo outro lado — só que agora perto do zero. Somar e subtrair um intervalo fixo (em vez de dividir) mantém os valores em faixa saudável, e com NUMERIC nenhum dos dois caminhos quebra de fato.

## 3.8 O desempate: nunca ordene só por posição

Com indexação fracionária, duas inserções simultâneas no mesmo intervalo calculam o mesmo ponto médio. Dois cartões com posição idêntica.

Não é catástrofe — é ambiguidade. E a defesa é uma linha:

```sql
ORDER BY posicao, id
```

O `id` é o critério de desempate. A ordem pode não ser a que ambos esperavam, mas é determinística e igual para todos os clientes — que é o que de fato importa. Sem o desempate, dois clientes podem exibir a mesma lista em ordens diferentes, e o bug resultante é daqueles que fazem duvidar da própria sanidade.

**Regra: toda consulta ordenada por posição carrega um segundo critério estável.**

## 3.9 Como testar

Ordenação é determinística e testa-se bem — aproveite, porque a Etapa 5 e a 6 são bem menos previsíveis:

- Inserir entre dois cartões produz posição estritamente entre as duas
- Inserir no topo produz posição menor que a do primeiro
- Inserir no fim produz posição maior que a do último
- Inserir em lista vazia funciona
- Mover um cartão altera apenas aquele cartão — nenhum outro registro é escrito
- Mover entre listas atualiza `lista_id` e recalcula a posição no destino
- Cinquenta inserções consecutivas no mesmo ponto mantêm a ordem correta — o teste que prova que a armadilha da 3.4 está fechada
- Duas posições iguais são desempatadas de forma estável pelo `id`

O sétimo é o teste de assinatura desta etapa. Com posições inteiras ele nem faria sentido; com float, ele falha. Vê-lo passar é a confirmação de que a escolha da 3.6 foi certa.

## 3.10 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Indexação fracionária** | Ordenar por valores que sempre aceitam um ponto médio entre dois vizinhos |
| **Mantissa** | A parte de um número de ponto flutuante que guarda os dígitos significativos. No float64, 52 bits |
| **LexoRank** | Ordenação por strings, onde sempre cabe um valor entre dois — usada no Jira |
| **NUMERIC** | Tipo decimal de precisão arbitrária do PostgreSQL |
| **Rebalanceamento** | Renumerar a lista inteira para recuperar espaço entre as posições |
| **Desempate estável** | Segundo critério de ordenação que garante resultado idêntico em qualquer consulta |
| **Posição relativa à lista** | A posição só faz sentido dentro de uma lista; não é global |

## 3.11 Notas soltas desta etapa

Um punhado de observações que vale manter registradas, além do texto corrido acima:

Os casos de borda (3.7) são o que a conversa inicial sobre esta etapa não cobriu de saída. O ponto médio resolve "entre dois cartões" — mas soltar no topo, no fim, ou numa lista vazia não tem vizinho dos dois lados. Cada um precisa de convenção. E tem uma pegadinha ali: se você sempre dividir por dois rumo ao zero ao inserir no topo, os valores encolhem indefinidamente e você reencontra o problema de precisão pelo outro lado. Somar e subtrair um intervalo fixo mantém tudo em faixa saudável.

A posição é relativa à lista, não global (3.3). Dois cartões em listas diferentes podem ter posição 1.5 sem conflito nenhum. E mover entre listas é duas coisas: mudar `lista_id` e calcular posição nova no destino. Parece óbvio escrito, mas é fonte comum de bug quando se pensa na posição como um número universal.

O isolamento em `servicos/ordenacao.py` (3.6) é uma decisão de arquitetura, não de arrumação. Nada no resto do código sabe como a posição é calculada — só chama "me dê a posição entre A e B". Isso é o que torna a estratégia trocável: se você quiser encarar o LexoRank depois, mexe num arquivo. NUMERIC fica como decisão do v1 justamente para o app existir logo, com o LexoRank disponível como desafio opcional sem risco.

E o teste de assinatura da etapa: cinquenta inserções consecutivas no mesmo ponto mantendo a ordem correta. Com posições inteiras esse teste nem faria sentido; com float, ele falha. Vê-lo passar é a prova de que a armadilha está fechada.

Uma ponte para adiante: a decisão desta etapa é a que vai tornar a Etapa 6 fácil. Como a operação vira "cartão X vai para lista B, posição 2.5" — absoluta, independente do estado anterior —, dois clientes podem mandar comandos simultâneos sem invalidar um ao outro. Se a posição fosse inteira e consecutiva, mover significaria "renumere todos os outros", uma operação relativa, e a sincronização exigiria artilharia pesada. Duas etapas que parecem separadas e são a mesma decisão.

---

# Etapa 4 — A dimensão tempo

## 4.1 O que esta etapa faz

Adicionar ao cartão a única dimensão que este projeto acrescenta ao kanban clássico: quando.

São duas funcionalidades que a usuária escolheu, e elas têm naturezas opostas. O calendário é barato — os mesmos cartões, olhados por outro eixo. O aviso de prazo é caro — ele exige que algo aconteça sem ninguém clicar, e é o assunto inteiro da Etapa 5.

Esta etapa cuida do modelo que sustenta os dois: quais campos o cartão ganha, e o que eles significam.

## 4.2 Dois campos, não um

```sql
cartao
├── ...
├── prazo          TIMESTAMPTZ      NULL     -- quando vence
├── aviso_previo   INTERVAL         NULL     -- quanto tempo antes avisar
├── notificar_em   TIMESTAMPTZ      NULL     -- prazo - aviso_previo (calculado)
└── notificado     BOOLEAN          NOT NULL DEFAULT false
```

`prazo` é o vencimento. TIMESTAMPTZ, e opcional — a maioria dos cartões não terá.

`aviso_previo` é a antecedência, configurável por cartão, como ela pediu. O tipo INTERVAL do PostgreSQL é o certo aqui: ele representa duração de forma nativa ('1 day', '2 hours', '30 minutes') e faz aritmética direto com timestamps. A alternativa — guardar minutos como inteiro — funciona, mas joga fora expressividade que o banco já oferece de graça.

Os outros dois campos merecem seção própria.

## 4.3 A decisão: materializar o momento do disparo

O worker da Etapa 5 vai perguntar, de tempos em tempos: "algum cartão precisa ser notificado agora?". Há duas formas de responder.

Calcular na hora:

```sql
WHERE prazo - aviso_previo <= now()
```

Correto, e o banco resolve. O problema é que essa expressão envolve duas colunas numa conta — o índice comum não ajuda, e o banco varre a tabela. Resolve-se com índice de expressão, mas é complexidade extra.

Materializar numa coluna:

```sql
WHERE notificar_em <= now() AND notificado = false
```

`notificar_em` é gravado quando o cartão é salvo, já com a conta feita. A consulta vira uma comparação simples com índice trivial.

Decisão do v1: materializar. Não pelo desempenho — com uma usuária, nada disso importa — mas porque a consulta do worker fica óbvia de ler e de testar, e porque `notificar_em` se encaixa naturalmente com o controle de "já notifiquei" da Etapa 5.

O custo, e é uma regra de negócio de verdade:

> Sempre que `prazo` ou `aviso_previo` mudarem, `notificar_em` precisa ser recalculado — e `notificado` volta para `false`.

A segunda metade é a que escapa. Se a usuária adia o prazo de um cartão que já foi notificado, ela espera ser avisada de novo na nova data. Sem resetar a flag, o cartão nunca mais notifica. É um bug silencioso: nada quebra, o aviso só não chega.

Isso mora na camada de serviço, junto com o resto das regras — não espalhado por cada rota que edita cartão.

## 4.4 Fuso horário, e o que TIMESTAMPTZ realmente faz

Uma confusão comum: TIMESTAMPTZ não guarda o fuso horário. Ele guarda um instante absoluto (internamente em UTC) e converte na leitura, conforme o fuso da sessão.

Na prática, isso significa que "quinta às 14h em Recife" vira um ponto único na linha do tempo, e o worker dispara no instante certo independentemente do fuso do servidor. É exatamente o que se quer, e é por isso que o tipo é esse — a mesma decisão do projeto de agendamento.

A limitação que vem junto, e vale saber agora: com `aviso_previo` como duração, você só consegue expressar "X tempo antes". Uma regra como "me avise sempre na véspera às 9h" é de relógio de parede, não de intervalo — não cabe neste modelo. Se ela pedir isso depois, é uma mudança de modelagem, não um ajuste. Fica registrado no roadmap.

## 4.5 O calendário é uma lente, não uma entidade

Nenhuma tabela nova. O calendário é uma consulta com outro recorte:

```sql
SELECT ... FROM cartao
JOIN lista ON ...
JOIN quadro ON ...
WHERE quadro.usuario_id = :usuario
  AND cartao.arquivado = false
  AND cartao.prazo BETWEEN :de AND :ate
ORDER BY cartao.prazo;
```

Os mesmos cartões do quadro, filtrados por data em vez de agrupados por lista.

Uma decisão de produto embutida aí: o calendário atravessa quadros. Se ela tem "Casa" e "Faculdade" separados, o calendário mostra os dois juntos — porque a pergunta que ele responde é "o que eu tenho hoje?", e essa pergunta não respeita a divisão de quadros. Um filtro opcional por quadro fica disponível para quem quiser recortar.

Vale notar o que isso resolve de graça: uma das fraquezas conhecidas do Trello é que trabalho espalhado por vários quadros é invisível — não existe visão unificada. O calendário, atravessando quadros, corrige parcialmente isso sem nenhum esforço adicional. Efeito colateral bem-vindo da dimensão escolhida.

## 4.6 A maioria dos cartões não terá prazo

Isso não é um detalhe — é uma característica que molda várias decisões.

Lista de compras não tem data. "Ideias de presente" não tem data. Num uso real, é normal que só uma minoria dos cartões tenha prazo, e o modelo trata isso como caso comum, não exceção:

`prazo` é NULL por padrão, e criar cartão não pede data. Obrigar a preencher data em toda tarefa é o tipo de atrito que faz alguém abandonar o app na primeira semana.

Toda consulta que toca `prazo` lida com NULL — inclusive a do worker, que naturalmente ignora quem não tem `notificar_em`.

O calendário vai parecer vazio no começo, e isso não é bug. Vale a interface dizer algo como "nenhum cartão com data neste período" em vez de mostrar uma grade em branco que parece quebrada.

## 4.7 O que fica de fora

| Item | Por quê |
|---|---|
| Início e fim (cartão como barra no calendário) | Mais rico e bem mais complexo; só o prazo já alimenta as duas funcionalidades |
| Recorrência (tarefa toda segunda) | Regra de negócio grande — gera cartões, ou é um cartão que se repete? Projeto à parte |
| Vários avisos no mesmo cartão (1 dia antes e 1 hora antes) | Exige tabela separada de avisos; o campo único cobre o caso comum |
| Aviso por regra de relógio ("véspera às 9h") | Não cabe no modelo de duração (seção 4.4) |

Cada um desses é uma boa ideia. Nenhum é necessário para o v1 funcionar — e a regra da Etapa 1 vale aqui como valeu antes.

## 4.8 Como testar

Ainda determinístico, ainda testável de verdade — aproveite, porque a Etapa 5 e a 6 são menos previsíveis:

- Cartão sem prazo é válido; `notificar_em` fica nulo
- Definir prazo e aviso prévio calcula `notificar_em` corretamente
- Alterar o prazo recalcula `notificar_em` e reseta `notificado` para `false` — o teste que fecha o bug silencioso da 4.3
- Alterar só o aviso prévio também recalcula
- Remover o prazo limpa `notificar_em`
- O calendário devolve só cartões com prazo dentro do intervalo pedido
- O calendário atravessa quadros do mesmo usuário
- Cartões arquivados não aparecem no calendário
- Um prazo salvo e lido de volta preserva o instante correto

O terceiro é o mais valioso: ele testa uma regra que não quebra nada quando está errada — o aviso simplesmente não chega, e você descobriria semanas depois, provavelmente pela usuária reclamando.

## 4.9 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Prazo** | Data e hora de vencimento do cartão. Opcional |
| **Aviso prévio** | Duração antes do prazo em que a notificação dispara. Por cartão |
| **INTERVAL** | Tipo do PostgreSQL para duração ('1 day', '2 hours') |
| **TIMESTAMPTZ** | Instante absoluto, guardado em UTC e convertido na leitura |
| **Materializar** | Guardar um valor já calculado numa coluna, em vez de calculá-lo a cada consulta |
| **notificar_em** | O instante do disparo: `prazo - aviso_previo` |
| **Relógio de parede** | Regra baseada na hora local ("às 9h"), diferente de duração ("1 dia antes") |
| **Lente** | Uma visualização alternativa dos mesmos dados, sem entidade nova |

## 4.10 Notas soltas desta etapa

O cartão ganha quatro campos, não dois. Além de `prazo` e `aviso_previo`, entram `notificar_em` (o instante do disparo, já calculado) e `notificado` (a flag de controle). A decisão de materializar `notificar_em` em vez de calcular na hora deixa a consulta do worker trivial e indexável — e ela se encaixa naturalmente com o controle de idempotência da Etapa 5.

A regra que esconde o bug silencioso (4.3): mudar o prazo precisa recalcular `notificar_em` e resetar `notificado` para `false`. A segunda metade é a que escapa. Se ela adiar um cartão já notificado e a flag não voltar, o aviso nunca mais chega — e nada quebra, nada dá erro. Você descobriria semanas depois, pela usuária reclamando. Por isso virou um teste explícito.

A limitação de fuso que vale saber agora (4.4): com `aviso_previo` como duração, você só expressa "X tempo antes". Uma regra como "me avise sempre na véspera às 9h" é de relógio de parede, não de intervalo — não cabe neste modelo. Se ela pedir isso depois, é mudança de modelagem, não ajuste. Está no roadmap.

O calendário atravessa quadros, e isso corrige uma fraqueza do Trello de graça. A pergunta que ele responde é "o que eu tenho hoje?", e essa pergunta não respeita a divisão entre "Casa" e "Faculdade". Efeito colateral: aquela invisibilidade de trabalho espalhado por vários quadros, que é reclamação clássica de usuário veterano, fica parcialmente resolvida sem esforço adicional.

E a seção 4.6 tem uma consequência de interface que vale carregar: criar cartão não pede data. Obrigar a preencher prazo em toda tarefa é atrito que faz abandonar app na primeira semana. A maioria dos cartões nunca terá data, o calendário vai parecer vazio no começo, e isso é o funcionamento normal — não um bug.

---

# Etapa 5 — Notificações

## 5.1 A virada arquitetural

Até aqui, tudo no app aconteceu porque alguém clicou. Uma requisição chega, o servidor responde, acabou. É o modelo de todos os seus projetos anteriores.

A notificação quebra isso. Ela precisa acontecer porque o tempo passou — com o app fechado, o celular no bolso, ninguém olhando. Não há requisição para responder.

Isso exige uma peça que o projeto ainda não tem: um processo com ciclo de vida próprio, que acorda sozinho, verifica o mundo e age. É a diferença entre um sistema reativo e um sistema que também é ativo, e é o desafio central desta etapa.

## 5.2 O worker: por que separado da API

A tentação é colocar um agendador dentro do próprio processo do FastAPI — existe biblioteca para isso, e funciona. Mas três problemas aparecem:

Reiniciar a API mata o agendador. Todo deploy vira uma janela cega onde nada é notificado.

Duas instâncias da API viram notificação duplicada. Se um dia o app rodar com dois processos, ambos acordam e ambos notificam o mesmo cartão.

Trabalho pesado disputa com as requisições. Enviar notificações trava o processo que deveria estar respondendo a usuária.

Decisão do v1: um processo separado, na pasta `backend/worker/`. Ele compartilha os modelos e o banco com a API, mas tem vida própria — sobe junto no docker-compose como um serviço distinto.

Para o v1, um laço simples basta: acorda, consulta, envia, dorme. A resposta de produção seria uma fila com agendador (ARQ, Celery beat), e trocar depois é um upgrade natural — mas arrastar Redis e broker agora adicionaria infraestrutura sem ensinar o conceito, que é o que interessa aqui.

## 5.3 O laço

O coração do worker é uma consulta:

```sql
SELECT c.id, c.titulo, c.prazo, q.usuario_id
FROM cartao c
JOIN lista l  ON l.id = c.lista_id
JOIN quadro q ON q.id = l.quadro_id
WHERE c.notificar_em <= now()
  AND c.notificado = false
  AND c.arquivado  = false;
```

Simples — e é simples porque a Etapa 4 materializou `notificar_em`. Sem aquela decisão, esta consulta teria uma conta entre colunas e um índice de expressão.

Frequência: a cada minuto é suficiente. Isso significa até 60 segundos de atraso no aviso, o que é irrelevante para prazos medidos em horas ou dias. Rodar a cada segundo só gastaria recurso.

Repare no `<= now()`, não numa janela de tempo. A consulta pega tudo que já venceu, não só o que venceu no último minuto. Essa escolha torna o worker resistente a queda: se ele ficar fora do ar por três horas, ao voltar ele encontra e envia tudo que ficou para trás. Uma janela (entre agora-1min e agora) perderia silenciosamente esses avisos.

O efeito colateral disso, e vale tratar: se o app ficar desligado por dias, ao ligar dispara uma enxurrada de avisos vencidos. Uma regra simples resolve — ignorar avisos atrasados além de um limite (digamos, 24 horas), marcando-os como notificados sem enviar. Um lembrete de três dias atrás não ajuda ninguém.

## 5.4 Idempotência: a decisão que ninguém percebe até doer

A flag `notificado` existe para não avisar duas vezes. Mas há uma pergunta sutil: marcar antes ou depois de enviar?

| | Se marcar antes | Se marcar depois |
|---|---|---|
| Envio falha | Notificação perdida para sempre | Tenta de novo no próximo ciclo |
| Processo morre no meio | Perdida | Pode enviar duplicado |

É o clássico dilema de semântica de entrega: **no máximo uma vez** contra **pelo menos uma vez**. Não existe "exatamente uma vez" sem complexidade considerável.

Decisão do v1: marcar depois do envio bem-sucedido — ou seja, pelo menos uma vez. O raciocínio é do domínio, não da técnica: receber o mesmo lembrete duas vezes é levemente irritante; não receber significa perder um prazo. Num app pessoal, o erro tolerável é o primeiro.

Vale escrever isso no código como comentário, porque é uma decisão consciente que parece descuido para quem lê depois.

## 5.5 Como o Web Push realmente funciona

Esta é a parte que mais confunde, porque a intuição está errada. Seu servidor não envia nada para o celular dela.

O fluxo real:

```
1. O navegador dela pede permissão para notificar
2. Autorizado → o navegador gera uma "assinatura":
   uma URL única + duas chaves de criptografia
3. O frontend manda essa assinatura para o seu backend, que guarda
4. Na hora de notificar, o worker criptografa a mensagem
   e faz um POST para aquela URL
5. Aquela URL pertence ao serviço de push do navegador
   (Google, no caso do Chrome — não ao seu servidor)
6. O serviço de push entrega ao navegador dela
7. O service worker acorda e mostra a notificação
```

Ou seja: você entrega a mensagem ao carteiro do Google, e ele leva. Você nunca fala com o celular diretamente — o que é justamente o que permite a notificação chegar com o app fechado.

VAPID é o que identifica seu servidor nesse processo: um par de chaves, gerado uma vez. A pública vai para o frontend (usada ao criar a assinatura); a privada assina os envios do worker. É o que impede qualquer um de enviar notificações em nome do seu app.

No Python, `pywebpush` cobre a parte de criptografia e envio. Não é preciso conta no Firebase — Web Push com VAPID é padrão aberto.

## 5.6 A nova entidade: assinatura

```sql
assinatura_push
├── id
├── usuario_id      → usuario
├── endpoint        -- a URL única do serviço de push
├── chave_p256dh    -- criptografia
├── chave_auth      -- criptografia
└── criado_em
```

Dois pontos que não são óbvios:

Um usuário tem várias assinaturas. Uma por navegador/dispositivo — celular e notebook são assinaturas diferentes. Notificar significa enviar para todas.

Assinaturas morrem. Quando ela limpa dados do navegador, reinstala, ou o navegador decide renovar, a assinatura antiga vira lixo. O serviço de push responde 404 ou 410 nesses casos, e a reação correta é apagar a assinatura do banco. Sem essa limpeza, você acumula endpoints mortos e tenta enviar para eles para sempre.

## 5.7 O service worker

É um script JavaScript que roda fora da página, no navegador, e continua vivo depois que a aba fecha. É ele que recebe o push e mostra a notificação — sem ele, Web Push não existe.

Duas responsabilidades no v1:

Receber o evento push e chamar a exibição da notificação com título e texto

Tratar o clique — abrir o app já no cartão certo, não na tela inicial. É um detalhe pequeno e é o que faz a notificação parecer útil em vez de decorativa

Ele mora em `frontend/src/sw.ts`, e junto com o `manifest.json` é o que torna o app instalável na tela inicial dela.

## 5.8 A notificação dentro do app

Ela pediu as duas: no celular e dentro do app. A segunda é bem mais simples — e reaproveita a infraestrutura da próxima etapa.

Quando o worker notifica um cartão, ele também emite um evento no canal em tempo real daquele usuário (Etapa 6). Se ela estiver com o app aberto, o aviso aparece ali na hora, sem recarregar.

Um detalhe de experiência: se o app estiver aberto, ela pode receber o push do sistema e o aviso na tela — redundante. Dá para detectar presença e suprimir um dos dois, mas isso adiciona coordenação. Para o v1, mandar os dois é aceitável, e vale observar no uso real se incomoda antes de complicar.

## 5.9 O que pode dar errado

| Situação | O que acontece | Como tratar |
|---|---|---|
| Ela nega a permissão | Não há assinatura | O app degrada para aviso in-app apenas — e deve deixar claro na interface |
| Serviço de push fora do ar | Envio falha | A flag não é marcada; o próximo ciclo tenta de novo |
| Assinatura expirada (404/410) | Envio recusado | Apagar a assinatura do banco |
| Worker fora do ar por horas | Avisos acumulam | O `<= now()` recupera; o limite de atraso evita a enxurrada |
| Cartão arquivado após agendado | Aviso não faz mais sentido | A consulta já filtra `arquivado = false` |

## 5.10 Como testar

Aqui a testabilidade muda de natureza pela primeira vez neste projeto: o envio depende de um serviço externo. A resposta é isolar a função de envio atrás de uma interface e substituí-la por um dublê nos testes — você testa a lógica, não a rede.

O que dá para testar de verdade:

- O worker seleciona cartões com `notificar_em` vencido e `notificado = false`
- Ignora arquivados, sem prazo, e já notificados
- Após envio bem-sucedido, `notificado` vira `true`
- Após envio com falha, `notificado` permanece `false` — o teste que prova a decisão da 5.4
- Um cartão com várias assinaturas envia para todas
- Assinatura que responde 410 é removida do banco
- Avisos atrasados além do limite são marcados sem enviar
- Rodar o worker duas vezes seguidas não envia duplicado

O último é o teste de assinatura da etapa. Ele é o que prova a idempotência — e é fácil de escrever, porque basta chamar o laço duas vezes e contar os envios.

## 5.11 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Worker** | Processo separado da API, que executa trabalho por tempo, não por requisição |
| **Idempotência** | Propriedade de uma operação que, repetida, não muda o resultado |
| **Pelo menos uma vez** | Semântica que tolera duplicata para nunca perder — a escolha do v1 |
| **Web Push** | Padrão que permite ao servidor enviar notificação ao navegador com o app fechado |
| **Assinatura** (*subscription*) | Endpoint + chaves que o navegador gera e o backend guarda |
| **Serviço de push** | Intermediário do navegador (ex.: Google) que entrega a mensagem ao dispositivo |
| **VAPID** | Par de chaves que identifica seu servidor perante o serviço de push |
| **Service worker** | Script que roda fora da página e sobrevive ao fechamento da aba |

## 5.12 Notas soltas desta etapa

A intuição sobre Web Push está errada, e vale desfazer (5.5): seu servidor não envia nada para o celular dela. Você entrega a mensagem criptografada ao serviço de push do navegador (o Google, no caso do Chrome), e ele leva. É justamente isso que faz a notificação chegar com o app fechado. E não precisa de conta no Firebase — Web Push com VAPID é padrão aberto.

A decisão de idempotência (5.4) é uma escolha de domínio, não de técnica. Marcar `notificado` antes de enviar arrisca perder o aviso; marcar depois arrisca duplicar. Escolhi pelo menos uma vez porque receber o lembrete duas vezes irrita um pouco, mas não receber significa perder um prazo. Num app pessoal, o erro tolerável é claro. Vale comentar isso no código, porque parece descuido para quem lê depois.

O `<= now()` em vez de uma janela de tempo (5.3) é o que torna o worker resistente a queda: se ele ficar fora do ar três horas, ao voltar encontra tudo que ficou para trás. Uma janela perderia esses avisos em silêncio. O efeito colateral — enxurrada de avisos antigos se o app ficar dias fora — se resolve com um limite de atraso.

Assinaturas morrem, e limpar é obrigatório (5.6). Quando ela limpar dados do navegador ou reinstalar, a assinatura vira lixo e o serviço de push responde 410. A reação correta é apagar do banco — senão você acumula endpoints mortos e tenta enviar para eles indefinidamente.

E uma consequência que vem de duas etapas atrás: a consulta do worker é simples porque a Etapa 4 materializou `notificar_em`. Sem aquela decisão, essa etapa começaria com uma conta entre colunas e um índice de expressão. Decisões de modelagem pagam ou cobram mais tarde — de novo.

O teste de assinatura desta etapa é o mais fácil de escrever e o mais valioso: rodar o laço duas vezes seguidas e contar os envios. Se der dois, a idempotência está quebrada.

---

## Próxima etapa

**Etapa 6 — Tempo real:** WebSocket e atualização otimista — a peça que faz o app parecer vivo, e que a Etapa 3 (posições absolutas, não relativas) deixou pronta para ser fácil.
