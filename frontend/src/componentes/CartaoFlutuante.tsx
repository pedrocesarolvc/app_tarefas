import type { CSSProperties } from "react";
import type { Cartao } from "../api/tipos";
import { formatarPrazo } from "./utilCartao";

/**
 * A cópia visual do cartão que segue o cursor enquanto ele está sendo
 * segurado -- vive dentro do `<DragOverlay>` do dnd-kit (ver
 * QuadroKanban.tsx), fora da árvore normal da lista, para poder ter sua
 * própria escala/rotação/sombra sem empurrar os cartões vizinhos.
 *
 * É aqui que a animação de "segurar" mora: `.cartao--flutuante`
 * (kanban.css) aumenta levemente a escala, inclina um pouco o cartão e
 * acende um brilho suave na cor da coluna -- poucos efeitos, só o
 * suficiente para o cartão se destacar do resto enquanto está no ar.
 */
export default function CartaoFlutuante({
  cartao,
  acento,
}: {
  cartao: Cartao;
  acento: { cor: string; corFraca: string };
}) {
  const estilo = {
    "--acento-cor": acento.cor,
    "--acento-cor-fraca": acento.corFraca,
  } as CSSProperties;

  return (
    <div className="cartao cartao--flutuando" style={estilo}>
      <div className="cartao__titulo">{cartao.titulo}</div>
      {cartao.prazo && <span className="cartao__prazo">{formatarPrazo(cartao.prazo)}</span>}
    </div>
  );
}
