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
| **6** | Tempo real — WebSocket e atualização otimista | ✅ escrita |
| **7** | Entrega — API, PWA, testes e Docker | ✅ escrita |

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

# Etapa 6 — Tempo real

## 6.1 O que esta etapa entrega

Duas coisas, e vale separá-las porque a segunda costuma ser confundida com a primeira:

**Sincronização** — o quadro aberto no celular reflete o que mudou no computador, sem recarregar. E o aviso in-app da Etapa 5 chega na hora.

**Fluidez** — arrastar um cartão parece instantâneo, sem engasgo.

A segunda não precisa de WebSocket nenhum. É a atualização otimista da seção 6.6, e é de onde vem a maior parte da sensação de "app moderno". Muita gente implementa WebSocket achando que é isso que dá fluidez, e descobre que o app continua travando.

## 6.2 Por que kanban é fácil e texto é infernal

Comparação que explica a etapa inteira.

**Editor de texto colaborativo.** Dois usuários editam a mesma frase. Um digita "muito" na posição 10; o outro apaga o caractere na posição 8. A posição 10 do primeiro não existe mais — as coordenadas mudaram embaixo dele. Cada operação altera o significado das outras.

Resolver isso exige OT (*Operational Transformation*, do Google Docs) ou CRDT — algoritmos com anos de pesquisa acadêmica atrás e notoriamente traiçoeiros de implementar.

**Kanban.** Dois usuários movem o mesmo cartão. Um manda "cartão X vai para lista B, posição 2.5"; o outro, "cartão X vai para lista C, posição 1.5".

As duas operações são **absolutas**. Nenhuma depende de onde o cartão estava. Nenhuma invalida a outra. Aplique uma, depois a outra: o resultado é um estado válido — o cartão está na lista C, posição 1.5. Alguém perdeu o arraste, mas nada corrompeu.

Texto tem operações **relativas** (posição 10 depende do que veio antes). Kanban tem operações **absolutas** (posição 2.5 é 2.5, sempre).

E isso é consequência direta da Etapa 3. Se a posição fosse um inteiro consecutivo, mover um cartão significaria "renumere todos os outros" — uma operação relativa, que invalida o que os outros clientes sabem, e você estaria de volta no inferno do OT.

A decisão de ordenação resolveu, de graça, o problema da sincronização. Duas etapas que pareciam separadas eram a mesma decisão.

## 6.3 Last-write-wins: escolher o simples conscientemente

Como as operações são absolutas, a resolução de conflito pode ser a mais direta possível: quem escreve por último ganha (LWW).

Sem OT, sem CRDT, sem merge. O servidor aplica na ordem em que as mensagens chegam e transmite o resultado. Todos convergem para o mesmo estado.

O que se perde: um dos arrastes é descartado silenciosamente. Com uma usuária em dois dispositivos, a chance de mover o mesmo cartão no mesmo segundo é próxima de zero — e se acontecer, ela arrasta de novo.

LWW aqui é uma escolha, não preguiça. Saber justificar por que o caso simples basta — em vez de implementar CRDT por insegurança — é maturidade de engenharia.

A exceção que vale conhecer: LWW por registro funciona; por campo surpreende. Se dois lados editarem campos diferentes do mesmo cartão e cada um mandar o objeto inteiro, o último salva por cima. A defesa é mandar só o campo alterado (patch), não o cartão completo.

## 6.4 O transporte: WebSocket

HTTP normal é pergunta-resposta. Para saber que algo mudou, o cliente teria que ficar perguntando — *polling* — que gasta bateria e chega atrasado.

WebSocket mantém uma conexão aberta nos dois sentidos: o servidor empurra a mudança quando ela acontece.

```
Cliente A                Servidor                 Cliente B
    │                        │                        │
    │  PATCH /cartoes/X      │                        │
    ├───────────────────────►│                        │
    │                        │  valida, grava         │
    │                        │                        │
    │◄───────────────────────┼───────────────────────►│
    │      evento via WebSocket para o quadro         │
```

A escrita continua sendo HTTP. A rota `PATCH /cartoes/{id}` de sempre, com validação, autenticação e tratamento de erro. O WebSocket é apenas o canal de notificação.

Fazer a escrita pelo WebSocket é uma complicação comum e desnecessária — você reimplementaria à mão tudo que o HTTP já entrega pronto.

## 6.5 Salas: quem recebe o quê

