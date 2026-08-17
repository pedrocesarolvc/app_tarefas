import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useState, type CSSProperties, type KeyboardEvent } from "react";
import type { Cartao, Lista } from "../api/tipos";
import CartaoItem from "./CartaoItem";
import { acentoParaIndice } from "./utilCartao";

interface Props {
  lista: Lista;
  indice: number;
  cartoes: Cartao[];
  cartaoQueAcabouDePousar: number | null;
  onCriarCartao: (listaId: number, titulo: string) => void;
  onAbrirCartao: (cartao: Cartao) => void;
}

/**
 * Uma coluna do quadro. `useDroppable` no contêiner da lista de cartões
 * é o que permite soltar um cartão numa coluna VAZIA -- os cartões
 * individuais (via `useSortable`, dentro de CartaoItem) já servem como
 * alvo entre si, mas uma coluna sem nenhum cartão não tem nenhum alvo
 * "entre" -- precisa do próprio contêiner como alvo de reserva.
 */
export default function ColunaLista({
  lista,
  indice,
  cartoes,
  cartaoQueAcabouDePousar,
  onCriarCartao,
  onAbrirCartao,
}: Props) {
  const acento = acentoParaIndice(indice);
  const { setNodeRef, isOver } = useDroppable({
    id: `lista-${lista.id}`,
    data: { tipo: "lista", listaId: lista.id },
  });
  const [criando, setCriando] = useState(false);
  const [titulo, setTitulo] = useState("");

  function confirmarCriacao() {
    const valor = titulo.trim();
    if (valor) onCriarCartao(lista.id, valor);
    setTitulo("");
    setCriando(false);
  }

  function aoTeclar(evento: KeyboardEvent<HTMLInputElement>) {
    if (evento.key === "Enter") confirmarCriacao();
    if (evento.key === "Escape") {
      setTitulo("");
      setCriando(false);
    }
  }

  const estiloAcento = { "--acento-cor": acento.cor } as CSSProperties;

  return (
    <div className={`coluna ${isOver ? "coluna--sobrevoada" : ""}`} style={estiloAcento}>
      <div className="coluna__cabecalho">
        <span className="coluna__ponto" />
        <span className="coluna__nome">{lista.nome}</span>
        <span className="coluna__contagem">{cartoes.length}</span>
      </div>

      <div ref={setNodeRef} className="coluna__lista">
        <SortableContext items={cartoes.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          {cartoes.map((cartao) => (
            <CartaoItem
              key={cartao.id}
              cartao={cartao}
              acento={acento}
              acabouDePousar={cartaoQueAcabouDePousar === cartao.id}
              onAbrir={() => onAbrirCartao(cartao)}
            />
          ))}
        </SortableContext>
      </div>

      <div className="coluna__rodape">
        {criando ? (
          <input
            autoFocus
            className="entrada-cartao"
            value={titulo}
            onChange={(evento) => setTitulo(evento.target.value)}
            onBlur={confirmarCriacao}
            onKeyDown={aoTeclar}
            placeholder="Título do cartão"
          />
        ) : (
          <button type="button" className="botao-adicionar" onClick={() => setCriando(true)}>
            + Adicionar cartão
          </button>
        )}
      </div>
    </div>
  );
}
