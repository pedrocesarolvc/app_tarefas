/**
 * Cliente HTTP fino para a API (backend/app/rotas/*.py). Sem biblioteca
 * externa -- `fetch` já é suficiente para o que este app precisa, e
 * evita mais uma dependência só para isso.
 *
 * Dois modos, escolhidos por uma única variável de ambiente do Vite:
 *
 * - `VITE_API_URL` AUSENTE (desenvolvimento local): as chamadas vão para
 *   `/api/...`, reescrito para o backend pelo proxy do Vite (ver
 *   vite.config.ts), que também remove o prefixo `/api` antes de repassar
 *   -- por isso as rotas deste arquivo nunca incluem `/api` nelas mesmas.
 * - `VITE_API_URL` DEFINIDA (produção -- frontend e API em domínios
 *   diferentes): as chamadas vão direto para essa URL, sem proxy nenhum
 *   no meio -- por isso, aqui também, sem prefixo `/api` (a API nunca
 *   teve essa rota; `/api` só existia porque o proxy de desenvolvimento
 *   removia).
 *
 * `credentials: "include"` é necessário nos dois modos assim que a API
 * está numa origem diferente da página: sem isso, o navegador não manda
 * (nem aceita) o cookie de sessão em requisições entre origens, mesmo com
 * CORS liberado (ver app/config.py, `cookie_entre_sites`, no backend).
 */

import type { Cartao, Lista, Quadro, Usuario } from "./tipos";

const URL_BASE_DA_API = import.meta.env.VITE_API_URL ?? "/api";

export class ErroDeApi extends Error {
  constructor(
    public status: number,
    detalhe: string
  ) {
    super(detalhe);
  }
}

async function requisicao<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const resposta = await fetch(`${URL_BASE_DA_API}${caminho}`, {
    ...opcoes,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...opcoes.headers },
  });

  if (!resposta.ok) {
    // O backend sempre devolve {"detail": "..."} em erros (o padrão do
    // FastAPI) -- extrai isso quando existe, cai para o texto cru senão.
    const corpo = await resposta.json().catch(() => null);
    throw new ErroDeApi(resposta.status, corpo?.detail ?? resposta.statusText);
  }

  // 204 No Content (arquivar, apagar) não tem corpo para decodificar.
  if (resposta.status === 204) return undefined as T;
  return resposta.json();
}

/** Cabeçalho opcional presente em toda escrita que pode gerar eco (Etapa
 * 6.7) -- o id de conexão devolvido por `useCanalDoQuadro`
 * (api/tempoReal.ts). `undefined` quando não há canal em tempo real
 * aberto (ex.: a escrita aconteceu antes do WebSocket conectar); nesse
 * caso o evento simplesmente não carrega `origem`, e ninguém tem como
 * confundi-lo com eco -- comportamento correto, só sem a otimização. */
function cabecalhoDeOrigem(origemConexao?: string): HeadersInit | undefined {
  return origemConexao ? { "X-Origem-Conexao": origemConexao } : undefined;
}

// --- Autenticação (Etapa 1.4) ---

export const auth = {
  registrar: (email: string, senha: string) =>
    requisicao<Usuario>("/auth/registrar", { method: "POST", body: JSON.stringify({ email, senha }) }),

  login: (email: string, senha: string) =>
    requisicao<Usuario>("/auth/login", { method: "POST", body: JSON.stringify({ email, senha }) }),

  logout: () => requisicao<void>("/auth/logout", { method: "POST" }),

  eu: () => requisicao<Usuario>("/auth/eu"),
};

// --- Quadros (Etapa 2) ---

export const quadros = {
  listar: () => requisicao<Quadro[]>("/quadros"),
  criar: (nome: string) => requisicao<Quadro>("/quadros", { method: "POST", body: JSON.stringify({ nome }) }),
};

// --- Listas (Etapa 2 + Etapa 3) ---