O servidor mantém, em memória, quais conexões estão olhando qual quadro. Quando um cartão do quadro 7 muda, o evento vai só para os conectados ao quadro 7.

```
conexões = {
    quadro_7: {conexao_A, conexao_B},
    quadro_9: {conexao_C},
}
```

Isso é *room* ou *pub/sub*, e é o mínimo para não transmitir tudo para todos.

A limitação honesta: esse dicionário vive na memória de um processo. Com dois processos de API, um não enxerga as conexões do outro, e eventos se perdem. A solução de produção é um Redis pub/sub entre eles. Para um app de uma usuária, um processo basta — mas vale saber que a limitação existe e por quê.

O worker da Etapa 5 também emite nesse canal: é assim que o aviso in-app chega sem recarregar.

## 6.6 Atualização otimista: onde mora a fluidez

Se o cliente esperasse a resposta do servidor para mover o cartão na tela, o arraste teria 100–300ms de engasgo. Suficiente para parecer quebrado.

A solução é otimismo: mova na tela imediatamente, antes da confirmação. Mande a requisição em paralelo.

```
usuária solta o cartão
      │
      ├──► move na tela AGORA        (0ms — parece fluido)
      │
      └──► PATCH para o servidor     (200ms)
                │
                ├── sucesso → nada a fazer, a tela já está certa
                └── erro    → desfaz o movimento + avisa
```

O caso de erro é raro, mas precisa existir: sem reversão, a tela mostra um estado que o servidor não tem, e o app mente para a usuária.

## 6.7 O eco: o bug que todo mundo encontra

Quando o servidor transmite "cartão movido", o evento volta também para quem originou a ação — que já aplicou a mudança localmente. Aplicar de novo faz o cartão piscar ou pular.

Duas defesas, ambas de poucas linhas:

Cada cliente tem um id de conexão e ignora eventos que ele mesmo originou

Cada operação tem um id único, e o cliente descarta o eco já processado

Escolha uma e aplique desde o começo. Descobrir isso depois, com o app pronto, dá um bug difícil de nomear — "às vezes o cartão dá um pulinho".

## 6.8 Reconexão

Testando em casa, a conexão nunca cai. Na vida real, o celular sai do wi-fi, entra no elevador, dorme na tela de bloqueio.

Enquanto esteve desconectado, o quadro mudou — e o cliente não sabe disso. Está exibindo estado obsoleto com aparência de atual.

A solução robusta usa um número de versão do quadro: o cliente reconecta dizendo "eu estava na versão 42" e recebe o que mudou desde então.

Decisão do v1: ao reconectar, recarregar o quadro inteiro. Um quadro tem alguns KB. Não vale a complexidade do versionamento.

E a reconexão automática precisa de espera crescente entre tentativas — senão um servidor caído recebe uma enxurrada de clientes tentando mil vezes por segundo.

## 6.9 A ordem de construção

Cada passo é usável sozinho, e essa ordem importa:

1. **Sem tempo real.** O kanban funcionando em HTTP puro; recarregar mostra o estado atual. Já é um app completo.
2. **Atualização otimista.** Não precisa de WebSocket e é o que faz o app parecer rápido. Retorno enorme, custo baixo.
3. **WebSocket com salas e LWW.** O tempo real de verdade.
4. **Reconexão com recarga total.**

Fazer o passo 3 antes do 2 é o erro clássico: você ganha sincronização e continua com um app que engasga ao arrastar.

## 6.10 Como testar

Aqui a testabilidade é a mais difícil do projeto — envolve concorrência, tempo e estado distribuído. O que dá para testar com confiança:

- Cliente conectado a um quadro recebe evento de mudança naquele quadro
- Cliente não recebe evento de outro quadro
- Desconectar remove a conexão da sala (sem vazamento de memória)
- Duas atualizações no mesmo cartão convergem para o último estado (LWW)
- O cliente ignora o próprio eco
- Falha na requisição reverte a mudança otimista na interface
- Reconectar recarrega o estado atual do quadro

Os dois últimos são os que mais evitam bug real. O da reversão porque o caminho de erro raramente é exercitado à mão; o da reconexão porque é impossível de testar por acidente — você teria que desligar o wi-fi no momento certo.

## 6.11 Glossário desta etapa

