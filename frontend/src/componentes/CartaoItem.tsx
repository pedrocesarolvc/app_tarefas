import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { CSSProperties } from "react";
import type { Cartao } from "../api/tipos";
import { formatarPrazo } from "./utilCartao";

interface Props {
  cartao: Cartao;
  acento: { cor: string; corFraca: string };
  /** True só durante o meio segundo depois que este cartão pousou num
   * lugar novo -- dispara a animação de pulso (ver kanban.css,
   * `.cartao--pousou`). Controlado pelo QuadroKanban, não por este
   * componente: quem sabe quando um arrasto terminou é quem ouve o
   * `onDragEnd` do dnd-kit. */
  acabouDePousar: boolean;
}

/**
 * Um cartão dentro de uma coluna. `useSortable` (dnd-kit) é quem dá a ele
 * a capacidade de ser arrastado E de servir como alvo de soltura para
 * outros cartões -- os dois papéis ao mesmo tempo, que é como
 * reordenar-dentro-da-lista funciona.
 *
 * Enquanto ESTE cartão está sendo arrastado, `isDragging` fica true e ele
 * vira um "espaço reservado" (contorno tracejado, sem conteúdo visível) --
 * a cópia que de fato segue o cursor é outro componente, CartaoFlutuante,
 * renderizado à parte dentro do `<DragOverlay>` do QuadroKanban. Esse é o
 * padrão recomendado do dnd-kit, e também é o que permite a "cópia
 * flutuante" ter uma sombra/rotação sem afetar o layout da lista embaixo
 * dela.
 */
export default function CartaoItem({ cartao, acento, acabouDePousar }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: cartao.id,
  });

  const estilo = {
    transform: CSS.Transform.toString(transform),
    transition,
    "--acento-cor": acento.cor,
    "--acento-cor-fraca": acento.corFraca,
  } as CSSProperties;

  const classes = ["cartao", isDragging && "cartao--espaco-reservado", acabouDePousar && "cartao--pousou"]
    .filter(Boolean)
    .join(" ");

  const vencido = cartao.prazo !== null && !cartao.notificado && new Date(cartao.prazo).getTime() < Date.now();

  return (
    <div ref={setNodeRef} style={estilo} className={classes} {...attributes} {...listeners}>
      <div className="cartao__titulo">{cartao.titulo}</div>
      {cartao.prazo && (
        <span className={`cartao__prazo ${vencido ? "cartao__prazo--vencido" : ""}`}>
          {formatarPrazo(cartao.prazo)}
        </span>
      )}
    </div>
  );
}
