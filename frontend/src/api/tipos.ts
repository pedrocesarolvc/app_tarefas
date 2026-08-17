/**
 * Tipos TypeScript que espelham os schemas Pydantic do backend
 * (backend/app/schemas/*.py). Mantidos de propósito em espelho, campo a
 * campo -- se um schema do backend mudar, este arquivo precisa mudar
 * junto, e o TypeScript aponta os lugares que quebraram.
 *
 * `posicao` é `string`, não `number`: o backend guarda um `Decimal`
 * (Etapa 3.6, NUMERIC de precisão arbitrária) e o Pydantic serializa
 * Decimal como string em JSON, exatamente para não perder precisão ao
 * passar por um `number` de 64 bits do JavaScript. O frontend nunca faz
 * conta com `posicao` -- só usa a ordem em que a API já devolve os
 * itens -- então isso nunca precisa virar `number` aqui.
 */

export interface Usuario {
  id: number;
  email: string;
  criado_em: string;
}

export interface Quadro {
  id: number;
  nome: string;
  criado_em: string;
}

export interface Lista {
  id: number;
  quadro_id: number;
  nome: string;
  posicao: string;
  arquivado: boolean;
  criado_em: string;
}

export interface Cartao {
  id: number;
  lista_id: number;
  titulo: string;
  descricao: string | null;
  posicao: string;
  prazo: string | null;
  aviso_previo: string | null;
  notificar_em: string | null;
  notificado: boolean;
  arquivado: boolean;
  criado_em: string;
}