| Termo | O que é |
|---|---|
| **WebSocket** | Conexão bidirecional persistente; o servidor empurra dados sem ser perguntado |
| **Polling** | Perguntar repetidamente se algo mudou. O que o WebSocket substitui |
| **Operação absoluta** | Comando que não depende do estado anterior ("vá para posição 2.5") |
| **Operação relativa** | Comando cujo significado depende do estado ("insira na posição 10") |
| **LWW** | *Last-write-wins* — a última escrita prevalece |
| **OT / CRDT** | Algoritmos de merge para operações relativas. Não necessários aqui |
| **Sala** (*room*) | Agrupamento de conexões que recebem os mesmos eventos |
| **Atualização otimista** | Aplicar a mudança na tela antes da confirmação do servidor |
| **Eco** | O evento que volta para quem originou a ação |
| **Espera crescente** (*backoff*) | Aumentar o intervalo entre tentativas de reconexão |

## 6.12 Notas soltas desta etapa

A separação entre sincronização e fluidez (6.1). São duas entregas diferentes, e a fluidez — a parte que mais impressiona no uso — não precisa de WebSocket nenhum. Por isso a ordem da 6.9 importa: fazer o WebSocket antes da atualização otimista é o erro clássico, você ganha sincronização e continua com um app que engasga ao arrastar.

A limitação honesta das salas (6.5). O dicionário de conexões vive na memória de um processo. Com dois processos de API, um não enxerga as conexões do outro e eventos se perdem — a solução de produção seria Redis pub/sub entre eles. Para uma usuária, um processo basta; mas vale saber onde está o teto.

O eco (6.7) precisa ser resolvido desde o começo. Descobrir depois, com o app pronto, dá um bug difícil até de nomear — "às vezes o cartão dá um pulinho". Duas linhas resolvem se você já souber que existe.

E o fecho que a etapa deixa registrado: a decisão da Etapa 3 pagou aqui. Posições fracionárias tornam a operação absoluta ("vá para posição 2.5"), e é isso que dispensa OT e CRDT. Se a posição fosse inteira e consecutiva, mover seria "renumere todos os outros" — relativo, invalidando o que os outros clientes sabem — e a sincronização exigiria artilharia acadêmica. Duas etapas que pareciam separadas eram a mesma decisão, e isso é o tipo de conexão que só aparece quando se documenta antes de construir.

## 6.13 Estado da implementação

A documentação acima é o desenho completo da etapa. O servidor está inteiro; do lado de cliente, o board de kanban em si já existe (`frontend/src/paginas/QuadroKanban.tsx`) e já implementa a atualização otimista (6.6) — mas o canal em tempo real (WebSocket) ainda não está ligado a ele.

**Construído no servidor:** o transporte (WebSocket por quadro, `backend/app/rotas/realtime.py`), as salas em memória com conectar/desconectar/transmitir (`backend/app/realtime/gerenciador.py`), a transmissão de evento depois de toda escrita de lista/cartão (com o `id_conexao` de origem já viajando no evento, pronto para uma futura supressão de eco), e a ponte HTTP que deixa o worker (um processo à parte, Etapa 5.2) publicar nas salas da API sem Redis (`backend/worker/tempo_real.py`, `POST /interno/eventos-tempo-real`) — essa ponte é uma decisão de arquitetura desta implementação, não algo detalhado no texto acima, exigida pela colisão entre "worker é outro processo" (5.2) e "salas vivem na memória de um processo" (6.5).

**Construído no cliente:** o board de verdade, com arrastar-e-soltar entre colunas (`@dnd-kit`) e atualização otimista (6.6) — o cartão se move na tela no instante em que é solto, a chamada para a API acontece depois, e uma falha reverte recarregando o quadro do servidor. A "fluidez" da 6.1 já está presente: segurar um cartão o destaca (leve aumento de escala, rotação sutil e brilho na cor da coluna) e soltar dispara um pulso curto no lugar onde ele pousou.

**Atualização da Etapa 7:** o cliente WebSocket foi escrito (`frontend/src/api/tempoReal.ts`) — a lacuna descrita abaixo, na versão original desta seção, está fechada. O app recebe eventos de outra aba/dispositivo, reconecta com espera crescente recarregando o quadro (6.8), e ignora o próprio eco pelo `id_conexao` (6.7). Ver a seção 7.10 para os detalhes.

