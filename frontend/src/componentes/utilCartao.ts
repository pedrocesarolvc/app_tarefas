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

/** `aviso_previo` sempre volta da API como uma duração ISO 8601
 * ("PT1H", "P1D", "PT0S") -- é assim que o Pydantic serializa um
 * `timedelta` (backend/app/schemas/cartao.py). Converte para segundos,
 * o formato mais fácil de usar num <select> no formulário do cartão. */
export function duracaoIsoParaSegundos(iso: string): number {
  const partes = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$/.exec(iso);
  if (!partes) return 0;
  const [, dias, horas, minutos, segundos] = partes;
  return (
    Number(dias ?? 0) * 86400 +
    Number(horas ?? 0) * 3600 +
    Number(minutos ?? 0) * 60 +
    Number(segundos ?? 0)
  );
}

/** Converte um `Date` de um `<input type="datetime-local">` (sem fuso,
 * horário local) para o ISO 8601 em UTC que a API espera -- `null` se o
 * campo estiver vazio (o prazo é opcional, Etapa 4.6). */
export function datetimeLocalParaIso(valor: string): string | null {
  if (!valor) return null;
  return new Date(valor).toISOString();
}

/** O inverso: um ISO 8601 (sempre UTC, vindo da API) para o formato que
 * `<input type="datetime-local">` espera ("AAAA-MM-DDTHH:mm", em horário
 * local, sem fuso). */
export function isoParaDatetimeLocal(iso: string | null): string {
  if (!iso) return "";
  const data = new Date(iso);
  const comFusoDescontado = new Date(data.getTime() - data.getTimezoneOffset() * 60_000);
  return comFusoDescontado.toISOString().slice(0, 16);
}
