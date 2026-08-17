import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type UniqueIdentifier,
} from "@dnd-kit/core";
import { arrayMove, sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { auth, cartoes, listas, quadros } from "../api/cliente";
import type { Cartao, Lista, Quadro } from "../api/tipos";
import CartaoFlutuante from "../componentes/CartaoFlutuante";
import ColunaLista from "../componentes/ColunaLista";
import { acentoParaIndice } from "../componentes/utilCartao";
import "../estilos/kanban.css";

/** Acha em qual lista (container) um id -- de um cartão, ou de uma
 * coluna vazia identificada como "lista-{id}" -- está agora. É o mesmo
 * truque usado em todo exemplo multi-contêiner do dnd-kit: sem um id de
 * contêiner "de reserva", não haveria como soltar um cartão numa coluna
 * que ainda não tem nenhum cartão dentro. */
function containerDoId(id: UniqueIdentifier, mapa: Record<number, Cartao[]>): number | undefined {
  if (typeof id === "string" && id.startsWith("lista-")) {
    return Number(id.slice("lista-".length));
  }
  const alvo = Number(id);
  return Object.keys(mapa)
    .map(Number)
    .find((listaId) => mapa[listaId].some((cartao) => cartao.id === alvo));
}

export default function QuadroKanban({ onSair }: { onSair: () => void }) {
  const [quadrosDisponiveis, setQuadrosDisponiveis] = useState<Quadro[]>([]);
  const [quadroAtual, setQuadroAtual] = useState<Quadro | null>(null);
  const [listasOrdenadas, setListasOrdenadas] = useState<Lista[]>([]);
  const [cartoesPorLista, setCartoesPorLista] = useState<Record<number, Cartao[]>>({});
  const [carregando, setCarregando] = useState(true);
  const [cartaoAtivo, setCartaoAtivo] = useState<Cartao | null>(null);
  const [cartaoQueAcabouDePousar, setCartaoQueAcabouDePousar] = useState<number | null>(null);
  const [criandoLista, setCriandoLista] = useState(false);
  const [nomeNovaLista, setNomeNovaLista] = useState("");

  // Guarda de qual lista o cartão partiu, capturado no início do arrasto
  // -- necessário porque, assim que o cursor passa por cima de outra
  // coluna, o estado local (a pré-visualização otimista) já move o
  // cartão para lá, mas a API ainda não sabe disso: a rota de mover
  // (Etapa 3) precisa da lista de ORIGEM de verdade na URL.
  const origemArrasteRef = useRef<number | null>(null);

  const sensores = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  useEffect(() => {
    quadros.listar().then((lista) => {
      setQuadrosDisponiveis(lista);
      if (lista.length > 0) void carregarQuadro(lista[0]);
      else setCarregando(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function carregarQuadro(quadro: Quadro) {
    setCarregando(true);
    setQuadroAtual(quadro);
    const listasDoQuadro = await listas.listar(quadro.id);
    const cartoesCarregados = await Promise.all(
      listasDoQuadro.map((lista) => cartoes.listar(quadro.id, lista.id))
    );
    const mapa: Record<number, Cartao[]> = {};
    listasDoQuadro.forEach((lista, indice) => {
      mapa[lista.id] = cartoesCarregados[indice];
    });
    setListasOrdenadas(listasDoQuadro);
    setCartoesPorLista(mapa);
    setCarregando(false);
  }

  async function criarQuadro(nome: string) {
    const novo = await quadros.criar(nome);
    setQuadrosDisponiveis((atual) => [...atual, novo]);
    await carregarQuadro(novo);
  }

  async function criarLista(nome: string) {
    if (!quadroAtual) return;
    const nova = await listas.criar(quadroAtual.id, nome);
    setListasOrdenadas((atual) => [...atual, nova]);
    setCartoesPorLista((atual) => ({ ...atual, [nova.id]: [] }));
  }

  async function criarCartao(listaId: number, titulo: string) {
    if (!quadroAtual) return;
    const novo = await cartoes.criar(quadroAtual.id, listaId, titulo);
    setCartoesPorLista((atual) => ({ ...atual, [listaId]: [...atual[listaId], novo] }));
  }

  function aoComecarArrasto(evento: DragStartEvent) {
    const container = containerDoId(evento.active.id, cartoesPorLista);
    origemArrasteRef.current = container ?? null;
    const id = Number(evento.active.id);
    const cartao = container !== undefined ? cartoesPorLista[container].find((c) => c.id === id) : undefined;
    setCartaoAtivo(cartao ?? null);
  }

  /** Move o cartão de pré-visualização entre colunas ENQUANTO arrasta --
   * puramente visual (otimista); a escrita de verdade só acontece em
   * `aoTerminarArrasto`. É o padrão multi-contêiner recomendado pelo
   * dnd-kit: sem isso, o cartão só "salta" de coluna no instante de
   * soltar, em vez de acompanhar o cursor. */
  function aoArrastarSobre(evento: DragOverEvent) {
    const { active, over } = evento;
    if (!over) return;
    const containerAtivo = containerDoId(active.id, cartoesPorLista);
    const containerSobre = containerDoId(over.id, cartoesPorLista);
    if (containerAtivo === undefined || containerSobre === undefined || containerAtivo === containerSobre) return;

    setCartoesPorLista((atual) => {
      const origem = atual[containerAtivo];
      const destino = atual[containerSobre];
      const cartaoMovido = origem.find((c) => c.id === Number(active.id));
      if (!cartaoMovido) return atual;

      const novaOrigem = origem.filter((c) => c.id !== cartaoMovido.id);
      const indiceSobre = destino.findIndex((c) => c.id === Number(over.id));
      const posicaoDeInsercao = indiceSobre >= 0 ? indiceSobre : destino.length;
      const novoDestino = [...destino.slice(0, posicaoDeInsercao), cartaoMovido, ...destino.slice(posicaoDeInsercao)];

      return { ...atual, [containerAtivo]: novaOrigem, [containerSobre]: novoDestino };
    });
  }

  async function aoTerminarArrasto(evento: DragEndEvent) {
    const { over } = evento;
    const cartaoArrastado = cartaoAtivo;
    const listaDeOrigem = origemArrasteRef.current;
    setCartaoAtivo(null);
    origemArrasteRef.current = null;
    if (!over || !cartaoArrastado || listaDeOrigem === null || !quadroAtual) return;

    const containerFinal = containerDoId(over.id, cartoesPorLista);
    if (containerFinal === undefined) return;

    const listaFinal = cartoesPorLista[containerFinal];
    const indiceAtivo = listaFinal.findIndex((c) => c.id === cartaoArrastado.id);
    let indiceAlvo = listaFinal.findIndex((c) => c.id === Number(over.id));
    if (indiceAlvo === -1) indiceAlvo = listaFinal.length - 1;

    const listaReordenada =
      indiceAtivo !== -1 && indiceAtivo !== indiceAlvo ? arrayMove(listaFinal, indiceAtivo, indiceAlvo) : listaFinal;

    setCartoesPorLista((atual) => ({ ...atual, [containerFinal]: listaReordenada }));

    const posicaoFinal = listaReordenada.findIndex((c) => c.id === cartaoArrastado.id);
    const vizinhoAnterior = listaReordenada[posicaoFinal - 1];
    const vizinhoPosterior = listaReordenada[posicaoFinal + 1];

    try {
      const cartaoConfirmado = await cartoes.mover(quadroAtual.id, listaDeOrigem, cartaoArrastado.id, {
        lista_id: containerFinal,
        anterior_id: vizinhoAnterior?.id,
        posterior_id: vizinhoPosterior?.id,
      });
      setCartoesPorLista((atual) => ({
        ...atual,
        [containerFinal]: atual[containerFinal].map((c) => (c.id === cartaoConfirmado.id ? cartaoConfirmado : c)),
      }));
      // Dispara o pulso de "pousou" (Etapa: animação ao colocar o
      // cartão) e desliga sozinho meio segundo depois -- é só um estado
      // temporário, não algo que precise ser limpo manualmente em outro
      // lugar.
      setCartaoQueAcabouDePousar(cartaoConfirmado.id);
      setTimeout(() => {
        setCartaoQueAcabouDePousar((atual) => (atual === cartaoConfirmado.id ? null : atual));
      }, 600);
    } catch {
      // A escrita falhou: descarta a mudança otimista recarregando do
      // servidor, para nunca deixar a tela mentir sobre o que a API tem
      // (a mesma preocupação da Etapa 6.6 — aqui resolvida com uma
      // recarga completa, já que o cliente ainda não guarda o estado
      // anterior para uma reversão cirúrgica).
      void carregarQuadro(quadroAtual);
    }
  }

  function aoTeclarNovaLista(evento: KeyboardEvent<HTMLInputElement>) {
    if (evento.key === "Enter") confirmarNovaLista();
    if (evento.key === "Escape") {
      setNomeNovaLista("");
      setCriandoLista(false);
    }
  }

  function confirmarNovaLista() {
    const nome = nomeNovaLista.trim();
    if (nome) void criarLista(nome);
    setNomeNovaLista("");
    setCriandoLista(false);
  }

  async function sair() {
    await auth.logout();
    onSair();
  }

  if (carregando && quadrosDisponiveis.length === 0) {
    return <TelaVazia mensagem="Carregando..." />;
  }

  if (!carregando && !quadroAtual) {
    return <TelaSemQuadro aoCriar={criarQuadro} aoSair={sair} />;
  }

  return (
    <div className="pagina-quadro">
      <header className="cabecalho-quadro">
        <div className="cabecalho-quadro__titulo">
          <span>📋</span>
          {quadroAtual && (
            <select
              className="cabecalho-quadro__seletor"
              value={quadroAtual.id}
              onChange={(evento) => {
                const escolhido = quadrosDisponiveis.find((q) => q.id === Number(evento.target.value));
                if (escolhido) void carregarQuadro(escolhido);
              }}
            >
              {quadrosDisponiveis.map((quadro) => (
                <option key={quadro.id} value={quadro.id}>
                  {quadro.nome}
                </option>
              ))}
            </select>
          )}
        </div>
        <button type="button" className="botao-fantasma" onClick={sair}>
          Sair
        </button>
      </header>

      <DndContext
        sensors={sensores}
        collisionDetection={closestCorners}
        onDragStart={aoComecarArrasto}
        onDragOver={aoArrastarSobre}
        onDragEnd={aoTerminarArrasto}
      >
        <div className="quadro-kanban">
          {listasOrdenadas.map((lista, indice) => (
            <ColunaLista
              key={lista.id}
              lista={lista}
              indice={indice}
              cartoes={cartoesPorLista[lista.id] ?? []}
              cartaoQueAcabouDePousar={cartaoQueAcabouDePousar}
              onCriarCartao={criarCartao}
            />
          ))}

          {criandoLista ? (
            <input
              autoFocus
              className="entrada-cartao"
              style={{ flex: "0 0 220px" }}
              value={nomeNovaLista}
              onChange={(evento) => setNomeNovaLista(evento.target.value)}
              onBlur={confirmarNovaLista}
              onKeyDown={aoTeclarNovaLista}
              placeholder="Nome da lista"
            />
          ) : (
            <button type="button" className="coluna-nova" onClick={() => setCriandoLista(true)}>
              + Nova lista
            </button>
          )}
        </div>

        <DragOverlay>
          {cartaoAtivo && (
            <CartaoFlutuante
              cartao={cartaoAtivo}
              acento={acentoParaIndice(listasOrdenadas.findIndex((l) => l.id === cartaoAtivo.lista_id))}
            />
          )}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

function TelaVazia({ mensagem }: { mensagem: string }) {
  return (
    <div className="pagina-quadro" style={{ alignItems: "center", justifyContent: "center", color: "var(--cor-texto-fraco)" }}>
      {mensagem}
    </div>
  );
}

function TelaSemQuadro({ aoCriar, aoSair }: { aoCriar: (nome: string) => Promise<void>; aoSair: () => void }) {
  const [nome, setNome] = useState("");
  return (
    <div className="pagina-quadro" style={{ alignItems: "center", justifyContent: "center", gap: 12 }}>
      <p style={{ color: "var(--cor-texto-fraco)" }}>Você ainda não tem nenhum quadro.</p>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          className="entrada-cartao"
          style={{ width: 220 }}
          value={nome}
          onChange={(evento) => setNome(evento.target.value)}
          placeholder="Nome do quadro (ex.: Casa)"
        />
        <button
          type="button"
          className="botao-fantasma"
          onClick={() => {
            if (nome.trim()) void aoCriar(nome.trim());
          }}
        >
          Criar
        </button>
      </div>
      <button type="button" className="botao-fantasma" onClick={aoSair}>
        Sair
      </button>
    </div>
  );
}