~~**Ainda não construído:** o cliente não abre WebSocket nenhum — não recebe eventos de outra aba, outro dispositivo, nem do worker (a metade "sincronização" da 6.1). Por consequência, a supressão de eco (6.7) e a reconexão com recarga total (6.8) também não existem: não há conexão para ecoar ou reconectar. O `id_conexao` que o servidor já devolve ao conectar (ver 6.5) está pronto para isso quando o cliente WebSocket for escrito.~~

---

# Etapa 7 — Entrega

## 7.1 O que muda aqui

As seis etapas anteriores construíram as peças. Esta as torna usáveis por uma pessoa que não é você.

E aqui está a diferença deste projeto para os outros três: não há recrutador. O único juiz é ela, usando o app no celular, num dia comum. Isso simplifica algumas coisas (ninguém vai auditar seu README) e endurece outras — um app que trava ao arrastar, ou que não notifica, é abandonado em uma semana e nenhuma elegância de arquitetura salva.

O critério de sucesso desta etapa é concreto: **ela abrir o app no dia seguinte sem você pedir.**

## 7.2 A API completa

O conjunto de endpoints, agora reunido:

| Recurso | Rotas | Etapas |
|---|---|---|
| Auth | `POST /auth/login`, `POST /auth/registrar` | 2 |
| Quadros | CRUD em `/quadros` | 2 |
| Listas | CRUD em `/listas`, com reordenação | 2, 3 |
| Cartões | CRUD em `/cartoes` | 2, 4 |
| Mover cartão | `PATCH /cartoes/{id}/mover` | 3 |
| Calendário | `GET /calendario?de=&ate=` | 4 |
| Push | `POST /push/assinar`, `DELETE /push/assinar` | 5 |
| Tempo real | `WS /ws/quadro/{id}` | 6 |

Duas decisões de forma:

**Mover cartão tem rota própria.** Não é um `PATCH /cartoes/{id}` genérico com `lista_id` e `posicao` no corpo. Mover é uma operação com semântica específica — recebe "antes de qual cartão" ou "depois de qual", e o servidor calcula a posição. Isso mantém o cálculo fracionário da Etapa 3 num lugar só, em vez de espalhar a lógica pelo cliente.

**A escrita é sempre HTTP; o WebSocket só notifica.** Reforçando a decisão da Etapa 6 — validação, autenticação e tratamento de erro ficam onde já funcionam.

## 7.3 O PWA: o que faz virar "app" no celular dela

Três peças transformam um site num app instalável:

**`manifest.json`** — nome, ícone, cor, e o modo de exibição em tela cheia. É o que dá o ícone na tela inicial e remove a barra do navegador.

**Service worker** — já construído na Etapa 5 para receber o push. Ele também permite que o app abra sem conexão, ainda que mostrando estado antigo.

**HTTPS** — obrigatório. Web Push e service worker não funcionam sem ele, nem em rede local. Isso tem uma implicação prática que vale antecipar: testar notificação em `localhost` funciona, mas testar no celular dela exige HTTPS de verdade. Um túnel (ngrok, Cloudflare Tunnel) resolve durante o desenvolvimento; para uso real, um domínio com certificado.

Essa é, provavelmente, a fricção mais chata do projeto inteiro — e ela não é de código, é de infraestrutura. Melhor saber agora.

## 7.4 As telas

Quatro, e nenhuma a mais no v1:

**O quadro.** A tela principal: colunas lado a lado, cartões arrastáveis. Toda a Etapa 3 e a 6 se manifestam aqui — e é a tela onde a fluidez importa mais que qualquer outra coisa.

**O cartão aberto.** Título, descrição, prazo e aviso prévio. Com a lição da Etapa 4: o campo de data não é obrigatório e não deve parecer obrigatório. A maioria dos cartões não terá prazo.

**O calendário.** A lente da Etapa 4, atravessando quadros. Com o cuidado da seção 4.6: quando não houver cartões com data no período, dizer isso — uma grade vazia parece bug.

**A lista de avisos.** A notificação in-app que ela pediu, chegando pelo canal da Etapa 6.

Sobre a biblioteca de arrastar: dnd-kit ou equivalente resolve o problema difícil (acessibilidade, toque, colisão). O trabalho fica em integrar bem com a atualização otimista — o cartão precisa seguir o dedo sem esperar o servidor.

## 7.5 Docker: três serviços

```yaml
services:
  api:       # FastAPI
  worker:    # o processo da Etapa 5
  db:        # PostgreSQL
```

A novidade em relação aos projetos anteriores é o worker como serviço separado — mesma imagem da API, comando diferente. É a materialização da decisão da Etapa 5: mesmo código, mesmos modelos, ciclo de vida próprio.