export const listas = {
  listar: (quadroId: number) => requisicao<Lista[]>(`/quadros/${quadroId}/listas`),

  criar: (quadroId: number, nome: string, origemConexao?: string) =>
    requisicao<Lista>(`/quadros/${quadroId}/listas`, {
      method: "POST",
      headers: cabecalhoDeOrigem(origemConexao),
      body: JSON.stringify({ nome }),
    }),

  mover: (
    quadroId: number,
    listaId: number,
    vizinhos: { anterior_id?: number; posterior_id?: number },
    origemConexao?: string
  ) =>
    requisicao<Lista>(`/quadros/${quadroId}/listas/${listaId}/mover`, {
      method: "POST",
      headers: cabecalhoDeOrigem(origemConexao),
      body: JSON.stringify({
        lista_anterior_id: vizinhos.anterior_id ?? null,
        lista_posterior_id: vizinhos.posterior_id ?? null,
      }),
    }),
};

// --- Cartões (Etapa 2 + Etapa 3 + Etapa 4) ---

/** O que o modal de cartão (Etapa 7.4) edita -- os quatro campos de
 * conteúdo, todos opcionais porque é um PATCH (só o que mudou vai no
 * corpo; ver CartaoAtualizar, backend/app/schemas/cartao.py). */
export interface CamposDoCartao {
  titulo?: string;
  descricao?: string | null;
  prazo?: string | null;
  aviso_previo?: number | null;
}

export const cartoes = {
  listar: (quadroId: number, listaId: number) =>
    requisicao<Cartao[]>(`/quadros/${quadroId}/listas/${listaId}/cartoes`),

  criar: (quadroId: number, listaId: number, titulo: string, origemConexao?: string) =>
    requisicao<Cartao>(`/quadros/${quadroId}/listas/${listaId}/cartoes`, {
      method: "POST",
      headers: cabecalhoDeOrigem(origemConexao),
      body: JSON.stringify({ titulo }),
    }),

  atualizar: (
    quadroId: number,
    listaId: number,
    cartaoId: number,
    campos: CamposDoCartao,
    origemConexao?: string
  ) =>
    requisicao<Cartao>(`/quadros/${quadroId}/listas/${listaId}/cartoes/${cartaoId}`, {
      method: "PATCH",
      headers: cabecalhoDeOrigem(origemConexao),
      body: JSON.stringify(campos),
    }),

  mover: (
    quadroId: number,
    listaOrigemId: number,
    cartaoId: number,
    destino: { lista_id: number; anterior_id?: number; posterior_id?: number },
    origemConexao?: string
  ) =>
    requisicao<Cartao>(`/quadros/${quadroId}/listas/${listaOrigemId}/cartoes/${cartaoId}/mover`, {
      method: "POST",
      headers: cabecalhoDeOrigem(origemConexao),
      body: JSON.stringify({
        lista_id: destino.lista_id,
        cartao_anterior_id: destino.anterior_id ?? null,
        cartao_posterior_id: destino.posterior_id ?? null,
      }),
    }),

  arquivar: (quadroId: number, listaId: number, cartaoId: number, origemConexao?: string) =>
    requisicao<Cartao>(`/quadros/${quadroId}/listas/${listaId}/cartoes/${cartaoId}/arquivar`, {
      method: "POST",
      headers: cabecalhoDeOrigem(origemConexao),
    }),
};

// --- Calendário (Etapa 4.5) ---

export const calendario = {
  /** `de`/`ate` em ISO 8601. Atravessa todos os quadros do usuário por
   * padrão (Etapa 4.5) -- `quadroId` é o filtro opcional que a própria
   * rota já previa. */
  listar: (de: string, ate: string, quadroId?: number) => {
    const parametros = new URLSearchParams({ de, ate });
    if (quadroId !== undefined) parametros.set("quadro_id", String(quadroId));
    return requisicao<Cartao[]>(`/calendario?${parametros.toString()}`);
  },
};
