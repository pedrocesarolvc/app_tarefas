/**
 * Cliente HTTP fino para a API (backend/app/rotas/*.py). Sem biblioteca
 * externa -- `fetch` já é suficiente para o que este app precisa, e
 * evita mais uma dependência só para isso.
 *
 * Todas as chamadas passam por `/api/...`, reescrito para o backend pelo
 * proxy do Vite (ver vite.config.ts) -- o código aqui nunca precisa saber
 * a URL real da API, nem em desenvolvimento nem quando isso mudar depois.
 */

import type { Cartao, Lista, Quadro, Usuario } from "./tipos";

export class ErroDeApi extends Error {
  constructor(
    public status: number,
    detalhe: string
  ) {
    super(detalhe);
  }
}

async function requisicao<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const resposta = await fetch(`/api${caminho}`, {
    ...opcoes,
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

  criar: (quadroId: number, nome: string) =>
    requisicao<Lista>(`/quadros/${quadroId}/listas`, { method: "POST", body: JSON.stringify({ nome }) }),

  mover: (quadroId: number, listaId: number, vizinhos: { anterior_id?: number; posterior_id?: number }) =>
    requisicao<Lista>(`/quadros/${quadroId}/listas/${listaId}/mover`, {
      method: "POST",
      body: JSON.stringify({
        lista_anterior_id: vizinhos.anterior_id ?? null,
        lista_posterior_id: vizinhos.posterior_id ?? null,
      }),
    }),
};

// --- Cartões (Etapa 2 + Etapa 3 + Etapa 4) ---

export const cartoes = {
  listar: (quadroId: number, listaId: number) =>
    requisicao<Cartao[]>(`/quadros/${quadroId}/listas/${listaId}/cartoes`),

  criar: (quadroId: number, listaId: number, titulo: string) =>
    requisicao<Cartao>(`/quadros/${quadroId}/listas/${listaId}/cartoes`, {
      method: "POST",
      body: JSON.stringify({ titulo }),
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
      headers: origemConexao ? { "X-Origem-Conexao": origemConexao } : undefined,
      body: JSON.stringify({
        lista_id: destino.lista_id,
        cartao_anterior_id: destino.anterior_id ?? null,
        cartao_posterior_id: destino.posterior_id ?? null,
      }),
    }),
};