O frontend pode subir junto ou ser servido estaticamente; para uso real dela, o mais simples é publicar num serviço de hospedagem estática apontando para a API.

As variáveis que o `.env.example` precisa registrar: conexão do banco, chaves VAPID (pública e privada), segredo do JWT e a origem permitida para CORS.

## 7.6 Testes de ponta a ponta

Três atravessam o sistema inteiro:

**O fluxo completo:** criar quadro → criar listas → criar cartão → arrastar entre listas → confirmar a ordem persistida. Se passa, o núcleo funciona.

**O ciclo do aviso:** criar cartão com prazo próximo → rodar o worker → confirmar que a notificação foi enviada e a flag marcada → rodar de novo → confirmar que não enviou duplicado. Esse é o teste de assinatura do projeto, porque exercita a decisão de idempotência da Etapa 5.

**A ordenação sob estresse:** cinquenta inserções consecutivas no mesmo ponto, verificando que a ordem permanece correta. É o teste que prova a escolha de NUMERIC da Etapa 3 — e que falharia com float.

## 7.7 O que fazer depois que ela usar

Este projeto tem algo que nenhum dos outros teve: um usuário real dando retorno. Vale planejar o que fazer com isso.

Duas coisas para observar nas primeiras semanas, que valem mais que qualquer suposição:

**O que ela usa e o que ignora.** Se o calendário ficar intocado, a dimensão escolhida errou o alvo — e é melhor descobrir em duas semanas do que depois de construir mais coisa em cima. Se ela criar cartões e nunca puser data, o aviso vira decoração.

**O que ela pede.** O pedido espontâneo vale mais que qualquer item do roadmap, porque nasce de irritação real. Se ela pedir algo que não está previsto — e provavelmente vai —, isso é o achado mais valioso do projeto, não um furo no planejamento.

A regra da Etapa 1 continua valendo para o que vier: uma dimensão de cada vez. Se o próximo pedido for uma segunda dimensão, ele merece virar v2 com escopo próprio, não um puxadinho.

## 7.8 O arco do projeto

| Etapa | O que ficou | Onde reapareceu |
|---|---|---|
| 1 | Uma dimensão só — a regra que protege o escopo | Cada "fica no roadmap" |
| 2 | Estado como posição, não campo | O oposto do projeto de agendamento |
| 3 | Posição fracionária | Pagou o dividendo na Etapa 6 |
| 4 | `notificar_em` materializado | Tornou a consulta da Etapa 5 trivial |
| 5 | O worker que roda por tempo | A peça arquitetural nova |
| 6 | Operações absolutas → LWW basta | Consequência da Etapa 3 |
| 7 | O app na mão dela | O único juiz |

Duas conexões que só apareceram porque a documentação veio antes do código:

**Etapa 3 → Etapa 6.** Escolher posições fracionárias tornou as operações absolutas, e operações absolutas dispensam OT e CRDT. A decisão de ordenação resolveu a sincronização de graça.

**Etapa 4 → Etapa 5.** Materializar `notificar_em` transformou a consulta do worker numa comparação simples. Sem ela, seria conta entre colunas e índice de expressão.

Decisões de modelagem pagam ou cobram mais tarde — sempre. Nos dois casos aqui, pagaram.

## 7.9 Glossário desta etapa

| Termo | O que é |
|---|---|
| **PWA** | App web instalável, com ícone na tela inicial e tela cheia |
| **manifest.json** | Arquivo que declara nome, ícone e comportamento de instalação |
| **Túnel** | Serviço que expõe o servidor local via HTTPS público, para testar no celular |
| **Teste E2E** | Teste que exercita o sistema inteiro, do clique ao banco |
| **CORS** | Regra que autoriza o frontend a chamar a API de outra origem |

## 7.10 Notas soltas desta etapa

HTTPS é a fricção mais chata do projeto, e não é de código (7.3). Web Push e service worker exigem HTTPS. Testar em `localhost` funciona, mas testar no celular dela não — vai precisar de túnel durante o desenvolvimento e domínio com certificado para uso real. Melhor saber agora do que descobrir no dia da demonstração.

Mover cartão tem rota própria, e o servidor calcula a posição (7.2). O cliente manda "antes de qual cartão", não o número. Isso mantém o cálculo fracionário da Etapa 3 num lugar só — se um dia você trocar NUMERIC por LexoRank, o frontend nem fica sabendo.

