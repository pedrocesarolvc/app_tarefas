/** Pequenos utilitários compartilhados entre CartaoItem e CartaoFlutuante. */

const QUANTIDADE_DE_ACENTOS = 7;

/** A cor de acento de uma coluna, pela posição dela no quadro -- não pelo
 * nome. O kanban não tem estados fixos (Etapa 2.3), então não faz sentido
 * mapear "vermelho = travado"; isso aqui é só variedade visual. */
export function acentoParaIndice(indice: number): { cor: string; corFraca: string } {
  const n = (indice % QUANTIDADE_DE_ACENTOS) + 1;
  return { cor: `var(--acento-${n})`, corFraca: `var(--acento-${n}-fraca)` };
}

export function formatarPrazo(prazoIso: string): string {
  const data = new Date(prazoIso);
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
