import { useState, type FormEvent, type MouseEvent } from "react";
import { cartoes, type CamposDoCartao } from "../api/cliente";
import type { Cartao } from "../api/tipos";
import { datetimeLocalParaIso, duracaoIsoParaSegundos, isoParaDatetimeLocal } from "./utilCartao";
import "../estilos/modal.css";

/** Opções de aviso prévio (Etapa 4.2) em segundos -- o formato que a API
 * aceita como entrada para `aviso_previo` (um `Interval`/`timedelta` no
 * backend). Um punhado de durações comuns cobre o caso normal sem exigir
 * um seletor de duração genérico, que seria complexidade desproporcional
 * para o v1. */
const OPCOES_DE_AVISO: { rotulo: string; segundos: number }[] = [
  { rotulo: "No momento do prazo", segundos: 0 },
  { rotulo: "15 minutos antes", segundos: 15 * 60 },
  { rotulo: "30 minutos antes", segundos: 30 * 60 },
  { rotulo: "1 hora antes", segundos: 60 * 60 },
  { rotulo: "1 dia antes", segundos: 24 * 60 * 60 },
];

interface Props {
  cartao: Cartao;
  quadroId: number;
  origemConexao?: string;
  aoFechar: () => void;
  aoAtualizar: (cartao: Cartao) => void;
  aoArquivar: (cartao: Cartao) => void;
}

/**
 * "O cartão aberto" da Etapa 7.4: título, descrição, prazo e aviso
 * prévio. A lição da Etapa 4 aplicada de propósito na interface: o campo
 * de data não é obrigatório e não deve PARECER obrigatório -- por isso
 * ele vem com um rótulo "(opcional)" explícito, um botão para remover um
 * prazo já definido, e o seletor de aviso só aparece depois que existe um
 * prazo para avisar sobre (não faz sentido escolher "1 hora antes" de
 * nada).
 */
export default function ModalDoCartao({ cartao, quadroId, origemConexao, aoFechar, aoAtualizar, aoArquivar }: Props) {
  const [titulo, setTitulo] = useState(cartao.titulo);
  const [descricao, setDescricao] = useState(cartao.descricao ?? "");
  const [prazoLocal, setPrazoLocal] = useState(isoParaDatetimeLocal(cartao.prazo));
  const [avisoSegundos, setAvisoSegundos] = useState<number>(
    cartao.aviso_previo ? duracaoIsoParaSegundos(cartao.aviso_previo) : 0
  );
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      const campos: CamposDoCartao = {
        titulo: titulo.trim() || cartao.titulo,
        descricao: descricao.trim() ? descricao.trim() : null,
        prazo: datetimeLocalParaIso(prazoLocal),
        // Sem prazo, um aviso não tem sobre o que avisar -- manda null
        // mesmo que o <select> tenha algum valor escolhido de antes.
        aviso_previo: prazoLocal ? avisoSegundos : null,
      };
      const atualizado = await cartoes.atualizar(quadroId, cartao.lista_id, cartao.id, campos, origemConexao);
      aoAtualizar(atualizado);
    } catch {
      setErro("Não foi possível salvar. Tente de novo.");
    } finally {
      setSalvando(false);
    }
  }

  async function arquivar() {
    const arquivado = await cartoes.arquivar(quadroId, cartao.lista_id, cartao.id, origemConexao);
    aoArquivar(arquivado);
  }

  function pararPropagacao(evento: MouseEvent) {
    evento.stopPropagation();
  }

  return (
    <div className="modal-fundo" onClick={aoFechar}>
      <form className="modal-cartao" onClick={pararPropagacao} onSubmit={salvar}>
        <div className="modal-cartao__cabecalho">
          <input
            className="modal-cartao__titulo"
            value={titulo}
            onChange={(evento) => setTitulo(evento.target.value)}
            placeholder="Título"
          />
          <button type="button" className="modal-cartao__fechar" onClick={aoFechar} aria-label="Fechar">
            ✕
          </button>
        </div>

        <label className="modal-cartao__campo">
          Descrição
          <textarea
            value={descricao}
            onChange={(evento) => setDescricao(evento.target.value)}
            rows={4}
            placeholder="Sem descrição"
          />
        </label>

        <label className="modal-cartao__campo">
          Prazo <span className="modal-cartao__opcional">(opcional — a maioria dos cartões não precisa de um)</span>
          <div className="modal-cartao__linha-prazo">
            <input
              type="datetime-local"
              value={prazoLocal}
              onChange={(evento) => setPrazoLocal(evento.target.value)}
            />
            {prazoLocal && (
              <button
                type="button"
                className="modal-cartao__remover-prazo"
                onClick={() => setPrazoLocal("")}
              >
                Remover
              </button>
            )}
          </div>
        </label>

        {prazoLocal && (
          <label className="modal-cartao__campo">
            Avisar
            <select value={avisoSegundos} onChange={(evento) => setAvisoSegundos(Number(evento.target.value))}>
              {OPCOES_DE_AVISO.map((opcao) => (
                <option key={opcao.rotulo} value={opcao.segundos}>
                  {opcao.rotulo}
                </option>
              ))}
            </select>
          </label>
        )}

        {erro && <p className="tela-login__erro">{erro}</p>}

        <div className="modal-cartao__rodape">
          <button type="button" className="botao-fantasma modal-cartao__arquivar" onClick={arquivar}>
            Arquivar cartão
          </button>
          <button type="submit" className="tela-login__botao" disabled={salvando}>
            {salvando ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </form>
    </div>
  );
}