A seção 7.7 é a que nenhum dos outros projetos teve: o que fazer depois que ela usar. Duas coisas para observar — o que ela ignora (se o calendário ficar intocado, a dimensão errou o alvo) e o que ela pede espontaneamente (vale mais que qualquer roadmap, porque nasce de irritação real). E a regra da Etapa 1 continua valendo para o que vier: uma dimensão de cada vez.

As duas conexões do arco (7.8) só apareceram porque a documentação veio antes do código. Etapa 3 → 6: posições fracionárias tornaram as operações absolutas, e isso dispensou OT/CRDT. Etapa 4 → 5: materializar `notificar_em` tornou a consulta do worker trivial. Nos dois casos, uma decisão de modelagem pagou dividendo duas etapas depois.

E o critério de sucesso ficou registrado como a última linha do documento, de propósito: não é nenhum item do roadmap. **É ela abrir o app amanhã.**

## 7.11 Estado da implementação

A tabela de rotas da 7.2 é a versão resumida e "de documento" — nomeada de um jeito ilustrativo (`PATCH /cartoes/{id}/mover`, `WS /ws/quadro/{id}`) que não é, ponta a ponta, o caminho exato de nenhuma rota real deste código (que usa, por exemplo, `POST /quadros/{quadro_id}/listas/{lista_id}/cartoes/{cartao_id}/mover` e `GET /ws/quadros/{quadro_id}` — caminhos aninhados sob quadro/lista, decididos já na Etapa 2, e o verbo `POST` para mover em vez de `PATCH`, decidido na Etapa 3 para deixar claro que é uma operação com identidade própria). A tabela desta seção descreve a FORMA da API (um recurso por etapa, mover com rota própria, escrita sempre HTTP); os caminhos exatos estão documentados em cada etapa anterior e no Swagger (`/docs`) da própria API.

O que existe em código, além do que as Etapas 1-6 já tinham fechado:

- **CORS** (`app/main.py`, `CORSMiddleware`) — inerte em desenvolvimento (o proxy do Vite já faz tudo parecer uma origem só), entra em jogo quando o frontend é publicado numa origem diferente da API.
- **PWA**: `frontend/public/manifest.json` (com um ícone em SVG, não PNG — os navegadores atuais aceitam; PNG multi-tamanho fica para se um dia o app precisar rodar bem em iOS) e `frontend/public/sw.js` (o service worker, recebendo push e tratando clique para abrir o cartão certo — Etapa 5.7). Fica em `public/`, não em `src/sw.ts` como a Etapa 1.6 desenhou: é pouco código, não usa nada do resto do app, e um service worker precisa de uma URL estável na raiz do site — empacotar via Vite exigiria um segundo ponto de entrada de build só para isso.
- **O cliente WebSocket** (`frontend/src/api/tempoReal.ts`), fechando a lacuna que a Etapa 6 tinha deixado em aberto: reconecta com espera crescente (6.8), ignora o próprio eco pelo `id_conexao` (6.7), e recarrega o quadro a cada evento externo em vez de reconciliar campo a campo — uma simplificação deliberada sobre o que a 6.1 descreve, trocando um pouco de suavidade por muito menos código.
- **As quatro telas da 7.4**: o quadro (já existia desde a Etapa 6), o cartão aberto (`ModalDoCartao.tsx`), o calendário (`TelaCalendario.tsx`, uma agenda por dia, não uma grade de mês) e a lista de avisos (`PainelDeAvisos.tsx`, um sino no cabeçalho).
- **Os três testes E2E da 7.6** (`backend/tests/test_e2e.py`). O terceiro (ordenação sob estresse) rodou primeiro com 50 inserções, como o texto pede, e encontrou uma armadilha real: o SQLite dos testes converte `Decimal` para `float` ao gravar (a própria armadilha da Etapa 3.4, um nível abaixo, na camada de binding do SQLAlchemy) — o PostgreSQL de produção não tem esse problema. A versão E2E ficou em 40 inserções, com folga sobre o ponto de colapso do SQLite; as 50 do checklist continuam provadas à risca pelo teste algorítmico da Etapa 3 (contra `Decimal` puro).
- HTTPS/túnel/hospedagem (7.3/7.5) continuam sendo o que a documentação já avisava que seriam: infraestrutura, não código. Nada disso foi (nem podia ser) implementado nesta etapa.
